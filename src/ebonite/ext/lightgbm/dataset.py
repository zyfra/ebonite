import lightgbm as lgb
from pyjackson.core import ArgList
from pyjackson.decorators import as_list

from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.dataset import DatasetAnalyzer, DatasetHook
from ebonite.core.objects import DatasetType


@as_list
class LightGBMDatasetType(DatasetType):
    """
    :class:`.DatasetType` implementation for `lightgbm.Dataset` type

    :param inner: :class:`.DatasetType` instance for underlying data
    """

    real_type = lgb.Dataset

    def __init__(self, inner: DatasetType):
        self.inner = inner

    def is_list(self):
        return self.inner.is_list()

    def list_size(self):
        return self.inner.list_size()

    def get_spec(self) -> ArgList:
        return self.inner.get_spec()

    def serialize(self, instance: lgb.Dataset) -> dict:
        return self.inner.serialize(instance.data)

    def deserialize(self, obj: dict) -> lgb.Dataset:
        return lgb.Dataset(self.inner.deserialize(obj), free_raw_data=False)

    @classmethod
    def from_dataset(cls, dataset: lgb.Dataset):
        return cls(DatasetAnalyzer.analyze(dataset.data))


class LightGBMDatasetHook(DatasetHook, TypeHookMixin):
    """
    :class:`.DatasetHook` implementation for `lightgbm.Dataset` type
    """
    valid_types = [lgb.Dataset]

    def process(self, obj) -> DatasetType:
        return LightGBMDatasetType.from_dataset(obj)
