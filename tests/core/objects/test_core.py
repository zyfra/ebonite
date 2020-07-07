import numpy as np
import pytest
from pyjackson import deserialize, serialize
from pyjackson.core import Unserializable

from ebonite.core.errors import (EboniteError, MetadataError, NonExistingModelError, NonExistingTaskError,
                                 UnboundObjectError)
from ebonite.core.objects import ModelWrapper
from ebonite.core.objects.artifacts import Blobs, InMemoryBlob
from ebonite.core.objects.core import Model, Pipeline, Project, Task, _WrapperMethodAccessor
from ebonite.core.objects.dataset_source import DatasetSource
from ebonite.core.objects.metric import Metric
from ebonite.core.objects.requirements import InstallableRequirement, Requirement, Requirements
from ebonite.ext.sklearn import SklearnModelWrapper
from ebonite.repository import MetadataRepository
from ebonite.repository.artifact.inmemory import InMemoryArtifactRepository
from tests.core.objects.conftest import serde_and_compare


def test_project__add_task__unbind(project: Project, task_factory):
    with pytest.raises(UnboundObjectError):
        project.add_task(task_factory())


@pytest.mark.parametrize('set_project_id', [True, False])
def test_project__add_task__new(set_project_id, meta: MetadataRepository, project_saved, task_factory):
    assert len(project_saved.tasks) == 0
    task: Task = task_factory()
    if set_project_id:
        task.project = project_saved
    project_saved.add_task(task)
    assert len(project_saved.tasks) == 1
    task_id = task.id
    assert task_id is not None
    assert task == meta.get_task_by_id(task_id)
    assert task == project_saved.tasks[task_id]
    assert task == project_saved.tasks(task.name)
    assert task.project == project_saved


def test_project__add_task__wrong_project(meta: MetadataRepository, project_factory, task_factory):
    project1 = project_factory(True)
    project2 = project_factory(True)
    assert len(project1.tasks) == 0
    task: Task = task_factory()
    task.project = project2
    meta.create_task(task)
    with pytest.raises(MetadataError):
        project1.add_task(task)


def test_project__add_tasks(project_saved, task_factory, meta: MetadataRepository):
    tasks = [task_factory() for _ in range(5)]
    assert len(project_saved.tasks) == 0
    project_saved.add_tasks(tasks)
    assert len(project_saved.tasks) == 5

    for t in tasks:
        task_id = t.id
        assert task_id is not None
        assert t == meta.get_task_by_id(task_id)
        assert t == project_saved.tasks[task_id]
        assert t == project_saved.tasks(t.name)


def test_project__add_tasks__empty(project_saved):
    project_saved.add_tasks([])
    assert len(project_saved.tasks) == 0


def test_project__delete_task(project_saved, task):
    project_saved.add_task(task)
    assert task.id is not None
    assert task.project_id is not None

    project_saved.delete_task(task)
    assert len(project_saved.tasks) == 0

    assert task.id is None
    assert task.project_id is None


def test_project__delete_task__nonexistent(project_factory, task):
    task_project = project_factory(True)
    task_project.add_task(task)

    project = project_factory(True)
    with pytest.raises(NonExistingTaskError):
        project.delete_task(task)


def test_project_serde(project_saved):
    serde_and_compare(project_saved)


def test_task__project_property(project_saved_art, task):
    assert project_saved_art.has_artifact_repo
    assert project_saved_art.has_meta_repo

    project_saved_art.add_task(task)
    assert task.has_meta_repo
    assert task.has_artifact_repo

    assert task.project == project_saved_art

    assert task.project.has_meta_repo
    assert task.project.has_artifact_repo


@pytest.mark.parametrize('set_task_id', [True, False])
def test_task__add_model__new(set_task_id, meta: MetadataRepository, task_saved, model_factory):
    assert len(task_saved.models) == 0
    model: Model = model_factory()
    if set_task_id:
        model.task = task_saved
    task_saved.add_model(model)
    assert len(task_saved.models) == 1
    model_id = model.id
    assert model_id is not None
    assert model == meta.get_model_by_id(model_id)
    assert model == task_saved.models[model_id]
    assert model == task_saved.models(model.name)
    assert model.task == task_saved


