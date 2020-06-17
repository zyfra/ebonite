import contextlib
import time

import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from ebonite import Ebonite
from ebonite.build import BuilderBase, RunnerBase
from ebonite.core.objects.core import Image, Model, RuntimeEnvironment, RuntimeInstance
from tests.client.test_func import func
from tests.conftest import MockMixin, has_docker, interface_hook_creator
from tests.core.objects.conftest import BuildableMock

CONTAINER_NAME = "ebonite-test-service"

CLEAR = True  # flag to disable removal of containers for easy inspection and debugging


class MockBuilder(BuilderBase, MockMixin):
    pass


class MockRunner(RunnerBase, MockMixin):
    pass


class _MockEnvironmentParams(RuntimeEnvironment.Params):
    def get_runner(self):
        return self.runner

    def get_builder(self):
        return self.builder

    @classmethod
    @contextlib.contextmanager
    def reset(cls):
        cls.builder = MockBuilder()
        cls.runner = MockRunner()
        yield


@pytest.fixture
def mock_env_params():
    with _MockEnvironmentParams.reset():
        yield _MockEnvironmentParams()


@pytest.fixture
def mock_env(mock_env_params):
    return RuntimeEnvironment('mock', params=mock_env_params)


@pytest.fixture
@pytest.mark.skipif(not has_docker(), reason='no docker installed')
def container_name():
    name = "{}-{}".format(CONTAINER_NAME, int(time.time() * 1000))
    yield name

    if not CLEAR:
        return

    from ebonite.ext.docker import DockerRunner, DockerBuilder, DockerContainer, DockerImage, DockerEnv
    DockerRunner().remove_instance(DockerContainer(name), DockerEnv(), force=True)
    DockerBuilder().delete_image(DockerImage(name), DockerEnv())


@pytest.fixture  # FIXME did not find the way to import fixture from build module
def model():
    model = Model.create(func, "kek", "Test Model")
    return model


@pytest.fixture
def image_to_delete(ebnt: Ebonite, model, mock_env):
    task = ebnt.get_or_create_task('Project', 'Task')
    ebnt.meta_repo.create_environment(mock_env)
    image = Image('image', BuildableMock(), id=None, task_id=task.id, params=Image.Params())
    image.environment = mock_env
    image.params.name = 'image'
    image.bind_builder(mock_env.params.get_builder())
    image = ebnt.meta_repo.create_image(image)
    yield image


@pytest.fixture
def regression_and_data():
    reg = LinearRegression()
    data = pd.DataFrame([[1, 1], [2, 1]], columns=['a', 'b'])
    reg.fit(data, [1, 0])
    return reg, data


@pytest.fixture
def image():
    return Image('Test Image', BuildableMock())


@pytest.fixture
def pipeline(model):
    return model.as_pipeline()


@pytest.fixture
def instance():
    return RuntimeInstance('Test Instance')


create_client_hooks = interface_hook_creator('tests/client/', 'client_common.py', 'ebnt')
