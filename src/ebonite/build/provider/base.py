from abc import abstractmethod
from typing import Dict

from ebonite.core.objects.artifacts import ArtifactCollection
from ebonite.core.objects.requirements import Requirements
from ebonite.runtime.interface import InterfaceLoader
from ebonite.runtime.server import Server
from ebonite.utils.module import get_python_version


class ProviderBase:
    """Base class for providers"""

    @abstractmethod
    def get_sources(self) -> Dict[str, str]:
        """Abstract method for text files"""
        pass  # pragma: no cover

    @abstractmethod
    def get_artifacts(self) -> ArtifactCollection:
        """Abstact method for binaries"""
        pass  # pragma: no cover

    @abstractmethod
    def get_env(self) -> Dict[str, str]:
        """Abstract method for environment variables"""
        pass  # pragma: no cover

    @abstractmethod
    def get_options(self) -> Dict[str, str]:
        """Abstract method for additional build options"""
        pass  # pragma: no cover


SERVER_ENV = 'EBONITE_SERVER'
LOADER_ENV = 'EBONITE_LOADER'


class PythonProvider(ProviderBase):
    """Provider for python-based builds. Includes python version and requirements

    :param server: Server instance to build with
    :param loader: InterfaceLoader instance to build with
    :param debug: Whether to run image in debug mode
    """

    def __init__(self, server: Server, loader: InterfaceLoader, debug: bool = False):
        self.debug = debug
        self.server = server
        self.loader = loader

    def get_python_version(self):
        """Returns current python version"""
        return get_python_version()

    @abstractmethod
    def get_requirements(self) -> Requirements:
        """Abstract method for python requirements"""
        pass  # pragma: no cover

    def get_env(self) -> Dict[str, str]:
        """Get env variables for image"""
        envs = {
            LOADER_ENV: self.loader.classpath,
            SERVER_ENV: self.server.classpath,
            'EBONITE_RUNTIME': 'true'
        }
        if self.debug:
            envs['EBONITE_DEBUG'] = 'true'

        envs.update(self.server.additional_envs)

        modules = set(self.get_requirements().modules)

        from ebonite.ext import ExtensionLoader
        extensions = ExtensionLoader.loaded_extensions.keys()
        used_extensions = [e.module for e in extensions if all(r in modules for r in e.reqs)]
        if len(used_extensions) > 0:
            envs['EBONITE_EXTENSIONS'] = ','.join(used_extensions)
        return envs

    def get_options(self) -> Dict[str, str]:
        return self.server.additional_options
