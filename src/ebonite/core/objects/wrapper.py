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
from ebonite.core.objects.artifacts import ArtifactCollection, Blob, Blobs, CompositeArtifactCollection, InMemoryBlob
from ebonite.core.objects.base import EboniteParams
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.core.objects.requirements import InstallableRequirement, Requirements
from ebonite.utils.module import get_object_requirements
from ebonite.utils.pickling import EbonitePickler

FilesContextManager = typing.ContextManager[ArtifactCollection]
MethodArg = DatasetType
MethodReturn = DatasetType
Method = typing.Tuple[str, MethodArg, MethodReturn]
Methods = typing.Dict[str, Method]


@type_field('type')
class ModelIO(EboniteParams):
    """
    Helps model wrapper with IO

    Must be pyjackson-serializable
    """
    @abstractmethod
    def dump(self, model) -> FilesContextManager:
        """
        Must return context manager with :class:`~ebonite.core.objects.ArtifactCollection`
        :return: :class:`~ebonite.core.objects.ArtifactCollection`
        """
        pass  # pragma: no cover

    @abstractmethod
    def load(self, path):
        """
        Must load and return model
        :param path: path to load model from
        :return: model object
        """
        pass  # pragma: no cover


@type_field('type')
class ModelWrapper(EboniteParams):
    """
    Base class for model wrapper. Wrapper is an object that can save, load and inference a model

    Must be pyjackson-serializable
    """
    type = None
    methods_json = 'methods.json'
    requirements_json = 'requirements.json'

    def __init__(self, io: ModelIO):
        self.model = None
        self.methods: typing.Optional[Methods] = None
        self.requirements: Requirements = None
        self.io = io

    @contextlib.contextmanager
    def dump(self) -> FilesContextManager:
        with self.io.dump(self.model) as artifact:
            yield artifact + Blobs({
                self.methods_json: InMemoryBlob(dumps(self.methods).encode('utf-8')),
                self.requirements_json: InMemoryBlob(dumps(self.requirements).encode('utf-8'))
            })

    def load(self, path):
        self.model = self.io.load(path)
        self.methods = read(os.path.join(path, self.methods_json), typing.Optional[Methods])
        self.requirements = read(os.path.join(path, self.requirements_json), Requirements)

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
        self.methods, self.requirements = self._prepare_methods_and_requirements(input_data)
        return self

    def _prepare_methods_and_requirements(self, input_data):
        requirements = Requirements()
        requirements += self._model_requirements()

        arg_type = DatasetAnalyzer.analyze(input_data)
        requirements += arg_type.requirements

        methods = {}
        for exposed, wrapped in self._exposed_methods_mapping().items():
            output_data = self._call_method(wrapped, input_data)
            out_type = DatasetAnalyzer.analyze(output_data)

            methods[exposed] = (wrapped, arg_type, out_type)
            requirements += out_type.requirements
        return methods, requirements

    def unbind(self):
        """
        Unbind model object from this wrapper

        :return: self
        """
        self.model = None
        self.methods = None
        self.requirements = None
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

    def _model_requirements(self) -> Requirements:
        """
        Should return runtime requirements of bound model.
        By default auto-detects them via Python interpreter internals.
        This is not 100% robust so we recommend to re-implement this method in subclasses.

        :return: :class:`.Requirements` object representing runtime requirements of bound module object
        """
        return get_object_requirements(self.model)

    @abstractmethod
    def _exposed_methods_mapping(self) -> typing.Dict[str, str]:
        """
        Should return methods exposed by this model wrapper

        :return: methods dict: exposed method name to wrapped method name
        If model wrapper itself has such method then it is going to be called:
        this allows to wrap existing API with your own pre/postprocessing.
        Otherwise, wrapped model object method is going to be called.
        """
        pass  # pragma: no cover

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
        obj.io = self.io
        obj.model = self.model
        obj.methods = self.methods
        obj.requirements = self.requirements
        for field in get_class_fields(cls):
            setattr(obj, field.name, getattr(self, field.name))
        return obj


