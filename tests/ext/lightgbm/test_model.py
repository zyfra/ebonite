import lightgbm as lgb
import numpy as np
import pytest

from ebonite.core.analyzer.model import ModelAnalyzer
from ebonite.core.objects import ModelWrapper
from ebonite.ext.lightgbm.model import LightGBMModelWrapper


@pytest.fixture
def booster(dataset_np):
    return lgb.train({}, dataset_np, 1)


@pytest.fixture
def wrapper(booster) -> ModelWrapper:
    return ModelAnalyzer.analyze(booster)


def test_hook(wrapper, booster):
    assert isinstance(wrapper, LightGBMModelWrapper)
    assert wrapper.model == booster


def test_wrapper__predict(wrapper, dataset_np):
    predict = wrapper.predict(dataset_np)
    assert isinstance(predict, np.ndarray)
    assert len(predict) == dataset_np.num_data()


def test_wrapper__predict_not_dataset(wrapper):
    data = [[1]]
    predict = wrapper.predict(data)
    assert isinstance(predict, np.ndarray)
    assert len(predict) == len(data)


def test_wrapper__dump_load(tmpdir, wrapper: ModelWrapper, dataset_np):
    with wrapper.dump() as d:
        d.materialize(tmpdir)
    wrapper.unbind()
    with pytest.raises(ValueError):
        wrapper.predict(dataset_np)

    wrapper.load(tmpdir)
    test_wrapper__predict(wrapper, dataset_np)
