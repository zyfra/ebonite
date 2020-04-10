import contextlib
import os

import docker.errors
import pytest
import tempfile
from testcontainers.core.container import DockerContainer

from ebonite.build.builder.base import use_local_installation
from ebonite.build.builder.docker import _DockerfileGenerator, DockerBuilder
from ebonite.build.docker import DockerImage, RemoteDockerRegistry, create_docker_client

from tests.build.conftest import has_docker
from tests.build.builder.test_base import ProviderMock, SECRET

CLEAN = True
IMAGE_NAME = 'ebonite_test_docker_builder_image'

REGISTRY_PORT = 5000
REGISTRY_HOST = f'localhost:{REGISTRY_PORT}'

no_docker = pytest.mark.skipif(not has_docker(), reason='docker is unavailable or skipped')


@pytest.fixture
def docker_builder_local_registry():
    with use_local_installation():
        yield DockerBuilder(ProviderMock(), DockerImage(IMAGE_NAME))


@pytest.fixture
def docker_builder_remote_registry():
    with use_local_installation(), DockerContainer('registry:latest').with_bind_ports(REGISTRY_PORT, REGISTRY_PORT):
        yield DockerBuilder(ProviderMock(),
                            DockerImage(IMAGE_NAME, registry=RemoteDockerRegistry(REGISTRY_HOST)))


@contextlib.contextmanager
def get_image_output(image_params):
    image_uri = image_params.get_uri()

    with create_docker_client() as client:
        if isinstance(image_params.registry, RemoteDockerRegistry):
            # remove to ensure that image was pushed to remote registry, if so following `run` call will pull it back
            client.images.remove(image_uri)

        try:
            yield client.containers.run(image_uri, remove=True).decode('utf8').strip()
        except docker.errors.ContainerError as e:
            yield e.stderr.decode('utf8')
        finally:
            client.images.remove(image_uri)


@pytest.mark.docker
@no_docker
@pytest.mark.parametrize('docker_builder', ['docker_builder_local_registry', 'docker_builder_remote_registry'])
def test_build(docker_builder, request):
    docker_builder = request.getfixturevalue(docker_builder)

    docker_builder.build()
    with get_image_output(docker_builder.params) as output:
        assert output == SECRET


def test_dockerfile_generator_custom_python_version():
    dockerfile = '''FROM python:3.6-slim

WORKDIR /app



COPY requirements.txt .
RUN pip install -r requirements.txt




COPY . ./



CMD sh run.sh
'''

    kwargs = {'python_version': '3.6'}
    assert _generate_dockerfile(**kwargs) == dockerfile


def test_dockerfile_generator_super_custom():
    dockerfile = '''FROM my-python:3.6

WORKDIR /app

RUN echo "pre_install"

COPY requirements.txt .
RUN pip install -r requirements.txt


RUN echo "post_install"

COPY . ./

RUN echo "post_copy"

CMD echo "cmd" && sh run.sh
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        for hook in {'pre_install', 'post_install', 'post_copy'}:
            with open(os.path.join(tmpdir, f'{hook}.j2'), 'w') as f:
                f.write(f'RUN echo "{hook}"')

        kwargs = {
            'base_image': 'my-python:3.6',
            'templates_dir': tmpdir,
            'run_cmd': 'echo "cmd" && sh run.sh'
        }
        assert _generate_dockerfile(**kwargs) == dockerfile


def _generate_dockerfile(**kwargs):
    with use_local_installation():
        return _DockerfileGenerator(**kwargs).generate({})
