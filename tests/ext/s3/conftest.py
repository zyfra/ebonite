from time import sleep

import pytest
from everett.manager import config_override
from testcontainers.core.container import DockerContainer

from ebonite.ext.s3.artifact import S3ArtifactRepository
from tests.build.builder.test_docker import has_docker
from tests.repository.artifact.conftest import create_artifact_hooks

ACCESS_KEY = 'eboniteAccessKey'
BUCKET_NAME = 'testbucket'
PORT = 9003
ENDPOINT = f'http://localhost:{PORT}'
SECRET_KEY = 'eboniteSecretKey'


def delete_bucket(repo: S3ArtifactRepository):
    if repo._bucket_exists():
        bucket = repo._s3_res.Bucket(BUCKET_NAME)
        bucket.objects.all().delete()
        bucket.delete()

    buckets = repo._s3.list_buckets()['Buckets']
    assert buckets == []


# fake fixture that ensures that S3 server is up between tests
@pytest.fixture(scope="module")
def s3server(pytestconfig):
    if not has_docker() or 'not docker' in pytestconfig.getoption('markexpr'):
        pytest.skip('skipping docker tests')

    with DockerContainer('minio/minio:latest') \
            .with_command('server /data') \
            .with_env('MINIO_ACCESS_KEY', ACCESS_KEY) \
            .with_env('MINIO_SECRET_KEY', SECRET_KEY) \
            .with_bind_ports(9000, PORT):
        sleep(5)  # wait to ensure that S3 server has enough time to properly start
        yield


@pytest.fixture
def s3_artifact(s3server):
    # `config_override` doesn't work here as decorator, probably because of generator
    with config_override(S3_ACCESS_KEY=ACCESS_KEY, S3_SECRET_KEY=SECRET_KEY):
        repo = S3ArtifactRepository(BUCKET_NAME, ENDPOINT)
        delete_bucket(repo)
        yield repo
        delete_bucket(repo)


pytest_runtest_protocol, pytest_collect_file = create_artifact_hooks(s3_artifact, 's3')


def pytest_collection_modifyitems(items, config):
    for colitem in items:
        if colitem.nodeid.startswith('tests/repository/artifact/s3.py::'):
            colitem.add_marker(pytest.mark.docker)
            colitem.add_marker(pytest.mark.skipif(not has_docker(), reason='no docker installed'))
