from abc import abstractmethod
from typing import Tuple

from pyjackson.decorators import type_field

from ebonite.core.objects import ArtifactCollection, DatasetType
from ebonite.core.objects.base import EboniteParams
from ebonite.core.objects.dataset_source import Dataset, DatasetSource
from ebonite.repository import ArtifactRepository
from ebonite.repository.dataset.base import DatasetRepository


@type_field('type')
class DatasetReader(EboniteParams):
    """ABC for reading Dataset from files (artifacts) to use with ArtifactDatasetSource"""

    @abstractmethod
    def read(self, artifacts: ArtifactCollection) -> Dataset:
        """Method to read Dataset from artifacts

        :param artifacts: artifacts to read"""


@type_field('type')
class DatasetWriter(EboniteParams):
    """ABC for writing Dataset to files (artifacts) to use with ArtifactDatasetSource"""

    @abstractmethod
    def write(self, dataset: Dataset) -> Tuple[DatasetReader, ArtifactCollection]:
        """Method to write dataset to artifacts

        :param dataset: dataset to write
        :returns: tuple of DatasetReader and ArtifactCollection.
        DatasetReader must produce the same dataset if used with same artifacts"""


class ArtifactDatasetRepository(DatasetRepository):
    """DatasetRpository implementation that saves datasets as artifacts to ArtifactRepository

    :param repo: underlying ArtifactRepository"""
    ARTIFACT_TYPE = 'datasets'

    def __init__(self, repo: ArtifactRepository):
        self.repo = repo

    def save(self, dataset_id: str, dataset: Dataset) -> DatasetSource:
        writer = dataset.get_writer()
        if writer is None:
            raise ValueError(f'{dataset.dataset_type} does not support artifacat persistance')

        reader, artifacts = writer.write(dataset)
        with artifacts.blob_dict() as blobs:
            pushed = self.repo.push_artifact(self.ARTIFACT_TYPE, dataset_id, blobs)
        return ArtifactDatasetSource(reader, pushed, dataset.dataset_type)


class ArtifactDatasetSource(DatasetSource):
    """DatasetSource for reading datasets from ArtifactDatasetRepository

    :param reader: DatasetReader for this dataset
    :param artifacts: ArtifactCollection with actual files
    :param dataset_type: DatasetType of contained dataset"""

    def __init__(self, reader: DatasetReader, artifacts: ArtifactCollection, dataset_type: DatasetType):
        super(ArtifactDatasetSource, self).__init__(dataset_type)
        self.reader = reader
        self.artifacts = artifacts

    def read(self) -> Dataset:
        return self.reader.read(self.artifacts)
