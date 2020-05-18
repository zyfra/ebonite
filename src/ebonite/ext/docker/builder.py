import logging
import os
import tempfile
from typing import Dict, List

import docker.models.images
from docker import errors
from jinja2 import Environment, FileSystemLoader

from ebonite.build.builder.base import BuilderBase, PythonBuildContext, ebonite_from_pip
from ebonite.build.provider import PythonProvider
from ebonite.core.objects import Image
from ebonite.core.objects.core import Buildable
from ebonite.core.objects.requirements import UnixPackageRequirement
from ebonite.ext.docker.helpers import create_docker_client, login_to_registry
from ebonite.utils.log import logger
from ebonite.utils.module import get_python_version

from .base import DockerEnv, DockerImage, DockerRegistry

TEMPLATE_FILE = 'dockerfile.j2'

EBONITE_INSTALL_COMMAND = 'pip install ebonite=={version}'


def _print_docker_logs(logs, level=logging.DEBUG):
    for log in logs:
        if 'stream' in log:
            logger.log(level, str(log['stream']).strip())
        else:
            logger.log(level, str(log).strip())


class DockerBuilder(BuilderBase):
    def create_image(self, name: str, tag: str = 'latest', repository: str = None, **kwargs) -> Image.Params:
        return DockerImage(name, tag, repository)

    def build_image(self, buildable: Buildable, image: DockerImage, environment: DockerEnv,
                    force_overwrite=False, **kwargs):
        context = DockerBuildContext(buildable.get_provider(), image, force_overwrite=force_overwrite, **kwargs)
        docker_image = context.build(environment.registry)
        image.image_id = docker_image.id

    def delete_image(self, image: DockerImage, environment: DockerEnv, **kwargs):
        with create_docker_client() as client:
            client.images.remove(image.name)

    def image_exists(self, image: DockerImage, environment: DockerEnv, **kwargs) -> bool:
        with create_docker_client() as client:
            try:
                client.images.get(image.name)
                return True
            except docker.errors.ImageNotFound:
                return False


class DockerBuildContext(PythonBuildContext):
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
        self.prebuild_hook = kwargs.get('prebuild_hook', None)

        options = {'python_version': self.provider.get_python_version()}
        options.update(self.provider.get_options())
        options.update(kwargs)
        options = {k: v for k, v in options.items() if k in
                   {'base_image', 'python_version', 'templates_dir', 'run_cmd', 'package_install_cmd'}}
        self.dockerfile_gen = _DockerfileGenerator(**options)

    def build(self, registry: DockerRegistry) -> docker.models.images.Image:
        with tempfile.TemporaryDirectory(prefix='ebonite_build_') as tempdir:
            if self.prebuild_hook is not None:
                self.prebuild_hook(self.dockerfile_gen.python_version)
            self._write_distribution(tempdir)
            return self._build_image(tempdir, registry)

    def _write_distribution(self, target_dir):
        super()._write_distribution(target_dir)

        logger.debug('Putting Dockerfile to distribution...')
        env = self.provider.get_env()
        logger.debug('Determined environment for running model: %s.', env)
        with open(os.path.join(target_dir, 'Dockerfile'), 'w') as df:
            unix_packages = self.provider.get_requirements().of_type(UnixPackageRequirement)
            dockerfile = self.dockerfile_gen.generate(env, unix_packages)
            df.write(dockerfile)

    def _build_image(self, context_dir, registry: DockerRegistry) -> docker.models.images.Image:
        tag = self.params.get_uri(registry)
        logger.debug('Building docker image %s from %s...', tag, context_dir)
        with create_docker_client() as client:
            login_to_registry(client, registry)

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
                image, logs = client.images.build(path=context_dir, tag=tag, rm=True)
                logger.info('Built docker image %s', tag)
                _print_docker_logs(logs)

                registry.push(client, tag)

                return image
            except errors.BuildError as e:
                _print_docker_logs(e.build_log, logging.ERROR)
                raise


class _DockerfileGenerator:
    """
    Class to generate Dockerfile

    :param base_image:  base image for the built image in form of a string or function from python version,
      default: python:{python_version}
    :param python_version: Python version to use, default: version of running interpreter
    :param templates_dir: directory for Dockerfile templates, default: ./docker_templates
       - `pre_install.j2` - Dockerfile commands to run before pip
       - `post_install.j2` - Dockerfile commands to run after pip
       - `post_copy.j2` - Dockerfile commands to run after pip and Ebonite distribution copy
    :param run_cmd: command to run in container, default: sh run.sh
    """

    def __init__(self, base_image=None, python_version=None, templates_dir=None,
                 package_install_cmd='apt-get install -y', run_cmd='sh run.sh'):
        self.python_version = python_version or get_python_version()
        if callable(base_image):
            base_image = base_image(self.python_version)
        self.base_image = base_image or f'python:{self.python_version}-slim'
        self.templates_dir = templates_dir or os.path.join(os.getcwd(), 'docker_templates')
        self.run_cmd = run_cmd
        self.package_install_cmd = package_install_cmd

    def generate(self, env: Dict[str, str], packages: List[UnixPackageRequirement] = None):
        """Generate Dockerfile using provided base image, python version and run_cmd

        :param env: dict with environmental variables
        :param packages: list of unix packages to install
        """
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
            'env': env,
            'package_install_cmd': self.package_install_cmd,
            'packages': [p.package_name for p in packages or []]
        }
        if ebonite_from_pip():
            import ebonite
            docker_args['ebonite_install'] = 'RUN ' + EBONITE_INSTALL_COMMAND.format(version=ebonite.__version__)

        return docker_tmpl.render(**docker_args)
