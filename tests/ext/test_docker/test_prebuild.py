import os

import pytest

from ebonite.ext.docker.prebuild import _generate_dockerfile, prebuild_image
from tests.conftest import docker_test


@pytest.fixture
def prebuild_contextdir(tmpdir):
    contextdir = tmpdir.mkdir('contextdir')
    dockerfile = contextdir.join('Dockerfile.j2')
    docker_template = """FROM python:{{ python_version }}-slim

WORKDIR /app

RUN true \
    && apt update \
    && apt install -y \
        bash \
        nginx \
        supervisor \
        gcc \
    && pip install uwsgi==2.0.18 \
    && apt remove gcc -y \
    && apt autoremove -y \
    && apt clean

RUN pip install flask==1.1.2 flasgger==0.9.3
"""

    with open(dockerfile, 'w+') as fd:
        fd.write(docker_template)
    yield contextdir


@docker_test
def test_prebuild__generate_image(prebuild_contextdir):
    _generate_dockerfile(prebuild_contextdir, '3.2.2')
    assert 'Dockerfile' in os.listdir(prebuild_contextdir)
    with open(prebuild_contextdir.join('Dockerfile'), 'r') as fd:
        assert fd.readlines()[0] == 'FROM python:3.2.2-slim\n'


@docker_test
def test_prebuild__prebuild_image(prebuild_contextdir, caplog):
    prebuild_image(prebuild_contextdir, 'zyfraai/ebaklya:{}', '3.7.1', push=False)
    assert caplog.records[0].getMessage().startswith('Building image zyfraai/ebaklya:3.7.1 on')
    assert caplog.records[1].getMessage() == 'Successfully built image zyfraai/ebaklya:3.7.1'

    caplog.clear()
    prebuild_image(prebuild_contextdir, 'nonexistent/ebaklya:{}', '3.2.2', push=False)
    assert caplog.records[0].getMessage().startswith('Building image nonexistent/ebaklya:3.2.2 on')
    assert caplog.records[1].getMessage().startswith('Failed to build image nonexistent/ebaklya:3.2.2')

    caplog.clear()
    prebuild_image(prebuild_contextdir, 'zyfraai/flask:{}', '3.7.7', push=False)
    assert caplog.records[0].getMessage().startswith('Skipped building image')
