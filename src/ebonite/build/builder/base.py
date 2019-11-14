import os
import shutil
from abc import abstractmethod
from contextlib import contextmanager

from ebonite.build.provider import PythonProvider
from ebonite.utils.fs import get_lib_path
from ebonite.utils.log import logger


REQUIREMENTS = 'requirements.txt'
EBONITE_FROM_PIP = True


def ebonite_from_pip():
    return EBONITE_FROM_PIP


@contextmanager
def use_local_installation():
    """Context manager that changes docker builder behaviour to copy
    this installation of ebonite instead of installing it from pip.
    This is needed for testing and examples"""
    global EBONITE_FROM_PIP
    tmp = EBONITE_FROM_PIP
    EBONITE_FROM_PIP = False
    try:
        yield
    finally:
        EBONITE_FROM_PIP = tmp


class BuilderBase:
    """Abstract class for building images from ebonite objects"""
    @abstractmethod
    def build(self):
        pass


# noinspection PyAbstractClass
class PythonBuilder(BuilderBase):
    """
    Basic class for building python images from ebonite objects

    :param provider: An implementation of PythonProvider to get distribution from
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
            with open(path, 'w', encoding='utf8') as src:
                src.write(content)

        if not ebonite_from_pip():
            logger.debug('Putting Ebonite sources to distribution as local installation is employed...')
            main_module_path = get_lib_path('.')
            shutil.copytree(main_module_path, os.path.join(target_dir, 'ebonite'))

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
            if not ebonite_from_pip():
                from setup import setup_args  # FIXME only for development
                requirements += list(setup_args['install_requires'])
                logger.debug('Adding Ebonite requirements as local installation is employed...')
                logger.debug('Overall requirements for model: %s.', requirements.to_pip())
            req.write('\n'.join(requirements.to_pip()))

    def _write_run_script(self, target_dir):
        """
        Writes run.sh script to dir
        :param target_dir: target directory to script
        """
        env = self.provider.get_env()
        logger.debug('Determined environment for running model: %s.', env)
        with open(os.path.join(target_dir, 'run.sh'), 'w') as sh:
            envs = ' '.join('{}={}'.format(k, v) for k, v in env.items())
            sh.write(
                'EBONITE_RUNTIME=true {} python -c "from ebonite import start_runtime; start_runtime()"'.format(
                    envs))
