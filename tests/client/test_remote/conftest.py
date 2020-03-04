import os
from time import sleep

import pytest
from testcontainers.core.container import DockerContainer

from ebonite.build.builder.base import use_local_installation
from ebonite.client import Ebonite
from ebonite.ext.sqlalchemy import SQLAlchemyMetaRepository
from ebonite.ext.sqlalchemy.models import Base
from tests.build.builder.test_docker import has_docker
from tests.client.conftest import create_client_hooks
# this import is needed to ensure that these fixtures are available for use
from tests.ext.s3.conftest import s3_artifact, s3server  # noqa

PG_PORT = 5435
PG_USER = "postgres"
PG_PASS = PG_USER
PG_DB = "ebonite"


# fake fixture that ensures that PostgreSQL server is up between tests
@pytest.fixture(scope="module")
def pg_server(pytestconfig):
    if not has_docker() or 'not docker' in pytestconfig.getoption('markexpr'):
        pytest.skip('skipping docker tests')

    with DockerContainer('postgres:alpine') \
            .with_bind_ports(5432, PG_PORT) \
            .with_env("POSTGRES_USER", PG_USER) \
            .with_env("POSTGRES_PASSWORD", PG_PASS) \
            .with_env("POSTGRES_DB", PG_DB):
        sleep(5)  # wait to ensure that PostgreSQL server has enough time to properly start
        yield


@pytest.fixture
def pg_meta(pg_server):
    repo = SQLAlchemyMetaRepository(f"postgresql://{PG_USER}:{PG_PASS}@localhost:{PG_PORT}/{PG_DB}")
    Base.metadata.drop_all(repo._engine)
    Base.metadata.create_all(repo._engine)
    yield repo
    Base.metadata.drop_all(repo._engine)


@pytest.fixture
def remote_ebnt(tmpdir, pg_server, pg_meta, s3server, s3_artifact):  # noqa
    with use_local_installation():
        # we reconstruct all objects here to ensure that config-related code is covered by tests

        ebnt = Ebonite.custom_client(
            metadata="sqlalchemy", meta_kwargs={
                "db_uri": pg_meta.db_uri
            },
            artifact="s3", artifact_kwargs={
                "bucket_name": s3_artifact.bucket_name,
                "endpoint": s3_artifact.endpoint,
                "region": s3_artifact.region
            })

        cfg_path = os.path.join(tmpdir, 'config.json')
        ebnt.save_client_config(cfg_path)
        yield Ebonite.from_config_file(cfg_path)


pytest_runtest_protocol, pytest_collect_file = create_client_hooks(remote_ebnt, 'remote')


def pytest_collection_modifyitems(items, config):
    for colitem in items:
        if colitem.nodeid.startswith('tests/client/remote.py::'):
            colitem.add_marker(pytest.mark.docker)
            colitem.add_marker(pytest.mark.skipif(not has_docker(), reason='no docker installed'))
