from abc import abstractmethod
from typing import Generator


class RunnerBase:
    @abstractmethod
    def run(self, instance, **kwargs):
        pass  # pragma: no cover

    @abstractmethod
    def is_running(self, instance) -> bool:
        pass  # pragma: no cover

    @abstractmethod
    def stop(self, instance):
        pass  # pragma: no cover

    @abstractmethod
    def logs(self, instance, **kwargs) -> Generator[str, None, None]:
        pass  # pragma: no cover
