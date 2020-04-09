from typing import List

import xgboost
from pyjackson.core import ArgList, Field
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.dataset import DatasetHook
from ebonite.core.objects.dataset_type import DatasetType, LibDatasetTypeMixin
from ebonite.ext.numpy.dataset import _python_type_from_np_string_repr


class DMatrixDatasetType(LibDatasetTypeMixin):
    """
    :class:`~.DatasetType` implementation for xgboost.DMatrix type

    :param is_from_list: whether DMatrix can be constructed from list
    :param feature_types: string representation of feature types
    :param feature_names: list of feature names
    """

    real_type = xgboost.DMatrix
    libraries = [xgboost]

    def __init__(self, is_from_list: bool, feature_type_names: List[str], feature_names: List[str] = None):
        self.is_from_list = is_from_list
        self.feature_type_names = feature_type_names or ['float32' for _ in range(len(feature_names))]
        self.feature_names = feature_names

    def is_list(self):
        return self.is_from_list

    def list_size(self):
        return len(self.feature_names)

    @property
    def feature_types(self):
        return [_python_type_from_np_string_repr(t) for t in self.feature_type_names]

    def get_spec(self) -> ArgList:
        return [Field(n, t, False) for n, t in zip(self.feature_names, self.feature_types)]

    def serialize(self, instance: xgboost.DMatrix) -> list:
        """
        Raises an error because there is no way to extract original data from DMatrix
        """
        raise SerializationError('xgboost matrix does not support serialization')

    def deserialize(self, obj: list) -> xgboost.DMatrix:
        try:
            return xgboost.DMatrix(obj)
        except (ValueError, TypeError):
            raise DeserializationError(f'given object: {obj} could not be converted to xgboost matrix')

    @classmethod
    def from_dmatrix(cls, dmatrix: xgboost.DMatrix):
        """
        Factory method to extract :class:`~.DatasetType` from actual xgboost.DMatrix

        :param dmatrix: obj to create :class:`~.DatasetType` from
        :return: :class:`DMatrixDatasetType`
        """
        is_from_list = (dmatrix.feature_names == [f'f{i}' for i in range(dmatrix.num_col())])
        return DMatrixDatasetType(is_from_list, dmatrix.feature_types, dmatrix.feature_names)


class DMatrixHook(DatasetHook, TypeHookMixin):
    """
    :class:`.DatasetHook` implementation for `xgboost.DMatrix` objects
    """
    valid_types = [xgboost.DMatrix]

    def process(self, obj: xgboost.DMatrix, **kwargs) -> DatasetType:
        return DMatrixDatasetType.from_dmatrix(obj)
