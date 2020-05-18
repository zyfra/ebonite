from abc import abstractmethod
from typing import Dict

from pyjackson.core import Comparable
from pyjackson.decorators import type_field

from ebonite.core.objects import Image, RuntimeEnvironment, RuntimeInstance
from ebonite.utils.log import logger


@type_field('type')
class DockerRegistry(Comparable):

    @abstractmethod
    def get_host(self) -> str:
        pass  # pragma: no cover

    def push(self, client, tag):
        pass


class DefaultDockerRegistry(DockerRegistry):
    """ The class represents docker registry.

    The default registry contains local images and images from the default registry (docker.io).

    """
    type = 'local'

    def get_host(self) -> str:
        return ''


class RemoteDockerRegistry(DockerRegistry):
    type = 'remote'

    def __init__(self, host: str = None):
        self.host = host or 'https://index.docker.io/v1/'

    def get_host(self) -> str:
        return self.host

    def push(self, client, tag):
        client.images.push(tag)
        logger.info('Pushed image %s to remote registry at host %s', tag, self.host)


@type_field('type')
class DockerDaemon(Comparable):
    def __init__(self, host: str):  # TODO credentials
        self.host = host


class DockerImage(Image.Params):
    def __init__(self, name: str, tag: str = 'latest', repository: str = None, image_id: str = None):
        self.repository = repository
        self.image_id = image_id
        self.name = name
        self.tag = tag

    def get_uri(self, registry: DockerRegistry) -> str:
        uri = '{}:{}'.format(self.name, self.tag)
        if self.repository is not None:
            uri = '{}/{}'.format(self.repository, uri)
        if isinstance(registry, RemoteDockerRegistry):
            uri = '{}/{}'.format(registry.get_host(), uri)
        return uri


class DockerContainer(RuntimeInstance.Params):
    def __init__(self, name: str, ports_mapping: Dict[int, int] = None, params: Dict[str, object] = None,
                 container_id: str = None):
        self.container_id = container_id
        self.name = name
        self.ports_mapping = ports_mapping or {}
        self.params = params or {}


class DockerEnv(RuntimeEnvironment.Params):
    def __init__(self, registry: DockerRegistry = None, daemon: DockerDaemon = None):
        self.registry = registry or DefaultDockerRegistry()
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
