import sys
import time
from typing import Dict, Generator

from ebonite.build.docker import DockerImage, create_docker_client, login_to_registry
from ebonite.build.runner.base import RunnerBase
from ebonite.utils.log import logger


class DockerRunnerException(Exception):
    pass


class DockerRuntimeInstance:
    def __init__(self, name: str, image: DockerImage, target_uri: str = '', ports_mapping: Dict[int, int] = None):
        self.name = name
        self.image = image
        self.target_uri = target_uri
        self.ports_mapping = ports_mapping or {}

    @staticmethod
    def from_core_instance(instance):
        return DockerRuntimeInstance(instance.name,
                                     DockerImage.from_core_image(instance.image),
                                     instance.environment.get_uri(),
                                     instance.params['ports_mapping'])


class DockerRunner(RunnerBase):

    def run(self, instance: DockerRuntimeInstance, rm=True, detach=True):
        with create_docker_client(instance.target_uri) as client:
            login_to_registry(client, instance.image.registry)

            from docker.errors import ContainerError  # FIXME
            try:
                # always detach from container and just stream logs if detach=False
                container = client.containers.run(instance.image.get_uri(),
                                                  name=instance.name,
                                                  auto_remove=rm,
                                                  ports=instance.ports_mapping,
                                                  detach=True)
                if not detach:
                    try:
                        # infinite loop of logs while container running or if everything ok
                        for log in self._logs(container, stream=True):
                            logger.debug(log)

                        self._sleep()
                        if not self._is_service_running(client, instance.name):
                            raise DockerRunnerException("The container died unexpectedly.")

                    except KeyboardInterrupt:
                        logger.info('Interrupted. Stopping the container')
                        container.stop()

                else:
                    self._sleep()
                    if not self._is_service_running(client, instance.name):
                        if not rm:
                            for log in self._logs(container, stdout=False, stderr=True):
                                raise DockerRunnerException("The container died unexpectedly.", log)
                        else:
                            # Can't get logs from removed container
                            raise DockerRunnerException("The container died unexpectedly. Try to run the container "
                                                        "with detach=False or rm=False args to get more info.")
            except ContainerError as e:
                if e.stderr:
                    print(e.stderr.decode(), file=sys.stderr)
                raise

    def logs(self, instance: DockerRuntimeInstance, **kwargs) -> Generator[str, None, None]:
        with create_docker_client(instance.target_uri) as client:
            container = client.containers.get(instance.name)
            yield from self._logs(container, **kwargs)

    def _logs(self, container, stdout=True, stderr=True, stream=False,
              tail='all', since=None, follow=None, until=None) -> Generator[str, None, None]:

        log = container.logs(stdout=stdout, stderr=stderr, stream=stream,
                             tail=tail, since=since, follow=follow, until=until)
        if stream:
            for l in log:
                yield l.decode("utf-8")
        else:
            yield log.decode("utf-8")

    def _sleep(self, timeout: float = 10):
        time.sleep(timeout)

    def _is_service_running(self, client, name):
        from docker.errors import NotFound
        try:
            container = client.containers.get(name)
            return container.status == 'running'
        except NotFound:
            return False

    def is_running(self, instance: DockerRuntimeInstance) -> bool:
        with create_docker_client(instance.target_uri) as client:
            return self._is_service_running(client, instance.name)

    def stop(self, instance: DockerRuntimeInstance):
        with create_docker_client(instance.target_uri) as client:
            container = client.containers.get(instance.name)
            container.stop()
