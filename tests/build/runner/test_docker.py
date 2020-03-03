import os
import time

import pytest

from ebonite.build.docker import DefaultDockerRegistry, DockerImage, RemoteDockerRegistry
from ebonite.build.runner.docker import DockerRunner, DockerRunnerException, DockerRuntimeInstance

from docker import DockerClient
from requests.exceptions import HTTPError
from testcontainers.core.container import DockerContainer

from tests.build.builder.test_docker import has_docker
from tests.build.conftest import rm_container, rm_image


IMAGE_NAME = 'mike0sv/ebaklya'
BROKEN_IMAGE_NAME = 'test-broken-image'
CONTAINER_NAME = 'ebonite-runner-test-docker-container'

REGISTRY_PORT = 5000
REGISTRY_HOST = f'localhost:{REGISTRY_PORT}'
REPOSITORY_NAME = 'ebonite'
TAG_NAME = f'{REGISTRY_HOST}/{REPOSITORY_NAME}/{IMAGE_NAME}'
BROKEN_TAG_NAME = f'{REGISTRY_HOST}/{REPOSITORY_NAME}/{BROKEN_IMAGE_NAME}'


@pytest.fixture
def runner(pytestconfig):
    if not has_docker() or 'not docker' in pytestconfig.getoption('markexpr'):
        pytest.skip('skipping docker tests')
    args = []

    def _runner(host: str, img: DockerImage, container_name: str):
        args.append((host, img, container_name))
        return DockerRunner()

    yield _runner

    for h, i, c in args:
        rm_container(c, h)
        rm_image(i.get_uri(), h)


# fixture that ensures that Docker registry is up between tests
@pytest.fixture(scope='module')
def registry(tmpdir_factory, pytestconfig):
    if not has_docker() or 'not docker' in pytestconfig.getoption('markexpr'):
        pytest.skip('skipping docker tests')
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
    img = DockerImage(IMAGE_NAME, registry=img_registry)

    _check_runner(runner, img)


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_run_remote_registry(runner, registry):
    img = DockerImage(IMAGE_NAME,
                      repository=REPOSITORY_NAME,
                      registry=registry)

    _check_runner(runner, img)


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_run_local_image_name_that_will_never_exist(runner):
    img_registry = DefaultDockerRegistry()
    img = DockerImage('ebonite_image_name_that_will_never_exist', registry=img_registry)

    with pytest.raises(HTTPError):
        _check_runner(runner, img)


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
@pytest.mark.parametrize('detach', [True, False])
def test_run_local_fail_inside_container(runner, registry, detach):
    img = DockerImage(BROKEN_IMAGE_NAME,
                      repository=REPOSITORY_NAME,
                      registry=registry)

    with pytest.raises(DockerRunnerException):
        _check_runner(runner, img, detach=detach, rm=True)


def _check_runner(runner, img, host='', **kwargs):
    runner = runner(host, img, CONTAINER_NAME)
    instance = DockerRuntimeInstance(CONTAINER_NAME, img, ports_mapping={80: 8080})

    assert not runner.is_running(instance)

    runner.run(instance, **kwargs)
    time.sleep(.1)

    assert runner.is_running(instance)

    runner.stop(instance)
    time.sleep(.1)

    assert not runner.is_running(instance)
