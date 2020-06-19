from ebonite.core.objects.dataset_source import Dataset, DatasetSource, InMemoryDatasetSource
from ebonite.repository.dataset.base import DatasetRepository


class InMemoryDatasetRepository(DatasetRepository):
    def save(self, dataset_id: str, dataset: Dataset) -> DatasetSource:
        return InMemoryDatasetSource(dataset)
