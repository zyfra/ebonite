import contextlib
import os
from typing import Dict, Optional

import numpy as np
import pytest

from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.model import BindingModelHook, ModelAnalyzer
from ebonite.core.objects.artifacts import ArtifactCollection, Blobs, InMemoryBlob
from ebonite.core.objects.wrapper import ModelIO, ModelWrapper


class _SummerModel:
    def __init__(self, b):
        # module objects can not be pickled, thus `ModelAnalyzer` is required to use
        # a combination of `pickle` and `_SummerModelIO` to deal with this model
        self.pickle_failure = pytest
        self.b = b

    def predict(self, data):
        return np.sum(data) + self.b


class _SummerModelIO(ModelIO):
    model_filename = 'model.smr'

    @contextlib.contextmanager
    def dump(self, model) -> ArtifactCollection:
        content = str(model.b).encode('utf-8')
        yield Blobs({self.model_filename: InMemoryBlob(content)})

    def load(self, path):
        with open(os.path.join(path, self.model_filename), 'rb') as f:
            return _SummerModel(int(f.read()))


class _SummerModelWrapper(ModelWrapper):
    type = 'summer'

    def __init__(self):
        super().__init__(_SummerModelIO())

    def _exposed_methods_mapping(self) -> Dict[str, Optional[str]]:
        return {
            'predict': 'predict'
        }


class _SummerModelHook(BindingModelHook, TypeHookMixin):
    valid_types = [_SummerModel]

    def _wrapper_factory(self) -> ModelWrapper:
        return _SummerModelWrapper()


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
def wrapper(summer_model, numpy_data):
    model_obj = _wrap_model(summer_model)
    return ModelAnalyzer.analyze(model_obj, input_data=numpy_data)


def test_func_model_dump_load(tmpdir, wrapper: ModelWrapper, numpy_data):
    before_model = wrapper.model
    with wrapper.dump() as artifact:
        artifact.materialize(tmpdir)
    wrapper.load(tmpdir)
    after_model = wrapper.model

    # we could not compare models directly as they are functions
    np.testing.assert_almost_equal(before_model(numpy_data), after_model(numpy_data))
