import pytest

from ebonite.client import Ebonite
from tests.client.conftest import create_client_hooks


@pytest.fixture
def inmemory_ebnt():
    ebnt = Ebonite.inmemory()
    yield ebnt


pytest_runtest_protocol, pytest_collect_file = create_client_hooks(inmemory_ebnt, 'inmemory')
