import os

import pytest

from ebonite.build.builder.base import use_local_installation
from ebonite.client import Ebonite
from tests.client.conftest import create_client_hooks



@pytest.fixture
def inmemory_ebnt():  # noqa

    ebnt = Ebonite.inmemory()

    yield ebnt


pytest_runtest_protocol, pytest_collect_file = create_client_hooks(inmemory_ebnt, 'inmemory')
