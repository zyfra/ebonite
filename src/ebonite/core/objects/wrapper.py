import contextlib
import os
import pickle
import typing
from abc import abstractmethod
from functools import wraps
from importlib import import_module
from io import BytesIO
from pickle import _Unpickler
from uuid import uuid4

from pyjackson import dumps, read
from pyjackson.core import Unserializable
from pyjackson.decorators import type_field
from pyjackson.utils import get_class_fields

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.artifacts import (ArtifactCollection, Blob, Blobs, CompositeArtifactCollection, InMemoryBlob,
                                            _RelativePathWrapper)
from ebonite.core.objects.base import EboniteParams
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.utils.pickling import EbonitePickler

FilesContextManager = typing.ContextManager[ArtifactCollection]
MethodArg = DatasetType
MethodReturn = DatasetType
Method = typing.Tuple[str, MethodArg, MethodReturn]
Methods = typing.Dict[str, Method]


@type_field('type')
class ModelWrapper(EboniteParams):
    """
    Base class for model wrapper. Wrapper is an object that can save, load and inference a model
    Must be pyjackson-serializable
    """
    type = None
    methods_json = 'methods.json'

    def __init__(self):
        self.model = None
        self.methods: typing.Optional[Methods] = None

    @contextlib.contextmanager
    def dump(self) -> FilesContextManager:
        with self._dump() as artifact:
            yield artifact + Blobs({self.methods_json: InMemoryBlob(dumps(self.methods).encode('utf-8'))})

    @abstractmethod
    def _dump(self) -> FilesContextManager:
        """
        Must return context manager with :class:`~ebonite.core.objects.ArtifactCollection`
        :return: :class:`~ebonite.core.objects.ArtifactCollection`
        """
        pass

    def load(self, path):
        self._load(path)
        self.methods = read(os.path.join(path, self.methods_json), typing.Optional[Methods])

    @abstractmethod
    def _load(self, path):
        """
        Must load and set internal .model field
        :param path:
        :return:
        """
        pass

    def bind_model(self, model, input_data=None, **kwargs):
        """
        Bind model object to this wrapper by using given input data sample

        :param model: model object to bind
        :param input_data: input data sample to determine model methods signatures
        :param kwargs: additional information to be used for analysis
        :return: self
        """
        if input_data is None:
            raise ValueError("Input data sample should be specified as 'input_data' key in order to analyze model")

        self.model = model
        self.methods = self._prepare_methods(input_data)
        return self

    def _prepare_methods(self, input_data):
        arg_type = DatasetAnalyzer.analyze(input_data)
        methods = {}
        for exposed, wrapped in self._exposed_methods_mapping().items():
            output_data = self._call_method(wrapped, input_data)
            out_type = DatasetAnalyzer.analyze(output_data)
            methods[exposed] = (wrapped, arg_type, out_type)
        return methods

    def unbind(self):
        """
        Unbind model object from this wrapper

        :return: self
        """
        self.model = None
        self.methods = None
        return self

    @property
    def exposed_methods(self) -> typing.Set[str]:
        if self.methods is None:
            raise ValueError('Wrapper {} has no model yet'.format(self))
        return set(self.methods.keys())

    def method_signature(self, name) -> typing.Tuple[DatasetType, DatasetType]:
        """
        Determines input / output types of model wrapper method with given name

        :param name: name of the method to determine input / output types
        :return: input / output type of method with given name
        """
        self._check_method(name)
        _, *signature = self.methods[name]
        return signature

    def call_method(self, name, input_data):
        """
        Calls model wrapper method with given name on given input data

        :param name: name of the method to call
        :param input_data: argument for the method
        :return: call result
        """
        self._check_method(name)
        wrapped, *_ = self.methods[name]
        output_data = self._call_method(wrapped, input_data)
        return output_data

    def _check_method(self, name):
        if self.model is None:
            raise ValueError('Wrapper {} has no model yet'.format(self))
        if name not in self.methods:
            raise ValueError(f"Wrapper '{self}' obj doesn't expose method '{name}'")

    def _call_method(self, wrapped, input_data):
        if hasattr(self, wrapped):
            return getattr(self, wrapped)(input_data)
        return getattr(self.model, wrapped)(input_data)

    @abstractmethod
    def _exposed_methods_mapping(self) -> typing.Dict[str, str]:
        """
        Should return methods exposed by this model wrapper

        :return: methods dict: exposed method name to wrapped method name
        If model wrapper itself has such method then it is going to be called:
        this allows to wrap existing API with your own pre/postprocessing.
        Otherwise, wrapped model object method is going to be called.
        """
        pass

    @staticmethod
    def with_model(f):
        """
        Decorator to mark method that only works when model is binded, for example save or predict

        :param f: method
        :return: decorated method
        """

        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if self.model is None:
                raise ValueError('Wrapper {} has no model yet'.format(self))
            return f(self, *args, **kwargs)

        return wrapper

    def __deepcopy__(self, memo):
        cls = type(self)
        obj = object.__new__(cls)
        obj.model = self.model
        obj.methods = self.methods
        for field in get_class_fields(cls):
            setattr(obj, field.name, getattr(self, field.name))
        return obj


