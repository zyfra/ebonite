from abc import abstractmethod
from collections import Iterable
from typing import Any, Optional

from pyjackson.core import Unserializable
from pyjackson.decorators import type_field

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.base import EboniteParams
from ebonite.core.objects.dataset_type import DatasetType


class AbstractDataset(Unserializable):
    """ABC for Dataset objects

    :param dataset_type: DatasetType instance for the data in the Dataset"""

    def __init__(self, dataset_type: DatasetType):
        self.dataset_type = dataset_type
        self.writer = None
        self.reader = None

    @abstractmethod
    def iterate(self) -> Iterable:
        """Abstract method to iterate through data"""

    @abstractmethod
    def get(self):
        """Abstract method to get data object"""

    @abstractmethod
    def get_writer(self):
        """Returns writer for this dataset. Defaults to dataset_type.get_writer()"""
        return self.writer or self.dataset_type.get_writer()

    @abstractmethod
    def get_reader(self):
        """Returns reader for this dataset. Defaults to dataset_type.get_reader()"""
        return self.reader or self.dataset_type.get_reader()


class Dataset(AbstractDataset):
    """Wrapper for dataset objects

    :param data: raw dataset
    :param dataset_type: DatasetType of the raw data"""

    def __init__(self, data: Any, dataset_type: DatasetType):
        super().__init__(dataset_type)
        self.data = data

    def iterate(self) -> Iterable:
        return iter(self.data)

    def get(self):
        return self.data

    @classmethod
    def from_object(cls, data):
        """Creates Dataset instance from raw data object"""
        return cls(data, DatasetAnalyzer.analyze(data))

    def to_inmemory_source(self) -> 'InMemoryDatasetSource':
        """Returns :class:`.InMemoryDatasetSource` with this dataset"""
        return InMemoryDatasetSource(self)


@type_field('type')
class DatasetSource(EboniteParams):
    """Class that represents a source that can produce a Dataset

    :param dataset_type: DatasetType of contained dataset"""
    is_dynamic = False

    def __init__(self, dataset_type: DatasetType):
        self.dataset_type = dataset_type

    @abstractmethod
    def read(self) -> Dataset:
        """Abstract method that must return produced Dataset instance"""
        raise NotImplementedError()

    def cache(self):
        """Returns :class:`.CachedDatasetSource` that will cache data on the first read"""
        return CachedDatasetSource(self)


class CachedDatasetSource(DatasetSource):
    """Wrapper that will cache the result of underlying source on the first read

    :param source: underlying DatasetSource"""

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
    """DatasetSource that holds existing dataset inmemory

    :param dataset: Dataset instance to hold"""

    def __init__(self, dataset: Dataset):
        super().__init__(DatasetSource(dataset.dataset_type))
        self._cache = dataset
