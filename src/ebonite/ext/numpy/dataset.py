from typing import Tuple, Type

import numpy as np
from pyjackson.core import ArgList, Field
from pyjackson.generics import Serializer

from ebonite.core.analyzer.base import CanIsAMustHookMixin, TypeHookMixin
from ebonite.core.analyzer.dataset import DatasetHook
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.runtime.interface.typing import ListTypeWithSpec, SizedTypedListType


def _python_type_from_np_string_repr(string_repr: str) -> type:
    np_type = _np_type_from_string(string_repr)
    return _python_type_from_np_type(np_type)


def _python_type_from_np_type(np_type: Type):
    value = np_type()
    if np_type.__module__ == 'numpy':
        value = value.item()
    return type(value)


def _np_type_from_string(string_repr):
    try:
        return getattr(np, string_repr)
    except AttributeError:
        raise ValueError('Unknown numpy type {}'.format(string_repr))


class NumpyNumberDatasetType(DatasetType):
    """
    :class:`.DatasetType` implementation for `numpy.number` objects which
    converts them to built-in Python numbers and vice versa.

    :param dtype: `numpy.number` data type as string
    """

    type = 'numpy_number'

    def __init__(self, dtype: str):
        self.dtype = dtype

    def get_spec(self) -> ArgList:
        return [Field(None, self.actual_type, False)]

    def deserialize(self, obj: dict) -> object:
        return self.actual_type(obj)

    def serialize(self, instance: np.number) -> object:
        return instance.item()

    @property
    def actual_type(self):
        return _np_type_from_string(self.dtype)


class NumpyNumberHook(CanIsAMustHookMixin, DatasetHook):
    """
    :class:`.DatasetHook` implementation for `numpy.number` objects which uses :class:`NumpyNumberDatasetType`.
    """

    def must_process(self, obj) -> bool:
        return isinstance(obj, np.number)

    def process(self, obj: np.number) -> DatasetType:
        return NumpyNumberDatasetType(obj.dtype.name)


class NumpyNdarrayHook(TypeHookMixin, DatasetHook):
    """
    :class:`.DatasetHook` implementation for `np.ndarray` objects which uses :class:`NumpyNdarrayDatasetType`
    """

    valid_types = [np.ndarray]

    def process(self, obj) -> DatasetType:
        return NumpyNdarrayDatasetType(obj.shape, obj.dtype.name)


class NumpyDTypeSerializer(Serializer):
    """
    PyJackson :class:`.Serializer` for `numpy` data types: stores types in JSON as their names.
    """

    def deserialize(self, obj: str):
        return getattr(np, obj)

    def serialize(self, instance) -> str:
        return str(instance)


class NumpyNdarrayDatasetType(DatasetType, ListTypeWithSpec):
    """
    :class:`.DatasetType` implementation for `np.ndarray` objects
    which converts them to built-in Python lists and vice versa.

    :param shape: shape of `numpy.ndarray` objects in dataset
    :param dtype: data type of `numpy.ndarray` objects in dataset
    """

    real_type = np.ndarray
    type = 'numpy_ndarray'

    def __init__(self, shape: Tuple[int, ...], dtype: str):
        # TODO assert shape and dtypes len
        self.shape = shape
        self.dtype = dtype

    @property
    def size(self):
        if len(self.shape) == 1:
            return 1
        else:
            return self.shape[0]  # TODO more dimensions

    def list_size(self):
        return self.shape[0]

    def _get_subtype(self, shape):
        if len(shape) == 0:
            return _python_type_from_np_string_repr(self.dtype)
        elif len(shape) == 1:
            subtype = _python_type_from_np_string_repr(self.dtype)
        else:
            subtype = self._get_subtype(shape[1:])
        return SizedTypedListType(shape[0], subtype)

    def get_spec(self) -> ArgList:
        return [Field(None, self._get_subtype(self.shape[1:]), False)]

    def deserialize(self, obj):
        return np.array(obj)

    def serialize(self, instance: np.ndarray):
        # if self.shape == 1:
        #     return [instance.tolist()]  # TODO better shapes
        return instance.tolist()
