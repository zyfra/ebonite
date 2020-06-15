import os
import warnings
from typing import List, Optional, Union

from pyjackson import dumps
from pyjackson.decorators import cached_property

from ebonite.build.provider.utils import BuildableWithServer
from ebonite.core.analyzer import CanIsAMustHookMixin
from ebonite.core.analyzer.buildable import BuildableHook
from ebonite.build.provider.ml_model import MLModelProvider, read
from ebonite.core.objects import ArtifactCollection, Model, Requirements, Task
from ebonite.core.objects.artifacts import _RelativePathWrapper, CompositeArtifactCollection
from ebonite.core.objects.core import WithMetadataRepository
from ebonite.runtime.interface.ml_model import MODEL_BIN_PATH, MODELS_META_PATH
from ebonite.runtime.server import Server
from ebonite.utils.module import get_object_requirements
from ebonite.utils.log import logger


class MLModelMultiProvider(MLModelProvider):
    """Provider to put multiple models in one service

    :param models: List of Model instances
    :param server: Server instance to build with
    :param debug: Debug for instance"""

    def __init__(self, models: List[Model], server: Server, debug: bool = False):
        from ebonite.runtime.interface.ml_model import MultiModelLoader
        super(MLModelProvider, self).__init__(server, MultiModelLoader(), debug)
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
            **self._get_sources(),
            **{os.path.basename(f): read(f) for f in self.server.additional_sources}
        }

    def get_artifacts(self) -> ArtifactCollection:
        """Returns binaries of models artifacts"""
        # TODO additional server binaries
        return CompositeArtifactCollection([
            _RelativePathWrapper(m.artifact_any, os.path.join(MODEL_BIN_PATH, str(i)))
            for i, m in enumerate(self.models)
        ])

    def get_python_version(self):
        versions = [model.params.get(Model.PYTHON_VERSION) for model in self.models]
        if len(set(versions)) > 1:
            logger.warn('Models in MultModelProvider have varying python versions in requirements')
        return max(versions)


class MultiModelBuildable(BuildableWithServer, WithMetadataRepository):
    def __init__(self, model_ids: List[Union[int, Model]], server_type: str, debug: bool = False):
        if len(model_ids) == 0:
            raise ValueError('model_ids must contain at least one model')
        super().__init__(server_type)
        if isinstance(model_ids[0], int):
            self.model_ids = model_ids
            self.models_cache = None
        else:
            self.models_cache = model_ids
            self.model_ids = [m.id for m in model_ids]
            self.bind_meta_repo(self.models_cache[0]._meta)
        self.debug = debug

    @property
    def task(self) -> Optional[Task]:
        tasks = [m.task for m in self.models]
        if len(set(t.id for t in tasks)) != 1:
            warnings.warn(f'Ambiguious task for buildable {self}')
        return tasks[0]

    @property
    def models(self) -> List[Model]:
        if self.models_cache is None:
            self._check_meta(False)
            self.models_cache = [self._meta.get_model_by_id(mid) for mid in self.model_ids]
        return self.models_cache

    def get_provider(self) -> MLModelMultiProvider:
        return MLModelMultiProvider(self.models, self.server, self.debug)


class BuildableMultiModelHook(BuildableHook, CanIsAMustHookMixin):

    def must_process(self, obj) -> bool:
        return isinstance(obj, list) and all(isinstance(o, Model) for o in obj)

    def process(self, obj, **kwargs):
        server = kwargs.get('server')  # TODO ???
        debug = kwargs.get('debug', False)
        return MultiModelBuildable(obj, server.type, debug)
