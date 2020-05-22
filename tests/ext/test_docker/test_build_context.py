import os
import tempfile

from ebonite.build.builder.base import use_local_installation
from ebonite.core.objects.requirements import UnixPackageRequirement
from ebonite.ext.docker.build_context import DockerBuildArgs, _DockerfileGenerator

CLEAN = True
IMAGE_NAME = 'ebonite_test_docker_builder_image'

REGISTRY_PORT = 5000


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
        return _cut_empty_lines(_DockerfileGenerator(DockerBuildArgs(**kwargs)).generate({}, unix_packages))
