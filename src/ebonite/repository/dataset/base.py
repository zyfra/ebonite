from abc import abstractmethod

from ebonite.core.objects.dataset_source import Dataset, DatasetSource


class DatasetRepository:
    @abstractmethod
    def save(self, dataset_id: str, dataset: Dataset) -> DatasetSource:
        pass
