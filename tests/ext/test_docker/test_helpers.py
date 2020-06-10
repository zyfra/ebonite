import pytest

from ebonite.core.analyzer.buildable import BuildableAnalyzer, BuildableHook
from ebonite.ext.docker import DockerContainer, DockerImage
from ebonite.ext.docker.helpers import build_docker_image, run_docker_instance
from tests.build.builder.test_base import BuildableMock
from tests.conftest import docker_test


@pytest.fixture
def dummy_buildable():
    class DummyBuildableHook(BuildableHook):
        def can_process(self, obj) -> bool:
            return True

        def must_process(self, obj) -> bool:
            return False

        def process(self, obj, **kwargs):
            return BuildableMock()

    yield
    BuildableAnalyzer.hooks = [h for h in BuildableAnalyzer.hooks if not isinstance(h, DummyBuildableHook)]


@pytest.fixture
def built_image(dummy_buildable):
    image = build_docker_image('test_docker_helper_image', '', tag='test_tag', repository='test_repository',
                               force_overwrite=True)
    yield image
    image.remove(force=True)
    assert not image.is_built()


@docker_test
def test_build_docker_image(built_image):
    assert isinstance(built_image.params, DockerImage)
    assert built_image.has_builder
    assert built_image.name == built_image.params.name == 'test_docker_helper_image'
    assert built_image.params.tag == 'test_tag'
    assert built_image.params.repository == 'test_repository'
    assert built_image.params.image_id is not None
    assert built_image.is_built()


@docker_test
def test_run_docker_instance(built_image):
    instance = run_docker_instance(built_image, 'test_docker_helper_container', port_mapping={9000: 9000}, detach=True,
                                   command='sleep 1000')
    assert isinstance(instance.params, DockerContainer)
    assert instance.has_runner
    assert instance.params.name == 'test_docker_helper_container'
    assert instance.params.port_mapping == {9000: 9000}
    assert instance.params.container_id is not None
    assert instance.exists()
    assert instance.is_running()

    instance.stop()
    assert not instance.is_running()
    instance.remove()
    assert not instance.exists()
