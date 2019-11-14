import datetime

import pytest

from ebonite.core.objects.core import Model, Project, Task
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
    return Model("Test Model", mock_model_wrapper)


@pytest.fixture
def model2(mock_model_wrapper):
    return Model("Test Model2", mock_model_wrapper)


create_metadata_hooks = interface_hook_creator('tests/repository/metadata/', 'meta_common.py', 'meta')
