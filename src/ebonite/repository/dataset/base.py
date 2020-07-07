from abc import abstractmethod

from ebonite.core.objects.dataset_source import Dataset, DatasetSource


class DatasetRepository:
    """Base class for persisting datasets"""

    @abstractmethod
    def save(self, dataset_id: str, dataset: Dataset) -> DatasetSource:
        """Method to save dataset to this repository

        :param dataset_id: string identifier
        :param dataset: dataset to save
        :returns: DatasetSource that produces same Dataset"""

    @abstractmethod
    def delete(self, dataset_id: str):
        """Method to delete dataset from this repository

        :param dataset_id: dataset identifier
        """
