import builtins
from typing import Dict, List

from pyjackson import deserialize, serialize
from pyjackson.core import ArgList, Field
from pyjackson.decorators import as_list, type_field

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
        return self.to_type(obj)

    def serialize(self, instance):
        return instance


@as_list
class ListDatasetType(DatasetType):
    """
    DatasetType for list type
    """
    real_type = list
    type = 'list'

    def __init__(self, items: List[DatasetType]):
        self.items = items

    def get_spec(self) -> ArgList:
        return [Field(i, t, False) for i, t in enumerate(self.item_types)]

    def deserialize(self, obj):
        return [deserialize(o, t) for t, o in zip(self.items, obj)]

    def serialize(self, instance: list):
        return [serialize(o, t) for t, o in zip(self.items, instance)]


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
        return {k: deserialize(v, self.item_types[k]) for k, v in obj.items()}

    def serialize(self, instance: real_type):
        return {
            k: serialize(v, self.item_types[k]) for k, v in instance.items()
        }


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
