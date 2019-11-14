import contextlib
import os

import docker.errors
import pytest
import tempfile
from ebonite.build.builder.base import use_local_installation
from ebonite.build.builder.docker_builder import _DockerfileGenerator, DockerBuilder, create_docker_client

from tests.build.conftest import has_docker
from tests.build.builder.test_base import ProviderMock, SECRET

CLEAN = True
IMAGE_NAME = 'ebonite_test_docker_builder_image'


no_docker = pytest.mark.skipif(not has_docker(), reason='docker is unavailable or skipped')


@pytest.fixture
def docker_builder():
    with use_local_installation():
        yield DockerBuilder(ProviderMock(), IMAGE_NAME)


@contextlib.contextmanager
def get_image_output():
    with create_docker_client() as client:
        try:
            yield client.containers.run(IMAGE_NAME, remove=True).decode('utf8').strip()
        except docker.errors.ContainerError as e:
            yield e.stderr.decode('utf8')
        finally:
            client.images.remove(IMAGE_NAME)


@pytest.mark.docker
@no_docker
def test_build(docker_builder):
    docker_builder.build()
    with get_image_output() as output:
        assert output == SECRET


def test_dockerfile_generator_custom_python_version():
    dockerfile = '''FROM python:3.6-slim

WORKDIR /app



COPY requirements.txt .
RUN pip install -r requirements.txt




COPY . ./



CMD sh run.sh
'''

    kwargs = {'python_version': '3.6-slim'}
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
        return _DockerfileGenerator(**kwargs).generate()
