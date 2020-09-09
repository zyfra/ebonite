import pytest

from ebonite.repository.artifact.local import LocalArtifactRepository
from ebonite.repository.dataset.artifact import ArtifactDatasetRepository
from tests.repository.dataset.conftest import create_dataset_hooks


@pytest.fixture
def artifact_dataset_repo(tmpdir_factory):
    return ArtifactDatasetRepository(LocalArtifactRepository(tmpdir_factory.mktemp('repo')))


pytest_runtest_protocol, pytest_collect_file = create_dataset_hooks(artifact_dataset_repo, 'artifact')
