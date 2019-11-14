import os

import pyjackson
import pytest
from pyjackson.generics import Serializer

from ebonite.core.objects.core import Model, Project, Task
from ebonite.repository import MetadataRepository
from ebonite.repository.artifact.inmemory import InMemoryArtifactRepository
from ebonite.repository.metadata.local import LocalMetadataRepository
from tests.conftest import MockModelWrapper


@pytest.fixture
def meta():
    return LocalMetadataRepository()


@pytest.fixture
def project_factory(meta: MetadataRepository):
    counter = 0

    def factory(saved=False):
        nonlocal counter
        counter += 1
        project = Project('Test Project-{}'.format(counter))
        if saved:
            p = meta.create_project(project)
            return p
        return project

    return factory


@pytest.fixture
def task_factory(project_factory):
    counter = 0

    def factory(saved=False):
        nonlocal counter
        counter += 1
        task = Task('Test Task-{}'.format(counter))
        if saved:
            project = project_factory(True)
            project.add_task(task)
        return task

    return factory


@pytest.fixture
def model_factory(task_factory):
    counter = 0

    def factory(saved=False):
        nonlocal counter
        counter += 1
        model = Model('Test Model-{}'.format(counter), MockModelWrapper())
        if saved:
            task = task_factory(True)
            task.add_model(model)
        return model

    return factory


@pytest.fixture
def task_b(task_factory):
    return task_factory(True)


@pytest.fixture
def task_b2(task_b: Task):
    task_b.bind_artifact_repo(InMemoryArtifactRepository())
    return task_b


@pytest.fixture
def task(task_factory):
    return task_factory()


@pytest.fixture
def project_b(project_factory):
    return project_factory(True)


@pytest.fixture
def project(project_factory):
    return project_factory()


@pytest.fixture
def model(sklearn_model_obj, pandas_data):
    return Model.create(sklearn_model_obj, pandas_data)


def serde_and_compare(obj, obj_type=None, true_payload=None, check_payload=True):
    if obj_type is None:
        obj_type = type(obj)
        check_subtype = False
        check_instance = True
    else:
        check_subtype = not issubclass(obj_type, Serializer)
        check_instance = False

    payload = pyjackson.serialize(obj, obj_type)
    if true_payload is not None:
        if check_payload:
            assert true_payload == payload
        payload = true_payload
    new_obj = pyjackson.deserialize(payload, obj_type)
    if check_subtype:
        assert issubclass(type(new_obj), obj_type), '{} type must be subtype of {}'.format(new_obj, obj_type)
    elif check_instance:
        assert isinstance(new_obj, obj_type)
    assert obj == new_obj


@pytest.fixture
def username():
    cur_logname = os.environ.get('LOGNAME', '')
    usr_name = "EBONITE_TEST_USERNAME"
    os.environ["LOGNAME"] = usr_name
    yield usr_name
    os.environ["LOGNAME"] = cur_logname
