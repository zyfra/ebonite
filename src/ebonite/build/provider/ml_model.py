import os

from ebonite.build.provider import PythonProvider
from ebonite.core.objects.artifacts import ArtifactCollection, _RelativePathWrapper, CompositeArtifactCollection, Blobs, \
    LocalFileBlob
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


def read(path):
    with open(path) as f:
        return f.read()


class MLModelProvider(PythonProvider):
    """Provider to build service from Model object

    :param model: Model instance to build from
    :param server: Server instance to build with
    :param debug: Whether to run image in debug mode
    """

    def __init__(self, model: 'core.Model', server: Server, debug: bool = False):
        from ebonite.runtime.interface.ml_model import ModelLoader
        super().__init__(server, ModelLoader(), debug)
        self.model = model

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
            **self._get_sources(),
            **{os.path.basename(f): read(f) for f in self.server.additional_sources}
        }

    def get_artifacts(self) -> ArtifactCollection:
        """Return model binaries"""
        artifacts = _RelativePathWrapper(self.model.artifact_any, MODEL_BIN_PATH)
        if len(self.server.additional_binaries) > 0:
            artifacts = CompositeArtifactCollection([
                artifacts,
                Blobs({os.path.basename(f): LocalFileBlob(f) for f in self.server.additional_binaries})
            ])
        return artifacts
