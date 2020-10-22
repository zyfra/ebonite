import contextlib
import os
from abc import abstractmethod
from typing import Dict, List, Type, Union

import onnx
from onnx import ModelProto
from pyjackson.decorators import cached_property

from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.model import BindingModelHook
from ebonite.core.objects import ModelIO, ModelWrapper, Requirements
from ebonite.core.objects.artifacts import Blobs, InMemoryBlob
from ebonite.core.objects.wrapper import FilesContextManager
from ebonite.utils.abc_utils import is_abstract_method
from ebonite.utils.importing import module_importable

_DEFAULT_BACKEND = 'onnxruntime'


def set_default_onnx_backend(backend: Union[Type['ONNXInferenceBackend'], str]):
    global _DEFAULT_BACKEND
    if not isinstance(backend, str):
        backend = backend.name
    if backend not in ONNXInferenceBackend.subtypes:
        raise ValueError(f'unknown onnx backend {backend}')
    _DEFAULT_BACKEND = backend


class ONNXModelIO(ModelIO):
    FILENAME = 'model.onnx'

    @contextlib.contextmanager
    def dump(self, model: ModelProto) -> FilesContextManager:
        yield Blobs({self.FILENAME: InMemoryBlob(model.SerializeToString())})  # TODO change to LazyBlob

    def load(self, path):
        return onnx.load(os.path.join(path, self.FILENAME))


class ONNXInferenceBackend:
    subtypes: Dict[str, Type['ONNXInferenceBackend']] = {}
    name: str
    requirements: List[str]

    def __init__(self, wrapper: 'ONNXModelWrapper'):
        self.wrapper = wrapper

    def __init_subclass__(cls, **kwargs):
        if not is_abstract_method(cls.run) and not is_abstract_method(cls.is_available):
            if 'name' not in cls.__dict__ or 'requirements' not in cls.__dict__:
                raise AttributeError(f'provide name and requirements fields for {cls}')
            ONNXInferenceBackend.subtypes[cls.name] = cls
        super().__init_subclass__(**kwargs)

    @abstractmethod
    def run(self, data):
        """"""

    @classmethod
    def is_available(cls):
        return all(module_importable(m) for m in cls.requirements)


class ONNXRuntimeBackend(ONNXInferenceBackend):
    name = 'onnxruntime'
    requirements = ['onnxruntime']
    _session = None

    @cached_property
    def session(self):
        import onnxruntime as rt
        if self._session is None:
            self._session = rt.InferenceSession(self.wrapper.model.SerializeToString())
        return self._session

    def run(self, data):
        return self.session.run([o.name for o in self.session.get_outputs()], data)


class ONNXModelWrapper(ModelWrapper):
    model: ModelProto

    def __init__(self, io: ModelIO, backend: str = None):
        super().__init__(io)
        self.backend = backend or _DEFAULT_BACKEND
        if self.backend not in ONNXInferenceBackend.subtypes:
            raise ValueError(f'unknown onnx backend {self.backend}')
        self._backend: ONNXInferenceBackend = ONNXInferenceBackend.subtypes[self.backend](self)

    def run(self, data):
        if not self._backend.is_available():
            raise RuntimeError(f'{self.backend} inference backend is unavailable')
        return self._backend.run(data)

    def _exposed_methods_mapping(self) -> Dict[str, str]:
        return {'predict': 'run'}

    def _model_requirements(self) -> Requirements:
        return super(ONNXModelWrapper, self)._model_requirements() + self._backend.requirements


class ONNXModelHook(BindingModelHook, TypeHookMixin):
    valid_types = [ModelProto]

    def _wrapper_factory(self) -> ModelWrapper:
        return ONNXModelWrapper(ONNXModelIO())