def test_task__add_model__wrong_task(meta: MetadataRepository, task_factory, model_factory):
    task1 = task_factory(True)
    task2 = task_factory(True)
    assert len(task1.models) == 0
    model: Model = model_factory()
    model.task = task2
    meta.create_model(model)
    with pytest.raises(MetadataError):
        task1.add_model(model)


def test_task__add_models(task_saved, model_factory, meta: MetadataRepository):
    models = [model_factory() for _ in range(5)]
    assert len(task_saved.models) == 0
    task_saved.add_models(models)
    assert len(task_saved.models) == 5

    for m in models:
        model_id = m.id
        assert model_id is not None
        assert m == meta.get_model_by_id(model_id)
        assert m == task_saved.models[model_id]
        assert m == task_saved.models(m.name)
        assert m.task == task_saved


def test_task__add_models__empty(task_saved):
    task_saved.add_models([])
    assert len(task_saved.models) == 0


def test_task__delete_model(task_saved, model):
    task_saved.add_model(model)
    assert model.id is not None
    assert model.task_id is not None

    task_saved.delete_model(model)
    assert len(task_saved.models) == 0

    assert model.id is None
    assert model.task_id is None


def test_task__delete_model_with_artifacts(task_saved, model, artifact_repo):
    model._unpersisted_artifacts = Blobs({'data': InMemoryBlob(b'data')})
    task_saved.bind_artifact_repo(artifact_repo)
    task_saved.push_model(model)
    assert model.id is not None
    assert model.task_id is not None

    task_saved.delete_model(model)
    assert len(task_saved.models) == 0

    assert model.id is None
    assert model.task_id is None


def test_task__delete_model__nonexistent(task_factory, model):
    model_task = task_factory(True)
    model_task.add_model(model)

    task = task_factory(True)
    with pytest.raises(NonExistingModelError):
        task.delete_model(model)


def test_task__serde(task_saved):
    serde_and_compare(task_saved)


def test_task__create_and_push_model(task_saved_art, sklearn_model_obj, pandas_data):
    model_name = 'Test Model'
    task_saved_art.create_and_push_model(sklearn_model_obj, pandas_data, model_name)

    assert task_saved_art._meta.get_model_by_name(model_name, task_saved_art) is not None
    assert task_saved_art.models(model_name) is not None


def test_task__push_model(task_saved_art, created_model):
    task_saved_art.push_model(created_model)

    assert task_saved_art._meta.get_model_by_name(created_model.name, task_saved_art) is not None
    assert created_model.id in task_saved_art.models


def test_task__add_metric(task_saved):
    from sklearn.metrics import roc_auc_score
    task_saved.add_metric('auc', roc_auc_score)
    task_saved.save()

    task = task_saved._meta.get_task_by_name(task_saved.project, task_saved.name)
    assert 'auc' in task.metrics
    assert isinstance(task.metrics['auc'], Metric)


def test_task__add_metric_exists(task_saved, metric):
    task_saved.add_metric('auc', metric)
    with pytest.raises(EboniteError):
        task_saved.add_metric('auc', metric)


def test_task__delete_metric(task_saved, metric):
    task_saved.add_metric('auc', metric)
    task_saved.save()
    task_saved.delete_metric('auc')

    task = task_saved._meta.get_task_by_name(task_saved.project, task_saved.name)
    assert 'auc' not in task.metrics


def test_task__delete_metric_non_existing(task_saved):
    with pytest.raises(EboniteError):
        task_saved.delete_metric('auc')


