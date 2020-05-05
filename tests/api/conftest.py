import json
import os

import pytest

from ebonite.api.api_base import EboniteAPI
from ebonite.build.builder.base import use_local_installation
from tests.ext.sqlalchemy.test_postgres.conftest import postgres_server, postgres_meta
from tests.ext.s3.conftest import s3_artifact, s3server


@pytest.fixture
def api(tmpdir_factory, postgres_server, postgres_meta, s3server, s3_artifact):
    os.environ['S3_ACCESS_KEY'] = 'eboniteAccessKey'
    os.environ['S3_SECRET_KEY'] = 'eboniteSecretKey'

    with use_local_installation():
        config = dict(
            meta_repo={
                'db_uri': postgres_meta.db_uri,
                'type': 'sqlalchemy'
            },
            artifact_repo={
                'bucket_name': s3_artifact.bucket_name,
                'endpoint': s3_artifact.endpoint,
                'type': 's3'
            })

        cfg_path = tmpdir_factory.mktemp('data').join('config.json')
        with open(cfg_path, 'w+') as fd:
            json.dump(config, fd)

    api = EboniteAPI(name='test_api', config_path=cfg_path, debug=False, host='127.0.0.1', port='5000')
    api.app.config['TESTING'] = True
    yield api

@pytest.fixture
def client(api):
    yield api.app.test_client()


@pytest.fixture
def create_project_1(client):
    rv = client.post('/projects', data=json.dumps({'name': 'project_1'}))
    assert rv.status_code == 201


@pytest.fixture
def create_project_2(client):
    rv = client.post('/projects', data=json.dumps({'name': 'project_2'}))
    assert rv.status_code == 201


@pytest.fixture
def create_task_1(client, create_project_1):
    rv = client.post('/tasks', data=json.dumps({'name': 'task_1', 'project_id': 1}))
    assert rv.status_code == 201


@pytest.fixture
def create_task_2(client, create_project_1):
    rv = client.post('/tasks', data=json.dumps({'name': 'task_2', 'project_id': 1}))
    assert rv.status_code == 201
