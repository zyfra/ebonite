import logging
import os
import tempfile

from typing import Dict

from docker import errors

from jinja2 import Environment, FileSystemLoader

from ebonite.build.builder.base import PythonBuilder, ebonite_from_pip
from ebonite.build.docker import DockerImage, RemoteDockerRegistry, create_docker_client, login_to_registry
from ebonite.build.provider.base import PythonProvider
from ebonite.core.objects import Image
from ebonite.utils.log import logger
from ebonite.utils.module import get_python_version

TEMPLATE_FILE = 'dockerfile.j2'

EBONITE_INSTALL_COMMAND = 'pip install ebonite=={version}'


def _print_docker_logs(logs, level=logging.DEBUG):
    for l in logs:
        if 'stream' in l:
            logger.log(level, l['stream'])
        else:
            logger.log(level, l)


class DockerBuilder(PythonBuilder):
    """
    PythonBuilder implementation for building docker containers

    `kwargs` possible keys:

    - `base_image` - base image for the built image, default: python:{python_version}
    - `python_version` - Python version to use, default: version of running interpreter
    - `templates_dir` - directory for Dockerfile templates, default: ./docker_templates
       - `pre_install.j2` - Dockerfile commands to run before pip
       - `post_install.j2` - Dockerfile commands to run after pip
       - `post_copy.j2` - Dockerfile commands to run after pip and Ebonite distribution copy
    - `run_cmd` - command to run in container, default: sh run.sh

    :param provider: PythonProvider instance
    :param params: params for docker image to be built
    :param force_overwrite: if false, raise error if image already exists
    """

    def __init__(self, provider: PythonProvider, params: DockerImage, force_overwrite=False, **kwargs):
        super().__init__(provider)
        self.params = params
        self.force_overwrite = force_overwrite

        kwargs.update(provider.get_options())
        kwargs = {k: v for k, v in kwargs.items() if k in
                  {'base_image', 'python_version', 'templates_dir', 'run_cmd'}}
        kwargs['python_version'] = kwargs.get('python_version', provider.get_python_version())
        self.dockerfile_gen = _DockerfileGenerator(**kwargs)

    def build(self) -> Image:
        with tempfile.TemporaryDirectory(prefix='ebonite_build_') as tempdir:
            self._write_distribution(tempdir)
            return self._build_image(tempdir)

    def _write_distribution(self, target_dir):
        super()._write_distribution(target_dir)

        logger.debug('Putting Dockerfile to distribution...')
        env = self.provider.get_env()
        logger.debug('Determined environment for running model: %s.', env)
        with open(os.path.join(target_dir, 'Dockerfile'), 'w') as df:
            dockerfile = self.dockerfile_gen.generate(env)
            df.write(dockerfile)

    def _build_image(self, context_dir):
        tag = self.params.get_uri()
        logger.debug('Building docker image %s from %s...', tag, context_dir)
        with create_docker_client() as client:
            login_to_registry(client, self.params.registry)

            if not self.force_overwrite:
                try:
                    client.images.get(tag)
                    raise ValueError(f'Image {tag} already exists. Change name or set force_overwrite=True.')
                except errors.ImageNotFound:
                    pass
            else:
                try:
                    client.images.remove(tag)  # to avoid spawning dangling images
                except errors.ImageNotFound:
                    pass
            try:
                _, logs = client.images.build(path=context_dir, tag=tag, rm=True)
                logger.info('Built image %s', tag)
                _print_docker_logs(logs)

                if isinstance(self.params.registry, RemoteDockerRegistry):
                    client.images.push(tag)
                    logger.info('Pushed image %s to remote registry at host %s', tag, self.params.registry.host)

                return Image(tag, params=self.params)
            except errors.BuildError as e:
                _print_docker_logs(e.build_log, logging.ERROR)
                raise


class _DockerfileGenerator:
    """
    Class to generate Dockerfile

    :param base_image:  base image for the built image, default: python:{python_version}
    :param python_version: Python version to use, default: version of running interpreter
    :param templates_dir: directory for Dockerfile templates, default: ./docker_templates
       - `pre_install.j2` - Dockerfile commands to run before pip
       - `post_install.j2` - Dockerfile commands to run after pip
       - `post_copy.j2` - Dockerfile commands to run after pip and Ebonite distribution copy
    :param run_cmd: command to run in container, default: sh run.sh
    """

    def __init__(self, base_image=None, python_version=None, templates_dir=None, run_cmd='sh run.sh'):
        self.python_version = python_version or get_python_version()
        self.base_image = base_image or f'python:{self.python_version}-slim'
        self.templates_dir = templates_dir or os.path.join(os.getcwd(), 'docker_templates')
        self.run_cmd = run_cmd

    def generate(self, env: Dict[str, str]):
        """Generate Dockerfile using provided base image, python version and run_cmd"""
        logger.debug('Generating Dockerfile via templates from "%s"...', self.templates_dir)
        j2 = Environment(loader=FileSystemLoader([
            os.path.dirname(__file__),
            self.templates_dir
        ]))
        docker_tmpl = j2.get_template(TEMPLATE_FILE)

        logger.debug('Docker image is using Python version: %s.', self.python_version)
        logger.debug('Docker image is based on "%s".', self.base_image)

        docker_args = {
            'python_version': self.python_version,
            'base_image': self.base_image,
            'run_cmd': self.run_cmd,
            'ebonite_install': '',
            'env': env
        }
        if ebonite_from_pip():
            import ebonite
            docker_args['ebonite_install'] = 'RUN ' + EBONITE_INSTALL_COMMAND.format(version=ebonite.__version__)

        return docker_tmpl.render(**docker_args)
