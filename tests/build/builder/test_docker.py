import contextlib
import os

import docker.errors
import pytest
import tempfile
from testcontainers.core.container import DockerContainer

from ebonite.build.builder.base import use_local_installation
from ebonite.build.builder.docker import _DockerfileGenerator, DockerBuilder
from ebonite.core.objects.requirements import UnixPackageRequirement

from ebonite.build.docker import DockerImage, RemoteDockerRegistry, create_docker_client, DockerHost
from ebonite.core.objects import Image
from tests.build.builder.test_base import ProviderMock, SECRET
from tests.build.conftest import has_docker


CLEAN = True
IMAGE_NAME = 'ebonite_test_docker_builder_image'

REGISTRY_PORT = 5000

no_docker = pytest.mark.skipif(not has_docker(), reason='docker is unavailable or skipped')


@pytest.fixture
def dockerhost():
    yield DockerHost()


@pytest.fixture
def helloworld_image():
    with create_docker_client() as client:
        client.images.pull('hello-world:latest')
    image = Image('hello-world', 0, 0, Image.Params())
    image.params.name = 'hello-world'
    yield image


@pytest.fixture
def docker_builder_local_registry():
    with use_local_installation():
        yield DockerBuilder(ProviderMock(), DockerImage(IMAGE_NAME))


@pytest.fixture
def docker_builder_remote_registry():
    with use_local_installation(), DockerContainer('registry:latest').with_exposed_ports(REGISTRY_PORT) as container:
        host = f'localhost:{container.get_exposed_port(REGISTRY_PORT)}'
        yield DockerBuilder(ProviderMock(),
                            DockerImage(IMAGE_NAME, registry=RemoteDockerRegistry(host)))


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
def test_image_deletion(dockerhost, helloworld_image):
    with create_docker_client() as client:
        try:
            client.images.get('hello-world')
        except docker.errors.ImageNotFound:
            pytest.fail('Fixture image hello-world was not pulled')
    dockerhost.remove_image(helloworld_image)
    with create_docker_client() as client:
        with pytest.raises(docker.errors.ImageNotFound):
            client.images.get('hello-world')


@pytest.mark.docker
@no_docker
@pytest.mark.parametrize('docker_builder', ['docker_builder_local_registry', 'docker_builder_remote_registry'])
def test_build(docker_builder, request):
    docker_builder = request.getfixturevalue(docker_builder)

    docker_builder.build()
    with get_image_output(docker_builder.params) as output:
        assert output == SECRET


def test_dockerfile_generator_custom_python_version():
    dockerfile = _cut_empty_lines('''FROM python:AAAA-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . ./
CMD sh run.sh
''')

    kwargs = {'python_version': 'AAAA'}
    assert _generate_dockerfile(**kwargs) == dockerfile


def test_dockerfile_generator_unix_packages():
    dockerfile = _cut_empty_lines('''FROM python:3.6-slim
WORKDIR /app
RUN kek aaa bbb
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . ./
CMD sh run.sh
''')

    kwargs = {'python_version': '3.6',
              'package_install_cmd': 'kek'}
    assert _generate_dockerfile(**kwargs, unix_packages=[UnixPackageRequirement('aaa'),
                                                         UnixPackageRequirement('bbb')]) == dockerfile


def test_dockerfile_generator_super_custom():
    dockerfile = _cut_empty_lines('''FROM my-python:3.6
WORKDIR /app
RUN echo "pre_install"
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN echo "post_install"
COPY . ./
RUN echo "post_copy"
CMD echo "cmd" && sh run.sh
''')

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


def _cut_empty_lines(string):
    return '\n'.join(line for line in string.splitlines() if line)


def _generate_dockerfile(unix_packages=None, **kwargs):
    with use_local_installation():
        return _cut_empty_lines(_DockerfileGenerator(**kwargs).generate({}, unix_packages))
