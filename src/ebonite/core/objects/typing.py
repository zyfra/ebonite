from abc import abstractmethod
from typing import Union

from pyjackson.core import ArgList, Field
from pyjackson.generics import Serializer


class TypeWithSpec(Serializer):
    """
    Abstract base class for types providing its OpenAPI schema definition
    """

    @abstractmethod
    def get_spec(self) -> ArgList:
        pass  # pragma: no cover

    def is_list(self):
        return False

    @abstractmethod
    def list_size(self):
        pass  # pragma: no cover


class ListTypeWithSpec(TypeWithSpec):
    """
    Abstract base class for `list`-like types providing its OpenAPI schema definition
    """

    def is_list(self):
        return True

    @abstractmethod
    def list_size(self):
        return NotImplementedError  # pragma: no cover


class SizedTypedListType(ListTypeWithSpec):
    """
    Subclass of :class:`ListTypeWithSpec` which specifies size of internal `list`
    """

    def __init__(self, size: Union[int, None], dtype: type):
        self.dtype = dtype
        self.size = size

    def get_spec(self) -> ArgList:
        return [Field(0, self.dtype, False)]

    def list_size(self):
        return self.size

    @abstractmethod
    def deserialize(self, obj):
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def serialize(self, instance):
        raise NotImplementedError  # pragma: no cover
