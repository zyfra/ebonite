from abc import abstractmethod
from collections import Iterable
from typing import Any

from pyjackson.core import Unserializable
from pyjackson.decorators import type_field

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.base import EboniteParams
from ebonite.core.objects.dataset_type import DatasetType


class AbstractDataset(Unserializable):
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


class Dataset(AbstractDataset):
    def __init__(self, data: Any, dataset_type: DatasetType, target: Any = None, target_type: DatasetType = None):
        super().__init__(dataset_type, target_type)
        self.data = data
        self.target = target

    @abstractmethod
    def iterate(self) -> Iterable:
        return iter(self.data)

    @abstractmethod
    def get(self):
        return self.data

    @abstractmethod
    def get_target(self):
        return self.target

    @classmethod
    def from_object(cls, data, target=None):
        return cls(data, DatasetAnalyzer.analyze(data),
                   target, DatasetAnalyzer.analyze(target) if target is not None else None)


@type_field('type')
class DatasetSource(EboniteParams):
    # TODO docs
    def __init__(self, dataset_type: DatasetType, target_type: DatasetType = None):
        self.target_type = target_type
        self.dataset_type = dataset_type

    @abstractmethod
    def read(self) -> Dataset:
        raise NotImplementedError()


@type_field('type')
class DatasetWriter(EboniteParams):
    @abstractmethod
    def write(self, dataset: Dataset) -> DatasetSource:
        pass

# class BlobDatasetSource(DatasetSource):
#     def __init__(self, blob: Blob, dataset_type: DatasetType, target_type: DatasetType = None):
#         super(BlobDatasetSource, self).__init__(dataset_type, target_type)
#         self.blob = blob

# class ArtifactDatasetSource(DatasetSource):
#     def __init__(self, artifacts: ArtifactCollection, dataset_type: DatasetType, target_type: DatasetType = None):
#         super(ArtifactDatasetSource, self).__init__(dataset_type, target_type)
#         self.artifacts = artifacts
