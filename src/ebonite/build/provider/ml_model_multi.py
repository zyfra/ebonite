import os
from typing import List

from pyjackson import dumps
from pyjackson.decorators import cached_property

from ebonite.build.provider.ml_model import MLModelProvider
from ebonite.core.objects import ArtifactCollection, Model, Requirements
from ebonite.core.objects.artifacts import _RelativePathWrapper, CompositeArtifactCollection
from ebonite.runtime.interface.ml_model import MODEL_BIN_PATH, MODELS_META_PATH
from ebonite.runtime.server import Server
from ebonite.utils.module import get_object_requirements


class MLModelMultiProvider(MLModelProvider):
    """Provider to put multiple models in one service

    :param models: List of Model instances
    :param server: Server instance to build with"""

    def __init__(self, models: List[Model], server: Server):
        from ebonite.runtime.interface.ml_model import MultiModelLoader
        super(MLModelProvider, self).__init__(server, MultiModelLoader())
        self.models: List[Model] = models

    @cached_property
    def _requirements(self) -> Requirements:
        """Union of server, loader and all models requirements"""
        return (get_object_requirements(self.server) +
                get_object_requirements(self.loader) +
                sum((model.requirements for model in self.models), Requirements()))

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
            _RelativePathWrapper(m.artifact_any, os.path.join(MODEL_BIN_PATH, str(i)))
            for i, m in enumerate(self.models)
        ])
