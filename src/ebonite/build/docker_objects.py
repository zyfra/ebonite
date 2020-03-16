import re
from abc import abstractmethod

from pyjackson.decorators import type_field
from pyjackson.deserialization import deserialize
from pyjackson.serialization import serialize

from ebonite.core.objects import core


# TODO check
VALID_HOST_REGEX = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]).)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'


@type_field('type')
class DockerRegistry:

    @abstractmethod
    def get_host(self) -> str:
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

    def __init__(self, host: str, username: str = None, password: str = None):
        if re.match(VALID_HOST_REGEX, host):
            self.host = host
        else:
            raise ValueError('Host {} is not valid'.format(host))
        self.username = username
        self.password = password

    def get_host(self) -> str:
        return self.host


class DockerImage:
    def __init__(self, name: str, tag: str = 'latest',
                 repository: str = None, registry: DockerRegistry = None):
        self.name = name
        self.tag = tag
        self.repository = repository
        self.registry = registry or DefaultDockerRegistry()

    def get_image_uri(self) -> str:
        image = '{}:{}'.format(self.name, self.tag)
        if self.repository is not None:
            image = '{}/{}'.format(self.repository, image)
        if self.registry.get_host():
            image = '{}/{}'.format(self.registry.get_host(), image)
        return image

    def to_core_image(self) -> 'core.Image':
        return core.Image(self.get_image_uri(), params=serialize(self))

    @staticmethod
    def from_core_image(image: 'core.Image') -> 'DockerImage':
        return deserialize(image.params, DockerImage)
