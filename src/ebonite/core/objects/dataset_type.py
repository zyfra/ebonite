import builtins
from typing import Dict, List

from pyjackson import deserialize, serialize
from pyjackson.core import ArgList, Field
from pyjackson.decorators import type_field
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.objects.base import EboniteParams
from ebonite.runtime.interface.typing import TypeWithSpec


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
        return PrimitiveDatasetType[str(type(obj))]

    @property
    def to_type(self):
        return getattr(builtins, self.ptype)

    def get_spec(self) -> ArgList:
        return [Field(None, self.to_type, False)]

    def deserialize(self, obj):
        try:
            return self.to_type(obj)
        except ValueError:
            raise DeserializationError(f'given object: {obj} could not be converted to {self.to_type}')

    def serialize(self, instance):
        self._check_type(instance, self.to_type, SerializationError)
        return instance


class ListDatasetType(DatasetType):
    """
    DatasetType for list type
    """
    real_type = list
    type = 'list'

    def __init__(self, items: List[DatasetType]):
        self.items = items

    def get_spec(self) -> ArgList:
        return [Field(i, t, False) for i, t in enumerate(self.items)]

    def deserialize(self, obj):
        self._check_type_and_size(obj, DeserializationError)
        return [deserialize(o, t) for t, o in zip(self.items, obj)]

    def serialize(self, instance: list):
        self._check_type_and_size(instance, SerializationError)
        return [serialize(o, t) for t, o in zip(self.items, instance)]

    def _check_type_and_size(self, obj, exc_type):
        self._check_type(obj, list, exc_type)
        if len(obj) != len(self.items):
            raise exc_type(f'given list has len: {len(obj)}, expected: {len(self.items)}')


class DictDatasetType(DatasetType):
    """
    DatasetType for dict type
    """
    real_type = dict
    type = 'dict'

    def __init__(self, item_types: Dict[str, DatasetType]):
        self.item_types = item_types

    def get_spec(self) -> ArgList:
        return [Field(name, t, False) for name, t in self.item_types.items()]

    def deserialize(self, obj):
        self._check_type_and_keys(obj, DeserializationError)
        return {k: deserialize(v, self.item_types[k]) for k, v in obj.items()}

    def serialize(self, instance: real_type):
        self._check_type_and_keys(instance, SerializationError)
        return {
            k: serialize(v, self.item_types[k]) for k, v in instance.items()
        }

    def _check_type_and_keys(self, obj, exc_type):
        self._check_type(obj, dict, exc_type)
        if set(obj.keys()) != set(self.item_types.keys()):
            raise exc_type(f'given dict has keys: {set(obj.keys())}, expected: {set(self.item_types.keys())}')


class FilelikeDatasetType(DatasetType):
    """
    DatasetType for file-like objects
    """
    type = 'filelike'
    real_type = None

    def __init__(self):
        pass

    def get_spec(self) -> ArgList:
        return [Field('file', bytes, False)]

    def deserialize(self, obj) -> object:
        return obj

    def serialize(self, instance: object) -> dict:
        return instance
