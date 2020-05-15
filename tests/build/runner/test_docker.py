import os
import time

import pytest

from ebonite.build import DefaultDockerRegistry, DockerContainer, DockerHost, DockerImage, RemoteDockerRegistry
from ebonite.build.runner.docker import DockerRunner, DockerRunnerException

from docker import DockerClient
from requests.exceptions import HTTPError
from testcontainers.core.container import DockerContainer as Container

from tests.build.builder.test_docker import has_docker
from tests.build.conftest import rm_container, rm_image


IMAGE_NAME = 'mike0sv/ebaklya'
BROKEN_IMAGE_NAME = 'test-broken-image'
CONTAINER_NAME = 'ebonite-runner-test-docker-container'
REPOSITORY_NAME = 'ebonite'

REGISTRY_PORT = 5000


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
    with Container('registry:latest').with_exposed_ports(REGISTRY_PORT) as container:
        host = f'localhost:{container.get_exposed_port(REGISTRY_PORT)}'

        client = DockerClient()

        # migrate our image to custom Docker registry
        tag_name = f'{host}/{REPOSITORY_NAME}/{IMAGE_NAME}'
        client.images.pull(IMAGE_NAME, 'latest').tag(tag_name)
        client.images.push(tag_name)

        tmpdir = str(tmpdir_factory.mktemp("image"))
        # create failing image: alpine is too small to have python inside
        with open(os.path.join(tmpdir, 'Dockerfile'), 'w') as f:
            f.write("""
                FROM alpine:latest

                CMD python
           """)
        broken_tag_name = f'{host}/{REPOSITORY_NAME}/{BROKEN_IMAGE_NAME}'
        client.images.build(path=tmpdir, tag=broken_tag_name)
        client.images.push(broken_tag_name)

        yield RemoteDockerRegistry(host)


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


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_instance_creation_with_kwargs(runner, registry):
    runner = DockerRunner()
    kwargs = {'key': 'val', 'host': '', 'int_key': 1, 'ports_mapping': {8000: 8000}}
    instance = runner.create_instance('instance', **kwargs)
    assert 'ports_mapping' not in instance.params
    assert instance.ports_mapping == {8000: 8000}

    kwargs = {'key': 'val', 'host': '', 'int_key': 1}
    instance = runner.create_instance('instance_2', **kwargs)
    assert instance.ports_mapping == {}


def _check_runner(runner, img, host='', **kwargs):
    runner = runner(host, img, CONTAINER_NAME)
    instance = DockerContainer(CONTAINER_NAME, ports_mapping={80: None})
    env = DockerHost(host)

    assert not runner.is_running(instance, env)

    runner.run(instance, img, env, **kwargs)
    time.sleep(.1)

    assert runner.is_running(instance, env)

    runner.stop(instance, env)
    time.sleep(.1)

    assert not runner.is_running(instance, env)
