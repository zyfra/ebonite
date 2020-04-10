from typing import Tuple, Type

import numpy as np
from pyjackson.core import ArgList, Field
from pyjackson.errors import DeserializationError, SerializationError
from pyjackson.generics import Serializer

from ebonite.core.analyzer.base import CanIsAMustHookMixin, TypeHookMixin
from ebonite.core.analyzer.dataset import DatasetHook
from ebonite.core.objects.dataset_type import DatasetType, LibDatasetTypeMixin
from ebonite.core.objects.typing import ListTypeWithSpec, SizedTypedListType


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


class NumpyNumberDatasetType(LibDatasetTypeMixin):
    """
    :class:`.DatasetType` implementation for `numpy.number` objects which
    converts them to built-in Python numbers and vice versa.

    :param dtype: `numpy.number` data type as string
    """
    libraries = [np]

    def __init__(self, dtype: str):
        self.dtype = dtype

    def get_spec(self) -> ArgList:
        return [Field(None, self.actual_type, False)]

    def deserialize(self, obj: dict) -> object:
        return self.actual_type(obj)

    def serialize(self, instance: np.number) -> object:
        self._check_type(instance, np.number, SerializationError)
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

    def process(self, obj: np.number, **kwargs) -> DatasetType:
        return NumpyNumberDatasetType(obj.dtype.name)


class NumpyNdarrayHook(TypeHookMixin, DatasetHook):
    """
    :class:`.DatasetHook` implementation for `np.ndarray` objects which uses :class:`NumpyNdarrayDatasetType`
    """

    valid_types = [np.ndarray]

    def process(self, obj, **kwargs) -> DatasetType:
        return NumpyNdarrayDatasetType(obj.shape, obj.dtype.name)


class NumpyDTypeSerializer(Serializer):
    """
    PyJackson :class:`.Serializer` for `numpy` data types: stores types in JSON as their names.
    """

    def deserialize(self, obj: str):
        return getattr(np, obj)

    def serialize(self, instance) -> str:
        return str(instance)


class NumpyNdarrayDatasetType(ListTypeWithSpec, LibDatasetTypeMixin):
    """
    :class:`.DatasetType` implementation for `np.ndarray` objects
    which converts them to built-in Python lists and vice versa.

    :param shape: shape of `numpy.ndarray` objects in dataset
    :param dtype: data type of `numpy.ndarray` objects in dataset
    """

    real_type = np.ndarray
    libraries = [np]

    def __init__(self, shape: Tuple[int, ...], dtype: str):
        # TODO assert shape and dtypes len
        self.shape = (None, ) + shape[1:]
        self.dtype = dtype

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
        try:
            ret = np.array(obj, dtype=_np_type_from_string(self.dtype))
        except (ValueError, TypeError):
            raise DeserializationError(f'given object: {obj} could not be converted to array '
                                       f'of type: {_np_type_from_string(self.dtype)}')
        self._check_shape(ret, DeserializationError)
        return ret

    def serialize(self, instance: np.ndarray):
        self._check_type(instance, np.ndarray, SerializationError)
        exp_type = _np_type_from_string(self.dtype)
        if instance.dtype != exp_type:
            raise SerializationError(f'given array is of type: {instance.dtype}, expected: {exp_type}')
        self._check_shape(instance, SerializationError)
        return instance.tolist()

    def _check_shape(self, array, exc_type):
        if tuple(array.shape)[1:] != self.shape[1:]:
            raise exc_type(f'given array is of shape: {(None,) + tuple(array.shape)[1:]}, expected: {self.shape}')
