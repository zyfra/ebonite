import os
from typing import List

from pyjackson import dumps
from pyjackson.decorators import cached_property

from ebonite.build.provider.ml_model import MLModelProvider
from ebonite.build.provider.utils import BuildableWithServer
from ebonite.core.analyzer import CanIsAMustHookMixin
from ebonite.core.analyzer.buildable import BuildableHook
from ebonite.core.objects import ArtifactCollection, Model, Requirements
from ebonite.core.objects.artifacts import _RelativePathWrapper, CompositeArtifactCollection
from ebonite.core.objects.core import WithMetadataRepository
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
        # TODO additional server binaries
        return CompositeArtifactCollection([
            _RelativePathWrapper(m.artifact_any, os.path.join(MODEL_BIN_PATH, str(i)))
            for i, m in enumerate(self.models)
        ])

    def image_source(self) -> 'MultiModelBuildable':
        return MultiModelBuildable([m.id for m in self.models], self.server.type)


class MultiModelBuildable(BuildableWithServer, WithMetadataRepository):
    def __init__(self, model_ids: List[int], server_type: str):
        super().__init__(server_type)
        self.model_ids = model_ids

    @property
    def models(self) -> List[Model]:
        return [self._meta.get_model_by_id(mid) for mid in self.model_ids]

    def get_provider(self) -> MLModelMultiProvider:
        return MLModelMultiProvider(self.models, self.server)


class BuildableMultiModelHook(BuildableHook, CanIsAMustHookMixin):

    def must_process(self, obj) -> bool:
        return isinstance(obj, list) and all(isinstance(o, Model) for o in obj)

    def process(self, obj, **kwargs):
        server = kwargs.get('server')  # TODO ???
        return MultiModelBuildable([o.id for o in obj], server.type)
