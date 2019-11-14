import os
import subprocess
import tempfile
from contextlib import contextmanager
from threading import Lock

import docker
import requests
from docker import errors

from jinja2 import Environment, FileSystemLoader

from ebonite.build.builder.base import PythonBuilder, ebonite_from_pip
from ebonite.build.provider.base import PythonProvider
from ebonite.utils.log import logger

TEMPLATE_FILE = 'dockerfile.j2'


EBONITE_INSTALL_COMMAND = 'pip install ebonite=={version}'


def is_docker_running():
    """
    Check if docker binary and docker daemon are available

    :return: true or false
    """
    try:
        subprocess.check_output('which docker', shell=True)
        with create_docker_client() as client:
            client.images.list()
        return True
    except (subprocess.CalledProcessError, ImportError, requests.exceptions.ConnectionError):
        return False


_docker_host_lock = Lock()


@contextmanager
def create_docker_client(docker_host: str = '') -> docker.DockerClient:
    """
    Context manager for DockerClient creation

    :param docker_host: DOCKER_HOST arg for DockerClient
    :return: DockerClient instance
    """
    with _docker_host_lock:
        os.environ["DOCKER_HOST"] = docker_host  # The env var DOCKER_HOST is used to configure docker.from_env()
        client = docker.from_env()
    try:
        yield client
    finally:
        client.close()


def _print_docker_logs(logs):
    for l in logs:
        if 'stream' in l:
            logger.debug(l['stream'])
        else:
            logger.debug(l)


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
    :param name: name for docker image
    :param tag: tag for docker image
    :param force_overwrite: if false, raise error if image already exists
    """
    def __init__(self, provider: PythonProvider, name: str, tag: str = 'latest', force_overwrite=False, **kwargs):
        super().__init__(provider)
        self.name = name
        self.tag = tag
        self.force_overwrite = force_overwrite
        self.dockerfile_gen = _DockerfileGenerator(**kwargs)

    def build(self):
        with tempfile.TemporaryDirectory(prefix='ebonite_build_') as tempdir:
            self._write_distribution(tempdir)
            self._build_image(tempdir)

    def _write_distribution(self, target_dir):
        super()._write_distribution(target_dir)

        logger.debug('Putting Dockerfile to distribution...')
        with open(os.path.join(target_dir, 'Dockerfile'), 'w') as df:
            dockerfile = self.dockerfile_gen.generate()
            df.write(dockerfile)

    def _build_image(self, context_dir):
        tag = '{}:{}'.format(self.name, self.tag)
        logger.debug('Building docker image %s from %s...', tag, context_dir)
        with create_docker_client() as client:
            if not self.force_overwrite:
                try:
                    client.images.get(tag)
                    raise ValueError(f'Image {tag} already exists. Change name or set force_overwrite=True.')
                except errors.ImageNotFound:
                    pass

            try:
                _, logs = client.images.build(path=context_dir, tag=tag)
                logger.info('Build successful')
                _print_docker_logs(logs)
            except errors.BuildError as e:
                _print_docker_logs(e.build_log)
                raise


class _DockerfileGenerator:
    """
    Class to generate Dockerfile

    `kwargs` possible keys:

    - `base_image` - base image for the built image, default: python:{python_version}
    - `python_version` - Python version to use, default: version of running interpreter
    - `templates_dir` - directory for Dockerfile templates, default: ./docker_templates
       - `pre_install.j2` - Dockerfile commands to run before pip
       - `post_install.j2` - Dockerfile commands to run after pip
       - `post_copy.j2` - Dockerfile commands to run after pip and Ebonite distribution copy
    - `run_cmd` - command to run in container, default: sh run.sh
    """
    def __init__(self, **kwargs):
        self.kwargs = kwargs

        valid_keys = {'base_image', 'python_version', 'templates_dir', 'run_cmd'}
        if self.kwargs.keys() - valid_keys:
            raise ValueError(f'DockerBuilder accepts {valid_keys} only as kwargs, {self.kwargs.keys()} given')

    def generate(self):
        """Generate Dockerfile using provided base image, python version and run_cmd"""
        templates_dir = self._resolve_property('templates_dir', os.path.join(os.getcwd(), 'docker_templates'))
        logger.debug('Generating Dockerfile via templates from "%s"...', templates_dir)
        j2 = Environment(loader=FileSystemLoader([
            os.path.dirname(__file__),
            templates_dir
        ]))
        docker_tmpl = j2.get_template(TEMPLATE_FILE)

        python_version = self._resolve_property('python_version', PythonProvider.get_python_version())
        logger.debug('Docker image is using Python version: %s.', python_version)
        base_image = self._resolve_property('base_image', 'python:{}'.format(python_version))
        logger.debug('Docker image is based on "%s".', base_image)

        docker_args = {
            'python_version': python_version,
            'base_image': base_image,
            'run_cmd': self._resolve_property('run_cmd', 'sh run.sh'),
            'ebonite_install': ''
        }
        if ebonite_from_pip():
            import ebonite
            docker_args['ebonite_install'] = 'RUN ' + EBONITE_INSTALL_COMMAND.format(version=ebonite.__version__)

        return docker_tmpl.render(**docker_args)

    def _resolve_property(self, name, default):
        if name in self.kwargs:
            return self.kwargs[name]
        else:
            return os.getenv('EBONITE_DOCKER_' + name.upper(), default)
