import os
import warnings
from functools import reduce
from typing import Optional, Union

from pyjackson import dumps
from pyjackson.decorators import cached_property

from ebonite.build.provider import PythonProvider
from ebonite.build.provider.utils import BuildableWithServer
from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.buildable import BuildableHook
from ebonite.core.objects import ArtifactCollection, Model, Pipeline, Requirements, Task
from ebonite.core.objects.artifacts import Blobs, CompositeArtifactCollection, LocalFileBlob, _RelativePathWrapper
from ebonite.core.objects.core import _with_meta
from ebonite.runtime.interface.pipeline import MODEL_BIN_PATH, PIPELINE_META_PATH, PipelineLoader, PipelineMeta
from ebonite.runtime.server import Server
from ebonite.utils.module import get_object_requirements

LOADER_PATH = 'loader'
SERVER_PATH = 'server'


def read(path):
    with open(path) as f:
        return f.read()


class PipelineProvider(PythonProvider):
    """Provider to build service from Pipeline object

    :param pipeline: Pipeline instance to build from
    :param server: Server instance to build with
    :param debug: Whether to run image in debug mode
    """

    def __init__(self, pipeline: Pipeline, server: Server, debug: bool = False):
        super().__init__(server, PipelineLoader(), debug)
        self.pipeline = pipeline

    @cached_property
    def _requirements(self) -> Requirements:
        """Union of pipeline, server and loader requirements"""
        model_reqs = reduce(Requirements.__add__,
                            [m.requirements for m in self.pipeline.models.values()],
                            Requirements())
        return (model_reqs +
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

        # add __init__.py for all dirs that doesnt have it already
        packages = set(os.path.join(os.path.dirname(p), '__init__.py') for p in sources if os.path.dirname(p) != '')
        sources.update({
            p: '' for p in packages if p not in sources
        })
        return sources

    def get_sources(self):
        """Returns model metadata file and sources of custom modules from requirements"""
        meta = PipelineMeta(self.pipeline, {
            k: v.without_artifacts() for k, v in self.pipeline.models.items()
        })
        return {
            PIPELINE_META_PATH: dumps(meta),
            **self._get_sources(),
            **{os.path.basename(f): read(f) for f in self.server.additional_sources}
        }

    def get_artifacts(self) -> ArtifactCollection:
        """Return model binaries"""

        artifacts = CompositeArtifactCollection(
            [_RelativePathWrapper(m.artifact_any, os.path.join(MODEL_BIN_PATH, m.name)) for m in
             self.pipeline.models.values()])
        if len(self.server.additional_binaries) > 0:
            artifacts = CompositeArtifactCollection([
                artifacts,
                Blobs({os.path.basename(f): LocalFileBlob(f) for f in self.server.additional_binaries})
            ])
        return artifacts

    def get_python_version(self):
        """
        :return: version of python that produced model
        """
        versions = {model.params.get(Model.PYTHON_VERSION) for model in self.pipeline.models.values()}
        versions.discard(None)
        if len(versions) == 0:
            return super(PipelineProvider, self).get_python_version()
        elif len(versions) > 1:
            warnings.warn(f'Inconsistent python version for pipeline models: {versions}')
        return min(versions)  # in backward compatibility we trust


class PipelineBuildable(BuildableWithServer):
    def __init__(self, pipeline_id: Union[int, Pipeline], server_type: str, debug: bool = False):
        super().__init__(server_type)
        self.debug = debug
        if isinstance(pipeline_id, int):
            self.pipeline_id = pipeline_id
            self.pipeline_cache = None
        else:
            self.pipeline_cache = pipeline_id
            self.pipeline_id = pipeline_id.id
            self.bind_meta_repo(self.pipeline_cache._meta)

    @property
    def task(self) -> Optional[Task]:
        return self.pipeline.task

    @property
    @_with_meta(False)
    def pipeline(self):
        if self.pipeline_cache is None:
            self._check_meta(False)
            self.pipeline_cache = self._meta.get_pipeline_by_id(self.pipeline_id)
        return self.pipeline_cache

    def get_provider(self) -> PipelineProvider:
        return PipelineProvider(self.pipeline, self.server, self.debug)


class BuildableModelHook(BuildableHook, TypeHookMixin):
    valid_types = [Pipeline]

    def process(self, obj, **kwargs):
        server = kwargs.get('server')  # TODO ???
        debug = kwargs.get('debug', False)
        return PipelineBuildable(obj, server.type, debug)
