import numpy as np
import pytest

from ebonite.core.objects import ModelWrapper
from ebonite.ext.lightgbm.model import LightGBMModelWrapper


def test_hook(wrapper, booster):
    assert isinstance(wrapper, LightGBMModelWrapper)
    assert wrapper.model == booster


def test_wrapper__predict(wrapper, dataset_np):
    predict = wrapper.call_method('predict', dataset_np)
    assert isinstance(predict, np.ndarray)
    assert len(predict) == dataset_np.num_data()


def test_wrapper__predict_not_dataset(wrapper):
    data = [[1]]
    predict = wrapper.call_method('predict', data)
    assert isinstance(predict, np.ndarray)
    assert len(predict) == len(data)


def test_wrapper__dump_load(tmpdir, wrapper: ModelWrapper, dataset_np):
    expected_requirements = {'lightgbm', 'numpy'}
    assert set(wrapper.requirements.modules) == expected_requirements

    with wrapper.dump() as d:
        d.materialize(tmpdir)
    wrapper.unbind()
    with pytest.raises(ValueError):
        wrapper.call_method('predict', dataset_np)

    wrapper.load(tmpdir)
    test_wrapper__predict(wrapper, dataset_np)

    assert set(wrapper.requirements.modules) == expected_requirements