class WrapperArtifactCollection(ArtifactCollection, Unserializable):
    """
    This is a proxy ArtifactCollection for not persisted artifacts.
    Internally uses :meth:`~ebonite.core.objects.ModelWrapper.dump` to create model artifacts

    :param wrapper: :class:`ModelWrapper` instance
    """
    type = '_wrapper'

    def __init__(self, wrapper: ModelWrapper):
        self.wrapper = wrapper

    def materialize(self, path):
        """
        Calls :meth:`~ebonite.core.objects.ModelWrapper.dump` to materialize model in path

        :param path: path to materialize model
        """
        with self.wrapper.dump() as art:
            art.materialize(path)

    def bytes_dict(self) -> typing.Dict[str, bytes]:
        """
        Calls :meth:`~ebonite.core.objects.wrapper.ModelWrapper.dump` to get model artifacts bytes dict
        :return: dict artifact name -> bytes
        """
        with self.wrapper.dump() as art:
            return art.bytes_dict()

    @contextlib.contextmanager
    def blob_dict(self) -> typing.Iterable[typing.Dict[str, Blob]]:
        """
        Calls :meth:`~ebonite.core.objects.wrapper.ModelWrapper.dump` to get model artifacts blob dict

        :return: dict artifact name -> :class:`~ebonite.core.objects.artifacts.Blob`
        """
        with self.wrapper.dump() as art, art.blob_dict() as blobs:
            yield blobs


# noinspection PyAbstractClass
class PickleModelWrapper(ModelWrapper):
    """
    ModelWrapper for pickle-able models

    When model is dumped, recursively checks objects if they can be dumped with ModelWrapper instead of pickling

    So, if you use function that internally calls tensorflow model, this tensorflow model will be dumped with
    tensorflow code and not pickled
    """
    model_filename = 'model.pkl'
    wrapper_ext = '.wrapper'

    @ModelWrapper.with_model
    @contextlib.contextmanager
    def _dump(self) -> ArtifactCollection:
        """
        Dumps model artifacts as :class:`~ebonite.core.objects.ArtifactCollection`

        :return: context manager with :class:`~ebonite.core.objects.ArtifactCollection`
        """
        model_blob, refs = self._serialize_model()
        blobs = {self.model_filename: InMemoryBlob(model_blob)}
        additional_artifacts = []

        for uuid, wrapper in refs.items():
            blobs[uuid + self.wrapper_ext] = InMemoryBlob(self._serialize_wrapper(wrapper))
            with wrapper.dump() as artifact:
                additional_artifacts.append(_RelativePathWrapper(artifact, uuid))

        yield CompositeArtifactCollection([Blobs(blobs)] + additional_artifacts)

    def _load(self, path):
        """
        Loads artifacts into model field

        :param path: path to load from
        """
        refs = {}
        for entry in os.listdir(path):
            if not entry.endswith(self.wrapper_ext):
                continue

            with open(os.path.join(path, entry), 'rb') as f:
                wrapper = self._deserialize_wrapper(f)

            uuid = entry[:-len(self.wrapper_ext)]
            wrapper.load(os.path.join(path, uuid))
            refs[uuid] = wrapper.model

        with open(os.path.join(path, self.model_filename), 'rb') as f:
            self.model = self._deserialize_model(f, refs)

    def _serialize_model(self):
        """
        Helper method to pickle model and get payload and refs

        :return: tuple of payload and refs
        """
        f = BytesIO()
        pklr = _ModelPickler(self.model, f, recurse=True)
        pklr.dump(self.model)
        return f.getvalue(), pklr.refs

    def _deserialize_model(self, in_file, refs):
        """
        Helper method to unpickle model from payload and refs

        :param in_file: payload
        :param refs: refs
        :return: unpickled model
        """
        return _ModelUnpickler(refs, in_file).load()

    def _serialize_wrapper(self, wrapper):
        """
        Helper method to serialize object's wrapper as ref

        :param wrapper: :class:`ModelWrapper` instance
        :return: ref payload
        """
        wrap_type = type(wrapper)
        return f'{wrap_type.__module__}.{wrap_type.__name__}'.encode('utf-8')

    def _deserialize_wrapper(self, in_file):
        """
        Helper method to deserialize object's wrapper from ref payload

        :param in_file: ref payload
        :return: :class:`ModelWrapper` instance
        """
        wrapper_type_full_name = in_file.read().decode('utf-8')
        *mod_name, type_name = wrapper_type_full_name.split('.')
        mod_name, pkg_name = '.'.join(mod_name), '.'.join(mod_name[:-1])
        return import_module(mod_name, pkg_name).__dict__[type_name]()


