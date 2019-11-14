import pytest

from ebonite.repository.artifact.local import LocalArtifactRepository
from tests.repository.artifact.conftest import create_artifact_hooks


@pytest.fixture
def local_artifact(tmpdir_factory):
    yield LocalArtifactRepository(tmpdir_factory.mktemp('repo'))


pytest_runtest_protocol, pytest_collect_file = create_artifact_hooks(local_artifact, 'local')
