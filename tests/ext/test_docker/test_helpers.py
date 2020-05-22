# import time
#
# import pytest
#
# from ebonite.build.builder.base import use_local_installation
# from ebonite.ext.flask import FlaskServer
# from tests.conftest import docker_test

# @pytest.fixture
# def server():
#     return FlaskServer()
#
#
# @pytest.fixture
# def img_name():
#     img_name = "helper-test-image"
#     with use_local_installation():
#         yield img_name
#
#     rm_image(img_name + ":latest")  # FIXME later
#
#
# @pytest.fixture
# def container_name():
#     container_name = "ebaklya"
#     yield container_name
#     rm_container(container_name)
#
#
# @pytest.fixture
# def service_name():
#     service_name = 'ebnt-test-service'
#     yield service_name
#     rm_container(service_name)
#     rm_image(service_name + ":latest")


# @docker_test
# def test_run_docker_img(container_name):
#     run_docker_img(container_name, 'mike0sv/ebaklya', ports_mapping={80: None}, detach=True)
#     _assert_docker_container_running(container_name)
#
#
# def _assert_docker_container_running(name):
#     time.sleep(.1)
#     assert is_docker_container_running(name)
