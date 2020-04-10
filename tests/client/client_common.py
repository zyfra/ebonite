import time

import pytest

from ebonite.client import Ebonite
from ebonite.core.errors import ExistingModelError
from ebonite.core.objects.core import Model
from tests.build.builder.test_docker import has_docker
from tests.build.conftest import train_model


def test_get_or_create_task(ebnt: Ebonite):
    task = ebnt.get_or_create_task("Project", "Task")
    assert task.name == "Task"
    assert task.project.name == "Project"


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


def test_push_model_same_model(ebnt: Ebonite, model: Model):
    task = ebnt.get_or_create_task("Project", "Task1")
    model = ebnt.push_model(model, task)

    with pytest.raises(ExistingModelError):
        ebnt.push_model(model, task)


def test_push_model_with_same_name(ebnt: Ebonite, model: Model):
    task = ebnt.get_or_create_task("Project", "Task1")
    model = ebnt.push_model(model, task)

    model._id = None
    with pytest.raises(ExistingModelError):
        ebnt.push_model(model, task)


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
def test_build_and_run_instance(ebnt, container_name):
    reg, data = train_model()

    instance = ebnt.create_instance_from_model("Test Model", reg, data, project_name="Test Project",
                                               task_name="Test Task", instance_name=container_name, run_instance=True)
    time.sleep(.1)

    assert ebnt.get_environment(instance.environment.name) == instance.environment
    assert ebnt.get_image(instance.image.name, instance.image.model) == instance.image
    assert ebnt.get_instance(instance.name, instance.image, instance.environment) == instance
    assert instance.is_running()

    ebnt.stop_instance(instance)
    time.sleep(.1)

    assert not instance.is_running()
