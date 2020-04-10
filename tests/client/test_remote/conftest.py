import os

import pytest

from ebonite.build.builder.base import use_local_installation
from ebonite.client import Ebonite
from tests.build.builder.test_docker import has_docker
from tests.client.conftest import create_client_hooks
# these imports are needed to ensure that these fixtures are available for use
from tests.ext.s3.conftest import s3_artifact, s3server  # noqa
from tests.ext.sqlalchemy.test_postgres.conftest import postgres_meta, postgres_server  # noqa


@pytest.fixture
def remote_ebnt(tmpdir, postgres_server, postgres_meta, s3server, s3_artifact):  # noqa
    with use_local_installation():
        # we reconstruct all objects here to ensure that config-related code is covered by tests

        ebnt = Ebonite.custom_client(
            metadata="sqlalchemy", meta_kwargs={
                "db_uri": postgres_meta.db_uri
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
