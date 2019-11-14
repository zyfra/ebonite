import os
from typing import List

from pyjackson import read

from ebonite.build.provider.ml_model import MODEL_BIN_PATH, MODEL_META_PATH
from ebonite.core.objects import core
from ebonite.runtime.interface import Interface, expose
from ebonite.runtime.interface.base import InterfaceLoader
from ebonite.runtime.interface.utils import merge
from ebonite.utils.log import rlogger


def model_interface(model_meta: 'core.Model'):
    """
    Creates an interface from given model with the only `predict` method.
    Methods signature is determined via metadata associated with given model.

    :param model_meta: model to create interface for
    :return: instance of :class:`.Interface` implementation
    """

    rlogger.debug('Creating interface for model %s', model_meta)
    input_type = model_meta.input_meta
    output_type = model_meta.output_meta

    class MLModelInterface(Interface):
        def __init__(self, model):
            self.model = model

        @expose
        def predict(self, vector: input_type) -> output_type:
            rlogger.debug('predicting given %s', vector)
            predict = self.model.predict(vector)
            rlogger.debug('prediction: %s', predict)
            return output_type.serialize(predict)

    return MLModelInterface(model_meta.wrapper)


class ModelLoader(InterfaceLoader):
    """
    Implementation of :class:`InterfaceLoader` which loads a model via PyJackson and wraps it into an interface
    """

    def load(self) -> Interface:
        meta = read(MODEL_META_PATH, core.Model)
        meta.wrapper.load(MODEL_BIN_PATH)
        return model_interface(meta)


class MultiModelLoader(InterfaceLoader):
    """
    Implementation of :class:`InterfaceLoader` which loads a collection of models via PyJackson
    and wraps them into a single interface
    """

    def load(self) -> Interface:
        metas = read(MODEL_META_PATH, List[core.Model])
        for meta in metas:
            meta.wrapper.load(os.path.join(MODEL_BIN_PATH, meta.name))
        ifaces = {
            meta.name: model_interface(meta) for meta in metas
        }
        return merge(ifaces)
