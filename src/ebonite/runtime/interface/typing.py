from abc import abstractmethod
from typing import Union

from pyjackson.core import ArgList, Field
from pyjackson.decorators import as_list
from pyjackson.generics import Serializer


class TypeWithSpec(Serializer):
    """
    Abstract base class for types providing its OpenAPI schema definition
    """

    @abstractmethod
    def get_spec(self) -> ArgList:
        pass

    def is_list(self):
        return False

    def list_size(self):
        pass


class ListTypeWithSpec(TypeWithSpec):
    """
    Abstract base class for `list`-like types providing its OpenAPI schema definition
    """

    def is_list(self):
        return True

    @abstractmethod
    def list_size(self):
        return NotImplementedError


@as_list
class SizedTypedListType(ListTypeWithSpec):
    """
    Subclass of :class:`ListTypeWithSpec` which specifies size of internal `list`
    """

    real_type = list

    def __init__(self, size: Union[int, None], dtype: type):
        self.dtype = dtype
        self.size = size

    def get_spec(self) -> ArgList:
        return [Field(0, self.dtype, False)]

    def list_size(self):
        return self.size

    def deserialize(self, obj):
        raise NotImplementedError

    def serialize(self, instance):
        raise NotImplementedError
