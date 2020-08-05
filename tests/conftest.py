import contextlib
import os
import traceback
from itertools import chain
from typing import Any, Callable, Dict, Optional, Type
from unittest.mock import MagicMock, _CallList

import pandas as pd
import pytest
from _pytest.doctest import DoctestModule
from _pytest.python import Module
from sklearn.linear_model import LogisticRegression

from ebonite.core.objects.artifacts import Blobs, InMemoryBlob
from ebonite.core.objects.core import Model
from ebonite.core.objects.dataset_source import Dataset
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.core.objects.wrapper import FilesContextManager, ModelIO, ModelWrapper
from ebonite.ext.docker.utils import is_docker_running
from ebonite.repository.artifact.local import LocalArtifactRepository
from ebonite.repository.dataset.artifact import DatasetReader, DatasetWriter


class _CallList2(_CallList):
    def append(self, object) -> None:
        super(_CallList2, self).append(object)


class MoreMagicMock(MagicMock):
    # __fields = {'mock_call_stacks'}

    def __init__(self, *args, **kwargs):
        super(MoreMagicMock, self).__init__(*args, **kwargs)
        self.mock_call_stacks = []

    # def __setattr__(self, key, value):
    #     if key in self.__fields:
    #         object.__setattr__(self, key, value)
    #     else:
    #         super(MoreMagicMock, self).__setattr__(key, value)
    #
    # def __getattr__(self, item):
    #     if item in self.__fields:
    #         return self.__dict__[item]
    #     return super(MoreMagicMock, self).__getattr__(item)

    def _mock_call(self, *args, **kwargs):
        self.mock_call_stacks.append(traceback.extract_stack()[:-3])
        return super(MoreMagicMock, self)._mock_call(*args, **kwargs)

    @contextlib.contextmanager
    def called_within_context(self, first=True, times=1):
        if first:
            self.assert_not_called()
        times_called = self.call_count
        yield

        if first and times > 0:
            self.assert_called()

        if self.call_count != times_called + times:

            frames_summary = []
            for frame in self.mock_call_stacks[times_called:]:
                summary = '\n'.join(f'{f.filename}:{f.lineno}' for f in frame if 'site-packages' not in f.filename)
                frames_summary.append(summary)
            frames_summary = '\n\n'.join(frames_summary)
            raise AssertionError(f"Expected '{self._mock_name}' to have been called {times} times "
                                 f"(got {self.call_count - times_called})\n"
                                 f"Mock calls: \n{frames_summary}")


class MockMethod:
    def __init__(self, method, proxy_mode=True):
        self.proxy_mode = proxy_mode
        self.method = method

    @property
    def __name(self):
        return f'_{self.method.__name__}_mock'

    def _side_effect(self, instance):
        return lambda *args, **kwargs: self.method(instance, *args, **kwargs)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        self._ensure_mock(instance)
        return getattr(instance, self.__name)

    def _ensure_mock(self, instance):
        if self.__name not in instance.__dict__:
            setattr(instance, self.__name,
                    MoreMagicMock(side_effect=self._side_effect(instance) if self.proxy_mode else None,
                                  name=self.method.__name__))


def mock_method(method):
    return MockMethod(method)


class MockMixin:
    def __init_subclass__(cls, proxy_mode=True):
        super().__init_subclass__()
        cls.__original = dict()
        for base in cls.mro():
            for name, item in base.__dict__.items():
                if name.startswith('_') or name in cls.__original or not callable(item):
                    continue
                cls.__original[name] = item
                setattr(cls, name, MockMethod(getattr(cls, name), proxy_mode))


class DummyModelIO(ModelIO):
    @contextlib.contextmanager
    def dump(self, model) -> FilesContextManager:
        yield Blobs({'test.bin': InMemoryBlob(b'test')})

    def load(self, path):
        return None


class DummyModelWrapper(ModelWrapper):
    def __init__(self):
        super().__init__(DummyModelIO())

    def _exposed_methods_mapping(self) -> Dict[str, Optional[str]]:
        return {
            'predict': '_predict'
        }

    def _predict(self, data):
        return data


@pytest.fixture
def dummy_model_wrapper():
    return DummyModelWrapper()


@pytest.fixture
def artifact_repository(tmpdir):
    return LocalArtifactRepository(tmpdir)


@pytest.fixture
def sklearn_model_obj(pandas_data):
    reg = LogisticRegression()
    reg.fit(pandas_data, [1, 0])
    return reg


@pytest.fixture
def pandas_data():
    return pd.DataFrame([[1, 0], [0, 1]], columns=['a', 'b'])


@pytest.fixture
def created_model(sklearn_model_obj, pandas_data):
    return Model.create(sklearn_model_obj, pandas_data)


@pytest.fixture
def artifact():
    return Blobs({'kek': InMemoryBlob(b'kek')})


class DatasetTypeDummy(DatasetType):
    def __init__(self, name: str):
        self.name = name


def interface_hook_creator(package_path, common_filename, fixture_name):
    def create_interface_hooks(meta_fixture, name):
        tests_node_id = os.path.join(package_path, '{}.py'.format(name))

        def pytest_runtest_protocol(item, nextitem):
            filename, *test_name = item.nodeid.split('::')

            if filename == tests_node_id and fixture_name in item.fixturenames:
                fixture = _remap_fixture(item, meta_fixture.__name__, fixture_name)

                for dep_fixt_name in chain.from_iterable(e.argnames for e in fixture):
                    _remap_fixture(item, dep_fixt_name, dep_fixt_name)

        def _remap_fixture(item, actual_name, expected_name):
            fixture = tuple(item.session._fixturemanager._arg2fixturedefs[actual_name])
            item._request._arg2fixturedefs[expected_name] = fixture
            return fixture

        @pytest.hookimpl(hookwrapper=True)
        def pytest_collect_file(path, parent):
            outcome = yield
            result = outcome.get_result()

            if parent.parent is None:
                result.append(
                    DoctestModule(os.path.join(parent.fspath, package_path, 'conftest.py'), parent,
                                  nodeid=os.path.join(package_path, '{}_conf.py'.format(name))))

                result.append(Module(os.path.join(parent.fspath, package_path, common_filename), parent,
                                     nodeid=tests_node_id))

        return pytest_runtest_protocol, pytest_collect_file

    return create_interface_hooks


def has_docker():
    if os.environ.get('SKIP_DOCKER_TESTS', None) == 'true':
        return False
    return is_docker_running()


def docker_test(f):
    mark = pytest.mark.docker
    skip = pytest.mark.skipif(not has_docker(), reason='docker is unavailable or skipped')
    return mark(skip(f))


def dataset_write_read_check(dataset: Dataset, writer: DatasetWriter = None, reader_type: Type[DatasetReader] = None,
                             custom_eq: Callable[[Any, Any], bool] = None,
                             custom_assert: Callable[[Any, Any], Any] = None):
    writer = writer or dataset.get_writer()

    reader, artifacts = writer.write(dataset)
    if reader_type is not None:
        assert isinstance(reader, reader_type)

    new = reader.read(artifacts)

    assert dataset.dataset_type == new.dataset_type
    if custom_assert is not None:
        custom_assert(new.data, dataset.data)
    else:
        if custom_eq is not None:
            assert custom_eq(new.data, dataset.data)
        else:
            assert new.data == dataset.data
