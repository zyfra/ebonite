import pytest

from ebonite.build.docker import image_exists_at_dockerhub, repository_tags_at_dockerhub
from ebonite.utils.module import get_python_version
from tests.build.conftest import has_docker


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_image_exists():
    assert image_exists_at_dockerhub(f'python:{get_python_version()}-slim')
    assert image_exists_at_dockerhub('minio/minio:latest')
    assert image_exists_at_dockerhub('postgres:alpine')
    assert image_exists_at_dockerhub('registry:latest')


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_image_not_exists():
    assert not image_exists_at_dockerhub(f'python:100.200.300')
    assert not image_exists_at_dockerhub('ebonite:forever')
    assert not image_exists_at_dockerhub('minio:minio')
    assert not image_exists_at_dockerhub('postgres/alpine:latest')
    assert not image_exists_at_dockerhub('registry:docker')


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_repository_tags():
    tags = repository_tags_at_dockerhub('python')
    assert f'{get_python_version()}-slim' in tags
    assert get_python_version() in tags

    tags = repository_tags_at_dockerhub('minio/minio')
    assert 'latest' in tags
