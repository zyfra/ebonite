import ebonite.ext as ext
from ebonite.build.provider import LOADER_ENV, PythonProvider, SERVER_ENV
from ebonite.core.objects.artifacts import ArtifactCollection, _RelativePathWrapper
from ebonite.core.objects import core
from ebonite.core.objects.requirements import Requirements
from pyjackson import dumps
from pyjackson.decorators import cached_property
from ebonite.runtime.server import Server
from ebonite.utils.module import get_object_requirements

MODEL_BIN_PATH = 'model_dump'

LOADER_PATH = 'loader'
SERVER_PATH = 'server'
MODEL_META_PATH = 'model.json'


class MLModelProvider(PythonProvider):
    """Provider to build service from Model object

    :param model: Model instance to build from
    :param server: Server instance to build with
    """

    def __init__(self, model: 'core.Model', server: Server):
        from ebonite.runtime.interface.ml_model import ModelLoader
        super().__init__(server, ModelLoader())
        self.model = model

    def get_env(self):
        """Sets loader, server and extensions env variables"""
        env = {
            LOADER_ENV: self.loader.classpath,
            SERVER_ENV: self.server.classpath,

        }

        modules = set(self.get_requirements().modules)

        extensions = ext.ExtensionLoader.loaded_extensions.keys()
        used_extensions = [e.module for e in extensions if all(r in modules for r in e.reqs)]
        if len(used_extensions) > 0:
            env['EBONITE_EXTENSIONS'] = ','.join(used_extensions)

        return env

    @cached_property
    def _requirements(self) -> Requirements:
        """Union of model, server and loader requirements"""
        return (self.model.requirements +
                get_object_requirements(self.server) +
                get_object_requirements(self.loader))

    def get_requirements(self) -> Requirements:
        """Returns union of model, server and loader requirements"""
        return self._requirements

    def _get_sources(self):
        """Returns sources of custom modules from requirements"""
        sources = {}
        for cr in self.get_requirements().custom:
            sources.update(cr.to_sources_dict())
        return sources

    def get_sources(self):
        """Returns model metadata file and sources of custom modules from requirements"""
        return {
            MODEL_META_PATH: dumps(self.model.without_artifacts()),
            **self._get_sources()
        }

    def get_artifacts(self) -> ArtifactCollection:
        """Return model binaries"""
        return _RelativePathWrapper(self.model.artifact_any, MODEL_BIN_PATH)
