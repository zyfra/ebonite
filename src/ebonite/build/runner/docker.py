import sys
import time
from typing import Dict, Generator

from ebonite.build.builder.docker_builder import create_docker_client
from ebonite.build.docker_objects import DockerImage, RemoteDockerRegistry
from ebonite.build.runner.base import RunnerBase, ServiceInstance, TargetHost
from ebonite.utils.log import logger


class DockerRunnerException(Exception):
    pass


class DockerServiceInstance(ServiceInstance):
    type = 'docker'

    def __init__(self, container_name: str,
                 docker_image: DockerImage,
                 target_host: TargetHost,
                 ports_mapping: Dict[int, int] = None):
        super().__init__(container_name, target_host)
        self.docker_image = docker_image
        self.ports_mapping = ports_mapping or {}


class DockerRunner(RunnerBase):

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
