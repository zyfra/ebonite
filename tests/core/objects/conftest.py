import os

import pyjackson
import pytest
from pyjackson.generics import Serializer

from ebonite.core.analyzer.metric import MetricAnalyzer
from ebonite.core.objects.core import Buildable, Image, Model, Pipeline, Project, Task
from ebonite.core.objects.dataset_source import Dataset
from ebonite.repository import DatasetRepository, MetadataRepository
from ebonite.repository.artifact.inmemory import InMemoryArtifactRepository
from ebonite.repository.dataset.artifact import ArtifactDatasetRepository
from ebonite.repository.metadata.local import LocalMetadataRepository
from tests.conftest import DummyModelWrapper


@pytest.fixture
def meta():
    return LocalMetadataRepository()


@pytest.fixture
def artifact_repo():
    return InMemoryArtifactRepository()


@pytest.fixture
def dataset_repo(artifact_repo):
    return ArtifactDatasetRepository(artifact_repo)


@pytest.fixture
def project_factory(meta: MetadataRepository, artifact_repo: InMemoryArtifactRepository):
    counter = 0

    def factory(saved=False):
        nonlocal counter
        counter += 1
        project = Project('Test Project-{}'.format(counter))
        if saved:
            p = meta.create_project(project)
            p.bind_artifact_repo(artifact_repo)
            return p
        return project

    return factory


@pytest.fixture
def task_factory(project_factory, dataset_repo: DatasetRepository):
    counter = 0

    def factory(saved=False):
        nonlocal counter
        counter += 1
        task = Task('Test Task-{}'.format(counter))
        if saved:
            project = project_factory(True)
            project.add_task(task)
            task.bind_dataset_repo(dataset_repo)
        return task

    return factory


@pytest.fixture
def model_factory(task_factory):
    counter = 0

    def factory(saved=False):
        nonlocal counter
        counter += 1
        model = Model('Test Model-{}'.format(counter), DummyModelWrapper())
        if saved:
            task = task_factory(True)
            task.add_model(model)
        return model

    return factory


@pytest.fixture
def pipeline_factory(task_factory):
    counter = 0

    def factory(saved=False):
        nonlocal counter
        counter += 1
        pipeline = Pipeline('Test Pipeline-{}'.format(counter), [], None, None)
        if saved:
            task = task_factory(True)
            task.add_pipeline(pipeline)
        return pipeline

    return factory


class BuildableMock(Buildable):
    def get_provider(self):
        pass


@pytest.fixture
def image_factory(task_factory):
    counter = 0

    def factory(saved=False):
        nonlocal counter
        counter += 1
        image = Image('Test Image-{}'.format(counter), params={'test': counter}, source=BuildableMock())
        if saved:
            task = task_factory(True)
            task.add_image(image)
        return image

    return factory


@pytest.fixture
def task_saved(task_factory):
    return task_factory(True)


@pytest.fixture
def task_saved_art(task_saved):
    task_saved.bind_artifact_repo(InMemoryArtifactRepository())
    return task_saved


@pytest.fixture
def task(task_factory):
    return task_factory()


@pytest.fixture
def project_saved(project_factory):
    return project_factory(True)


@pytest.fixture
def project_saved_art(project_saved):
    return project_saved.bind_artifact_repo(InMemoryArtifactRepository())


@pytest.fixture
def project(project_factory):
    return project_factory()


@pytest.fixture
def model(sklearn_model_obj, pandas_data):
    return Model.create(sklearn_model_obj, pandas_data)


@pytest.fixture
def metric():
    from sklearn.metrics import roc_auc_score
    return MetricAnalyzer.analyze(roc_auc_score)


@pytest.fixture
def dataset(pandas_data):
    return Dataset.from_object(pandas_data)


@pytest.fixture
def pipeline(pipeline_factory):
    return pipeline_factory()


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
