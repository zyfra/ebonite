import datetime
from copy import deepcopy

import pytest

from ebonite.core.objects.core import (Buildable, Image, Model, Pipeline, PipelineStep, Project, RuntimeEnvironment,
                                       RuntimeInstance, Task)
from tests.conftest import interface_hook_creator


@pytest.fixture
def author():
    return "Test author"


@pytest.fixture
def creation_date():
    return datetime.datetime(1994, 4, 11)


@pytest.fixture
def project(author, creation_date):
    return Project("Test project", author=author, creation_date=creation_date)


@pytest.fixture
def project2():
    return Project('Test project2')


@pytest.fixture
def project_task(project):
    task = Task("Test Task")
    task.project = project
    return task


@pytest.fixture
def task():
    return Task("Test Task")


@pytest.fixture
def task2():
    return Task("Test Task2")


@pytest.fixture
def created_task(meta, project, task):
    project = meta.create_project(project)
    task.project = project
    return meta.create_task(task)


@pytest.fixture
def model(dummy_model_wrapper):
    return Model("Test Model", dummy_model_wrapper, description='')


@pytest.fixture
def model2(dummy_model_wrapper):
    return Model("Test Model2", dummy_model_wrapper, description='')


@pytest.fixture
def created_model(meta, created_task, model):
    model.task = created_task
    return meta.create_model(model)


@pytest.fixture
def pipeline():
    return Pipeline('Test Pipeline', [PipelineStep('a', 'b')], None, None)


@pytest.fixture
def pipeline2():
    return Pipeline('Test Pipeline2', [PipelineStep('b', 'c')], None, None)


class TestParams(Image.Params, RuntimeEnvironment.Params, RuntimeInstance.Params):
    def __init__(self, key: int):
        self.key = key


class TestBuildable(Buildable):
    pass


@pytest.fixture
def image():
    return Image("Meta Test Image", params=TestParams(123), source=TestBuildable())


@pytest.fixture
def created_image(meta, created_task, created_environment, image):
    image: Image = deepcopy(image)
    image.task = created_task
    image.environment = created_environment
    return meta.create_image(image)


@pytest.fixture
def environment():
    return RuntimeEnvironment("Test Environment", params=TestParams(123))


@pytest.fixture
def created_environment(meta, environment):
    environment = deepcopy(environment)
    return meta.create_environment(environment)


@pytest.fixture
def instance():
    return RuntimeInstance("Test Instance", params=TestParams(123))


@pytest.fixture
def created_instance(meta, created_image, created_environment, instance):
    instance = deepcopy(instance)
    instance.image = created_image
    instance.environment = created_environment
    return meta.create_instance(instance)


create_metadata_hooks = interface_hook_creator('tests/repository/metadata/', 'meta_common.py', 'meta')
