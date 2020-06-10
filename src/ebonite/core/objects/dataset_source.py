from abc import abstractmethod
from collections import Iterable

from pyjackson.decorators import type_field

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.base import EboniteParams
from ebonite.core.objects.dataset_type import DatasetType


@type_field('type')
class DatasetSource(EboniteParams):

    def __init__(self, dataset_type: DatasetType, target_type: DatasetType = None):
        self.target_type = target_type
        self.dataset_type = dataset_type

    @property
    def has_target(self):
        return self.target_type is not None

    @abstractmethod
    def iterate(self) -> Iterable:
        pass

    @abstractmethod
    def get(self):
        pass

    @abstractmethod
    def get_target(self):
        pass


class InMemoryDataset(DatasetSource):  # TODO Unserializable

    def __init__(self, dataset_type: DatasetType, data: object, target_type: DatasetType = None, target: object = None):
        super().__init__(dataset_type, target_type)
        self.target = target
        self.data = data

    def iterate(self) -> Iterable:
        return self.data

    def get(self):
        return self.data

    def get_target(self):
        return self.target

    @classmethod
    def from_object(cls, data, target=None):
        return cls(DatasetAnalyzer.analyze(data), data,
                   DatasetAnalyzer.analyze(target) if target is not None else None,
                   target)