class _ModelPickler(EbonitePickler):
    """
    A class to pickle model with respect to wrappers of inner objects

    :param model: model object to serialize
    :param args: dill.Pickler args
    :param kwargs: dill.Pickler kwargs
    """

    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.refs = {}

    # pickle "hook" for overriding serialization of objects
    def save(self, obj, save_persistent_id=True):
        """
        Checks if obj has wrapper.
        If it does, serializes object with :meth:`~ebonite.core.objects.wrapper.ModelWrapper.dump`
        and creates a ref to it. Otherwise, saves object as default pickle would do

        :param obj: obj to save
        :param save_persistent_id:
        :return:
        """
        if obj is self.model:
            # at starting point, follow usual path not to fall into infinite loop
            return super().save(obj, save_persistent_id)

        wrapper = self._safe_analyze(obj)
        if wrapper is None or isinstance(wrapper, PickleModelWrapper):
            # no wrapper or Pickle wrapper found, follow usual path
            return super().save(obj, save_persistent_id)

        # found model with non-pickle serialization:
        # replace with `_ExternalRef` stub and memorize wrapper to serialize model aside later
        obj_uuid = str(uuid4())
        self.refs[obj_uuid] = wrapper
        return super().save(_ExternalRef(obj_uuid), save_persistent_id)

    def _safe_analyze(self, obj):
        """
        Checks if obj has wrapper

        :param obj: object to check
        :return: :class:`ModelWrapper` instance or None
        """
        # we couldn't import analyzer at top as it leads to circular import failure
        from ebonite.core.analyzer.model import ModelAnalyzer
        try:
            return ModelAnalyzer.analyze(obj)
        except ValueError:
            return None


# We couldn't use `EboniteUnpickler` here as it (in fact `dill`) subclasses `Unpickler`
# `Unpickler`, unlike `_Unpickler`, doesn't support `load_build` overriding
class _ModelUnpickler(_Unpickler):
    """
    A class to unpickle model saved with :class:`_ModelPickler`

    :param refs: dict of object uuid -> it's :attr:`ModelWrapper.model`
    :param args: pickle._Unpickler args
    :param kwargs: pickle._Unpickle kwargs
    """
    dispatch = _Unpickler.dispatch.copy()

    def __init__(self, refs, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.refs = refs

    # pickle "hook" for overriding deserialization of objects
    def load_build(self):
        """
        Checks if last builded object is :class:`_ExternalRef` and if it is, swaps it with referenced object
        :return:
        """
        super().load_build()

        # this is the last deserialized object for now
        obj = self.stack[-1]
        if not isinstance(obj, _ExternalRef):
            return

        # replace `_ExternalRef` with a real model it references
        self.stack.pop()
        self.stack.append(self.refs[obj.ref])

    dispatch[pickle.BUILD[0]] = load_build


class _ExternalRef:
    """
    A class to mark objects dumped their own :class:`ModelWrapper`
    """

    def __init__(self, ref: str):
        self.ref = ref


class CallableMethodModelWrapper(PickleModelWrapper):
    """
    :class:`ModelWrapper` implementation for functions
    """
    type = 'callable_method'

    def _exposed_methods_mapping(self) -> typing.Dict[str, str]:
        return {
            'predict': '__call__'
        }
