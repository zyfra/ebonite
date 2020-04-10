import builtins
from abc import abstractmethod
from typing import Dict, List, Sized

from pyjackson import deserialize, serialize
from pyjackson.core import ArgList, Field
from pyjackson.decorators import type_field
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.objects.base import EboniteParams
from ebonite.core.objects.requirements import InstallableRequirement, Requirements
from ebonite.core.objects.typing import SizedTypedListType, TypeWithSpec


# noinspection PyAbstractClass
@type_field('type')
class DatasetType(EboniteParams, TypeWithSpec):
    """
    Base class for dataset type metadata.
    Children of this class must be both pyjackson-serializable and be a pyjackson serializer for it's dataset type
    """
    type = None

    @staticmethod
    def _check_type(obj, exp_type, exc_type):
        if not isinstance(obj, exp_type):
            raise exc_type(f'given dataset is of type: {type(obj)}, expected: {exp_type}')

    @property
    @abstractmethod
    def requirements(self) -> Requirements:
        pass  # pragma: no cover


class LibDatasetTypeMixin(DatasetType):
    """
    :class:`.DatasetType` mixin which provides requirements list consisting of
    PIP packages represented by module objects in `libraries` field.
    """
    libraries = None

    @property
    def requirements(self) -> Requirements:
        return Requirements([InstallableRequirement.from_module(lib) for lib in self.libraries])


PRIMITIVES = {int, str, bool, complex, float}


class PrimitiveDatasetType(DatasetType):
    """
    DatasetType for int, str, bool, complex and float types
    """
    type = 'primitive'

    def __init__(self, ptype: str):
        self.ptype = ptype

    @classmethod
    def from_object(cls, obj):
        if type(obj) not in PRIMITIVES:
            raise ValueError('{} type is not primitive')
        return PrimitiveDatasetType(str(type(obj)))

    @property
    def to_type(self):
        return getattr(builtins, self.ptype)

    def get_spec(self) -> ArgList:
        return [Field(None, self.to_type, False)]

    def deserialize(self, obj):
        try:
            return self.to_type(obj)
        except (ValueError, TypeError):
            raise DeserializationError(f'given object: {obj} could not be converted to {self.to_type}')

    def serialize(self, instance):
        self._check_type(instance, self.to_type, SerializationError)
        return instance

    @property
    def requirements(self) -> Requirements:
        return Requirements()


class ListDatasetType(DatasetType, SizedTypedListType):
    """
    DatasetType for list type
    """
    real_type = None
    type = 'list'

    def __init__(self, dtype: DatasetType, size: int):
        SizedTypedListType.__init__(self, size, dtype)

    def deserialize(self, obj):
        _check_type_and_size(obj, list, self.size, DeserializationError)
        return [deserialize(o, self.dtype) for o in obj]

    def serialize(self, instance: list):
        _check_type_and_size(instance, list, self.size, SerializationError)
        return [serialize(o, self.dtype) for o in instance]

    @property
    def requirements(self) -> Requirements:
        return self.dtype.requirements


class _TupleLikeDatasetType(DatasetType):
    """
    DatasetType for tuple-like collections
    """
    real_type = None

    def __init__(self, items: List[DatasetType]):
        self.items = items

    def get_spec(self) -> ArgList:
        return [Field(str(i), t, False) for i, t in enumerate(self.items)]

    def deserialize(self, obj):
        _check_type_and_size(obj, self.actual_type, len(self.items), DeserializationError)
        return self.actual_type(deserialize(o, t) for t, o in zip(self.items, obj))

    def serialize(self, instance: Sized):
        _check_type_and_size(instance, self.actual_type, len(self.items), SerializationError)
        return self.actual_type(serialize(o, t) for t, o in zip(self.items, instance))

    @property
    def requirements(self) -> Requirements:
        return sum([i.requirements for i in self.items], Requirements())


def _check_type_and_size(obj, dtype, size, exc_type):
    DatasetType._check_type(obj, dtype, exc_type)
    if len(obj) != size:
        raise exc_type(f'given {dtype.__name__} has len: {len(obj)}, expected: {size}')


class TupleLikeListDatasetType(_TupleLikeDatasetType):
    """
    DatasetType for tuple-like list type
    """
    actual_type = list
    type = 'tuple_like_list'


class TupleDatasetType(_TupleLikeDatasetType):
    """
    DatasetType for tuple type
    """
    actual_type = tuple
    type = 'tuple'


class DictDatasetType(DatasetType):
    """
    DatasetType for dict type
    """
    real_type = None
    type = 'dict'

    def __init__(self, item_types: Dict[str, DatasetType]):
        self.item_types = item_types

    def get_spec(self) -> ArgList:
        return [Field(name, t, False) for name, t in self.item_types.items()]

    def deserialize(self, obj):
        self._check_type_and_keys(obj, DeserializationError)
        return {k: deserialize(v, self.item_types[k]) for k, v in obj.items()}

    def serialize(self, instance: dict):
        self._check_type_and_keys(instance, SerializationError)
        return {
            k: serialize(v, self.item_types[k]) for k, v in instance.items()
        }

    def _check_type_and_keys(self, obj, exc_type):
        self._check_type(obj, dict, exc_type)
        if set(obj.keys()) != set(self.item_types.keys()):
            raise exc_type(f'given dict has keys: {set(obj.keys())}, expected: {set(self.item_types.keys())}')

    @property
    def requirements(self) -> Requirements:
        return sum([i.requirements for i in self.item_types.values()], Requirements())


class BytesDatasetType(DatasetType):
    """
    DatasetType for bytes objects
    """
    type = 'bytes'
    real_type = None

    def __init__(self):
        pass

    def get_spec(self) -> ArgList:
        return [Field('file', bytes, False)]

    def deserialize(self, obj) -> object:
        return obj

    def serialize(self, instance: object) -> dict:
        return instance

    @property
    def requirements(self) -> Requirements:
        return Requirements()
