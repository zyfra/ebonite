import os
from typing import Dict

from pyjackson import read

from ebonite.core.objects import Model, Pipeline
from ebonite.runtime.interface import Interface, expose
from ebonite.runtime.interface.base import InterfaceLoader
from ebonite.utils.log import rlogger

MODEL_BIN_PATH = 'model_dump'
PIPELINE_META_PATH = 'pipeline.json'


class PipelineMeta:
    def __init__(self, pipeline: Pipeline,
                 models: Dict[str, Model]):
        self.pipeline = pipeline
        self.models = models


def pipeline_interface(pipeline_meta: Pipeline):
    """
    Creates an interface from given pipeline with `run` method
    Method signature is determined via metadata associated with given pipeline.

    :param pipeline_meta: pipeline to create interface for
    :return: instance of :class:`.Interface` implementation
    """

    rlogger.debug('Creating interface for pipeline %s', pipeline_meta)

    class PipelineInterface(Interface):
        def __init__(self, pipeline):
            self.pipeline = pipeline

        @expose
        def run(self, data: pipeline_meta.input_data) -> pipeline_meta.output_data:
            rlogger.debug('running pipeline given %s', data)
            output_data = self.pipeline.run(data)
            rlogger.debug('run returned: %s', output_data)
            return pipeline_meta.output_data.serialize(output_data)

    return PipelineInterface(pipeline_meta)


class PipelineLoader(InterfaceLoader):
    """
    Implementation of :class:`.InterfaceLoader` which loads a pipeline via PyJackson and wraps it into an interface
    """

    def load(self) -> Interface:
        meta = read(PIPELINE_META_PATH, PipelineMeta)
        for name, model in meta.models.items():
            model.wrapper.load(os.path.join(MODEL_BIN_PATH, name))
        meta.pipeline.models = meta.models
        return pipeline_interface(meta.pipeline)
