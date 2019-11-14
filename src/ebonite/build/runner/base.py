from abc import abstractmethod
from collections import Generator

from pyjackson.decorators import type_field


@type_field('type')
class TargetHost:

    @abstractmethod
    def get_host(self) -> str:
        pass


class LocalTargetHost(TargetHost):
    type = 'local'

    def get_host(self) -> str:
        return ''


class RemoteTargetHost(TargetHost):
    type = 'remote'

    def __init__(self, host, port):
        self.host = '{}:{}'.format(host, port)

    def get_host(self) -> str:
        return self.host


@type_field('type')
class ServiceInstance:
    def __init__(self, name: str, target_host: TargetHost = None):
        self.name = name
        self.target_host = target_host or LocalTargetHost()


class RunnerBase:
    @abstractmethod
    def run(self, service_instance: ServiceInstance, **kwargs):
        pass

    @abstractmethod
    def stop(self, service_instance: ServiceInstance):
        pass

    @abstractmethod
    def logs(self, service_instance: ServiceInstance, **kwargs) -> Generator:
        pass
