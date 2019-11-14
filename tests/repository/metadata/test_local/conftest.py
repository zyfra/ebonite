import os

import pytest

from ebonite.repository.metadata.local import LocalMetadataRepository
from tests.repository.metadata.conftest import create_metadata_hooks


@pytest.fixture
def local_meta(tmpdir):
    yield LocalMetadataRepository(os.path.join(tmpdir, 'db.json'))


pytest_runtest_protocol, pytest_collect_file = create_metadata_hooks(local_meta, 'local')
