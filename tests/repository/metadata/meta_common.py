import datetime
from typing import List

import pytest
from pyjackson.utils import get_class_fields

from ebonite.core.errors import (ExistingEnvironmentError, ExistingImageError, ExistingInstanceError,
                                 ExistingModelError, ExistingPipelineError, ExistingProjectError, ExistingTaskError,
                                 ImageNotInTaskError, ModelNotInTaskError, NonExistingEnvironmentError,
                                 NonExistingImageError, NonExistingInstanceError, NonExistingModelError,
                                 NonExistingPipelineError, NonExistingProjectError, NonExistingTaskError,
                                 PipelineNotInTaskError, TaskNotInProjectError)
from ebonite.core.objects.core import Model, Pipeline, Project, Task
from ebonite.repository.metadata import MetadataRepository

# from tests.ext.sqlalchemy.conftest import sqlalchemy_meta as meta
# from tests.repository.metadata.test_local.conftest import local_meta as meta
# _ = [meta]


def assert_objects_equal_except_fields(o1, o2, *, excepted_fields: List[str] = None):
    excepted_fields = excepted_fields or []
    excepted_fields = set(excepted_fields)

    assert type(o1) == type(o2)
    fields1 = [f.name for f in get_class_fields(type(o1))]
    fields2 = [f.name for f in get_class_fields(type(o2))]
    assert fields1 == fields2

    for field1, field2 in zip(fields1, fields2):
        assert field1 == field2
        v1 = getattr(o1, field1)
        v2 = getattr(o2, field2)
        if field1 in excepted_fields:
            assert v1 != v2
        else:
            assert v1 == v2


def update_object_fields(o, *, excepted_fields: List[str] = None):
    excepted_fields = excepted_fields or []
    excepted_fields = set(excepted_fields)

    for field in [f.name for f in get_class_fields(type(o))]:
        additional_value = 2

        if field not in excepted_fields:
            v = getattr(o, field)

            if isinstance(v, str):
                additional_value = str(additional_value)
            if isinstance(v, datetime.datetime):
                additional_value = datetime.timedelta(additional_value)
            if isinstance(v, list):
                additional_value = [v[0]]
            try:
                setattr(o, field, v + additional_value)
            except TypeError as e:
                raise TypeError(f'Field {field}:', e)
    return o


# ################# PROJECT ##########################
def test_create_project(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)
    assert project is not None
    assert project.has_meta_repo


def test_create_project_is_reference(meta: MetadataRepository, project: Project, author, creation_date):
    expected_project = meta.create_project(project)
    assert expected_project is not None

    expected_project.name = "KEK"

    actual_project = meta.get_project_by_id(expected_project.id)
    assert_objects_equal_except_fields(expected_project, actual_project, excepted_fields=['name'])


def test_create_project_source_is_changed(meta: MetadataRepository, project: Project):
    new_project = meta.create_project(project)
    assert new_project is project


def test_create_existing_project(meta: MetadataRepository, project: Project):
    meta.create_project(project)
    with pytest.raises(ExistingProjectError):
        meta.create_project(project)


def test_get_projects(meta: MetadataRepository, project: Project):
    created_project = meta.create_project(project)
    assert meta.get_projects() == [created_project]


def test_get_project_by_name(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)
    assert project == meta.get_project_by_name(project.name)
    assert project.has_meta_repo


def test_get_project_by_id(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)
    assert project == meta.get_project_by_id(project.id)
    assert project.has_meta_repo


def test_get_or_create_project_not_exists(meta: MetadataRepository):
    project = meta.get_or_create_project("Test Project")
    assert project is not None
    assert project.id is not None
    assert project.name == "Test Project"


def test_get_or_create_project_exists(meta: MetadataRepository, project: Project):
    expected_project = meta.create_project(project)
    actual_project = meta.get_or_create_project(expected_project.name)
    assert actual_project is not None
    assert expected_project.id == actual_project.id
    assert expected_project.name == actual_project.name
    assert id(expected_project) != id(actual_project)


def test_update_project_with_tasks(meta: MetadataRepository, project: Project, task: Task):
    project = meta.create_project(project)

    task.project = project
    task = meta.create_task(task)
    project.add_task(task)

    project = update_object_fields(project, excepted_fields=['id', 'tasks'])
    task = update_object_fields(task,
                                excepted_fields=['id', 'models', 'pipelines', 'datasets', 'evaluation_sets', 'metrics',
                                                 'project_id'])

    updated_project = meta.update_project(project)

    assert updated_project is project
    assert project.has_meta_repo
    assert "Test project2" == updated_project.name
    assert project == meta.get_project_by_id(project.id)
    assert len(updated_project.tasks) == 1
    assert task.id in updated_project.tasks
    assert task == updated_project.tasks.get(task.id)


def test_update_project_source_is_changed(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)
    project.name = "Test project2"
    new_project = meta.update_project(project)
    assert new_project == project


def test_update_project_is_reference(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)
    id = project._id
    project.name = "Test project2"
    expected_project = meta.update_project(project)
    assert id == expected_project._id
    assert "Test project2" == expected_project.name

    expected_project.name = "KEK"

    actual_project = meta.get_project_by_id(expected_project.id)
    assert_objects_equal_except_fields(expected_project, actual_project, excepted_fields=['name'])


