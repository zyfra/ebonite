import sys
import time
from typing import Generator, Type

from ebonite.build.runner.base import RunnerBase
from ebonite.utils.log import logger

from .base import DockerContainer, DockerEnv, DockerImage
from .helpers import create_docker_client, login_to_registry


class DockerRunnerException(Exception):
    pass


class DockerRunner(RunnerBase):
    def instance_type(self) -> Type[DockerContainer]:
        return DockerContainer

    def create_instance(self, name: str, **kwargs) -> DockerContainer:
        ports_mapping = None
        ports_mapping = kwargs.pop('ports_mapping', ports_mapping)
        return DockerContainer(name, ports_mapping, kwargs)

    def run(self, instance: DockerContainer, image: DockerImage, env: DockerEnv, rm=True, detach=True, **kwargs):
        if not (isinstance(instance, DockerContainer) and isinstance(image, DockerImage) and
                isinstance(env, DockerEnv)):
            raise TypeError('DockerRunner works with DockerContainer, DockerImage and DockerHost only')

        with create_docker_client(env.daemon.host) as client:
            login_to_registry(client, env.registry)

            from docker.errors import ContainerError  # FIXME
            try:
                # always detach from container and just stream logs if detach=False
                container = client.containers.run(image.get_uri(env.registry),
                                                  name=instance.name,
                                                  auto_remove=rm,
                                                  ports=instance.ports_mapping,
                                                  detach=True,
                                                  **instance.params,
                                                  **kwargs)
                instance.container_id = container.id
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

    def logs(self, instance: DockerContainer, env: DockerEnv, **kwargs) -> Generator[str, None, None]:
        self._validate(instance, env)

        with create_docker_client(env.host) as client:
            container = client.containers.get(instance.name)
            yield from self._logs(container, **kwargs)

    def _logs(self, container, stdout=True, stderr=True, stream=False,
              tail='all', since=None, follow=None, until=None, **kwargs) -> Generator[str, None, None]:

        log = container.logs(stdout=stdout, stderr=stderr, stream=stream,
                             tail=tail, since=since, follow=follow, until=until)
        if stream:
            for line in log:
                yield line.decode("utf-8")
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

    def is_running(self, instance: DockerContainer, env: DockerEnv, **kwargs) -> bool:
        self._validate(instance, env)

        with create_docker_client(env.daemon.host) as client:
            return self._is_service_running(client, instance.name)

    def stop(self, instance: DockerContainer, env: DockerEnv, **kwargs):
        self._validate(instance, env)

        with create_docker_client(env.daemon.host) as client:
            container = client.containers.get(instance.name)
            container.stop()

    def _validate(self, instance: DockerContainer, env: DockerEnv):
        if not (isinstance(instance, DockerContainer) and isinstance(env, DockerEnv)):
            raise TypeError('DockerRunner works with DockerContainer and DockerHost only')
