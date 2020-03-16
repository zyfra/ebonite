from abc import abstractmethod
from typing import Generator


class RunnerBase:
    @abstractmethod
    def run(self, instance, **kwargs):
        pass

    @abstractmethod
    def is_running(self, instance) -> bool:
        pass

    @abstractmethod
    def stop(self, instance):
        pass

    @abstractmethod
    def logs(self, instance, **kwargs) -> Generator[str, None, None]:
        pass
