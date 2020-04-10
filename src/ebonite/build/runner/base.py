from abc import abstractmethod
from typing import Generator, Type

from ebonite.core.objects import Image, RuntimeEnvironment, RuntimeInstance


class RunnerBase:
    @abstractmethod
    def instance_type(self) -> Type[RuntimeInstance.Params]:
        """
        :return: subtype of :class:`.RuntimeInstance.Params` supported by this runner
        """
        pass  # pragma: no cover

    @abstractmethod
    def create_instance(self, name: str, **kwargs) -> RuntimeInstance.Params:
        """
        Creates new runtime instance on given name and args

        :param name: name of instance to use
        :return: created :class:`.RuntimeInstance.Params` subclass instance
        """
        pass  # pragma: no cover

    @abstractmethod
    def run(self, instance: RuntimeInstance.Params, image: Image.Params, env: RuntimeEnvironment.Params, **kwargs):
        """
        Runs given image on given environment with params given by instance

        :param instance: instance params to use for running
        :param image: image to base instance on
        :param env: environment to run on
        """
        pass  # pragma: no cover

    @abstractmethod
    def is_running(self, instance: RuntimeInstance.Params, env: RuntimeEnvironment.Params, **kwargs) -> bool:
        """
        Checks that given instance is running on given environment

        :param instance: instance to check running of
        :param env: environment to check running on
        :return: "is running" flag
        """
        pass  # pragma: no cover

    @abstractmethod
    def stop(self, instance: RuntimeInstance.Params, env: RuntimeEnvironment.Params, **kwargs):
        """
        Stops running of given instance on given environment

        :param instance: instance to stop running of
        :param env: environment to stop running on
        """
        pass  # pragma: no cover

    @abstractmethod
    def logs(self, instance: RuntimeInstance.Params, env: RuntimeEnvironment.Params,
             **kwargs) -> Generator[str, None, None]:
        """
        Exposes logs produced by given instance while running on given environment

        :param instance: instance to expose logs for
        :param env: environment to expose logs from
        :return: generator of log strings
        """
        pass  # pragma: no cover
