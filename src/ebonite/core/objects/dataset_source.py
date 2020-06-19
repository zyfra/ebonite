from abc import abstractmethod
from collections import Iterable
from typing import Any, Optional, Tuple

from pyjackson.core import Unserializable
from pyjackson.decorators import type_field

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects import ArtifactCollection
from ebonite.core.objects.base import EboniteParams
from ebonite.core.objects.dataset_type import DatasetType


class AbstractDataset(Unserializable):
    def __init__(self, dataset_type: DatasetType):
        self.dataset_type = dataset_type
        self.writer = None
        self.reader = None

    @abstractmethod
    def iterate(self) -> Iterable:
        pass

    @abstractmethod
    def get(self):
        pass

    @abstractmethod
    def get_writer(self) -> 'DatasetWriter':
        """"""  # TODO docs
        return self.writer or self.dataset_type.get_writer()

    @abstractmethod
    def get_reader(self) -> 'DatasetReader':
        """"""
        return self.reader or self.dataset_type.get_reader()


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

    def to_inmemory_source(self) -> 'InMemoryDatasetSource':
        return InMemoryDatasetSource(self)


@type_field('type')
class DatasetSource(EboniteParams):
    is_dynamic = False

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


class InMemoryDatasetSource(CachedDatasetSource, Unserializable):
    def __init__(self, dataset: Dataset):
        super().__init__(DatasetSource(dataset.dataset_type))
        self._cache = dataset


@type_field('type')
class DatasetReader(EboniteParams):
    @abstractmethod
    def read(self, artifacts: ArtifactCollection) -> Dataset:
        pass


@type_field('type')
class DatasetWriter(EboniteParams):
    @abstractmethod
    def write(self, dataset: Dataset) -> Tuple[DatasetReader, ArtifactCollection]:
        pass
