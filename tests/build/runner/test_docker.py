import os

import pytest

from ebonite.build.runner.base import LocalTargetHost, TargetHost
from ebonite.build.runner.simple_docker import DefaultDockerRegistry, DockerImage, DockerRunnerException, \
    DockerServiceInstance, RemoteDockerRegistry, SimpleDockerRunner

from docker import DockerClient
from requests.exceptions import HTTPError
from testcontainers.core.container import DockerContainer

from tests.build.builder.test_docker import has_docker
from tests.build.conftest import is_container_running, stop_container, rm_container, rm_image


IMAGE_NAME = 'mike0sv/ebaklya'
BROKEN_IMAGE_NAME = 'test-broken-image'
CONTAINER_NAME = 'ebonite-runner-test-docker-container'

REGISTRY_PORT = 5000
REGISTRY_HOST = 'localhost:5000'
REPOSITORY_NAME = 'ebonite'
TAG_NAME = f'{REGISTRY_HOST}/{REPOSITORY_NAME}/{IMAGE_NAME}'
BROKEN_TAG_NAME = f'{REGISTRY_HOST}/{REPOSITORY_NAME}/{BROKEN_IMAGE_NAME}'


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


# fixture that ensures that Docker registry is up between tests
@pytest.fixture(scope='module')
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def registry(tmpdir_factory):
    with DockerContainer('registry:latest').with_bind_ports(REGISTRY_PORT, REGISTRY_PORT):
        client = DockerClient()

        # migrate our image to custom Docker registry
        client.images.pull(IMAGE_NAME, 'latest').tag(TAG_NAME)
        client.images.push(TAG_NAME)

        tmpdir = str(tmpdir_factory.mktemp("image"))
        # create failing image: alpine is too small to have python inside
        with open(os.path.join(tmpdir, 'Dockerfile'), 'w') as f:
            f.write("""
                FROM alpine:latest

                CMD python
           """)
        client.images.build(path=tmpdir, tag=BROKEN_TAG_NAME)
        client.images.push(BROKEN_TAG_NAME)

        yield RemoteDockerRegistry(REGISTRY_HOST)


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_run_default_registry(runner):
    img_registry = DefaultDockerRegistry()
    img = DockerImage(IMAGE_NAME, docker_registry=img_registry)

    host = LocalTargetHost()

    instance = DockerServiceInstance(CONTAINER_NAME, img, host, {80: 8080})

    if is_container_running(CONTAINER_NAME):
        stop_container(CONTAINER_NAME, host)

    runner = runner(host, img, CONTAINER_NAME)
    runner.run(instance, detach=True)
    assert is_container_running(CONTAINER_NAME, host)


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_run_remote_registry(runner, registry):
    img = DockerImage(IMAGE_NAME,
                      repository=REPOSITORY_NAME,
                      docker_registry=registry)
    host = LocalTargetHost()
    instance = DockerServiceInstance(CONTAINER_NAME, img, host)

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


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_run_local_fail_inside_container(runner, registry):
    img = DockerImage(BROKEN_IMAGE_NAME,
                      repository=REPOSITORY_NAME,
                      docker_registry=registry)
    host = LocalTargetHost()
    instance = DockerServiceInstance(CONTAINER_NAME, img, host, {80: 8080})

    if is_container_running(CONTAINER_NAME):
        stop_container(CONTAINER_NAME, host)

    with pytest.raises(DockerRunnerException):
        runner = runner(host, img, CONTAINER_NAME)
        runner.run(instance, detach=True, rm=True)


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_run_local_fail_inside_container_attached(runner, registry):
    img = DockerImage(BROKEN_IMAGE_NAME,
                      repository=REPOSITORY_NAME,
                      docker_registry=registry)
    host = LocalTargetHost()
    instance = DockerServiceInstance(CONTAINER_NAME, img, host, {80: 8080})

    if is_container_running(CONTAINER_NAME):
        stop_container(CONTAINER_NAME, host)

    with pytest.raises(DockerRunnerException):
        runner = runner(host, img, CONTAINER_NAME)
        runner.run(instance, detach=False, rm=True)
