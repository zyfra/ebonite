import re
import sys
import time
from abc import abstractmethod
from typing import Dict, Generator

from ebonite.build.builder.docker_builder import create_docker_client
from ebonite.build.runner.base import RunnerBase, ServiceInstance, TargetHost
from pyjackson.decorators import type_field
from ebonite.utils.log import logger

# TODO check
VALID_HOST_REGEX = r'^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]).)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'


class DockerRunnerException(Exception):
    pass


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


@type_field('type')
class DockerImage:
    def __init__(self, name: str, tag: str = 'latest',
                 repository: str = None, docker_registry: DockerRegistry = None):
        self.name = name
        self.tag = tag
        self.repo = repository
        self.registry = docker_registry or DefaultDockerRegistry()

    def get_image_uri(self) -> str:
        image = '{}:{}'.format(self.name, self.tag)
        if self.repo is not None:
            image = '{}/{}'.format(self.repo, image)
        if self.registry.get_host():
            image = '{}/{}'.format(self.registry.get_host(), image)
        return image


class DockerServiceInstance(ServiceInstance):
    type = 'docker'

    def __init__(self, container_name: str,
                 docker_image: DockerImage,
                 target_host: TargetHost,
                 ports_mapping: Dict[int, int] = None):
        super().__init__(container_name, target_host)
        self.docker_image = docker_image
        self.ports_mapping = ports_mapping or {}


class SimpleDockerRunner(RunnerBase):

    def run(self, service_instance: DockerServiceInstance, rm=True, detach=True):
        if not isinstance(service_instance, DockerServiceInstance):
            raise TypeError('ServiceInstance should be of type DockerServiceInstance instead of {}'
                            .format(type(service_instance)))
        with create_docker_client(service_instance.target_host.get_host()) as client:
            if isinstance(service_instance.docker_image.registry, RemoteDockerRegistry):
                client.login(registry=service_instance.docker_image.registry.host,
                             username=service_instance.docker_image.registry.username,
                             password=service_instance.docker_image.registry.password)

            import docker.errors  # FIXME
            try:
                # always detach from container and just stream logs if detach=False
                container = client.containers.run(service_instance.docker_image.get_image_uri(),
                                                  name=service_instance.name,
                                                  auto_remove=rm,
                                                  ports=service_instance.ports_mapping,
                                                  detach=True)
                if not detach:
                    try:
                        # infinite loop of logs while container running or if everything ok
                        for log in self.logs(container, stream=True):
                            logger.debug(log)

                        if not self._is_service_running(client, service_instance):
                            raise DockerRunnerException("The container died unexpectedly.")

                    except KeyboardInterrupt:
                        logger.info('Interrupted. Stopping the container')
                        container.stop()

                else:
                    if not self._is_service_running(client, service_instance):
                        if not rm:
                            for log in self.logs(container, stdout=False, stderr=True):
                                raise DockerRunnerException("The container died unexpectedly.", log)
                        else:
                            # Can't get logs from removed container
                            raise DockerRunnerException("The container died unexpectedly. Try to run the container "
                                                        "with detach=False or rm=False args to get more info.")
                return container
            except docker.errors.ContainerError as e:
                if e.stderr:
                    print(e.stderr.decode(), file=sys.stderr)
                raise

    def logs(self, container, stdout=True, stderr=True, stream=False,
             tail='all', since=None, follow=None, until=None) -> Generator[str, None, None]:
        log = container.logs(stdout=stdout, stderr=stderr, stream=stream,
                             tail=tail, since=since, follow=follow, until=until)
        if stream:
            for l in log:
                yield l.decode("utf-8")
        else:
            yield log.decode("utf-8")

    def _is_service_running(self, client, service_instance: DockerServiceInstance, timeout: float = 10):
        time.sleep(timeout)
        containers = client.containers.list()
        return any(service_instance.name == c.name for c in containers)

    def stop(self, container):
        container.stop()