def test_update_not_existing_project(meta: MetadataRepository, project: Project):
    with pytest.raises(NonExistingProjectError):
        meta.update_project(project)


def test_save_not_existing_project(meta: MetadataRepository, project: Project):
    saved_project = meta.save_project(project)
    assert saved_project.name == project.name
    assert project.name == meta.get_project_by_id(saved_project.id).name
    assert project.has_meta_repo


def test_save_existing_project(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)

    saved_project = meta.save_project(project)
    assert saved_project.id == project.id
    assert project == meta.get_project_by_id(saved_project.id)


def test_save_updated_existing_project(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)

    project = update_object_fields(project, excepted_fields=['id', 'tasks'])

    saved_project = meta.save_project(project)
    assert saved_project == project
    assert project == meta.get_project_by_id(saved_project.id)


def test_save_updated_existing_project_with_existing_name(meta: MetadataRepository,
                                                          project: Project,
                                                          project2: Project):
    meta.create_project(project)
    project2.name = project.name
    with pytest.raises(ExistingProjectError):
        meta.save_project(project2)


def test_save_project_is_reference(meta: MetadataRepository, project: Project):
    saved_project = meta.save_project(project)

    saved_project.name = "KEK"

    actual_project = meta.get_project_by_id(saved_project.id)
    assert_objects_equal_except_fields(saved_project, actual_project, excepted_fields=['name'])


def test_delete_project(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)
    meta.delete_project(project)
    assert meta.get_project_by_id(project.id) is None
    assert not project.has_meta_repo
    assert project.id is None


def test_delete_not_existing_project(meta: MetadataRepository, project: Project):
    with pytest.raises(NonExistingProjectError):
        meta.delete_project(project)


# ################## TASK ##########################
def test_create_task(meta: MetadataRepository, project: Project, task: Task):
    task.project_id = meta.create_project(project).id
    task = meta.create_task(task)
    assert task is not None
    assert task.has_meta_repo

    project = meta.get_project_by_id(project.id)
    assert len(project.tasks) == 1
    assert task.id in project.tasks
    assert project.tasks[task.id] == task


def test_create_task_without_project(meta: MetadataRepository, task: Task):
    with pytest.raises(TaskNotInProjectError):
        meta.create_task(task)


def test_create_task_with_unexisting_project(meta: MetadataRepository):
    task_with_wrong_project = Task(name='failed_task', project_id=2)
    with pytest.raises(NonExistingProjectError):
        meta.create_task(task_with_wrong_project)


def test_create_task_source_is_not_changed(meta: MetadataRepository, project: Project, task: Task):
    task.project = meta.create_project(project)
    new_task = meta.create_task(task)

    assert new_task is task


def test_create_task_is_reference(meta: MetadataRepository, project: Project, task: Task):
    task.project_id = meta.create_project(project).id
    expected_task = meta.create_task(task)
    assert expected_task is not None

    task.name = "KEK"

    actual_task = meta.get_task_by_id(expected_task.id)
    assert_objects_equal_except_fields(expected_task, actual_task, excepted_fields=['name'])


def test_create_existing_task(meta: MetadataRepository, project: Project, task: Task, task2: Task):
    project_id = meta.create_project(project).id

    task.project_id = project_id
    task = meta.create_task(task)
    assert task is not None

    task2.name = task.name
    task2.project_id = project_id
    with pytest.raises(ExistingTaskError):
        meta.create_task(task2)


def test_get_tasks(meta: MetadataRepository, project: Project, task: Task):
    created_project = meta.create_project(project)
    task.project = created_project
    created_task = meta.create_task(task)

    assert meta.get_tasks(created_project) == [created_task]


def test_get_task_by_name(meta: MetadataRepository, project: Project, task: Task):
    project = meta.create_project(project)
    task.project = project
    task_new = meta.create_task(task)
    assert task_new is not None
    assert task_new == meta.get_task_by_name(project, task.name)
    assert task.has_meta_repo


def test_get_task_by_id(meta: MetadataRepository, project: Project, task: Task):
    project = meta.create_project(project)
    task.project_id = project.id
    task_new = meta.create_task(task)  # Assume that we do not change the task var in the create_task.
    assert task_new is not None
    assert task_new == meta.get_task_by_id(task_new.id)
    assert task.has_meta_repo


def test_get_or_create_task_not_exists(meta: MetadataRepository):
    project_name = 'test project'
    task = meta.get_or_create_task(project_name, "Test Task")
    assert task is not None
    assert task.id is not None
    assert task.name == "Test Task"
    assert task.project_id is not None

    project = meta.get_project_by_name(project_name)
    assert project.id is not None
    assert project.name == project_name

    assert len(project.tasks) != 0
    assert task.id in project.tasks
    assert task.has_meta_repo


def test_get_or_create_task_exists(meta: MetadataRepository, project: Project, task: Task):
    task.project = meta.create_project(project)
    expected_task = meta.create_task(task)

    actual_task = meta.get_or_create_task(project.name, expected_task.name)
    assert actual_task is not None
    assert expected_task == actual_task
    assert id(expected_task) != id(actual_task)

    project = meta.get_project_by_name(project.name)
    assert expected_task in project.tasks.values()

    assert expected_task.project_id == actual_task.project_id
    assert actual_task.has_meta_repo


