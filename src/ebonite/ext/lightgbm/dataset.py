import lightgbm as lgb
from pyjackson.core import ArgList
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.dataset import DatasetAnalyzer, DatasetHook
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.core.objects.requirements import InstallableRequirement, Requirements


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
        self._check_type(instance, lgb.Dataset, SerializationError)
        return self.inner.serialize(instance.data)

    def deserialize(self, obj: dict) -> lgb.Dataset:
        v = self.inner.deserialize(obj)
        try:
            return lgb.Dataset(v, free_raw_data=False)
        except ValueError:
            raise DeserializationError(f'object: {obj} could not be converted to lightgbm dataset')

    @property
    def requirements(self) -> Requirements:
        return Requirements([InstallableRequirement.from_module(lgb)]) + self.inner.requirements

    @classmethod
    def from_dataset(cls, dataset: lgb.Dataset):
        return cls(DatasetAnalyzer.analyze(dataset.data))


class LightGBMDatasetHook(DatasetHook, TypeHookMixin):
    """
    :class:`.DatasetHook` implementation for `lightgbm.Dataset` type
    """
    valid_types = [lgb.Dataset]

    def process(self, obj, **kwargs) -> DatasetType:
        return LightGBMDatasetType.from_dataset(obj)
