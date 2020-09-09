import pytest

from ebonite.core.errors import DatasetExistsError, NoSuchDataset
from ebonite.core.objects.dataset_source import Dataset
from ebonite.repository import DatasetRepository


def test_save(dataset_repo: DatasetRepository, data: Dataset):
    source = dataset_repo.save('a', data)
    data2 = source.read()

    assert data2.data == data.data
    assert data2.dataset_type == data.dataset_type


def test_save_existing(dataset_repo: DatasetRepository, data: Dataset):
    dataset_repo.save('a', data)

    with pytest.raises(DatasetExistsError):
        dataset_repo.save('a', data)


def test_delete(dataset_repo: DatasetRepository, data: Dataset):
    source = dataset_repo.save('a', data)
    dataset_repo.delete('a')
    with pytest.raises(Exception):
        source.read()


def test_delete_not_existing(dataset_repo: DatasetRepository):
    with pytest.raises(NoSuchDataset):
        dataset_repo.delete('a')
