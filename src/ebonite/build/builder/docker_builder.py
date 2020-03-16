import logging
import os
import tempfile
from contextlib import contextmanager
from threading import Lock
from typing import Dict

import docker
import requests
from docker import errors

from jinja2 import Environment, FileSystemLoader

from ebonite.build.builder.base import PythonBuilder, ebonite_from_pip
from ebonite.build.docker_objects import DockerImage
from ebonite.build.provider.base import PythonProvider
from ebonite.core.objects import core
from ebonite.utils.log import logger
from ebonite.utils.module import get_python_version

TEMPLATE_FILE = 'dockerfile.j2'

EBONITE_INSTALL_COMMAND = 'pip install ebonite=={version}'


def is_docker_running():
    """
    Check if docker binary and docker daemon are available

    :return: true or false
    """
    try:
        with create_docker_client() as client:
            client.images.list()
        return True
    except (ImportError, requests.exceptions.ConnectionError, docker.errors.DockerException):
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

        kwargs = {k: v for k, v in kwargs.items() if k in
                  {'base_image', 'python_version', 'templates_dir', 'run_cmd'}}
        kwargs['python_version'] = kwargs.get('python_version', provider.get_python_version())
        self.dockerfile_gen = _DockerfileGenerator(**kwargs)

    def build(self) -> 'core.Image':
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
        tag = '{}:{}'.format(self.params.name, self.params.tag)
        logger.debug('Building docker image %s from %s...', tag, context_dir)
        with create_docker_client() as client:
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
                logger.info('Build successful')
                _print_docker_logs(logs)
                return self.params.to_core_image()
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
