import os
from typing import List

from pyjackson import read
from pyjackson.core import Field, Signature

from ebonite.core.objects import Model
from ebonite.runtime.interface import Interface
from ebonite.runtime.interface.base import InterfaceLoader
from ebonite.runtime.interface.utils import merge
from ebonite.utils.log import rlogger

MODEL_BIN_PATH = 'model_dump'
MODEL_META_PATH = 'model.json'
MODELS_META_PATH = 'models.json'


def model_interface(model_meta: Model):
    """
    Creates an interface from given model with `predict` and (if available) `predict_proba` methods.
    Methods signature is determined via metadata associated with given model.

    :param model_meta: model to create interface for
    :return: instance of :class:`.Interface` implementation
    """

    rlogger.debug('Creating interface for model %s', model_meta)

    class MLModelInterface(Interface):
        def __init__(self, model):
            self.model = model

            exposed = {**self.exposed}
            executors = {**self.executors}

            for name in self.model.exposed_methods:
                in_type, out_type = self.model.method_signature(name)
                exposed[name] = Signature([Field("vector", in_type, False)], Field(None, out_type, False))
                executors[name] = self._exec_factory(name, out_type)

            self.exposed = exposed
            self.executors = executors

        def _exec_factory(self, name, out_type):
            model = self.model

            def _exec(**kwargs):
                input_data = kwargs['vector']
                rlogger.debug('calling %s given %s', name, input_data)
                output_data = model.call_method(name, input_data)
                rlogger.debug('%s returned: %s', name, output_data)
                return out_type.serialize(output_data)

            return _exec

    return MLModelInterface(model_meta.wrapper)


class ModelLoader(InterfaceLoader):
    """
    Implementation of :class:`.InterfaceLoader` which loads a model via PyJackson and wraps it into an interface
    """

    def load(self) -> Interface:
        meta = read(MODEL_META_PATH, Model)
        meta.wrapper.load(MODEL_BIN_PATH)
        return model_interface(meta)


class MultiModelLoader(InterfaceLoader):
    """
    Implementation of :class:`.InterfaceLoader` which loads a collection of models via PyJackson
    and wraps them into a single interface
    """

    def load(self) -> Interface:
        metas = read(MODELS_META_PATH, List[Model])
        for i, meta in enumerate(metas):
            meta.wrapper.load(os.path.join(MODEL_BIN_PATH, str(i)))
        ifaces = {
            meta.name: model_interface(meta) for meta in metas
        }
        return merge(ifaces)
