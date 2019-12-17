import numpy as np
import pytest
from sklearn.linear_model import LinearRegression, LogisticRegression

from ebonite.core.analyzer.model import ModelAnalyzer
from ebonite.ext.sklearn import SklearnModelWrapper


@pytest.fixture
def inp_data():
    return [[1, 2, 3], [3, 2, 1]]


@pytest.fixture
def out_data():
    return [1, 2]


@pytest.fixture
def classifier(inp_data, out_data):
    lr = LogisticRegression()
    lr.fit(inp_data, out_data)
    return lr


@pytest.fixture
def regressor(inp_data, out_data):
    lr = LinearRegression()
    lr.fit(inp_data, out_data)
    return lr


@pytest.fixture
def wrapper(model):
    return


@pytest.mark.parametrize('model', ['classifier', 'regressor'])
def test_hook(model, request):
    model = request.getfixturevalue(model)
    wrapper = ModelAnalyzer.analyze(model)

    assert isinstance(wrapper, SklearnModelWrapper)


@pytest.mark.parametrize('model', ['classifier', 'regressor'])
def test_wrapper__predict(model, inp_data, request):
    model = request.getfixturevalue(model)
    wrapper = ModelAnalyzer.analyze(model)

    np.testing.assert_array_almost_equal(model.predict(inp_data), wrapper.predict(inp_data))


def test_wrapper__clf_predict_proba(classifier, inp_data):
    wrapper = ModelAnalyzer.analyze(classifier)

    np.testing.assert_array_almost_equal(classifier.predict_proba(inp_data), wrapper.predict_proba(inp_data))


def test_wrapper__reg_predict_proba(regressor, inp_data):
    wrapper = ModelAnalyzer.analyze(regressor)

    assert not hasattr(wrapper, 'predict_proba')


@pytest.mark.parametrize('model', ['classifier', 'regressor'])
def test_wrapper__dump_load(tmpdir, model, inp_data, request):
    model = request.getfixturevalue(model)
    wrapper = ModelAnalyzer.analyze(model)

    with wrapper.dump() as d:
        d.materialize(tmpdir)
    wrapper.unbind()
    with pytest.raises(ValueError):
        wrapper.predict(inp_data)

    wrapper.load(tmpdir)
    np.testing.assert_array_almost_equal(model.predict(inp_data), wrapper.predict(inp_data))
