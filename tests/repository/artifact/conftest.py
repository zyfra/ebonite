import pytest

from ebonite.core.objects.artifacts import InMemoryBlob
from ebonite.core.objects.core import Model
from tests.conftest import interface_hook_creator


@pytest.fixture
def model():
    mdl = Model.create(lambda data: data, 'input', 'test_model')
    mdl._id = 'test_model_id'
    return mdl


@pytest.fixture
def blobs():
    return {'blob1': InMemoryBlob(b'blob1'), 'blob2': InMemoryBlob(b'blob2')}


create_artifact_hooks = interface_hook_creator('tests/repository/artifact/', 'meta_common.py', 'art_repo')