def test_task__add_dataset(task_saved, dataset):
    task_saved.add_dataset('data', dataset)
    assert 'data' in task_saved.datasets
    assert isinstance(task_saved.datasets['data'], DatasetSource)
    assert isinstance(task_saved.datasets['data'], Unserializable)
    task_saved.save()

    task = task_saved._meta.get_task_by_name(task_saved.project, task_saved.name)
    assert 'data' in task.datasets
    assert isinstance(task.datasets['data'], DatasetSource)
    assert not isinstance(task.datasets['data'], Unserializable)


def test_task__add_dataset_exists(task_saved, dataset):
    task_saved.add_dataset('data', dataset)
    with pytest.raises(EboniteError):
        task_saved.add_dataset('data', dataset)


def test_task__delete_dataset(task_saved, dataset):
    task_saved.add_dataset('data', dataset)
    task_saved.save()
    art_repo: InMemoryArtifactRepository = task_saved._art
    assert len(art_repo._cache) > 0

    task_saved.delete_dataset('data')

    task = task_saved._meta.get_task_by_name(task_saved.project, task_saved.name)
    assert 'data' not in task.datasets
    assert len(art_repo._cache) == 0


def test_task__delete_dataset_non_existing(task_saved):
    with pytest.raises(EboniteError):
        task_saved.delete_dataset('data')


def test_task__add_evalset(task_saved, dataset, metric):
    task_saved.add_evaluation('eval', dataset, dataset, metric)
    assert 'eval' in task_saved.evaluation_sets
    assert all(isinstance(d, DatasetSource) for d in task_saved.datasets.values())
    assert all(isinstance(m, Metric) for m in task_saved.metrics.values())
    task_saved.save()

    task = task_saved._meta.get_task_by_name(task_saved.project, task_saved.name)
    assert 'eval' in task.evaluation_sets


def test_task__add_evalset_exists(task_saved, dataset, metric):
    task_saved.add_evaluation('data', dataset, dataset, metric)
    with pytest.raises(EboniteError):
        task_saved.add_evaluation('data', dataset, dataset, metric)


def test_task__delete_evalset(task_saved, dataset, metric):
    task_saved.add_evaluation('data', dataset, dataset, metric)
    task_saved.save()

    task_saved.delete_evaluation('data')

    task = task_saved._meta.get_task_by_name(task_saved.project, task_saved.name)
    assert 'data' not in task.evaluation_sets


def test_task__delete_evalset_non_existing(task_saved):
    with pytest.raises(EboniteError):
        task_saved.delete_evaluation('data')


def test_task__delete_metric_with_evalset(task_saved, dataset, metric):
    task_saved.add_metric('metric', metric)
    task_saved.add_dataset('data', dataset)
    task_saved.add_evaluation('eval', 'data', 'data', 'metric')

    with pytest.raises(EboniteError):
        task_saved.delete_metric('metric')

    task_saved.delete_metric('metric', force=True)
    assert 'metric' not in task_saved.metrics
    assert 'eval' not in task_saved.evaluation_sets


def test_task__delete_dataset_with_evalset(task_saved, dataset, metric):
    task_saved.add_metric('metric', metric)
    task_saved.add_dataset('data', dataset)
    task_saved.add_evaluation('eval', 'data', 'data', 'metric')

    with pytest.raises(EboniteError):
        task_saved.delete_dataset('data')

    task_saved.delete_dataset('data', force=True)
    assert 'data' not in task_saved.datasets
    assert 'eval' not in task_saved.evaluation_sets


# ###############MODEL##################
def test_create_model(sklearn_model_obj, pandas_data):
    model = Model.create(sklearn_model_obj, pandas_data)
    assert model is not None
    assert isinstance(model.wrapper, SklearnModelWrapper)
    input_meta, output_meta = model.wrapper.method_signature('predict')
    assert input_meta.columns == list(pandas_data)
    assert output_meta.real_type == np.ndarray
    assert {'numpy', 'sklearn', 'pandas'}.issubset(model.requirements.modules)


