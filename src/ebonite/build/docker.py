import re
import os
from abc import abstractmethod
from contextlib import contextmanager
from threading import Lock
from typing import Generator

import docker
import requests
from docker import errors

from pyjackson.decorators import type_field
from pyjackson.deserialization import deserialize
from pyjackson.serialization import serialize

from ebonite.core.objects import core
from ebonite.utils.log import logger


# TODO check
VALID_HOST_REGEX = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]).)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'


@type_field('type')
class DockerRegistry:

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


class DockerImage:
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

    def to_core_image(self) -> 'core.Image':
        return core.Image(self.get_uri(), params=serialize(self))

    @staticmethod
    def from_core_image(image: 'core.Image') -> 'DockerImage':
        return deserialize(image.params, DockerImage)


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


def is_docker_running() -> bool:
    """
    Check if docker binary and docker daemon are available

    :return: true or false
    """
    try:
        with create_docker_client() as client:
            client.images.list()
        return True
    except (ImportError, requests.exceptions.ConnectionError, errors.DockerException):
        return False


_docker_host_lock = Lock()


@contextmanager
def create_docker_client(docker_host: str = '') -> Generator[docker.DockerClient, None, None]:
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
