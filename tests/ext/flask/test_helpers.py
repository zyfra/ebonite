import time

import pytest

from ebonite.build import run_docker_img
from ebonite.build.builder.base import use_local_installation
from ebonite.core.objects import Model
from ebonite.ext.flask import FlaskServer
from ebonite.ext.flask.helpers import build_model_flask_docker
from tests.build.conftest import has_docker, rm_container, rm_image
from tests.build.test_helpers import _assert_docker_container_running
from tests.client.test_func import func


@pytest.fixture  # FIXME did not find the way to import fixture from build module
def model():
    model = Model.create(func, "kek", "Test Model")
    return model


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
    container_name = f"ebontie-test-flask-image-{int(time.time() * 1000)}"
    yield container_name
    rm_container(container_name)


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_build_model_docker(model, server, img_name, container_name):
    with use_local_installation():
        build_model_flask_docker(img_name, model, force_overwrite=True)
    run_docker_img(container_name, img_name, detach=True)
    _assert_docker_container_running(container_name)
