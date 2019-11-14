import numpy as np
import pandas as pd
import pytest
from pyjackson import deserialize

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.core import Model
from ebonite.core.objects.requirements import Requirements
from ebonite.ext.sklearn import SklearnModelWrapper
from ebonite.runtime.interface.ml_model import model_interface


class PandasModel:
    def __init__(self, prediction):
        self.prediction = prediction

    def predict(self, df: 'pd.DataFrame'):
        assert isinstance(df, pd.DataFrame)
        return self.prediction


@pytest.fixture
def data():
    return pd.DataFrame([{'a': 1, 'b': 1}])


@pytest.fixture
def prediction(data):
    return np.array([[.5 for _ in range(data.size)]])


@pytest.fixture
def model(data, prediction):
    dataset_meta = DatasetAnalyzer.analyze(data)
    output_meta = DatasetAnalyzer.analyze(prediction)
    return Model('test model', SklearnModelWrapper(), input_meta=dataset_meta,
                 output_meta=output_meta, requirements=Requirements([]))


@pytest.fixture
def pd_model(model: Model, prediction):
    model.wrapper.bind_model(PandasModel(prediction))
    return model


def test_interface_types(pd_model: Model, data, prediction):
    interface = model_interface(pd_model)
    pred = interface.predict(data)
    assert (pred == prediction).all()


def test_with_serde(pd_model: Model):
    interface = model_interface(pd_model)

    obj = {'values': [{'a': 1, 'b': 1}]}

    data_type = pd_model.input_meta
    data = deserialize(obj, data_type)

    interface.predict(data)
