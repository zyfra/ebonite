import time

import pytest

from ebonite.core.objects.core import Model
from tests.build.builder.test_docker import has_docker
from tests.build.conftest import rm_container, rm_image
from tests.client.test_func import func
from tests.conftest import interface_hook_creator

CONTAINER_NAME = "ebonite-test-service"

CLEAR = True  # flag to disable removal of containers for easy inspection and debugging


@pytest.fixture
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def container_name():
    name = "{}-{}".format(CONTAINER_NAME, int(time.time() * 1000))
    yield name

    if not CLEAR:
        return

    rm_container(name)
    rm_image(name + ":latest")  # FIXME later


@pytest.fixture  # FIXME did not find the way to import fixture from build module
def model():
    model = Model.create(func, "kek", "Test Model")
    return model


create_client_hooks = interface_hook_creator('tests/client/', 'client_common.py', 'ebnt')
