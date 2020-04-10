from typing import Tuple

import tensorflow as tf
from pyjackson.core import ArgList, Field
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.dataset import DatasetHook
from ebonite.core.objects.dataset_type import DatasetType, LibDatasetTypeMixin
from ebonite.core.objects.typing import ListTypeWithSpec, SizedTypedListType


class TFTensorDatasetType(ListTypeWithSpec, LibDatasetTypeMixin):
    """
    :class:`.DatasetType` implementation for `tensorflow.Tensor` objects
    which converts them to built-in Python lists and vice versa.

    :param shape: shape of `tensorflow.Tensor` objects in dataset
    :param dtype: data type of `tensorflow.Tensor` objects in dataset
    """

    real_type = tf.Tensor
    libraries = [tf]

    def __init__(self, shape: Tuple[int, ...], dtype: str):
        self.shape = (None, ) + shape[1:]
        self.dtype = dtype

    def list_size(self):
        return self.shape[0]

    def _get_subtype(self, shape):
        if len(shape) == 0:
            return self._get_dtype_from_str(self.dtype)
        elif len(shape) == 1:
            subtype = self._get_dtype_from_str(self.dtype)
        else:
            subtype = self._get_subtype(shape[1:])
        return SizedTypedListType(shape[0], subtype)

    @staticmethod
    def _get_dtype_from_str(dtype_str: str):
        known_types = {'float', 'int', 'bool', 'complex', 'str'}
        for known_type in known_types:
            if dtype_str.startswith(known_type):
                return __builtins__[known_type]
        raise ValueError(f'unsupported tensor dtype {dtype_str}')

    def get_spec(self) -> ArgList:
        return [Field(None, self._get_subtype(self.shape[1:]), False)]

    def deserialize(self, obj):
        try:
            ret = tf.convert_to_tensor(obj, dtype=getattr(tf, self.dtype))
        except (ValueError, TypeError):
            raise DeserializationError(f'given object: {obj} could not be converted to tensor '
                                       f'of type: {getattr(tf, self.dtype)}')
        self._check_shape(ret, DeserializationError)
        return ret

    def serialize(self, instance: tf.Tensor):
        self._check_type(instance, tf.Tensor, SerializationError)
        if instance.dtype is not getattr(tf, self.dtype):
            raise SerializationError(f'given tensor is of dtype: {instance.dtype}, '
                                     f'expected: {getattr(tf, self.dtype)}')
        self._check_shape(instance, SerializationError)
        return instance.numpy().tolist()

    def _check_shape(self, tensor, exc_type):
        if tuple(tensor.shape)[1:] != self.shape[1:]:
            raise exc_type(f'given tensor is of shape: {(None,) + tuple(tensor.shape)[1:]}, expected: {self.shape}')


class TFTensorHook(TypeHookMixin, DatasetHook):
    """
    :class:`.DatasetHook` implementation for `tensorflow.Tensor` objects which uses :class:`.TFTensorDatasetType`
    """
    valid_types = [tf.Tensor]

    def process(self, obj, **kwargs) -> DatasetType:
        return TFTensorDatasetType(tuple(obj.shape), obj.dtype.name)