def test_model__task_property(task_saved_art, created_model):
    assert task_saved_art.has_artifact_repo
    assert task_saved_art.has_meta_repo

    task_saved_art.add_model(created_model)
    assert created_model.has_meta_repo
    assert created_model.has_artifact_repo

    assert created_model.task == task_saved_art

    assert created_model.task.has_meta_repo
    assert created_model.task.has_artifact_repo


def test_create_model_with_custom_wrapper(sklearn_model_obj, pandas_data):
    wrapper = SklearnModelWrapper().bind_model(sklearn_model_obj, input_data=pandas_data)
    model = Model.create(sklearn_model_obj, pandas_data, custom_wrapper=wrapper)
    assert model is not None
    assert model.wrapper is wrapper
    input_meta, output_meta = model.wrapper.method_signature('predict')
    assert input_meta.columns == list(pandas_data)
    assert output_meta.real_type == np.ndarray
    assert {'numpy', 'sklearn', 'pandas'}.issubset(model.requirements.modules)


def test_create_model_with_custom_requirements(sklearn_model_obj, pandas_data):
    requirements = Requirements([InstallableRequirement('dumb', '0.4.1'), InstallableRequirement('art', '4.0')])
    model = Model.create(sklearn_model_obj, pandas_data, custom_requirements=Requirements([Requirement()]))
    assert model is not None
    assert all(req in [r.module for r in requirements.installable] for req in model.requirements.installable)


def test_create_model_with_additional_artifact(artifact, sklearn_model_obj, pandas_data, artifact_repository):
    model = Model.create(sklearn_model_obj, pandas_data, additional_artifacts=artifact)
    assert model is not None
    model._id = 'test_model'
    artifact_repository.push_model_artifacts(model)
    assert len(model.artifact_req_persisted.bytes_dict()) == 4

    model_payloads = model.artifact_req_persisted.bytes_dict()
    for name, payload in artifact.bytes_dict().items():
        assert name in model_payloads
        assert model_payloads[name] == payload


def test_model_serde(model):
    serde_and_compare(model, Model)
    assert isinstance(model.wrapper, ModelWrapper)


def test_model_with_wrapper_meta_serde(model):
    model._wrapper = None
    model._wrapper_meta = {'a': 'b'}
    model.wrapper_obj = model._wrapper_meta

    serde_and_compare(model, Model)


def test_model__as_pipeline(created_model):
    wrapper = created_model.wrapper
    method = wrapper.resolve_method('predict')
    _, input_data, output_data = wrapper.methods[method]
    pipeline = created_model.as_pipeline(method)
    assert isinstance(pipeline, Pipeline)
    assert pipeline.input_data == input_data
    assert pipeline.output_data == output_data
    assert len(pipeline.steps) == 1

    step = pipeline.steps[0]
    assert step.model_name == created_model.name
    assert step.method_name == method


def test_model__method_accessor(created_model):
    with pytest.raises(AttributeError):
        created_model.non_existing_method

    method = created_model.predict
    assert isinstance(method, _WrapperMethodAccessor)
    assert method.model == created_model
    assert method.method_name == 'predict'


# ################PIPELINES###########

@pytest.fixture
def double_model():
    def f1(a):
        return a + a

    model = Model.create(f1, 'a', '1')
    model._id = 1
    return model


@pytest.fixture
def len_model():
    def f2(a):
        return len(a)

    model = Model.create(f2, 'a', '2')
    model._id = 2
    return model


def test_pipeline__append(double_model, len_model):
    p1 = double_model.as_pipeline()
    p2 = p1.append(len_model)
    assert isinstance(p2, Pipeline)
    assert p1 == p2

    method = double_model.wrapper.resolve_method()
    assert p2.input_data == double_model.wrapper.methods[method][1]
    assert p2.output_data == len_model.wrapper.methods[method][2]
    assert len(p2.steps) == 2
    step1, step2 = p2.steps
    assert step1.model_name == double_model.name
    assert step1.method_name == method
    assert step2.model_name == len_model.name
    assert step2.method_name == method


