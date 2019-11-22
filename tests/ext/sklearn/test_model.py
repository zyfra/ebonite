import pytest
from sklearn.linear_model import LinearRegression

from ebonite.core.analyzer.model import ModelAnalyzer
from ebonite.ext.sklearn import SklearnModelWrapper


@pytest.fixture
def data():
    return [[1, 2, 3]]


@pytest.fixture
def model(data):
    lr = LinearRegression()
    lr.fit(data, data)
    return lr


@pytest.fixture
def wrapper(model):
    return ModelAnalyzer.analyze(model)


def test_hook(wrapper):
    assert isinstance(wrapper, SklearnModelWrapper)


def test_wrapper__predict(wrapper, data):

    prediction = wrapper.predict(data)

    assert len(prediction) == len(data)


def test_wrapper__dump_load(tmpdir, wrapper, data):
    with wrapper.dump() as d:
        d.materialize(tmpdir)
    wrapper.unbind()
    with pytest.raises(ValueError):
        wrapper.predict(data)

    wrapper.load(tmpdir)
    test_wrapper__predict(wrapper, data)
