import logging
import os
import tempfile
from typing import Any, Callable, Dict, List, Union

import docker.models.images
from docker import errors
from jinja2 import Environment, FileSystemLoader
from pyjackson.utils import get_class_fields

from ebonite.build.builder.base import PythonBuildContext, ebonite_from_pip
from ebonite.build.provider import PythonProvider
from ebonite.core.objects.requirements import UnixPackageRequirement
from ebonite.utils.log import logger
from ebonite.utils.module import get_python_version

from .base import DockerEnv, DockerImage

TEMPLATE_FILE = 'dockerfile.j2'

EBONITE_INSTALL_COMMAND = 'pip install ebonite=={version}'


def _print_docker_logs(logs, level=logging.DEBUG):
    for log in logs:
        if 'stream' in log:
            logger.log(level, str(log['stream']).strip())
        else:
            logger.log(level, str(log).strip())


class DockerBuildArgs:
    """
    Container for DockerBuild arguments

    :param base_image:  base image for the built image in form of a string or function from python version,
      default: python:{python_version}
    :param python_version: Python version to use, default: version of running interpreter
    :param templates_dir: directory or list of directories for Dockerfile templates, default: ./docker_templates
       - `pre_install.j2` - Dockerfile commands to run before pip
       - `post_install.j2` - Dockerfile commands to run after pip
       - `post_copy.j2` - Dockerfile commands to run after pip and Ebonite distribution copy
    :param run_cmd: command to run in container, default: sh run.sh
    :param package_install_cmd: command to install packages. Default is apt-get, change it for other package manager
    :param prebuild_hook: callable to call before build, accepts python version. Used for pre-building server images
    """

    def __init__(self, base_image: Union[str, Callable[[str], str]] = None,
                 python_version: str = None, templates_dir: Union[str, List[str]] = None,
                 run_cmd: Union[bool, str] = None, package_install_cmd: str = None,
                 prebuild_hook: Callable[[str], Any] = None):
        self._prebuild_hook = prebuild_hook
        self._package_install_cmd = package_install_cmd
        self._run_cmd = run_cmd
        self._base_image = base_image
        self._python_version = python_version
        self._templates_dir = [] if templates_dir is None else (
            templates_dir if isinstance(templates_dir, list) else [templates_dir])

    @property
    def prebuild_hook(self):
        return self._prebuild_hook

    @property
    def templates_dir(self):
        return self._templates_dir or [os.path.join(os.getcwd(), 'docker_templates')]

    @property
    def package_install_cmd(self):
        return self._package_install_cmd or 'apt-get install -y'

    @property
    def run_cmd(self):
        return self._run_cmd if self._run_cmd is not None else 'sh run.sh'

    @property
    def python_version(self):
        return self._python_version or get_python_version()

    @property
    def base_image(self):
        if self._base_image is None:
            return f'python:{self.python_version}-slim'
        return self._base_image if isinstance(self._base_image, str) else self._base_image(self.python_version)

    def update(self, other: 'DockerBuildArgs'):
        for field in get_class_fields(DockerBuildArgs):
            if field.name == 'templates_dir':
                self._templates_dir += other._templates_dir
            else:
                value = getattr(other, f'_{field.name}')
                if value is not None:
                    setattr(self, f'_{field.name}', value)


class DockerBuildContext(PythonBuildContext):
    """
    PythonBuilder implementation for building docker containers

    :param provider: PythonProvider instance
    :param params: params for docker image to be built
    :param force_overwrite: if false, raise error if image already exists
    :param kwargs: for possible keys, look at :class:`.DockerBuildArgs`
    """

    def __init__(self, provider: PythonProvider, params: DockerImage, force_overwrite=False, **kwargs):
        super().__init__(provider)
        self.params = params
        self.force_overwrite = force_overwrite

        self.args = DockerBuildArgs(python_version=self.provider.get_python_version())

        options = self.provider.get_options()
        if 'docker' in options:
            self.args.update(DockerBuildArgs(**options['docker']))
        self.args.update(DockerBuildArgs(**kwargs))
        self.dockerfile_gen = _DockerfileGenerator(self.args)

    def build(self, env: DockerEnv) -> docker.models.images.Image:
        with tempfile.TemporaryDirectory(prefix='ebonite_build_') as tempdir:
            if self.args.prebuild_hook is not None:
                self.args.prebuild_hook(self.args.python_version)
            self._write_distribution(tempdir)
            return self._build_image(tempdir, env)

    def _write_distribution(self, target_dir):
        super()._write_distribution(target_dir)

        logger.debug('Putting Dockerfile to distribution...')
        env = self.provider.get_env()
        logger.debug('Determined environment for running model: %s.', env)
        with open(os.path.join(target_dir, 'Dockerfile'), 'w') as df:
            unix_packages = self.provider.get_requirements().of_type(UnixPackageRequirement)
            dockerfile = self.dockerfile_gen.generate(env, unix_packages)
            df.write(dockerfile)

    def _build_image(self, context_dir, env: DockerEnv) -> docker.models.images.Image:
        tag = self.params.uri
        logger.debug('Building docker image %s from %s...', tag, context_dir)
        with env.daemon.client() as client:
            self.params.registry.login(client)

            if not self.force_overwrite:
                if self.params.exists(client):
                    raise ValueError(f'Image {tag} already exists at {self.params.registry}. '
                                     f'Change name or set force_overwrite=True.')

            else:
                self.params.delete(client)  # to avoid spawning dangling images
            try:
                image, logs = client.images.build(path=context_dir, tag=tag, rm=True)
                logger.info('Built docker image %s', tag)
                _print_docker_logs(logs)

                self.params.registry.push(client, tag)

                return image
            except errors.BuildError as e:
                _print_docker_logs(e.build_log, logging.ERROR)
                raise


class _DockerfileGenerator:
    """
    Class to generate Dockerfile

    :param args: DockerBuildArgs instance
    """

    def __init__(self, args: DockerBuildArgs):
        self.python_version = args.python_version
        self.base_image = args.base_image
        self.templates_dir = args.templates_dir
        self.run_cmd = args.run_cmd
        self.package_install_cmd = args.package_install_cmd

    def generate(self, env: Dict[str, str], packages: List[UnixPackageRequirement] = None):
        """Generate Dockerfile using provided base image, python version and run_cmd

        :param env: dict with environmental variables
        :param packages: list of unix packages to install
        """
        logger.debug('Generating Dockerfile via templates from "%s"...', self.templates_dir)
        j2 = Environment(loader=FileSystemLoader([os.path.dirname(__file__)] + self.templates_dir))
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
        ebonite_pip = ebonite_from_pip()
        if ebonite_pip is True:
            import ebonite
            docker_args['ebonite_install'] = 'RUN ' + EBONITE_INSTALL_COMMAND.format(version=ebonite.__version__)
        elif isinstance(ebonite_pip, str):
            docker_args['ebonite_install'] = f"COPY {os.path.basename(ebonite_pip)} . " \
                                             f"\n RUN pip install {os.path.basename(ebonite_pip)}"

        return docker_tmpl.render(**docker_args)
