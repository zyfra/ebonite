import pytest

from ebonite.ext.sqlalchemy.repository import SQLAlchemyMetaRepository
from tests.repository.metadata.conftest import create_metadata_hooks


@pytest.fixture
def sqlalchemy_meta():
    return SQLAlchemyMetaRepository('sqlite://')


pytest_runtest_protocol, pytest_collect_file = create_metadata_hooks(sqlalchemy_meta, 'sqlalchemy')
