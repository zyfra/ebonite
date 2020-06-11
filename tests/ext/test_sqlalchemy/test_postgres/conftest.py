from time import sleep

import pytest
from testcontainers.core.container import DockerContainer

from ebonite.ext.sqlalchemy.models import Base
from ebonite.ext.sqlalchemy.repository import SQLAlchemyMetaRepository
from tests.conftest import has_docker
from tests.repository.metadata.conftest import create_metadata_hooks

PG_PORT = 5432
PG_USER = "postgres"
PG_PASS = PG_USER
PG_DB = "ebonite"


# fake fixture that ensures that PostgreSQL server is up between tests
@pytest.fixture(scope="module")
def postgres_server(pytestconfig):
    if not has_docker() or 'not docker' in pytestconfig.getoption('markexpr'):
        pytest.skip('skipping docker tests')

    with DockerContainer('postgres:alpine') \
            .with_exposed_ports(PG_PORT) \
            .with_env("POSTGRES_USER", PG_USER) \
            .with_env("POSTGRES_PASSWORD", PG_PASS) \
            .with_env("POSTGRES_DB", PG_DB) as container:
        sleep(5)  # wait to ensure that PostgreSQL server has enough time to properly start
        yield container.get_exposed_port(PG_PORT)


@pytest.fixture
def postgres_meta(postgres_server):
    repo = SQLAlchemyMetaRepository(f"postgresql://{PG_USER}:{PG_PASS}@localhost:{postgres_server}/{PG_DB}")
    yield repo
    Base.metadata.drop_all(repo._engine)


pytest_runtest_protocol, pytest_collect_file = create_metadata_hooks(postgres_meta, 'postgres')


def pytest_collection_modifyitems(items, config):
    for colitem in items:
        if colitem.nodeid.startswith('tests/repository/metadata/postgres.py::'):
            colitem.add_marker(pytest.mark.docker)
            colitem.add_marker(pytest.mark.skipif(not has_docker(), reason='no docker installed'))
