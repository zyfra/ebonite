import contextlib
import os
from itertools import chain

import pandas as pd
import pytest
from _pytest.doctest import DoctestModule
from _pytest.python import Module
from sklearn.linear_model import LinearRegression

from ebonite.core.objects.artifacts import Blobs, InMemoryBlob
from ebonite.core.objects.core import Model
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.core.objects.wrapper import FilesContextManager, ModelWrapper
from ebonite.repository.artifact.local import LocalArtifactRepository


class MockModelWrapper(ModelWrapper):
    type = 'mock_wrapper'

    @contextlib.contextmanager
    def dump(self) -> FilesContextManager:
        yield Blobs({'test.bin': InMemoryBlob(b'test')})

    def load(self, path):
        pass

    def predict(self, data):
        return data


@pytest.fixture
def mock_model_wrapper():
    return MockModelWrapper()


@pytest.fixture
def artifact_repository(tmpdir):
    return LocalArtifactRepository(tmpdir)


@pytest.fixture
def sklearn_model_obj(pandas_data):
    reg = LinearRegression()
    reg.fit(pandas_data, [1, 0])
    return reg


@pytest.fixture
def pandas_data():
    return pd.DataFrame([[1, 1], [2, 1]], columns=['a', 'b'])


@pytest.fixture
def created_model(sklearn_model_obj, pandas_data):
    return Model.create(sklearn_model_obj, pandas_data)


@pytest.fixture
def artifact():
    return Blobs({'kek': InMemoryBlob(b'kek')})


class DatasetTypeMock(DatasetType):
    type = 'mock_dataset_type'

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
