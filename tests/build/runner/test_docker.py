import pytest

from ebonite.build.runner.base import LocalTargetHost, TargetHost
from ebonite.build.runner.simple_docker import DefaultDockerRegistry, DockerImage, DockerServiceInstance, \
    SimpleDockerRunner
from requests.exceptions import HTTPError

from tests.build.builder.test_docker import has_docker
from tests.build.conftest import has_local_image, is_container_running, stop_container, rm_container, rm_image

DOCKER_IMAGE_NAME = 'ebaas-test'
CONTAINER_NAME = 'ebonite-runner-test-docker-container'


@pytest.fixture
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def runner():
    args = []

    def _runner(host: TargetHost, img: DockerImage, container_name: str):
        args.append((host, img, container_name))
        return SimpleDockerRunner()

    yield _runner

    for h, i, c in args:
        rm_container(c, h.get_host())
        rm_image(i.get_image_uri, h.get_host())


@pytest.mark.docker
@pytest.mark.skipif(not has_local_image('mike0sv/ebaklya'), reason='no local mike0sv/ebaklya image found')
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_run_local(runner):
    img_registry = DefaultDockerRegistry()
    img = DockerImage('mike0sv/ebaklya', docker_registry=img_registry)

    host = LocalTargetHost()

    instance = DockerServiceInstance(CONTAINER_NAME, img, host, {80: 8080})

    if is_container_running(CONTAINER_NAME):
        stop_container(CONTAINER_NAME, host)

    runner = runner(host, img, CONTAINER_NAME)
    runner.run(instance, detach=True)
    assert is_container_running(CONTAINER_NAME, host)


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_run_remote_default_registry(runner):
    img_registry = DefaultDockerRegistry()
    img = DockerImage('mike0sv/ebaklya', docker_registry=img_registry)
    host = LocalTargetHost()
    instance = DockerServiceInstance(CONTAINER_NAME, img, host, {80: 8080})

    if is_container_running(CONTAINER_NAME):
        stop_container(CONTAINER_NAME, host)

    runner = runner(host, img, CONTAINER_NAME)
    runner.run(instance)
    assert is_container_running(CONTAINER_NAME, host)


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_run_local_image_name_that_will_never_exist(runner):
    img_registry = DefaultDockerRegistry()
    img = DockerImage('ebonite_image_name_that_will_never_exist', docker_registry=img_registry)

    host = LocalTargetHost()

    instance = DockerServiceInstance(CONTAINER_NAME, img, host, {80: 8080})

    if is_container_running(CONTAINER_NAME):
        stop_container(CONTAINER_NAME, host)

    with pytest.raises(HTTPError):
        runner = runner(host, img, CONTAINER_NAME)
        runner.run(instance)
