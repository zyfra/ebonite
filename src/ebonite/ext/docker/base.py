import contextlib
import os
from typing import Dict

import docker
import docker.errors
import requests
from pyjackson.core import Comparable
from pyjackson.decorators import type_field

from ebonite.core.objects import Image, RuntimeEnvironment, RuntimeInstance
from ebonite.ext.docker.utils import create_docker_client, image_exists_at_dockerhub
from ebonite.utils.log import logger


@type_field('type')
class DockerRegistry(Comparable):
    """Registry for docker images. This is the default implementation that represents registry of the docker daemon"""

    def get_host(self) -> str:
        """Returns registry host or emty string for local"""
        return ''

    def push(self, client: docker.DockerClient, tag: str):
        """Pushes image to registry

        :param client: DockerClient to use
        :param tag: name of the tag to push"""

    def login(self, client: docker.DockerClient):
        """Login to registry

        :param client: DockerClient to use"""

    def uri(self, image: str):
        """Cretate an uri for image in this registry

        :param image: image name"""
        return image

    def image_exists(self, client: docker.DockerClient, image: 'DockerImage'):
        """Check if image exists in this registry

        :param client: DockerClient to use
        :param image: :class:`.DockerImage` to check"""
        try:
            client.images.get(image.uri)
            return True
        except docker.errors.ImageNotFound:
            return False

    def delete_image(self, client: docker.DockerClient, image: 'DockerImage', force: bool = False, **kwargs):
        """Deleta image from this registry

        :param client: DockerClient to use
        :param image: :class:`.DockerImage` to delete
        :param force: force delete
        """
        try:
            client.images.remove(image.uri, force=force, **kwargs)
        except docker.errors.ImageNotFound:
            pass


class DockerIORegistry(DockerRegistry):
    """ The class represents docker.io registry.

    """

    def get_host(self) -> str:
        return 'https://index.docker.io/v1/'

    def push(self, client, tag):
        client.images.push(tag)
        logger.info('Pushed image %s to docker.io', tag)

    def image_exists(self, client, image: 'DockerImage'):
        return image_exists_at_dockerhub(image.uri)

    def delete_image(self, client, image: 'DockerImage', force=False, **kwargs):
        logger.warn('Skipping deleting image %s from docker.io', image.name, force, **kwargs)


class RemoteRegistry(DockerRegistry):
    """DockerRegistry implementation for official Docker Registry (as in https://docs.docker.com/registry/)

    :param host: adress of the registry"""

    def __init__(self, host: str = None):
        self.host = host  # TODO credentials?

    def login(self, client):
        """
        Logs in to Docker registry

        Corresponding credentials should be specified as environment variables per registry:
        e.g., if registry host is "168.32.25.1:5000" then
        "168_32_25_1_5000_USERNAME" and "168_32_25_1_5000_PASSWORD" variables should be specified

        :param client: Docker client instance
        :return: nothing
        """

        host_for_env = self.host.replace('.', '_').replace(':', '_')
        username_var = f'{host_for_env}_username'.upper()
        username = os.getenv(username_var)
        password_var = f'{host_for_env}_password'.upper()
        password = os.getenv(password_var)

        if username and password:
            client.login(registry=self.host, username=username, password=password)
            logger.info('Logged in to remote registry at host %s', self.host)
        else:
            logger.warning('Skipped logging in to remote registry at host %s because no credentials given. ' +
                           'You could specify credentials as %s and %s environment variables.',
                           self.host, username_var, password_var)

    def get_host(self) -> str:
        return self.host

    def push(self, client, tag):
        client.images.push(tag)
        logger.info('Pushed image %s to remote registry at host %s', tag, self.host)

    def uri(self, image: str):
        return f'{self.host}/{image}'

    def _get_digest(self, name, tag):
        r = requests.head(f'http://{self.host}/v2/{name}/manifests/{tag}',
                          headers={'Accept': 'application/vnd.docker.distribution.manifest.v2+json'})
        if r.status_code != 200:
            return
        return r.headers['Docker-Content-Digest']

    def image_exists(self, client, image: 'DockerImage'):
        name = image.fullname
        digest = self._get_digest(name, image.tag)
        if digest is None:
            return False
        r = requests.head(f'http://{self.host}/v2/{name}/manifests/{digest}')
        if r.status_code == 404:
            return False
        elif r.status_code == 200:
            return True
        r.raise_for_status()

    def delete_image(self, client, image: 'DockerImage', force=False, **kwargs):
        name = image.fullname
        digest = self._get_digest(name, image.tag)
        if digest is None:
            return
        requests.delete(f'http://{self.host}/v2/{name}/manifests/{digest}')


@type_field('type')
class DockerDaemon(Comparable):
    """Class that represents docker daemon

    :param host: adress of the docker daemon (empty string for local)"""

    def __init__(self, host: str):  # TODO credentials
        self.host = host

    @contextlib.contextmanager
    def client(self) -> docker.DockerClient:
        """Get DockerClient isntance"""
        with create_docker_client(self.host) as c:
            yield c


class DockerImage(Image.Params):
    """:class:`.Image.Params` implementation for docker images
    full uri for image looks like registry.host/repository/name:tag

    :param name: name of the image
    :param tag: tag of the image
    :param repository: repository of the image
    :param registry: :class:`.DockerRegistry` instance with this image
    :param image_id: docker internal id of this image"""

    def __init__(self, name: str, tag: str = 'latest', repository: str = None, registry: DockerRegistry = None,
                 image_id: str = None):
        self.repository = repository
        self.image_id = image_id
        self.name = name
        self.tag = tag
        self.registry = registry or DockerRegistry()

    @property
    def fullname(self):
        return f'{self.repository}/{self.name}' if self.repository is not None else self.name

    @property
    def uri(self) -> str:
        return self.registry.uri(f'{self.fullname}:{self.tag}')

    def exists(self, client: docker.DockerClient):
        """Checks if this image exists in it's registry"""
        return self.registry.image_exists(client, self)

    def delete(self, client: docker.DockerClient, force=False, **kwargs):
        """Deletes image from registry"""
        self.registry.delete_image(client, self, force, **kwargs)


class DockerContainer(RuntimeInstance.Params):
    """:class:`.RuntimeInstance.Params` implementation for docker containers

    :param name: name of the container
    :param port_mapping: port mapping in this container
    :param params: other parameters for docker run cmd
    :param container_id: internal docker id for this container"""

    def __init__(self, name: str, port_mapping: Dict[int, int] = None, params: Dict[str, object] = None,
                 container_id: str = None):
        self.container_id = container_id
        self.name = name
        self.port_mapping = port_mapping or {}
        self.params = params or {}


class DockerEnv(RuntimeEnvironment.Params):
    """:class:`.RuntimeEnvironment.Params` implementation for docker environment

    :param registry: default registry to push images to
    :param daemon: :class:`.DockerDaemon` instance"""

    def __init__(self, registry: DockerRegistry = None, daemon: DockerDaemon = None):
        self.registry = registry or DockerRegistry()
        self.daemon = daemon or DockerDaemon('')

    def get_runner(self):
        """
        :return: docker runner
        """
        if self.default_runner is None:
            from .runner import DockerRunner
            self.default_runner = DockerRunner()
        return self.default_runner

    def get_builder(self):
        """
        :return: docker builder instance
        """
        if self.default_builder is None:
            from .builder import DockerBuilder
            self.default_builder = DockerBuilder()
        return self.default_builder
