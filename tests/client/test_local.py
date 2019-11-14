import copy
import os
import time

import pytest

from ebonite.build.builder.base import use_local_installation
from ebonite.client import Ebonite
from ebonite.core.errors import ExistingModelError
from ebonite.core.objects.core import Model
from tests.build.builder.test_docker import has_docker
from tests.build.conftest import is_container_running, rm_container, rm_image, train_model
from tests.client.test_func import func

LOCAL_REPO_PATH = os.path.dirname(__file__)
LOCAL_ARTIFACT_REPO_PATH = os.path.join(LOCAL_REPO_PATH, 'artifacts')
CONTAINER_NAME = "ebonite-test-service"

CLEAR = True  # flag to disable removal of containers for easy inspection and debugging


@pytest.fixture
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def container_name():
    name = "{}-{}".format(CONTAINER_NAME, int(time.time() * 1000))
    yield name

    if not CLEAR:
        return

    rm_container(name)
    rm_image(name + ":latest")  # FIXME latter


@pytest.fixture
def ebnt(tmpdir):
    with use_local_installation():
        yield Ebonite.local(str(tmpdir))


@pytest.fixture  # FIXME did not find the way to import fixture from build module
def model():
    model = Model.create(func, "kek", "Test Model")
    return model


def test_clearing_turned_on():  # just to remember to turn it on before commit
    assert CLEAR


def test_get_or_create_task(ebnt: Ebonite):
    task = ebnt.get_or_create_task("Project", "Task")
    project = ebnt.meta_repo.get_project_by_id(task.project_id)  # FIXME
    assert task.name == "Task"
    assert project.name == "Project"


def test_get_or_create_task_exists(ebnt: Ebonite):
    task = ebnt.get_or_create_task("Project", "Task")

    task2 = ebnt.get_or_create_task("Project", "Task")

    assert task == task2


def test_get_model(ebnt: Ebonite):
    task = ebnt.get_or_create_task("Project", "Task")
    reg, data = train_model()
    model = task.create_and_push_model(reg, data, 'mymodel')

    assert ebnt.get_model(project='Project', task='Task', model_name='mymodel') == model


def test_push_model(ebnt: Ebonite, model: Model):
    task = ebnt.get_or_create_task("Project", "Task1")
    model.task_id = task.id  # For test purpose
    pushed_model = ebnt.push_model(model)

    assert model.name == pushed_model.name
    assert task.id == pushed_model.task_id


def test_push_model_task_argument(ebnt: Ebonite, model: Model):
    task = ebnt.get_or_create_task("Project", "Task1")
    pushed_model = ebnt.push_model(model, task)

    assert model.name == pushed_model.name
    assert task.id == pushed_model.task_id


def test_push_model_with_task_and_task_argument(ebnt: Ebonite, model: Model):
    task = ebnt.get_or_create_task("Project", "Task1")

    model.task_id = task.id  # For test purpose
    pushed_model = ebnt.push_model(model, task)

    assert model.name == pushed_model.name
    assert task.id == pushed_model.task_id


def test_push_model_with_task_and_different_task_as_argument(ebnt: Ebonite, model: Model):
    task = ebnt.get_or_create_task("Project", "Task1")

    task2 = ebnt.get_or_create_task("Project", "Task2")
    model.task = task2  # For test purpose

    with pytest.raises(ValueError):
        ebnt.push_model(model, task)


def test_push_model_with_task_and_task_argument_with_different_project(ebnt: Ebonite, model: Model):
    task = ebnt.get_or_create_task("Project", "Task1")

    task2 = ebnt.get_or_create_task("Project2", "Task1")
    model.task = task2  # For test purpose

    with pytest.raises(ValueError):
        ebnt.push_model(model, task)


def test_push_model_exists(ebnt: Ebonite, model: Model):
    task = ebnt.get_or_create_task("Project", "Task1")

    pushed_model = ebnt.push_model(model, task)
    assert pushed_model.id is not None

    pushed_model.name = "Model2"
    pushed_model._id = None
    pushed_model2 = ebnt.push_model(pushed_model)

    assert "Model2" == pushed_model2.name


def test_push_model_with_same_name(ebnt: Ebonite, model: Model):
    task = ebnt.get_or_create_task("Project", "Task1")
    ebnt.push_model(model, task)

    model2 = copy.deepcopy(model)
    with pytest.raises(ExistingModelError):
        ebnt.push_model(model2, task)


def test_push_model_project_contains_two_tasks(ebnt: Ebonite, model: Model):
    task1 = ebnt.get_or_create_task("Project", "Task1")
    ebnt.get_or_create_task("Project", "Task2")

    pushed_model = ebnt.push_model(model, task1)

    task = ebnt.meta_repo.get_task_by_id(pushed_model.task_id)
    project = ebnt.meta_repo.get_project_by_id(task.project_id)
    task1 = ebnt.get_or_create_task("Project", "Task1")
    assert project.tasks.get(task.id) == task1


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_build_and_run_service(ebnt, container_name):
    reg, data = train_model()

    task = ebnt.get_or_create_task("Test Project", "Test Task")
    model = task.create_and_push_model(reg, data, "Test Model")
    ebnt.build_and_run_service(container_name, model, detach=True)
    assert is_container_running(container_name)
