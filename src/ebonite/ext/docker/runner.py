import sys
import time
from typing import Dict, Generator, Type

import docker.errors

from ebonite.build.runner.base import RunnerBase
from ebonite.utils.log import logger

from .base import DockerContainer, DockerEnv, DockerImage


class DockerRunnerException(Exception):
    pass


class DockerRunner(RunnerBase):
    """RunnerBase implementation for docker containers"""

    def instance_exists(self, instance: DockerContainer, env: DockerEnv, **kwargs) -> bool:
        with env.daemon.client() as client:
            try:
                client.containers.get(instance.name)
                return True
            except docker.errors.NotFound:
                return False

    def remove_instance(self, instance: DockerContainer, env: DockerEnv, **kwargs):
        with env.daemon.client() as client:
            try:
                c = client.containers.get(instance.name)
                c.remove(**kwargs)
            except docker.errors.NotFound:
                pass

    def instance_type(self) -> Type[DockerContainer]:
        return DockerContainer

    def create_instance(self, name: str, port_mapping: Dict[int, int] = None, **kwargs) -> DockerContainer:
        return DockerContainer(name, port_mapping, kwargs)

    def run(self, instance: DockerContainer, image: DockerImage, env: DockerEnv, rm=True, detach=True, **kwargs):
        if not (isinstance(instance, DockerContainer) and isinstance(image, DockerImage) and
                isinstance(env, DockerEnv)):
            raise TypeError('DockerRunner works with DockerContainer, DockerImage and DockerHost only')

        with env.daemon.client() as client:
            image.registry.login(client)

            try:
                # always detach from container and just stream logs if detach=False
                container = client.containers.run(image.uri,
                                                  name=instance.name,
                                                  auto_remove=rm,
                                                  ports=instance.port_mapping,
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
                    self._sleep(.5)
                    if not self._is_service_running(client, instance.name):
                        if not rm:
                            for log in self._logs(container, stdout=False, stderr=True):
                                raise DockerRunnerException("The container died unexpectedly.", log)
                        else:
                            # Can't get logs from removed container
                            raise DockerRunnerException("The container died unexpectedly. Try to run the container "
                                                        "with detach=False or rm=False args to get more info.")
            except docker.errors.ContainerError as e:
                if e.stderr:
                    print(e.stderr.decode(), file=sys.stderr)
                raise

    def logs(self, instance: DockerContainer, env: DockerEnv, **kwargs) -> Generator[str, None, None]:
        self._validate(instance, env)

        with env.daemon.client() as client:
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

        with env.daemon.client() as client:
            return self._is_service_running(client, instance.name)

    def stop(self, instance: DockerContainer, env: DockerEnv, **kwargs):
        self._validate(instance, env)

        with env.daemon.client() as client:
            try:
                container = client.containers.get(instance.name)
                container.stop()
            except docker.errors.NotFound:
                pass

    @classmethod
    def _validate(cls, instance: DockerContainer, env: DockerEnv):
        if not (isinstance(instance, DockerContainer) and isinstance(env, DockerEnv)):
            raise TypeError('DockerRunner works with DockerContainer and DockerHost only')
