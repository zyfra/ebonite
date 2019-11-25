from typing import Tuple

import torch
from pyjackson.core import ArgList, Field

from ebonite.core.analyzer.base import TypeHookMixin
from ebonite.core.analyzer.dataset import DatasetHook
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.runtime.interface.typing import ListTypeWithSpec, SizedTypedListType


class TorchTensorHook(TypeHookMixin, DatasetHook):
    """
    :class:`.DatasetHook` implementation for `torch.Tensor` objects which uses :class:`TorchTensorDatasetType`
    """
    valid_types = [torch.Tensor]

    def process(self, obj) -> DatasetType:
        return TorchTensorDatasetType(tuple(obj.shape), str(obj.dtype)[len('torch.'):])


class TorchTensorDatasetType(DatasetType, ListTypeWithSpec):
    """
    :class:`.DatasetType` implementation for `torch.Tensor` objects
    which converts them to built-in Python lists and vice versa.

    :param shape: shape of `torch.Tensor` objects in dataset
    :param dtype: data type of `torch.Tensor` objects in dataset
    """

    real_type = torch.Tensor

    def __init__(self, shape: Tuple[int, ...], dtype: str):
        self.shape = shape
        self.dtype = dtype

    @property
    def size(self):
        if len(self.shape) == 1:
            return 1
        else:
            return self.shape[0]

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
        known_types = ['float', 'int']
        for known_type in known_types:
            if dtype_str.startswith(known_type):
                return __builtins__[known_type]
        raise ValueError(f'unsupported tensor dtype {dtype_str}')

    def get_spec(self) -> ArgList:
        return [Field(None, self._get_subtype(self.shape[1:]), False)]

    def deserialize(self, obj):
        return torch.tensor(obj, dtype=getattr(torch, self.dtype))

    def serialize(self, instance: torch.Tensor):
        return instance.tolist()
