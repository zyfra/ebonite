import numpy as np
import pytest
import xgboost

from ebonite.core.analyzer.model import ModelAnalyzer
from ebonite.core.objects import ModelWrapper
from ebonite.ext.xgboost.model import XGBoostModelWrapper


@pytest.fixture
def booster(dmatrix_np):
    return xgboost.train({}, dmatrix_np, 1)


@pytest.fixture
def wrapper(booster) -> ModelWrapper:
    return ModelAnalyzer.analyze(booster)


def test_hook(booster):
    wrapper = ModelAnalyzer.analyze(booster)
    assert isinstance(wrapper, XGBoostModelWrapper)
    assert wrapper.model == booster


def test_wrapper__predict(wrapper, dmatrix_np):
    predict = wrapper.predict(dmatrix_np)
    assert isinstance(predict, np.ndarray)
    assert len(predict) == dmatrix_np.num_row()


def test_wrapper__predict_not_dmatrix(wrapper):
    data = [1]
    predict = wrapper.predict(data)
    assert isinstance(predict, np.ndarray)
    assert len(predict) == len(data)


def test_wrapper__dump_load(tmpdir, wrapper: ModelWrapper, dmatrix_np):
    with wrapper.dump() as d:
        d.materialize(tmpdir)
    wrapper.unbind()
    with pytest.raises(ValueError):
        wrapper.predict(dmatrix_np)

    wrapper.load(tmpdir)
    test_wrapper__predict(wrapper, dmatrix_np)
