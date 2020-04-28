import time

import pytest

from ebonite.client import Ebonite
from ebonite.core.errors import (EnvironmentWithInstancesError, ExistingModelError, ImageWithInstancesError,
                                 ProjectWithTasksError, TaskWithFKError)
from ebonite.core.objects.core import Image, Model, Pipeline, Task
from tests.build.builder.test_docker import has_docker
from tests.build.conftest import check_ebonite_port_free, train_model
from tests.core.objects.conftest import BuildableMock


def test_delete_project__ok(ebnt: Ebonite):
    project = ebnt.meta_repo.get_or_create_project('Project')

    assert ebnt.meta_repo.get_or_create_project('Project') is not None
    ebnt.delete_project(project)

    assert ebnt.meta_repo.get_project_by_name('Project') is None


def test_delete_project_cascade__ok(ebnt: Ebonite):
    task = ebnt.get_or_create_task('Project', 'Task')
    project = ebnt.meta_repo.get_project_by_name('Project')

    assert ebnt.meta_repo.get_task_by_id(task.id) is not None
    assert ebnt.meta_repo.get_project_by_id(project.id) is not None
    ebnt.delete_project(project, cascade=True)

    assert ebnt.meta_repo.get_project_by_name('Project') is None
    assert ebnt.meta_repo.get_task_by_id(task.id) is None


def test_delete_project_cascade_project_with_tasks(ebnt: Ebonite):
    ebnt.get_or_create_task('Project', 'Task')
    project = ebnt.meta_repo.get_project_by_name('Project')

    assert ebnt.meta_repo.get_project_by_id(project.id) is not None

    with pytest.raises(ProjectWithTasksError):
        ebnt.delete_project(project)


def test_get_or_create_task(ebnt: Ebonite):
    task = ebnt.get_or_create_task("Project", "Task")
    project = ebnt.meta_repo.get_project_by_name('Project')
    assert task.name == "Task"
    assert task.project.name == "Project"
    assert task.id in project.tasks


def test_get_or_create_task_exists(ebnt: Ebonite):
    task = ebnt.get_or_create_task("Project", "Task")

    task2 = ebnt.get_or_create_task("Project", "Task")

    assert task == task2


def test_delete_task_ok(ebnt: Ebonite):
    task = ebnt.get_or_create_task('Project', 'Task')

    assert ebnt.meta_repo.get_task_by_id(task.id) is not None
    ebnt.delete_task(task)

    assert ebnt.meta_repo.get_task_by_id(task.id) is None


def test_a(pipeline: Pipeline):
    pipeline.id


def test_delete_task_cascade_ok(ebnt: Ebonite, model: Model, image: Image, pipeline: Pipeline):
    task = ebnt.get_or_create_task('Project', 'Task')
    model = ebnt.push_model(model, task)
    task.add_pipeline(pipeline)
    task.add_image(image)
    task = ebnt.meta_repo.get_task_by_id(task.id)

    assert ebnt.meta_repo.get_task_by_id(task.id) is not None
    assert ebnt.meta_repo.get_model_by_id(model.id) is not None
    assert ebnt.meta_repo.get_pipeline_by_id(pipeline.id) is not None
    assert ebnt.meta_repo.get_image_by_id(image.id) is not None
    ebnt.delete_task(task, cascade=True)

    assert ebnt.meta_repo.get_task_by_id(task.id) is None
    assert ebnt.meta_repo.get_model_by_id(model.id) is None
    assert ebnt.meta_repo.get_pipeline_by_id(pipeline.id) is None
    assert ebnt.meta_repo.get_image_by_id(image.id) is None


def test_delete_task_with_models(ebnt: Ebonite, model: Model):
    task = ebnt.get_or_create_task('Project', 'Task')
    model = ebnt.push_model(model, task)

    assert ebnt.meta_repo.get_task_by_id(task.id) is not None
    assert ebnt.meta_repo.get_model_by_id(model.id) is not None

    with pytest.raises(TaskWithFKError):
        ebnt.delete_task(task)


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


def delete_model_ok(ebnt: Ebonite):
    task = ebnt.get_or_create_task('Project', 'Task')
    model = Model(name='Model', task_id=task.id)
    model = ebnt.meta_repo.create_model(model)

    assert ebnt.meta_repo.get_task_by_id(task.id) is not None
    assert ebnt.meta_repo.get_model_by_id(model.id) is not None
    ebnt.delete_model(model)

    assert ebnt.meta_repo.get_model_by_id(model.id) is None


def delete_pipeline_ok(ebnt: Ebonite, task_b: Task, pipeline: Pipeline):
    task_b.add_pipeline(pipeline)

    assert ebnt.meta_repo.get_task_by_id(task_b.id) is not None
    assert ebnt.meta_repo.get_pipeline_by_id(pipeline.id) is not None
    ebnt.delete_pipeline(pipeline)

    assert ebnt.meta_repo.get_pipeline_by_id(pipeline.id) is None


def delete_image_ok(ebnt: Ebonite, model: Model):
    task = ebnt.get_or_create_task('Project', 'Task')
    model = ebnt.push_model(model, task)
    image = Image(task_id=task.id, name='Image', source=BuildableMock())
    image = ebnt.meta_repo.create_image(image)

    assert ebnt.meta_repo.get_task_by_id(task.id) is not None
    assert ebnt.meta_repo.get_model_by_id(model.id) is not None
    assert ebnt.meta_repo.get_image_by_id(image.id) is not None
    ebnt.delete_image(image)

    assert ebnt.meta_repo.get_image_by_id(image.id) is None


@pytest.mark.docker
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def test_build_and_run_instance(ebnt, container_name):
    reg, data = train_model()

    check_ebonite_port_free()

    instance = ebnt.create_instance_from_model("Test Model", reg, data, project_name="Test Project",
                                               task_name="Test Task", instance_name=container_name, run_instance=True)
    time.sleep(.1)

    assert ebnt.get_environment(instance.environment.name) == instance.environment
    assert ebnt.get_image(instance.image.name, instance.image.task) == instance.image
    assert ebnt.get_instance(instance.name, instance.image, instance.environment) == instance
    assert instance.is_running()

    with pytest.raises(ImageWithInstancesError):
        ebnt.delete_image(instance.image)

    with pytest.raises(EnvironmentWithInstancesError):
        ebnt.delete_environment(instance.environment)

    ebnt.stop_instance(instance)
    time.sleep(.1)

    assert not instance.is_running()