def test_pipeline__load(meta, model, task_saved_art):
    task_saved_art.push_model(model)

    p = model.as_pipeline('predict')
    task_saved_art.add_pipeline(p)

    p = deserialize(serialize(meta.get_pipeline_by_id(p.id)), Pipeline)
    assert p is not None
    assert len(p.models) == 0
    p.bind_meta_repo(meta)
    p.load()
    assert len(p.models) == 1
    assert model.name in p.models
    assert p.models[model.name] == model


def test_pipeline__run(created_model, pandas_data):
    p = created_model.as_pipeline('predict')
    result = p.run(pandas_data)
    assert len(result) == len(pandas_data)


def test_task__no_pipelines(task_factory):
    task = task_factory(True)

    assert len(task.pipelines) == 0


def test_task__add_pipelines(task_factory, pipeline_factory):
    task = task_factory(True)
    pipeline1 = pipeline_factory()
    pipeline2 = pipeline_factory()

    assert len(task.pipelines) == 0
    assert pipeline1.task_id is None
    assert pipeline1.id is None
    assert pipeline2.task_id is None
    assert pipeline2.id is None

    task.add_pipelines([pipeline1, pipeline2])

    assert len(task.pipelines) == 2
    assert task.pipelines[pipeline1.id] is pipeline1
    assert pipeline1.task_id is not None
    assert pipeline1.task == task
    assert pipeline1.id is not None
    assert task.pipelines[pipeline2.id] is pipeline2
    assert pipeline2.task_id is not None
    assert pipeline2.task == task
    assert pipeline2.id is not None


def test_task__add_pipeline__wrong_task(task_factory, pipeline_factory):
    task = task_factory(True)
    pipeline = pipeline_factory(True)

    with pytest.raises(MetadataError):
        task.add_pipeline(pipeline)


def test_task__delete_pipeline(task_factory, pipeline_factory):
    task = task_factory(True)
    pipeline = pipeline_factory()

    assert len(task.pipelines) == 0
    assert pipeline.task_id is None
    assert pipeline.id is None

    task.add_pipeline(pipeline)

    assert len(task.pipelines) == 1
    assert pipeline.task_id is not None
    assert pipeline.id is not None

    task.delete_pipeline(pipeline)

    assert len(task.pipelines) == 0
    assert pipeline.task_id is None
    assert pipeline.id is None


# ################IMAGES###########
def test_task__no_images(task_factory):
    task = task_factory(True)

    assert len(task.images) == 0


def test_task__add_images(task_factory, image_factory):
    task = task_factory(True)
    image1 = image_factory()
    image2 = image_factory()

    assert len(task.images) == 0
    assert image1.task_id is None
    assert image1.id is None
    assert image2.task_id is None
    assert image2.id is None

    task.add_images([image1, image2])

    assert len(task.images) == 2
    assert task.images[image1.id] is image1
    assert image1.task_id is not None
    assert image1.task == task
    assert image1.id is not None
    assert task.images[image2.id] is image2
    assert image2.task_id is not None
    assert image2.task == task
    assert image2.id is not None


def test_task__add_image__wrong_task(task_factory, image_factory):
    task = task_factory(True)
    image = image_factory(True)

    with pytest.raises(MetadataError):
        task.add_image(image)


def test_task__delete_image(task_factory, image_factory):
    task = task_factory(True)
    image = image_factory()

    assert len(task.images) == 0
    assert image.task_id is None
    assert image.id is None

    task.add_image(image)

    assert len(task.images) == 1
    assert image.task_id is not None
    assert image.id is not None

    task.delete_image(image, meta_only=True)

    assert len(task.images) == 0
    assert image.task_id is None
    assert image.id is None


# ################BASE#####################
def test_base_author(sklearn_model_obj, pandas_data, username):
    model = Model.create(sklearn_model_obj, pandas_data)
    assert model is not None
    assert model.author == username
