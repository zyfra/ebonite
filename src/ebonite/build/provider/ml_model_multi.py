from typing import List

from pyjackson import dumps
from pyjackson.decorators import cached_property

from ebonite.build.provider.ml_model import MLModelProvider
from ebonite.core.objects import core
from ebonite.core.objects.requirements import Requirements
from ebonite.core.objects.artifacts import ArtifactCollection, CompositeArtifactCollection
from ebonite.runtime.server import Server
from ebonite.utils.module import get_object_requirements

MODELS_META_PATH = 'models.json'


class MLModelMultiProvider(MLModelProvider):
    """Provider to put multiple models in one service

    :param models: List of Model instances
    :param server: Server instance to build with"""

    def __init__(self, models: List['core.Model'], server: Server):
        from ebonite.runtime.interface.ml_model import MultiModelLoader
        super(MLModelProvider, self).__init__(server, MultiModelLoader())
        self.models: List[core.Model] = models

    @cached_property
    def _requirements(self) -> Requirements:
        """Union of server, loader and all models requirements"""
        return (get_object_requirements(self.server) +
                get_object_requirements(self.loader) +
                [_ for model in self.models for _ in model.params.requirements])

    def get_requirements(self):
        """Returns union of server, loader and all models requirements"""
        return self._requirements

    def get_sources(self):
        """Returns models meta file and custom requirements"""
        return {
            MODELS_META_PATH: dumps([model.without_artifacts() for model in self.models]),
            **self._get_sources()
        }

    def get_artifacts(self) -> ArtifactCollection:
        """Returns binaries of models artifacts"""
        return CompositeArtifactCollection([
            m.artifact_any for m in self.models
        ])
