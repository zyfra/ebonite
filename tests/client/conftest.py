import time

import pytest
from pyjackson.core import Comparable

from ebonite.core.objects.core import Image, Model
from tests.build.builder.test_docker import has_docker
from tests.build.conftest import rm_container, rm_image
from tests.client.test_func import func
from tests.conftest import interface_hook_creator

CONTAINER_NAME = "ebonite-test-service"

CLEAR = True  # flag to disable removal of containers for easy inspection and debugging


class MockEnvironmentParams(Comparable):
    default_runner = None

    def get_runner(self):
        # TODO: Runner
        return self.default_runner

    def get_builder(self, name: str, model: Model, server, debug=False, **kwargs):
        # TODO: Builder
        return

    def remove_image(self, image: Image):
        if image.params.name:
            return True
        else:
            return False


@pytest.fixture
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def container_name():
    name = "{}-{}".format(CONTAINER_NAME, int(time.time() * 1000))
    yield name

    if not CLEAR:
        return

    rm_container(name)
    rm_image(name + ":latest")  # FIXME later


@pytest.fixture  # FIXME did not find the way to import fixture from build module
def model():
    model = Model.create(func, "kek", "Test Model")
    return model


@pytest.fixture
def image_to_delete(ebnt, model):
    task = ebnt.get_or_create_task('Project', 'Task')
    model = ebnt.push_model(model, task)
    image = Image('image', id=None, model_id=model.id, params=Image.Params())
    image.params.name = 'image'
    image = ebnt.meta_repo.create_image(image)
    yield image


create_client_hooks = interface_hook_creator('tests/client/', 'client_common.py', 'ebnt')
