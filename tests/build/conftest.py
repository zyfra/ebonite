import os

import docker.errors
import pandas as pd
import pytest
from ebonite.build.docker import create_docker_client, is_docker_running
from ebonite.core.objects.core import Model
from sklearn.linear_model import LinearRegression

from tests.client.test_func import func


def has_docker():
    if os.environ.get('SKIP_DOCKER_TESTS', None) == 'true':
        return False
    return is_docker_running()


def has_local_image(img_name: str) -> bool:
    if not has_docker():
        return False
    with create_docker_client() as client:
        try:
            client.images.get(img_name)
        except docker.errors.ImageNotFound:
            return False
    return True


def rm_container(container_name: str, host: str = ''):
    with create_docker_client(host) as client:
        containers = client.containers.list()
        if any(container_name == c.name for c in containers):
            client.containers.get(container_name).remove(force=True)


def rm_image(image_tag: str, host: str = ''):
    with create_docker_client(host) as client:
        tags = [t for i in client.images.list() for t in i.tags]
        if any(image_tag == t for t in tags):
            client.images.remove(image_tag, force=True)


def train_model():
    reg = LinearRegression()
    data = pd.DataFrame([[1, 1], [2, 1]], columns=['a', 'b'])
    reg.fit(data, [1, 0])
    return reg, data


def create_test_model(name):
    model = Model.create(func, "kek", name)
    return model


@pytest.fixture
def model():
    model = Model.create(func, "kek", "Test Model")
    return model
