import sys
from abc import abstractmethod
from typing import Dict

from ebonite.core.objects.artifacts import ArtifactCollection
from ebonite.core.objects.requirements import Requirements
from ebonite.runtime.interface import InterfaceLoader
from ebonite.runtime.server import Server


class ProviderBase:
    """Base class for providers"""

    @abstractmethod
    def get_sources(self) -> Dict[str, str]:
        """Abstract method for text files"""
        pass

    @abstractmethod
    def get_artifacts(self) -> ArtifactCollection:
        """Abstact method for binaries"""
        pass

    @abstractmethod
    def get_env(self) -> Dict[str, str]:
        """Abstract method for environment variables"""
        pass


SERVER_ENV = 'EBONITE_SERVER'
LOADER_ENV = 'EBONITE_LOADER'


class PythonProvider(ProviderBase):
    """Provider for python-based builds. Includes python version and requirements

    :param server: Server instance to build with
    :param loader: InterfaceLoader instance to build with
    """

    def __init__(self, server: Server, loader: InterfaceLoader):
        self.server = server
        self.loader = loader

    @staticmethod
    def get_python_version():
        """Returns current python version"""
        major, minor, *_ = sys.version_info
        return '{}.{}'.format(major, minor)

    @abstractmethod
    def get_requirements(self) -> Requirements:
        """Abstract method for python requirements"""
        pass
