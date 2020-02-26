import datetime
from copy import deepcopy

import pytest

from ebonite.core.objects.core import Image, Model, Project, RuntimeEnvironment, RuntimeInstance, Task
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
    task.project_id = project
    return task


@pytest.fixture
def task():
    return Task("Test Task")


@pytest.fixture
def task2():
    return Task("Test Task2")


@pytest.fixture
def model(mock_model_wrapper):
    return Model("Test Model", mock_model_wrapper, description='')


@pytest.fixture
def model2(mock_model_wrapper):
    return Model("Test Model2", mock_model_wrapper, description='')


@pytest.fixture
def created_model(meta, project, task, model):
    project = meta.create_project(project)
    task.project = project
    task = meta.create_task(task)
    model.task = task
    return meta.create_model(model)


@pytest.fixture
def image():
    return Image("Test Image", params={'test': 123})


@pytest.fixture
def created_image(meta, created_model, image):
    image = deepcopy(image)
    image.model = created_model
    return meta.create_image(image)


@pytest.fixture
def environment():
    return RuntimeEnvironment("Test Environment", host='168.132.157.0', port=8558)


@pytest.fixture
def created_environment(meta, environment):
    environment = deepcopy(environment)
    return meta.create_environment(environment)


@pytest.fixture
def instance():
    return RuntimeInstance("Test Instance", params={'test': 123})


@pytest.fixture
def created_instance(meta, created_image, created_environment, instance):
    instance = deepcopy(instance)
    instance.image = created_image
    instance.environment = created_environment
    return meta.create_instance(instance)


create_metadata_hooks = interface_hook_creator('tests/repository/metadata/', 'meta_common.py', 'meta')
