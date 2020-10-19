import os
import shutil
from abc import abstractmethod
from contextlib import contextmanager

from ebonite.build.provider import PythonProvider
from ebonite.core.objects import core
from ebonite.utils.fs import get_lib_path
from ebonite.utils.log import logger

REQUIREMENTS = 'requirements.txt'
_EBONITE_SOURCE = True
# _EBONITE_SOURCE defines in which way ebonite will be installed inside of the instance. Depending on it's value
# True - means that it will install ebonite from PIP
# False - That it will use local ebonite installation
# str, representing a path - that it will search for .whl file with ebonite package


def ebonite_from_pip():
    """
    :return boolen flag if ebonite inside image must be installed from pip (or copied local dist instread)"""
    return _EBONITE_SOURCE


@contextmanager
def use_local_installation():
    """Context manager that changes docker builder behaviour to copy
    this installation of ebonite instead of installing it from pip.
    This is needed for testing and examples"""
    global _EBONITE_SOURCE
    tmp = _EBONITE_SOURCE
    _EBONITE_SOURCE = False
    try:
        yield
    finally:
        _EBONITE_SOURCE = tmp


@contextmanager
def use_wheel_installation(path: str):
    """Context manager that changes docker builder behaviour to
    install ebonite from wheel.
    This is needed in the case you using ebonite from wheel"""
    global _EBONITE_SOURCE
    tmp = _EBONITE_SOURCE
    _EBONITE_SOURCE = path
    try:
        yield
    finally:
        _EBONITE_SOURCE = tmp


class BuilderBase:
    """Abstract class for building images from ebonite objects"""

    @abstractmethod
    def create_image(self, name: str, environment: 'core.RuntimeEnvironment', **kwargs) -> 'core.Image.Params':
        """Abstract method to create image"""

    @abstractmethod
    def build_image(self, buildable: 'core.Buildable', image: 'core.Image.Params',
                    environment: 'core.RuntimeEnvironment.Params', **kwargs):
        """Abstract method to build image"""

    @abstractmethod
    def delete_image(self, image: 'core.Image.Params', environment: 'core.RuntimeEnvironment.Params', **kwargs):
        """Abstract method to delete image"""

    @abstractmethod
    def image_exists(self, image: 'core.Image.Params', environment: 'core.RuntimeEnvironment.Params', **kwargs):
        """Abstract method to check if image exists"""


class PythonBuildContext:
    """
    Basic class for building python images from ebonite objects

    :param provider: A ProviderBase instance to get distribution from
    """

    def __init__(self, provider: PythonProvider):
        self.provider = provider

    def _write_distribution(self, target_dir):
        """
        Writes full distribution to dir
        :param target_dir: target directory to write distribution
        """
        logger.debug('Writing model distribution to "%s"...', target_dir)
        self._write_sources(target_dir)
        self._write_binaries(target_dir)
        self._write_requirements(target_dir)
        self._write_run_script(target_dir)

    def _write_sources(self, target_dir):
        """
        Writes sources to dir
        :param target_dir: target directory to write sources
        """
        for name, content in self.provider.get_sources().items():
            logger.debug('Putting model source "%s" to distribution...', name)
            path = os.path.join(target_dir, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w' if isinstance(content, str) else 'wb', encoding='utf8') as src:
                src.write(content)

        pip_ebonite = ebonite_from_pip()
        if pip_ebonite is False:
            logger.debug('Putting Ebonite sources to distribution as local installation is employed...')
            main_module_path = get_lib_path('.')
            shutil.copytree(main_module_path, os.path.join(target_dir, 'ebonite'))
        elif isinstance(pip_ebonite, str):
            logger.debug('Putting Ebonite wheel to distribution as wheel installation is employed...')
            shutil.copy(pip_ebonite, target_dir)

    def _write_binaries(self, path):
        """
        Writes binaries to dir
        :param path: target directory to write binaries
        """
        logger.debug('Putting model artifacts to distribution...')
        a = self.provider.get_artifacts()
        a.materialize(path)

    def _write_requirements(self, target_dir):
        """
        Writes requirements.txt to dir
        :param target_dir: target directory to write requirements
        """
        with open(os.path.join(target_dir, REQUIREMENTS), 'w', encoding='utf8') as req:
            requirements = self.provider.get_requirements()
            logger.debug('Auto-determined requirements for model: %s.', requirements.to_pip())
            if ebonite_from_pip() is False:
                cwd = os.getcwd()
                try:
                    from setup import setup_args  # FIXME only for development
                    requirements += list(setup_args['install_requires'])
                    logger.debug('Adding Ebonite requirements as local installation is employed...')
                    logger.debug('Overall requirements for model: %s.', requirements.to_pip())
                finally:
                    os.chdir(cwd)
            req.write('\n'.join(requirements.to_pip()))

    def _write_run_script(self, target_dir):
        """
        Writes run.sh script to dir
        :param target_dir: target directory to script
        """
        with open(os.path.join(target_dir, 'run.sh'), 'w') as sh:
            sh.write('python -c "from ebonite import start_runtime; start_runtime()"')
