import numpy as np
import pytest

from ebonite.core.errors import MetadataError, NonExistingModelError, NonExistingTaskError, UnboundObjectError
from ebonite.core.objects.core import Model, Project, Task
from ebonite.core.objects.requirements import InstallableRequirement, Requirement, Requirements
from ebonite.ext.pandas import DataFrameType
from ebonite.ext.sklearn import SklearnModelWrapper
from ebonite.repository import MetadataRepository
from tests.core.objects.conftest import serde_and_compare


def test_project__add_task__unbind(project: Project, task_factory):
    with pytest.raises(UnboundObjectError):
        project.add_task(task_factory())


@pytest.mark.parametrize('set_project_id', [True, False])
def test_project__add_task__new(set_project_id, meta: MetadataRepository, project_b: Project, task_factory):
    assert len(project_b.tasks) == 0
    task: Task = task_factory()
    if set_project_id:
        task.project = project_b
    project_b.add_task(task)
    assert len(project_b.tasks) == 1
    task_id = task.id
    assert task_id is not None
    assert task == meta.get_task_by_id(task_id)
    assert task == project_b.tasks[task_id]
    assert task == project_b.tasks(task.name)


def test_project__add_task__wrong_project(meta: MetadataRepository, project_factory, task_factory):
    project1 = project_factory(True)
    project2 = project_factory(True)
    assert len(project1.tasks) == 0
    task: Task = task_factory()
    task.project = project2
    meta.create_task(task)
    with pytest.raises(MetadataError):
        project1.add_task(task)


def test_project__add_tasks(project_b: Project, task_factory, meta: MetadataRepository):
    tasks = [task_factory() for _ in range(5)]
    assert len(project_b.tasks) == 0
    project_b.add_tasks(tasks)
    assert len(project_b.tasks) == 5

    for t in tasks:
        task_id = t.id
        assert task_id is not None
        assert t == meta.get_task_by_id(task_id)
        assert t == project_b.tasks[task_id]
        assert t == project_b.tasks(t.name)


def test_project__add_tasks__empty(project_b: Project):
    project_b.add_tasks([])
    assert len(project_b.tasks) == 0


def test_project__delete_task(project_b, task):
    project_b.add_task(task)
    assert task.id is not None
    assert task.project_id is not None

    project_b.delete_task(task)
    assert len(project_b.tasks) == 0

    assert task.id is None
    assert task.project_id is None


def test_project__delete_task__nonexistent(project_factory, task):
    task_project = project_factory(True)
    task_project.add_task(task)

    project = project_factory(True)
    with pytest.raises(NonExistingTaskError):
        project.delete_task(task)


def test_project_serde(project_b: Project):
    serde_and_compare(project_b)


@pytest.mark.parametrize('set_task_id', [True, False])
def test_task__add_model__new(set_task_id, meta: MetadataRepository, task_b: Task, model_factory):
    assert len(task_b.models) == 0
    model: Model = model_factory()
    if set_task_id:
        model.task = task_b
    task_b.add_model(model)
    assert len(task_b.models) == 1
    model_id = model.id
    assert model_id is not None
    assert model == meta.get_model_by_id(model_id)
    assert model == task_b.models[model_id]
    assert model == task_b.models(model.name)


def test_task__add_model__wrong_task(meta: MetadataRepository, task_factory, model_factory):
    task1 = task_factory(True)
    task2 = task_factory(True)
    assert len(task1.models) == 0
    model: Model = model_factory()
    model.task = task2
    meta.create_model(model)
    with pytest.raises(MetadataError):
        task1.add_model(model)


def test_task__add_models(task_b: Task, model_factory, meta: MetadataRepository):
    models = [model_factory() for _ in range(5)]
    assert len(task_b.models) == 0
    task_b.add_models(models)
    assert len(task_b.models) == 5

    for m in models:
        model_id = m.id
        assert model_id is not None
        assert m == meta.get_model_by_id(model_id)
        assert m == task_b.models[model_id]
        assert m == task_b.models(m.name)


def test_task__add_models__empty(task_b: Task):
    task_b.add_models([])
    assert len(task_b.models) == 0


def test_task__delete_model(task_b: Task, model):
    task_b.add_model(model)
    assert model.id is not None
    assert model.task_id is not None

    task_b.delete_model(model)
    assert len(task_b.models) == 0

    assert model.id is None
    assert model.task_id is None


def test_task__delete_model__nonexistent(task_factory, model):
    model_task = task_factory(True)
    model_task.add_model(model)

    task = task_factory(True)
    with pytest.raises(NonExistingModelError):
        task.delete_model(task)


def test_task__serde(task_b: Task):
    serde_and_compare(task_b)


def test_task__create_and_push_model(task_b2, sklearn_model_obj, pandas_data):
    model_name = 'Test Model'
    task_b2.create_and_push_model(sklearn_model_obj, pandas_data, model_name)

    assert task_b2._meta.get_model_by_name(model_name, task_b2) is not None


def test_task__push_model(task_b2, created_model):
    task_b2.push_model(created_model)

    assert task_b2._meta.get_model_by_name(created_model.name, task_b2) is not None


# ###############MODEL##################
def test_create_model(sklearn_model_obj, pandas_data):
    model = Model.create(sklearn_model_obj, pandas_data)
    assert model is not None
    assert isinstance(model.wrapper, SklearnModelWrapper)
    assert model.input_meta.columns == list(pandas_data)
    # assert model.input_meta. == data.values

    assert model.output_meta.real_type == np.ndarray
    assert {'numpy', 'sklearn', 'pandas'}.issubset(model.requirements.modules)


def test_create_model_with_custom_wrapper(sklearn_model_obj, pandas_data):
    wrapper = SklearnModelWrapper().bind_model(sklearn_model_obj)
    model = Model.create(sklearn_model_obj, pandas_data, custom_wrapper=wrapper)
    assert model is not None
    assert isinstance(model.wrapper, SklearnModelWrapper)
    assert model.input_meta.columns == list(pandas_data)
    assert model.output_meta.real_type == np.ndarray
    assert {'numpy', 'sklearn', 'pandas'}.issubset(model.requirements.modules)


def test_create_model_with_custom_input_meta(sklearn_model_obj, pandas_data):
    model = Model.create(sklearn_model_obj, pandas_data, custom_input_meta=DataFrameType(['kek1', 'kek2']))
    assert model is not None
    assert issubclass(model.input_meta, DataFrameType)


def test_create_model_with_custom_requirements(sklearn_model_obj, pandas_data):
    requirements = Requirements([InstallableRequirement('dumb', '0.4.1'), InstallableRequirement('art', '4.0')])
    model = Model.create(sklearn_model_obj, pandas_data, custom_requirements=Requirements([Requirement()]))
    assert model is not None
    assert all(req in [r.module for r in requirements.installable] for req in model.requirements.installable)


def test_create_model_with_additional_artifact(artifact, sklearn_model_obj, pandas_data, artifact_repository):
    model = Model.create(sklearn_model_obj, pandas_data, additional_artifacts=artifact)
    assert model is not None
    model._id = 'test_model'
    artifact_repository.push_artifacts(model)
    assert len(model.artifact_req_persisted.bytes_dict()) == 2

    model_payloads = model.artifact_req_persisted.bytes_dict()
    for name, payload in artifact.bytes_dict().items():
        assert name in model_payloads
        assert model_payloads[name] == payload


def test_model_serde(model):
    serde_and_compare(model, Model)


# ################BASE#####################
def test_base_author(sklearn_model_obj, pandas_data, username):
    model = Model.create(sklearn_model_obj, pandas_data)
    assert model is not None
    assert model.author == username
