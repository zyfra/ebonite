from ebonite.core.objects import ArtifactCollection, DatasetType
from ebonite.core.objects.dataset_source import Dataset, DatasetReader, DatasetSource
from ebonite.repository import ArtifactRepository
from ebonite.repository.dataset.base import DatasetRepository


class ArtifactDatasetRepository(DatasetRepository):
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
    def __init__(self, reader: DatasetReader, artifacts: ArtifactCollection, dataset_type: DatasetType):
        super(ArtifactDatasetSource, self).__init__(dataset_type)
        self.reader = reader
        self.artifacts = artifacts

    def read(self) -> Dataset:
        return self.reader.read(self.artifacts)
