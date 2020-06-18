from abc import abstractmethod
from collections import Iterable
from typing import Any, Optional

from pyjackson.core import Unserializable
from pyjackson.decorators import type_field

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.base import EboniteParams
from ebonite.core.objects.dataset_type import DatasetType


class AbstractDataset(Unserializable):
    def __init__(self, dataset_type: DatasetType):
        self.dataset_type = dataset_type

    @abstractmethod
    def iterate(self) -> Iterable:
        pass

    @abstractmethod
    def get(self):
        pass


class Dataset(AbstractDataset):
    def __init__(self, data: Any, dataset_type: DatasetType):
        super().__init__(dataset_type)
        self.data = data

    @abstractmethod
    def iterate(self) -> Iterable:
        return iter(self.data)

    @abstractmethod
    def get(self):
        return self.data

    @classmethod
    def from_object(cls, data):
        return cls(data, DatasetAnalyzer.analyze(data))


@type_field('type')
class DatasetSource(EboniteParams):
    # TODO docs
    def __init__(self, dataset_type: DatasetType):
        self.dataset_type = dataset_type

    @abstractmethod
    def read(self) -> Dataset:
        raise NotImplementedError()

    def cache(self):
        return CachedDatasetSource(self)


class CachedDatasetSource(DatasetSource):
    def __init__(self, source: DatasetSource):
        super().__init__(source.dataset_type)
        self.source = source
        self._cache: Optional[Dataset] = None

    def read(self) -> Dataset:
        if self._cache is None:
            self._cache = self.source.read()
        return self._cache

    def cache(self):
        return self


class InMemoryDatasetSource(CachedDatasetSource, ):  # Unserializable
    def __init__(self, dataset: Dataset):
        super().__init__(DatasetSource(dataset.dataset_type))
        self._cache = dataset


@type_field('type')
class DatasetWriter(EboniteParams):
    @abstractmethod
    def write(self, dataset: Dataset) -> DatasetSource:
        pass


class InMemoryDatasetWriter(DatasetWriter):
    def write(self, dataset: Dataset) -> DatasetSource:
        return InMemoryDatasetSource(dataset)
# class BlobDatasetSource(DatasetSource):
#     def __init__(self, blob: Blob, dataset_type: DatasetType, target_type: DatasetType = None):
#         super(BlobDatasetSource, self).__init__(dataset_type, target_type)
#         self.blob = blob

# class ArtifactDatasetSource(DatasetSource):
#     def __init__(self, artifacts: ArtifactCollection, dataset_type: DatasetType, target_type: DatasetType = None):
#         super(ArtifactDatasetSource, self).__init__(dataset_type, target_type)
#         self.artifacts = artifacts
