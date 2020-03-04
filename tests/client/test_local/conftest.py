import pytest

from ebonite.build.builder.base import use_local_installation
from ebonite.client import Ebonite
from tests.client.conftest import create_client_hooks


@pytest.fixture
def local_ebnt(tmpdir):
    with use_local_installation():
        yield Ebonite.local(str(tmpdir))


pytest_runtest_protocol, pytest_collect_file = create_client_hooks(local_ebnt, 'local')
