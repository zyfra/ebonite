import re
import os
from abc import abstractmethod
from contextlib import contextmanager
from threading import Lock
from typing import Dict, Generator

import docker
from docker.errors import DockerException

from pyjackson.core import Comparable
from pyjackson.decorators import type_field
from pyjackson.utils import get_class_field_names

from ebonite.build.provider import MLModelProvider
from ebonite.core.objects import Image, RuntimeEnvironment, RuntimeInstance, Model
from ebonite.runtime.server import Server
from ebonite.utils.log import logger

# TODO check
VALID_HOST_REGEX = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]).)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'


@type_field('type')
class DockerRegistry(Comparable):

    @abstractmethod
    def get_host(self) -> str:
        pass  # pragma: no cover


class DefaultDockerRegistry(DockerRegistry):
    """ The class represents docker registry.

    The default registry contains local images and images from the default registry (docker.io).

    """
    type = 'local'

    def get_host(self) -> str:
        return ''


class RemoteDockerRegistry(DockerRegistry):
    type = 'remote'

    def __init__(self, host: str):
        if re.match(VALID_HOST_REGEX, host):
            self.host = host
        else:
            raise ValueError('Host {} is not valid'.format(host))

    def get_host(self) -> str:
        return self.host


class DockerImage(Image.Params):
    def __init__(self, name: str, tag: str = 'latest',
                 repository: str = None, registry: DockerRegistry = None):
        self.name = name
        self.tag = tag
        self.repository = repository
        self.registry = registry or DefaultDockerRegistry()

    def get_uri(self) -> str:
        uri = '{}:{}'.format(self.name, self.tag)
        if self.repository is not None:
            uri = '{}/{}'.format(self.repository, uri)
        if isinstance(self.registry, RemoteDockerRegistry):
            uri = '{}/{}'.format(self.registry.get_host(), uri)
        return uri


class DockerContainer(RuntimeInstance.Params):
    def __init__(self, name: str, ports_mapping: Dict[int, int] = None):
        self.name = name
        self.ports_mapping = ports_mapping or {9000: 9000}


class DockerHost(RuntimeEnvironment.Params):
    def __init__(self, host: str = ''):
        self.host = host

    def get_runner(self):
        """
        :return: docker runner
        """
        if self.default_runner is None:
            from ebonite.build import DockerRunner
            self.default_runner = DockerRunner()
        return self.default_runner

    def get_builder(self, name: str, model: Model, server: Server, debug=False, **kwargs):
        """
        :param name: name for image
        :param model: model to build
        :param server: server to build
        :param debug: flag to build debug image
        :param kwargs: additional arguments for image parameters and docker builder

        :return: docker builder instance
        """
        from ebonite.build import DockerBuilder

        image_arg_names = set(get_class_field_names(DockerImage))
        params = DockerImage(name, **{k: v for k, v in kwargs.items() if k in image_arg_names})
        provider = MLModelProvider(model, server, debug)
        kwargs = {k: v for k, v in kwargs.items() if k not in image_arg_names}
        return DockerBuilder(provider, params, **kwargs)


def login_to_registry(client: docker.DockerClient, registry: DockerRegistry):
    """
    Logs in to Docker registry (if it is remote).

    Corresponding credentials should be specified as environment variables per registry:
    e.g., if registry host is "168.32.25.1:5000" then
    "168_32_25_1_5000_USERNAME" and "168_32_25_1_5000_PASSWORD" variables should be specified

    :param client: Docker client instance
    :param registry: Docker registry descriptor
    :return: nothing
    """
    if isinstance(registry, RemoteDockerRegistry):
        host_for_env = registry.host.replace('.', '_').replace(':', '_')
        username_var = f'{host_for_env}_username'.upper()
        username = os.getenv(username_var)
        password_var = f'{host_for_env}_password'.upper()
        password = os.getenv(password_var)

        if username and password:
            client.login(registry=registry.host, username=username, password=password)
            logger.info('Logged in to remote registry at host %s', registry.host)
        else:
            logger.warning('Skipped logging in to remote registry at host %s because no credentials given. ' +
                           'You could specify credentials as %s and %s environment variables.',
                           registry.host, username_var, password_var)


def _is_docker_running(client) -> bool:
    """
    Check if docker binary and docker daemon are available

    :param client: DockerClient instance
    :return: true or false
    """
    try:
        client.images.list()
        return True
    except (ImportError, IOError, DockerException):
        return False


def is_docker_running() -> bool:
    """
    Check if docker binary and docker daemon are available

    :return: true or false
    """
    with create_docker_client(check=False) as c:
        return _is_docker_running(c)


_docker_host_lock = Lock()


@contextmanager
def create_docker_client(docker_host: str = '', check=True) -> Generator[docker.DockerClient, None, None]:
    """
    Context manager for DockerClient creation

    :param docker_host: DOCKER_HOST arg for DockerClient
    :param check: check if docker is available
    :return: DockerClient instance
    """
    with _docker_host_lock:
        os.environ["DOCKER_HOST"] = docker_host  # The env var DOCKER_HOST is used to configure docker.from_env()
        client = docker.from_env()
    if check and not _is_docker_running(client):
        raise RuntimeError("Docker daemon is unavailable")
    try:
        yield client
    finally:
        client.close()
