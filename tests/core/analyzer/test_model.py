import contextlib
import os

import numpy as np
import pytest

from ebonite.core.analyzer.model import ModelAnalyzer, ModelHook
from ebonite.core.objects.artifacts import ArtifactCollection, Blobs, InMemoryBlob
from ebonite.core.objects.wrapper import ModelWrapper


class _SummerModel:
    def __init__(self, b):
        self.b = b

    def predict(self, data):
        return np.sum(data) + self.b


class _SummerModelWrapper(ModelWrapper):
    type = 'summer'
    model_filename = 'model.smr'

    @ModelWrapper.with_model
    def predict(self, data):
        return self.model.predict(data)

    @ModelWrapper.with_model
    @contextlib.contextmanager
    def dump(self) -> ArtifactCollection:
        content = str(self.model.b).encode('utf-8')
        yield Blobs({self.model_filename: InMemoryBlob(content)})

    def load(self, path):
        with open(os.path.join(path, self.model_filename), 'rb') as f:
            self.model = _SummerModel(int(f.read()))


class _SummerModelHook(ModelHook):
    def process(self, obj) -> ModelWrapper:
        return _SummerModelWrapper().bind_model(obj)

    def can_process(self, obj) -> bool:
        return isinstance(obj, _SummerModel)

    def must_process(self, obj) -> bool:
        return False


def _wrap_model(model):
    def _predict(data):
        return model.predict(data)
    return _predict


@pytest.fixture
def numpy_data():
    return np.asarray([1., -1., 0., -1., 0])


@pytest.fixture
def summer_model():
    return _SummerModel(7)


@pytest.fixture
def wrapper(summer_model):
    model_obj = _wrap_model(summer_model)
    return ModelAnalyzer.analyze(model_obj)


def test_func_model_dump_load(tmpdir, wrapper: ModelWrapper, numpy_data):
    before_model = wrapper.model
    with wrapper.dump() as artifact:
        artifact.materialize(tmpdir)
    wrapper.load(tmpdir)
    after_model = wrapper.model

    # we could not compare models directly as they are functions
    np.testing.assert_almost_equal(before_model(numpy_data), after_model(numpy_data))
