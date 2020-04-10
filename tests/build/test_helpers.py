import time

import pytest

from ebonite.build.builder.base import use_local_installation
from ebonite.build.helpers import is_docker_container_running, run_docker_img

from ebonite.ext.flask import FlaskServer

from tests.build.conftest import has_docker, rm_container, rm_image


@pytest.fixture
def server():
    return FlaskServer()


@pytest.fixture
def img_name():
    img_name = "helper-test-image"
    with use_local_installation():
        yield img_name

    rm_image(img_name + ":latest")  # FIXME later


@pytest.fixture
def container_name():
    container_name = "ebaklya"
    yield container_name
    rm_container(container_name)


@pytest.fixture
def service_name():
    service_name = 'ebnt-test-service'
    yield service_name
    rm_container(service_name)
    rm_image(service_name + ":latest")


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_run_docker_img(container_name):
    run_docker_img(container_name, 'mike0sv/ebaklya', detach=True)
    _assert_docker_container_running(container_name)


def _assert_docker_container_running(name):
    time.sleep(.1)
    assert is_docker_container_running(name)
