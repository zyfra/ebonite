import datetime
from typing import List

import pytest
from pyjackson.utils import get_class_fields

from ebonite.core.errors import (ExistingModelError, ExistingProjectError, ExistingTaskError, ModelNotInTaskError,
                                 NonExistingModelError, NonExistingProjectError, NonExistingTaskError,
                                 TaskNotInProjectError)
from ebonite.core.objects.core import Model, Project, Task
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
            setattr(o, field, v + additional_value)
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
    task = update_object_fields(task, excepted_fields=['id', 'models', 'project_id'])

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


def test_create_task_without_project(meta: MetadataRepository, task: Task):
    with pytest.raises(TaskNotInProjectError):
        meta.create_task(task)


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

    task = update_object_fields(task, excepted_fields=['id', 'models', 'project_id'])
    model = update_object_fields(model, excepted_fields=['id', 'wrapper', 'artifact',
                                                         'output_meta', 'input_meta', 'requirements',
                                                         'transformer', 'task_id'])
    updated_task = meta.update_task(task)

    assert id == task.id
    assert updated_task is task
    assert task == meta.get_task_by_id(task.id)
    assert len(task.models) == 1

    assert model.id in task.models
    assert model == meta.get_model_by_id(model.id)
    assert meta.get_model_by_id(model.id).name == 'Test Model2'
    assert task.has_meta_repo


def test_update_task_source_is_changed(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)

    saved_task = meta.create_task(task)
    assert saved_task is task

    id = saved_task.id

    model.task = saved_task
    model = meta.create_model(model)

    saved_task = update_object_fields(saved_task, excepted_fields=['id', 'models', 'project_id'])

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

    task = update_object_fields(task, excepted_fields=['id', 'models', 'project_id'])

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


def test_get_model(meta: MetadataRepository, project: Project, task: Task, model: Model):
    task.project = meta.create_project(project)
    task = meta.create_task(task)
    assert task is not None

    model.task_id = task.id
    model = meta.create_model(model)
    assert model is not None

    assert model == meta.get_model_by_name("Test Model", model.task_id)
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

    model = update_object_fields(model, excepted_fields=['id', 'wrapper', 'artifact',
                                                         'output_meta', 'input_meta', 'requirements',
                                                         'transformer', 'task_id'])
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

    saved_model = update_object_fields(model, excepted_fields=['id', 'wrapper', 'artifact',
                                                               'output_meta', 'input_meta', 'requirements',
                                                               'transformer', 'task_id'])
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

    model = update_object_fields(model, excepted_fields=['id', 'wrapper', 'artifact',
                                                         'output_meta', 'input_meta', 'requirements',
                                                         'transformer', 'task_id'])

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


def test_delete_not_existing_model(meta: MetadataRepository, model: Model):
    with pytest.raises(NonExistingModelError):
        meta.delete_model(model)
