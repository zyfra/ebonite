from typing import Tuple

import pytest

from ebonite.core.objects import ArtifactCollection, DatasetType
from ebonite.core.objects.artifacts import Blobs, InMemoryBlob
from ebonite.core.objects.dataset_source import Dataset
from ebonite.repository.dataset.artifact import DatasetReader, DatasetWriter
from tests.conftest import interface_hook_creator


class TestDatasetWriter(DatasetWriter):
    def write(self, dataset: Dataset) -> Tuple[DatasetReader, ArtifactCollection]:
        return TestDatasetReader(), Blobs({'data': InMemoryBlob(dataset.data.encode('utf8'))})


class TestDatasetReader(DatasetReader):
    def read(self, artifacts: ArtifactCollection) -> Dataset:
        return Dataset(artifacts.bytes_dict()['data'].decode('utf8'), TestDatasetType())


class TestDatasetType(DatasetType):

    def get_writer(self):
        return TestDatasetWriter()

    def deserialize(self, obj: dict) -> object:
        return obj

    def serialize(self, instance: object) -> dict:
        return instance


@pytest.fixture
def data() -> Dataset:
    return Dataset('abcdefg', TestDatasetType())


create_dataset_hooks = interface_hook_creator('tests/repository/dataset/', 'dataset_common.py', 'dataset_repo')
