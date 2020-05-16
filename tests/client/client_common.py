import time

import pytest

from ebonite.client import Ebonite
from ebonite.core.errors import ExistingModelError
from ebonite.core.objects.core import Image, Model
from tests.build.builder.test_docker import has_docker
from tests.build.conftest import check_ebonite_port_free
from tests.client.conftest import MockEnvironmentParams


def test_get_or_create_task(ebnt: Ebonite):
    task = ebnt.get_or_create_task("Project", "Task")
    assert task.name == "Task"
    assert task.project.name == "Project"


def test_get_or_create_task_exists(ebnt: Ebonite):
    task = ebnt.get_or_create_task("Project", "Task")

    task2 = ebnt.get_or_create_task("Project", "Task")

    assert task == task2


def test_create_model(ebnt: Ebonite, regression_and_data):
    reg, data = regression_and_data

    model = ebnt.create_model('test model', reg, data)
    assert isinstance(model, Model)
    assert ebnt.get_model(model.name, model.task) == model


def test_get_model(ebnt: Ebonite, regression_and_data):
    task = ebnt.get_or_create_task("Project", "Task")
    reg, data = regression_and_data
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


def test_delete_image__no_repo_ok(ebnt: Ebonite, image_to_delete: Image):
    assert ebnt.meta_repo.get_image_by_id(image_to_delete.id) is not None
    env = ebnt.get_default_environment()
    env.params = MockEnvironmentParams()
    assert ebnt.delete_image(image_to_delete, env, True)


def test_delete_image__with_repo_ok(ebnt: Ebonite, image_to_delete: Image):
    assert ebnt.meta_repo.get_image_by_id(image_to_delete.id) is not None
    env = ebnt.get_default_environment()
    env.params = MockEnvironmentParams()
    ebnt.delete_image(image_to_delete, env, False)
    assert ebnt.meta_repo.get_image_by_id(image_to_delete.id) is None


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_build_and_run_instance(ebnt: Ebonite, regression_and_data, container_name):
    reg, data = regression_and_data

    check_ebonite_port_free()

    model = ebnt.create_model('test model', reg, data)

    instance = ebnt.build_and_run_instance(container_name, model)
    time.sleep(.1)

    assert ebnt.get_environment(instance.environment.name) == instance.environment
    assert ebnt.get_image(instance.image.name, instance.image.model) == instance.image
    assert ebnt.get_instance(instance.name, instance.image, instance.environment) == instance
    assert instance.is_running()

    ebnt.stop_instance(instance)
    time.sleep(.1)

    assert not instance.is_running()
