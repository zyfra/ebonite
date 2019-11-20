import lightgbm as lgb
from pyjackson.core import ArgList
from pyjackson.decorators import as_list

from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.dataset import DatasetHook
from ebonite.core.objects import DatasetType


@as_list
class LightGBMDatasetType(DatasetType):
    type = 'lightgbm_dataset'

    real_type = lgb.Dataset

    def get_spec(self) -> ArgList:
        pass

    def serialize(self, instance: lgb.Dataset) -> list:
        return instance.data

    def deserialize(self, obj: list) -> lgb.Dataset:
        return lgb.Dataset(obj)


class DMatrixHook(DatasetHook, TypeHookMixin):
    valid_types = [lgb.Dataset]

    def process(self, obj) -> DatasetType:
        return LightGBMDatasetType()
