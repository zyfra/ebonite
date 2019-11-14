import pytest
from ebonite.build.builder.base import use_local_installation

from ebonite.build.helpers import build_model_docker, run_docker_img, create_service_from_model
from ebonite.ext.flask import FlaskServer

from tests.build.conftest import has_docker, has_local_image, is_container_running, rm_container, rm_image, train_model


@pytest.fixture
def server():
    return FlaskServer()


@pytest.fixture
def img_name():
    img_name = "helper-test-image"
    with use_local_installation():
        yield img_name

    rm_image(img_name + ":latest")  # FIXME latter


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
def test_build_model_docker(model, server, img_name):
    with use_local_installation():
        build_model_docker(img_name, model, server)
    assert has_local_image(img_name)


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_run_docker_img(container_name):
    run_docker_img(container_name, 'mike0sv/ebaklya', detach=True)
    assert is_container_running(container_name)


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_create_service_from_model(service_name):
    reg, data = train_model()
    with use_local_installation():
        create_service_from_model(model_name='test_model', model_object=reg, model_input=data,
                                  service_name=service_name, run_service=True)
    assert is_container_running(service_name)
