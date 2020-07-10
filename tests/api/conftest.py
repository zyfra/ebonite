import json
import os

import pytest

from ebonite.api.api_base import EboniteAPI
from ebonite.build.builder.base import use_local_installation
from ebonite.core.objects.core import Buildable, Image, Project, RuntimeEnvironment, RuntimeInstance, Task
from tests.ext.test_s3.conftest import s3_artifact, s3server  # noqa
from tests.ext.test_sqlalchemy.test_postgres.conftest import postgres_meta, postgres_server  # noqa


@pytest.fixture
def api(tmpdir_factory, postgres_server, postgres_meta, s3server, s3_artifact): # noqa
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

    api = EboniteAPI(name=__name__, config_path=cfg_path, debug=False, host='127.0.0.1', port='5000')
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


@pytest.fixture
def project_in_db(postgres_meta, s3_artifact): # noqa
    proj = Project(name='test_project')
    proj = postgres_meta.create_project(proj)
    yield proj


@pytest.fixture
def task_in_db(postgres_meta, project_in_db, s3_artifact): # noqa
    task = Task(name='test_task', project_id=project_in_db.id)
    task.bind_artifact_repo(s3_artifact)
    task = postgres_meta.create_task(task)
    yield task


@pytest.fixture
def model_in_db(postgres_meta, s3_artifact, task_in_db): # noqa
    mdl = task_in_db.create_and_push_model(lambda data: data, 'input', 'test_model')
    yield mdl


@pytest.fixture
def env_in_db(postgres_meta): # noqa
    test_env = RuntimeEnvironment('test_env', params=TestParams(123))
    test_env = postgres_meta.create_environment(test_env)
    yield test_env


class TestParams(Image.Params, RuntimeEnvironment.Params, RuntimeInstance.Params):
    def __init__(self, key: int):
        self.key = key


class TestBuildable(Buildable):
    pass


@pytest.fixture
def image_in_db(postgres_meta, task_in_db, env_in_db): # noqa
    test_image = Image('test_image', params=TestParams(123), source=TestBuildable())
    test_image.task = task_in_db
    test_image.environment = env_in_db
    test_image = postgres_meta.create_image(test_image)
    yield test_image


@pytest.fixture
def instance_in_db(postgres_meta, image_in_db, env_in_db): # noqa
    instance = RuntimeInstance('test_instance', params=TestParams(123))
    instance.image = image_in_db
    instance.environment = env_in_db
    instance = postgres_meta.create_instance(instance)
    yield instance
