import os
import time

import pytest
from requests.exceptions import HTTPError

from ebonite.ext.docker import DockerContainer, DockerEnv, DockerImage
from ebonite.ext.docker.runner import DockerRunner, DockerRunnerException
from tests.conftest import docker_test, has_docker

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

    def _runner(docker_env: DockerEnv, image: DockerImage, container_name: str):
        args.append((docker_env, image, container_name))
        return DockerRunner()

    yield _runner

    runner = DockerRunner()
    for env, img, container in args:
        runner.remove_instance(DockerContainer(container), env, force=True)
        with env.daemon.client() as client:
            env.registry.delete_image(client, img)


@pytest.fixture(scope='session')
def runner_test_images(tmpdir_factory, dockerenv_local, dockerenv_remote):
    with dockerenv_local.daemon.client() as client:
        tag_name = f'{dockerenv_remote.registry.get_host()}/{REPOSITORY_NAME}/{IMAGE_NAME}'
        client.images.pull(IMAGE_NAME, 'latest').tag(tag_name)
        client.images.push(tag_name)

        tmpdir = str(tmpdir_factory.mktemp("image"))
        # create failing image: alpine is too small to have python inside
        with open(os.path.join(tmpdir, 'Dockerfile'), 'w') as f:
            f.write("""
                FROM alpine:latest
                CMD python
           """)
        broken_tag_name = f'{dockerenv_remote.registry.get_host()}/{REPOSITORY_NAME}/{BROKEN_IMAGE_NAME}'
        client.images.build(path=tmpdir, tag=broken_tag_name)
        client.images.push(broken_tag_name)
        print()


@docker_test
def test_run_default_registry(runner, dockerenv_local, runner_test_images):
    img = DockerImage(IMAGE_NAME)
    _check_runner(runner, img, dockerenv_local)


@docker_test
def test_run_remote_registry(runner, dockerenv_remote, runner_test_images):
    img = DockerImage(IMAGE_NAME, repository=REPOSITORY_NAME, registry=dockerenv_remote.registry)

    _check_runner(runner, img, dockerenv_remote)


@docker_test
def test_run_local_image_name_that_will_never_exist(runner, dockerenv_local):
    img = DockerImage('ebonite_image_name_that_will_never_exist')

    with pytest.raises(HTTPError):
        _check_runner(runner, img, dockerenv_local)


@docker_test
@pytest.mark.parametrize('detach', [True, False])
def test_run_local_fail_inside_container(runner, dockerenv_remote, detach, runner_test_images):
    img = DockerImage(BROKEN_IMAGE_NAME,
                      repository=REPOSITORY_NAME, registry=dockerenv_remote.registry)

    with pytest.raises(DockerRunnerException):
        _check_runner(runner, img, dockerenv_remote, detach=detach, rm=True)


@docker_test
def test_instance_creation_with_kwargs(runner, dockerenv_remote):
    runner = DockerRunner()
    kwargs = {'key': 'val', 'host': '', 'int_key': 1, 'port_mapping': {8000: 8000}}
    instance = runner.create_instance('instance', **kwargs)
    assert 'port_mapping' not in instance.params
    assert instance.port_mapping == {8000: 8000}

    kwargs = {'key': 'val', 'host': '', 'int_key': 1}
    instance = runner.create_instance('instance_2', **kwargs)
    assert instance.port_mapping == {}


def _check_runner(runner, img, env: DockerEnv, **kwargs):
    instance = DockerContainer(CONTAINER_NAME, port_mapping={80: None})
    runner = runner(env, img, CONTAINER_NAME)

    assert not runner.is_running(instance, env)

    runner.run(instance, img, env, **kwargs)
    time.sleep(.1)

    assert runner.is_running(instance, env)

    runner.stop(instance, env)
    time.sleep(.1)

    assert not runner.is_running(instance, env)
