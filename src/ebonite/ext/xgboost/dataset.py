import xgboost
from pyjackson.core import ArgList
from pyjackson.decorators import as_list

from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.dataset import DatasetHook
from ebonite.core.objects import DatasetType


@as_list
class DMatrixDatasetType(DatasetType):
    type = 'xgboost_dmatrix'

    real_type = xgboost.DMatrix

    def get_spec(self) -> ArgList:
        pass

    def serialize(self, instance: xgboost.DMatrix) -> list:
        raise RuntimeError('DMatrixDatasetType does not support serialization')

    def deserialize(self, obj: list) -> xgboost.DMatrix:
        return xgboost.DMatrix(obj)


class DMatrixHook(DatasetHook, TypeHookMixin):
    valid_types = [xgboost.DMatrix]

    def process(self, obj) -> DatasetType:
        return DMatrixDatasetType()