class LibModelWrapperMixin(ModelWrapper):
    """
    :class:`.ModelWrapper` mixin which provides model object requirements list consisting of
    PIP packages represented by module objects in `libraries` field.
    """
    libraries = None

    def _model_requirements(self) -> Requirements:
        return Requirements([InstallableRequirement.from_module(lib) for lib in self.libraries])


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
class PickleModelIO(ModelIO):
    """
    ModelIO for pickle-able models

    When model is dumped, recursively checks objects if they can be dumped with ModelIO instead of pickling

    So, if you use function that internally calls tensorflow model, this tensorflow model will be dumped with
    tensorflow code and not pickled
    """
    model_filename = 'model.pkl'
    io_ext = '.io'

    @contextlib.contextmanager
    def dump(self, model) -> ArtifactCollection:
        """
        Dumps model artifacts as :class:`~ebonite.core.objects.ArtifactCollection`

        :return: context manager with :class:`~ebonite.core.objects.ArtifactCollection`
        """
        model_blob, refs = self._serialize_model(model)
        blobs = {self.model_filename: InMemoryBlob(model_blob)}
        artifact_cms = []
        uuids = []

        for uuid, (io, obj) in refs.items():
            blobs[uuid + self.io_ext] = InMemoryBlob(self._serialize_io(io))
            artifact_cms.append(io.dump(obj))
            uuids.append(uuid)

        from ebonite.core.objects.artifacts import _enter_all_cm, _ExitAllCm, _RelativePathWrapper
        additional_artifacts = _enter_all_cm(artifact_cms)
        with _ExitAllCm(artifact_cms):
            additional_artifacts = [_RelativePathWrapper(art, uuid) for art, uuid in zip(additional_artifacts, uuids)]
            yield CompositeArtifactCollection([Blobs(blobs)] + additional_artifacts)

    def load(self, path):
        """
        Loads artifacts into model field

        :param path: path to load from
        """
        refs = {}
        for entry in os.listdir(path):
            if not entry.endswith(self.io_ext):
                continue

            with open(os.path.join(path, entry), 'rb') as f:
                io = self._deserialize_io(f)

            uuid = entry[:-len(self.io_ext)]
            refs[uuid] = io.load(os.path.join(path, uuid))

        with open(os.path.join(path, self.model_filename), 'rb') as f:
            return self._deserialize_model(f, refs)

    @staticmethod
    def _serialize_model(model):
        """
        Helper method to pickle model and get payload and refs

        :return: tuple of payload and refs
        """
        f = BytesIO()
        pklr = _ModelPickler(model, f, recurse=True)
        pklr.dump(model)
        return f.getvalue(), pklr.refs

    @staticmethod
    def _deserialize_model(in_file, refs):
        """
        Helper method to unpickle model from payload and refs

        :param in_file: payload
        :param refs: refs
        :return: unpickled model
        """
        return _ModelUnpickler(refs, in_file).load()

    @staticmethod
    def _serialize_io(io):
        """
        Helper method to serialize object's IO as ref

        :param io: :class:`ModelIO` instance
        :return: ref payload
        """
        io_type = type(io)
        return f'{io_type.__module__}.{io_type.__name__}'.encode('utf-8')

    @staticmethod
    def _deserialize_io(in_file):
        """
        Helper method to deserialize object's IO from ref payload

        :param in_file: ref payload
        :return: :class:`ModelIO` instance
        """
        io_type_full_name = in_file.read().decode('utf-8')
        *mod_name, type_name = io_type_full_name.split('.')
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

        # we couldn't import hook and analyzer at top as it leads to circular import failure
        from ebonite.core.analyzer.model import CallableMethodModelHook, ModelAnalyzer
        known_types = set()
        for hook in ModelAnalyzer.hooks:
            if not isinstance(hook, CallableMethodModelHook):
                known_types.update(hook.valid_types)
        self.known_types = tuple(known_types)

    # pickle "hook" for overriding serialization of objects
    def save(self, obj, save_persistent_id=True):
        """
        Checks if obj has IO.
        If it does, serializes object with :meth:`~ebonite.core.objects.wrapper.ModelIO.dump`
        and creates a ref to it. Otherwise, saves object as default pickle would do

        :param obj: obj to save
        :param save_persistent_id:
        :return:
        """
        if obj is self.model:
            # at starting point, follow usual path not to fall into infinite loop
            return super().save(obj, save_persistent_id)

        io = self._get_non_pickle_io(obj)
        if io is None:
            # no non-Pickle IO found, follow usual path
            return super().save(obj, save_persistent_id)

        # found model with non-pickle serialization:
        # replace with `_ExternalRef` stub and memorize IO to serialize model aside later
        obj_uuid = str(uuid4())
        self.refs[obj_uuid] = (io, obj)
        return super().save(_ExternalRef(obj_uuid), save_persistent_id)

    def _get_non_pickle_io(self, obj):
        """
        Checks if obj has non-Pickle IO and returns it

        :param obj: object to check
        :return: non-Pickle :class:`ModelIO` instance or None
        """

        # avoid calling heavy analyzer machinery for "unknown" objects:
        # they are either non-models or callables
        if not isinstance(obj, self.known_types):
            return None

        # we couldn't import analyzer at top as it leads to circular import failure
        from ebonite.core.analyzer.model import ModelAnalyzer
        try:
            io = ModelAnalyzer._find_hook(obj)._wrapper_factory().io
            return None if isinstance(io, PickleModelIO) else io
        except ValueError:
            # non-model object
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
    A class to mark objects dumped their own :class:`ModelIO`
    """

    def __init__(self, ref: str):
        self.ref = ref


class CallableMethodModelWrapper(ModelWrapper):
    """
    :class:`ModelWrapper` implementation for functions
    """
    type = 'callable_method'

    def __init__(self):
        super().__init__(PickleModelIO())

    def _exposed_methods_mapping(self) -> typing.Dict[str, str]:
        return {
            'predict': '__call__'
        }