def test_get_or_create_task_project_exists(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)
    assert project is not None

    task = meta.get_or_create_task(project.name, "Test Task")
    assert task is not None
    assert task.id is not None
    assert task.name == "Test Task"

    task_project = meta.get_project_by_id(task.project_id)
    assert task_project.id == task.project_id


def test_update_task_with_models(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    id = task.id

    model.task = task
    model = meta.create_model(model)
    task.add_model(model)

    task = update_object_fields(task,
                                excepted_fields=['id', 'models', 'pipelines', 'datasets', 'evaluation_sets', 'metrics',
                                                 'project_id'])
    model = update_object_fields(model, excepted_fields=['id', 'wrapper', 'artifact', 'requirements',
                                                         'wrapper_meta', 'task_id', 'wrapper_obj', 'params',
                                                         'evaluations'])
    updated_task = meta.update_task(task)

    assert id == task.id
    assert updated_task is task
    assert task == meta.get_task_by_id(task.id)
    assert len(task.models) == 1

    assert model.id in task.models
    assert model == meta.get_model_by_id(model.id)
    assert meta.get_model_by_id(model.id).name == 'Test Model2'
    assert task.has_meta_repo


def test_update_task_with_pipelines(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    id = task.id

    pipeline.task = task
    pipeline = meta.create_pipeline(pipeline)
    task.add_pipeline(pipeline)

    task = update_object_fields(task, excepted_fields=['id', 'pipelines', 'models', 'images', 'project_id', 'datasets',
                                                       'metrics', 'evaluation_sets', 'evaluations'])
    pipeline = update_object_fields(pipeline, excepted_fields=['id', 'steps', 'input_data', 'output_data',
                                                               'models', 'task_id', 'evaluations'])
    updated_task = meta.update_task(task)

    assert id == task.id
    assert updated_task is task
    assert task == meta.get_task_by_id(task.id)
    assert len(task.pipelines) == 1

    assert pipeline.id in task.pipelines
    assert pipeline == meta.get_pipeline_by_id(pipeline.id)
    assert meta.get_pipeline_by_id(pipeline.id).name == 'Test Pipeline2'
    assert task.has_meta_repo


def test_update_task_with_images(meta: MetadataRepository, project: Project, task: Task, image, environment):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    id = task.id
    env = meta.create_environment(environment)

    image.task = task
    image.environment = env
    image = meta.create_image(image)
    task.add_image(image)

    task = update_object_fields(task, excepted_fields=['id', 'pipelines', 'models', 'images', 'project_id', 'datasets',
                                                       'evaluation_sets', 'metrics'])
    image = update_object_fields(image, excepted_fields=['id', 'params', 'source', 'environment_id', 'task_id'])
    updated_task = meta.update_task(task)

    assert id == task.id
    assert updated_task is task
    assert task == meta.get_task_by_id(task.id)
    assert len(task.images) == 1

    assert image.id in task.images
    assert image == meta.get_image_by_id(image.id)
    assert meta.get_image_by_id(image.id).name == 'Meta Test Image2'
    assert task.has_meta_repo


def test_update_task_source_is_changed(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)

    saved_task = meta.create_task(task)
    assert saved_task is task

    id = saved_task.id

    model.task = saved_task
    model = meta.create_model(model)

    saved_task = update_object_fields(saved_task,
                                      excepted_fields=['id', 'models', 'pipelines', 'datasets', 'evaluation_sets',
                                                       'metrics', 'project_id'])

    saved_task.add_model(model)
    saved_task = meta.update_task(saved_task)

    assert id == saved_task.id
    assert saved_task == meta.get_task_by_id(saved_task.id)
    assert model == saved_task.models.get(model.id)

    assert task is saved_task


def test_update_task_is_reference(meta: MetadataRepository, project: Project, model: Model):
    task_entity = Task("Test Task")
    task_entity.project = meta.create_project(project)
    task = meta.create_task(task_entity)
    assert task is not None

    id = task.id

    model.task_id = task.id
    model = meta.create_model(model)

    task.name = "Test Task 2"
    task.add_model(model)
    task = meta.update_task(task)

    assert id == task.id
    assert "Test Task 2" == task.name
    assert model == task.models.get(model.id)

    task.name = "KEK"
    actual_task = meta.get_task_by_id(task.id)
    assert_objects_equal_except_fields(task, actual_task, excepted_fields=['name'])


def test_update_not_existing_task(meta: MetadataRepository, project: Project, task: Task):
    project = meta.create_project(project)
    assert project is not None

    task.project = project
    with pytest.raises(NonExistingTaskError):
        meta.update_task(task)


def test_save_not_existing_task(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)
    task = Task("Task")
    task.project = project

    saved_task = meta.save_task(task)
    assert saved_task.name == task.name
    assert saved_task.project_id == task.project_id
    assert task.name == meta.get_task_by_id(saved_task.id).name
    assert task.has_meta_repo


def test_save_existing_task(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)
    task = Task("Task")
    task.project = project
    task = meta.create_task(task)

    saved_task = meta.save_task(task)
    assert saved_task.id == task.id
    assert saved_task.project_id == task.project_id
    assert task == meta.get_task_by_id(saved_task.id)
    assert task.has_meta_repo


def test_save_updated_existing_task(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)
    task = Task("Task")
    task.project = project
    task = meta.create_task(task)

    task = update_object_fields(task,
                                excepted_fields=['id', 'models', 'pipelines', 'datasets', 'evaluation_sets', 'metrics',
                                                 'project_id'])

    saved_task = meta.save_task(task)
    assert saved_task == task
    assert task == meta.get_task_by_id(saved_task.id)


def test_save_updated_existing_task_with_existing_name(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)
    task = Task("Task")
    task.project = project
    task = meta.create_task(task)

    task2 = Task("Task2")
    task2.project = project
    task2 = meta.create_task(task2)

    task.name = "Task2"
    with pytest.raises(ExistingTaskError):
        meta.save_task(task)


def test_save_task_is_reference(meta: MetadataRepository, project: Project):
    project = meta.create_project(project)
    task = Task("Task")
    task.project = project
    saved_task = meta.save_task(task)

    saved_task.name = "KEK"
    actual_task = meta.get_task_by_id(saved_task.id)
    assert_objects_equal_except_fields(saved_task, actual_task, excepted_fields=['name'])


def test_delete_task(meta: MetadataRepository, project: Project, task: Task):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    meta.delete_task(task)
    assert meta.get_task_by_id(task.id) is None
    assert not task.has_meta_repo
    assert task.id is None

    project = meta.get_project_by_id(project.id)

    assert len(project.tasks) == 0


def test_delete_not_existing_task(meta: MetadataRepository, task: Task):
    with pytest.raises(NonExistingTaskError):
        meta.delete_task(task)


def test_create_model(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    model.task_id = task.id
    model = meta.create_model(model)
    assert model is not None
    assert model.has_meta_repo

    task = meta.get_task_by_id(task.id)
    assert len(task.models) == 1
    assert model.id in task.models
    assert task.models[model.id] == model


def test_create_model_without_task(meta: MetadataRepository, model: Model):
    with pytest.raises(ModelNotInTaskError):
        meta.create_model(model)


def test_create_model_source_is_changed(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    model.task_id = task.id
    saved_model = meta.create_model(model)
    assert saved_model is model


def test_create_model_is_reference(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    model.task_id = task.id
    model = meta.create_model(model)
    assert model is not None

    model.name = "KEK"
    actual_model = meta.get_model_by_id(model.id)
    assert_objects_equal_except_fields(model, actual_model, excepted_fields=['name'])

    model.task_id = None
    actual_model = meta.get_model_by_id(model.id)
    assert_objects_equal_except_fields(model, actual_model, excepted_fields=['name', 'task_id'])


def test_create_existing_model(meta: MetadataRepository, project: Project, task: Task, model: Model, model2: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    model.task_id = task.id
    model = meta.create_model(model)
    assert model is not None

    model2.task_id = task.id
    model2.name = model.name
    with pytest.raises(ExistingModelError):
        meta.create_model(model2)


def test_create_model_with_unexisting_task(meta: MetadataRepository, model: Model):
    model.task_id = 3
    with pytest.raises(NonExistingTaskError):
        meta.create_model(model)


def test_get_models(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    created_task = meta.create_task(task)
    model.task = created_task
    created_model = meta.create_model(model)

    actual_models = meta.get_models(created_task)
    assert actual_models == [created_model]


def test_get_model(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    model.task_id = task.id
    model = meta.create_model(model)
    assert model is not None

    assert model == meta.get_model_by_name(model.name, model.task_id)
    assert model.has_meta_repo


def test_get_model_by_id(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    model.task_id = task.id
    model = meta.create_model(model)
    assert model is not None
    assert model == meta.get_model_by_id(model.id)
    assert model.has_meta_repo


def test_update_model(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    model.task_id = task.id
    model = meta.create_model(model)
    assert model is not None

    id = model.id

    model = update_object_fields(model, excepted_fields=['id', 'wrapper', 'artifact', 'requirements',
                                                         'wrapper_meta', 'task_id', 'wrapper_obj', 'params',
                                                         'evaluations'])
    model = meta.update_model(model)

    assert id == model.id
    assert model == meta.get_model_by_id(model.id)
    assert model.has_meta_repo


def test_update_model_source_is_changed(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    model.task_id = task.id
    saved_model = meta.create_model(model)
    assert saved_model is not None

    id = saved_model.id

    saved_model = update_object_fields(model, excepted_fields=['id', 'wrapper', 'artifact', 'requirements',
                                                               'wrapper_meta', 'task_id', 'wrapper_obj', 'params',
                                                               'evaluations'])
    saved_model = meta.update_model(saved_model)

    assert id == saved_model.id
    assert model == meta.get_model_by_id(saved_model.id)
    assert model is saved_model


def test_update_model_is_reference(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    model.task_id = task.id
    model = meta.create_model(model)
    assert model is not None

    id = model.id

    model.name = "Test Model 2"
    model = meta.update_model(model)

    assert id == model.id
    assert "Test Model 2" == model.name

    model.name = "KEK"
    actual_model = meta.get_model_by_id(model.id)
    assert_objects_equal_except_fields(model, actual_model, excepted_fields=['name'])


def test_update_not_existing_model(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    model.task_id = task.id

    with pytest.raises(NonExistingModelError):
        meta.update_model(model)


def test_save_not_existing_model(meta: MetadataRepository, project: Project, task: Task, model: Model):
    project = meta.create_project(project)
    task.project = project
    task = meta.create_task(task)

    model.task_id = task.id

    saved_model = meta.save_model(model)
    assert saved_model.name == model.name
    assert saved_model.task_id == model.task_id
    assert model.name == meta.get_model_by_id(saved_model.id).name
    assert model.has_meta_repo


def test_save_existing_model(meta: MetadataRepository, project: Project, task: Task, model: Model):
    project = meta.create_project(project)
    task.project = project
    task = meta.create_task(task)

    model.task_id = task.id
    model = meta.create_model(model)

    saved_model = meta.save_model(model)
    assert saved_model.id == model.id
    assert saved_model.task_id == model.task_id
    assert model == meta.get_model_by_id(saved_model.id)


def test_save_updated_existing_model(meta: MetadataRepository, project: Project, task: Task, model: Model):
    project = meta.create_project(project)
    task.project = project
    task = meta.create_task(task)

    model.task_id = task.id
    model = meta.create_model(model)

    model = update_object_fields(model, excepted_fields=['id', 'wrapper', 'artifact', 'requirements',
                                                         'wrapper_meta', 'task_id', 'wrapper_obj', 'params',
                                                         'evaluations'])

    saved_model = meta.save_model(model)
    assert saved_model == model
    assert model == meta.get_model_by_id(saved_model.id)


def test_save_updated_existing_model_with_existing_name(meta: MetadataRepository, project: Project, task: Task,
                                                        model: Model, model2: Model):
    project = meta.create_project(project)
    task.project = project
    task = meta.create_task(task)

    model.task_id = task.id
    model = meta.create_model(model)

    model2.task_id = task.id
    model2 = meta.create_model(model2)

    model.name = model2.name
    with pytest.raises(ExistingModelError):
        meta.save_model(model)


def test_save_model_is_reference(meta: MetadataRepository, project: Project, task: Task, model: Model):
    project = meta.create_project(project)
    task.project = project
    task = meta.create_task(task)

    model.task_id = task.id

    saved_model = meta.save_model(model)

    saved_model.name = "KEK"
    actual_model = meta.get_model_by_id(saved_model.id)
    assert_objects_equal_except_fields(saved_model, actual_model, excepted_fields=['name'])


def test_delete_model(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    model.task_id = task.id
    model = meta.create_model(model)
    assert model is not None

    meta.delete_model(model)
    assert meta.get_model_by_id(model.id) is None
    assert not model.has_meta_repo
    assert model.id is None

    task = meta.get_task_by_id(task.id)

    assert len(task.models) == 0


def test_delete_not_existing_model(meta: MetadataRepository, model: Model):
    with pytest.raises(NonExistingModelError):
        meta.delete_model(model)


# __________
def test_create_pipeline(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    pipeline.task_id = task.id
    pipeline = meta.create_pipeline(pipeline)
    assert pipeline is not None
    assert pipeline.has_meta_repo

    task = meta.get_task_by_id(task.id)
    assert len(task.pipelines) == 1
    assert pipeline.id in task.pipelines
    assert task.pipelines[pipeline.id] == pipeline


def test_create_pipeline_without_task(meta: MetadataRepository, pipeline: Pipeline):
    with pytest.raises(PipelineNotInTaskError):
        meta.create_pipeline(pipeline)


def test_create_pipeline_with_unexisting_task(meta: MetadataRepository, pipeline: Pipeline):
    pipeline.task_id = 3
    with pytest.raises(NonExistingTaskError):
        meta.create_pipeline(pipeline)


def test_create_pipeline_source_is_changed(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    pipeline.task_id = task.id
    saved_pipeline = meta.create_pipeline(pipeline)
    assert saved_pipeline is pipeline


def test_create_pipeline_is_reference(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    pipeline.task_id = task.id
    pipeline = meta.create_pipeline(pipeline)
    assert pipeline is not None

    pipeline.name = "KEK"
    actual_pipeline = meta.get_pipeline_by_id(pipeline.id)
    assert_objects_equal_except_fields(pipeline, actual_pipeline, excepted_fields=['name'])

    pipeline.task_id = None
    actual_pipeline = meta.get_pipeline_by_id(pipeline.id)
    assert_objects_equal_except_fields(pipeline, actual_pipeline, excepted_fields=['name', 'task_id'])


def test_create_existing_pipeline(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline,
                                  pipeline2: Pipeline):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    pipeline.task_id = task.id
    pipeline = meta.create_pipeline(pipeline)
    assert pipeline is not None

    pipeline2.task_id = task.id
    pipeline2.name = pipeline.name
    with pytest.raises(ExistingPipelineError):
        meta.create_pipeline(pipeline2)


def test_get_pipelines(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    task.project = meta.create_project(project)
    created_task = meta.create_task(task)
    pipeline.task = created_task
    created_pipeline = meta.create_pipeline(pipeline)

    actual_pipelines = meta.get_pipelines(created_task)
    assert actual_pipelines == [created_pipeline]


def test_get_pipeline(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    pipeline.task_id = task.id
    pipeline = meta.create_pipeline(pipeline)
    assert pipeline is not None

    assert pipeline == meta.get_pipeline_by_name("Test Pipeline", pipeline.task_id)
    assert pipeline.has_meta_repo


def test_get_pipeline_by_id(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    pipeline.task_id = task.id
    pipeline = meta.create_pipeline(pipeline)
    assert pipeline is not None
    assert pipeline == meta.get_pipeline_by_id(pipeline.id)
    assert pipeline.has_meta_repo


def test_update_pipeline(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    pipeline.task_id = task.id
    pipeline = meta.create_pipeline(pipeline)
    assert pipeline is not None

    id = pipeline.id

    pipeline = update_object_fields(pipeline,
                                    excepted_fields=['id', 'input_data', 'output_data', 'task_id', 'evaluations'])
    pipeline = meta.update_pipeline(pipeline)

    assert id == pipeline.id
    assert pipeline == meta.get_pipeline_by_id(pipeline.id)
    assert pipeline.has_meta_repo


def test_update_pipeline_source_is_changed(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    pipeline.task_id = task.id
    saved_pipeline = meta.create_pipeline(pipeline)
    assert saved_pipeline is not None

    id = saved_pipeline.id

    saved_pipeline = update_object_fields(pipeline,
                                          excepted_fields=['id', 'input_data', 'output_data', 'task_id', 'evaluations'])
    saved_pipeline = meta.update_pipeline(saved_pipeline)

    assert id == saved_pipeline.id
    assert pipeline == meta.get_pipeline_by_id(saved_pipeline.id)
    assert pipeline is saved_pipeline


def test_update_pipeline_is_reference(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    pipeline.task_id = task.id
    pipeline = meta.create_pipeline(pipeline)
    assert pipeline is not None

    id = pipeline.id

    pipeline.name = "Test Pipeline 2"
    pipeline = meta.update_pipeline(pipeline)

    assert id == pipeline.id
    assert "Test Pipeline 2" == pipeline.name

    pipeline.name = "KEK"
    actual_pipeline = meta.get_pipeline_by_id(pipeline.id)
    assert_objects_equal_except_fields(pipeline, actual_pipeline, excepted_fields=['name'])


def test_update_not_existing_pipeline(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    pipeline.task_id = task.id

    with pytest.raises(NonExistingPipelineError):
        meta.update_pipeline(pipeline)


def test_save_not_existing_pipeline(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    project = meta.create_project(project)
    task.project = project
    task = meta.create_task(task)

    pipeline.task_id = task.id

    saved_pipeline = meta.save_pipeline(pipeline)
    assert saved_pipeline.name == pipeline.name
    assert saved_pipeline.task_id == pipeline.task_id
    assert pipeline.name == meta.get_pipeline_by_id(saved_pipeline.id).name
    assert pipeline.has_meta_repo


def test_save_existing_pipeline(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    project = meta.create_project(project)
    task.project = project
    task = meta.create_task(task)

    pipeline.task_id = task.id
    pipeline = meta.create_pipeline(pipeline)

    saved_pipeline = meta.save_pipeline(pipeline)
    assert saved_pipeline.id == pipeline.id
    assert saved_pipeline.task_id == pipeline.task_id
    assert pipeline == meta.get_pipeline_by_id(saved_pipeline.id)


def test_save_updated_existing_pipeline(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    project = meta.create_project(project)
    task.project = project
    task = meta.create_task(task)

    pipeline.task_id = task.id
    pipeline = meta.create_pipeline(pipeline)

    pipeline = update_object_fields(pipeline,
                                    excepted_fields=['id', 'input_data', 'output_data', 'task_id', 'evaluations'])

    saved_pipeline = meta.save_pipeline(pipeline)
    assert saved_pipeline == pipeline
    assert pipeline == meta.get_pipeline_by_id(saved_pipeline.id)


def test_save_updated_existing_pipeline_with_existing_name(meta: MetadataRepository, project: Project, task: Task,
                                                           pipeline: Pipeline, pipeline2: Pipeline):
    project = meta.create_project(project)
    task.project = project
    task = meta.create_task(task)

    pipeline.task_id = task.id
    pipeline = meta.create_pipeline(pipeline)

    pipeline2.task_id = task.id
    pipeline2 = meta.create_pipeline(pipeline2)

    pipeline.name = pipeline2.name
    with pytest.raises(ExistingPipelineError):
        meta.save_pipeline(pipeline)


def test_save_pipeline_is_reference(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    project = meta.create_project(project)
    task.project = project
    task = meta.create_task(task)

    pipeline.task_id = task.id

    saved_pipeline = meta.save_pipeline(pipeline)

    saved_pipeline.name = "KEK"
    actual_pipeline = meta.get_pipeline_by_id(saved_pipeline.id)
    assert_objects_equal_except_fields(saved_pipeline, actual_pipeline, excepted_fields=['name'])


def test_delete_pipeline(meta: MetadataRepository, project: Project, task: Task, pipeline: Pipeline):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    pipeline.task_id = task.id
    pipeline = meta.create_pipeline(pipeline)
    assert pipeline is not None

    meta.delete_pipeline(pipeline)
    assert meta.get_pipeline_by_id(pipeline.id) is None
    assert not pipeline.has_meta_repo
    assert pipeline.id is None

    task = meta.get_task_by_id(task.id)

    assert len(task.pipelines) == 0


def test_delete_not_existing_pipeline(meta: MetadataRepository, pipeline: Pipeline):
    with pytest.raises(NonExistingPipelineError):
        meta.delete_pipeline(pipeline)


# ___________

def test_get_images__empty(meta: MetadataRepository, created_task):
    assert meta.get_images(created_task) == []


def test_get_images__full(meta: MetadataRepository, created_task, created_image):
    assert meta.get_images(created_task) == [created_image]


def test_get_image_by_name(meta: MetadataRepository, created_task, created_image):
    assert meta.get_image_by_name(created_image.name, created_task) == created_image


def test_get_image_by_id(meta: MetadataRepository, created_image):
    assert meta.get_image_by_id(created_image.id) == created_image


def test_create_image__ok(meta: MetadataRepository, image, created_image, created_task):
    assert image.id is None
    assert created_image.id is not None

    assert created_image.task_id == created_task.id

    assert created_image.name == image.name
    assert created_image.params == image.params

    task = meta.get_task_by_id(created_image.task_id)
    assert len(task.images) == 1
    assert created_image.id in task.images
    assert task.images[created_image.id] == created_image


def test_create_image__no_task(meta: MetadataRepository, image):
    with pytest.raises(ImageNotInTaskError):
        meta.create_image(image)


def test_create_image__saved_image(meta: MetadataRepository, created_image):
    with pytest.raises(ExistingImageError):
        meta.create_image(created_image)


def test_create_image_with_unexisting_task(meta: MetadataRepository, image):
    image.task_id = 3
    with pytest.raises(NonExistingTaskError):
        meta.create_image(image)


def test_update_image__ok(meta: MetadataRepository, created_image):
    author = 'hey'
    key = 2
    assert created_image.author != author
    assert created_image.params.key != key

    created_image.author = author
    created_image.params.key = key
    i = meta.update_image(created_image)

    assert i.author == author
    assert i.params.key == key


def test_update_image__no_task(meta: MetadataRepository, created_image):
    created_image.task_id = None

    with pytest.raises(ImageNotInTaskError):
        meta.create_image(created_image)


def test_update_image__unsaved_image(meta: MetadataRepository, created_task, image):
    image.task = created_task

    with pytest.raises(NonExistingImageError):
        meta.update_image(image)


def test_delete_image__ok(meta: MetadataRepository, created_image):
    task = meta.get_task_by_id(created_image.task_id)
    meta.delete_image(created_image)

    assert created_image.id is None
    assert not created_image.has_meta_repo

    task = meta.get_task_by_id(task.id)

    assert len(task.images) == 0


def test_delete_image__unsaved_image(meta: MetadataRepository, image):
    with pytest.raises(NonExistingImageError):
        meta.delete_image(image)


def test_save_image_ok_unsaved(meta: MetadataRepository, created_task, created_environment, image):
    image.task = created_task
    image.environment = created_environment
    image = meta.save_image(image)

    assert image.id is not None
    assert image.task_id is not None
    assert image.task == created_task
    assert image.has_meta_repo


def test_save_image_ok_saved(meta: MetadataRepository, created_image):
    image = meta.save_image(created_image)

    assert image.id is not None
    assert image.has_meta_repo


def test_save_image__no_model(meta: MetadataRepository, image):
    with pytest.raises(ImageNotInTaskError):
        meta.save_image(image)


def test_save_image__other_id(meta: MetadataRepository, created_image):
    created_image._id = 12345

    with pytest.raises(ExistingImageError):
        meta.save_image(created_image)


def test_get_environments__empty(meta: MetadataRepository):
    assert meta.get_environments() == []


def test_get_environments__full(meta: MetadataRepository, created_environment):
    assert meta.get_environments() == [created_environment]


def test_get_environment_by_id__empty(meta: MetadataRepository):
    assert meta.get_environment_by_id(12345) is None


def test_get_environment_by_id__full(meta: MetadataRepository, created_environment):
    assert meta.get_environment_by_id(created_environment.id) == created_environment


def test_get_environment_by_name__empty(meta: MetadataRepository):
    assert meta.get_environment_by_name('qwerty') is None


def test_get_environment_by_name__full(meta: MetadataRepository, created_environment):
    assert meta.get_environment_by_name(created_environment.name) == created_environment


def test_create_environment__ok(meta: MetadataRepository, environment, created_environment):
    assert environment.id is None
    assert not environment.has_meta_repo

    assert created_environment.id is not None
    assert created_environment.has_meta_repo

    assert created_environment.name == environment.name
    assert created_environment.params == environment.params


def test_create_environment__saved(meta: MetadataRepository, created_environment):
    with pytest.raises(ExistingEnvironmentError):
        meta.create_environment(created_environment)


def test_update_environment__ok(meta: MetadataRepository, created_environment):
    key = 2
    assert created_environment.params.key != key

    created_environment.params.key = key
    environment = meta.update_environment(created_environment)

    assert environment.params.key == key


def test_update_environment__not_existing(meta: MetadataRepository, environment):
    with pytest.raises(NonExistingEnvironmentError):
        meta.update_environment(environment)


def test_delete_environment__ok(meta: MetadataRepository, created_environment):
    assert meta.get_environments() == [created_environment]

    meta.delete_environment(created_environment)

    assert meta.get_environments() == []


def test_delete_environment__not_existing(meta: MetadataRepository, environment):
    with pytest.raises(NonExistingEnvironmentError):
        meta.delete_environment(environment)


def test_save_environment__ok_existing(meta: MetadataRepository, created_environment):
    key = 2
    assert created_environment.params.key != key

    created_environment.params.key = key
    environment = meta.save_environment(created_environment)

    assert environment.params.key == key


def test_save_environment__ok_not_existing(meta: MetadataRepository, environment):
    assert environment.id is None
    assert not environment.has_meta_repo

    created_environment = meta.save_environment(environment)

    assert created_environment.id is not None
    assert created_environment.has_meta_repo

    assert created_environment.name == environment.name
    assert created_environment.params == environment.params


def test_save_environment__other_id(meta: MetadataRepository, created_environment):
    created_environment._id = 12345

    with pytest.raises(ExistingEnvironmentError):
        meta.save_environment(created_environment)


def test_get_instances__empty(meta: MetadataRepository, created_image, created_environment):
    assert meta.get_instances(created_image, created_environment) == []


def test_get_instances__full(meta: MetadataRepository, created_image, created_environment, created_instance):
    assert meta.get_instances(created_image, created_environment) == [created_instance]


def test_get_instances__empty_only_image(meta: MetadataRepository, created_image):
    assert meta.get_instances(created_image, None) == []


def test_get_instance__only_image(meta: MetadataRepository, created_image, created_instance):
    assert meta.get_instances(created_image, None) == [created_instance]


def test_get_instances__full_only_image(meta: MetadataRepository, created_image, created_instance):
    assert meta.get_instances(created_image, None) == [created_instance]


def test_get_instances__empty_only_environment(meta: MetadataRepository, created_environment):
    assert meta.get_instances(None, created_environment) == []


def test_get_instance__only_environment(meta: MetadataRepository, created_environment, created_instance):
    assert meta.get_instances(None, created_environment) == [created_instance]


def test_get_instances__full_only_environment(meta: MetadataRepository, created_environment, created_instance):
    assert meta.get_instances(None, created_environment) == [created_instance]


def test_get_instance_by_name__empty(meta: MetadataRepository, created_image, created_environment):
    assert meta.get_instance_by_name('qwerty', created_image, created_environment) is None


def test_get_instance_by_name__full(meta: MetadataRepository, created_image, created_environment, created_instance):
    assert meta.get_instance_by_name(created_instance.name, created_image, created_environment) == created_instance


def test_get_instance_by_id__empty(meta: MetadataRepository):
    assert meta.get_instance_by_id(12345) is None


def test_get_instance_by_id__full(meta: MetadataRepository, created_instance):
    assert meta.get_instance_by_id(created_instance.id) == created_instance


def test_create_instance__ok(meta: MetadataRepository, instance, created_instance):
    assert instance.id is None
    assert not instance.has_meta_repo

    assert created_instance.id is not None
    assert created_instance.has_meta_repo

    assert created_instance.name == instance.name
    assert created_instance.params == instance.params


def test_created_instance__existing(meta: MetadataRepository, created_instance):
    with pytest.raises(ExistingInstanceError):
        meta.create_instance(created_instance)


def test_update_instance__ok(meta: MetadataRepository, created_instance):
    key = 2
    assert created_instance.params.key != key

    created_instance.params.key = key
    instance = meta.update_instance(created_instance)

    assert instance.params.key == key


def test_update_instance__not_existing(meta: MetadataRepository, created_instance):
    created_instance._id = 12345

    with pytest.raises(NonExistingInstanceError):
        meta.update_instance(created_instance)


def test_delete_instance__ok(meta: MetadataRepository, created_instance):
    image, environment = created_instance.image_id, created_instance.environment_id
    assert meta.get_instances(image, environment) == [created_instance]

    meta.delete_instance(created_instance)

    assert meta.get_instances(image, environment) == []


def test_delete_instance__not_existing(meta: MetadataRepository, instance):
    with pytest.raises(NonExistingInstanceError):
        meta.delete_instance(instance)


def test_save_instance__ok_existing(meta: MetadataRepository, created_instance):
    key = 2
    assert created_instance.params.key != key

    created_instance.params.key = key
    instance = meta.save_instance(created_instance)

    assert instance.params.key == key


def test_save_instance__ok_not_existing(meta: MetadataRepository, created_image, created_environment, instance):
    assert instance.id is None
    assert not instance.has_meta_repo

    instance.image = created_image
    instance.environment = created_environment
    created_instance = meta.save_instance(instance)

    assert created_instance.id is not None
    assert created_instance.has_meta_repo

    assert created_instance.image == created_image
    assert created_instance.environment == created_environment

    assert created_instance.name == instance.name
    assert created_instance.params == instance.params


def test_inner_objects_binded(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    meta.create_task(task)

    model.task_id = task.id
    model = meta.create_model(model)

    new_project = meta.get_project_by_name(project.name)
    assert new_project.id is not None
    assert new_project.has_meta_repo
    new_task = new_project.tasks(task.name)
    assert new_task.id is not None
    assert new_task.has_meta_repo
    new_model = new_task.models(model.name)
    assert new_model.id is not None
    assert new_model.has_meta_repo
