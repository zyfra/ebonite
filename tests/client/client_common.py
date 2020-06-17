import pytest

from ebonite.client import Ebonite
from ebonite.core.errors import (EnvironmentWithInstancesError, ExistingModelError, ImageWithInstancesError,
                                 ProjectWithTasksError, TaskWithFKError)
from ebonite.core.objects.core import Image, Model, Pipeline, RuntimeInstance, Task
from tests.build.conftest import check_ebonite_port_free
from tests.conftest import docker_test
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
    assert task.has_meta_repo
    assert task.has_artifact_repo


def test_get_or_create_task_exists(ebnt: Ebonite):
    task = ebnt.get_or_create_task("Project", "Task")

    task2 = ebnt.get_or_create_task("Project", "Task")

    assert task == task2


def test_delete_task_ok(ebnt: Ebonite):
    task = ebnt.get_or_create_task('Project', 'Task')

    assert ebnt.meta_repo.get_task_by_id(task.id) is not None
    ebnt.delete_task(task)

    assert ebnt.meta_repo.get_task_by_id(task.id) is None


def test_delete_task_cascade_ok(ebnt: Ebonite, model: Model, mock_env, image: Image, pipeline: Pipeline):
    task = ebnt.get_or_create_task('Project', 'Task')
    model = ebnt.push_model(model, task)
    image.environment = ebnt.meta_repo.create_environment(mock_env)
    task.add_pipeline(pipeline)
    task.add_image(image)
    task = ebnt.meta_repo.get_task_by_id(task.id).bind_as(task)

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


def test_create_model(ebnt: Ebonite, regression_and_data):
    reg, data = regression_and_data

    model = ebnt.create_model(reg, data, 'sklearn_model')
    assert isinstance(model, Model)
    assert ebnt.get_model(model.name, model.task) == model


def test_get_model(ebnt: Ebonite, regression_and_data):
    task = ebnt.get_or_create_task("Project", "Task")
    reg, data = regression_and_data
    model = task.create_and_push_model(reg, data, 'mymodel')

    get_model = ebnt.get_model(project='Project', task='Task', model_name='mymodel')
    assert get_model == model
    assert get_model.has_meta_repo
    assert get_model.has_artifact_repo


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


def test_delete_image__only_meta_ok(ebnt: Ebonite, image_to_delete: Image, instance: RuntimeInstance, mock_env_params):
    assert ebnt.meta_repo.get_image_by_id(image_to_delete.id) is not None
    instance.image = image_to_delete
    instance.environment = image_to_delete.environment
    ebnt.meta_repo.save_instance(instance)
    with mock_env_params.builder.delete_image.called_within_context(times=0):
        ebnt.delete_image(image_to_delete, True, True)
    assert ebnt.meta_repo.get_image_by_id(image_to_delete.id) is None


def test_delete_image__not_only_meta_ok(ebnt: Ebonite, image_to_delete: Image, mock_env_params):
    assert ebnt.meta_repo.get_image_by_id(image_to_delete.id) is not None
    assert image_to_delete.builder == mock_env_params.builder
    with mock_env_params.builder.delete_image.called_within_context(times=1):
        ebnt.delete_image(image_to_delete, False)
    assert ebnt.meta_repo.get_image_by_id(image_to_delete.id) is None


@docker_test
def test_build_and_run_instance(ebnt: Ebonite, regression_and_data, container_name, mock_env):
    reg, data = regression_and_data
    mock_env = ebnt.meta_repo.create_environment(mock_env)
    check_ebonite_port_free()

    model = ebnt.create_model(reg, data, 'test_model')

    p = mock_env.params
    with p.builder.build_image.called_within_context(), p.runner.run.called_within_context():
        instance = ebnt.build_and_run_instance(model, container_name, environment=mock_env)

    assert ebnt.get_environment(instance.environment.name) == instance.environment
    assert ebnt.get_image(instance.image.name, instance.image.task) == instance.image
    assert ebnt.get_instance(instance.name, instance.image, instance.environment) == instance

    with pytest.raises(ImageWithInstancesError):
        ebnt.delete_image(instance.image)

    with pytest.raises(EnvironmentWithInstancesError):
        ebnt.delete_environment(instance.environment)

    with p.runner.stop.called_within_context(), p.runner.remove_instance.called_within_context():
        ebnt.delete_instance(instance)
