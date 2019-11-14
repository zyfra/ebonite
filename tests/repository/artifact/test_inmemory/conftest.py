import pytest

from ebonite.repository.artifact.inmemory import InMemoryArtifactRepository
from tests.repository.artifact.conftest import create_artifact_hooks


@pytest.fixture
def inmemory_artifact():
    yield InMemoryArtifactRepository()


pytest_runtest_protocol, pytest_collect_file = create_artifact_hooks(inmemory_artifact, 'inmemory')
