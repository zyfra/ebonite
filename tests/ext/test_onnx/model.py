import numpy as np
import onnx
import pytest
from onnxruntime.datasets import get_example
from pyjackson import deserialize, serialize

from ebonite.core.analyzer.model import ModelAnalyzer
from ebonite.core.objects import ModelWrapper
from ebonite.ext.onnx.model import ONNXModelWrapper


@pytest.fixture
def onnx_model():
    return onnx.load(get_example('sigmoid.onnx'))


@pytest.fixture
def onnx_input():
    x = np.random.random((3, 4, 5)).astype(np.float32)
    return {'x': x}


@pytest.fixture
def onnx_wrapper(onnx_model, onnx_input):
    return ModelAnalyzer.analyze(onnx_model, input_data=onnx_input)


def test_onnx_hook(onnx_wrapper):
    assert isinstance(onnx_wrapper, ONNXModelWrapper)


def test_onnx_io(onnx_wrapper: ModelWrapper, tmpdir, onnx_input):
    with onnx_wrapper.dump() as artifacts:
        artifacts.materialize(tmpdir)

    onnx_wrapper: ONNXModelWrapper = deserialize(serialize(onnx_wrapper), ModelWrapper)
    assert isinstance(onnx_wrapper, ONNXModelWrapper)
    onnx_wrapper.load(tmpdir)
    predict = onnx_wrapper.run(onnx_input)
    assert isinstance(predict, list)
    assert len(predict) == 1
    tensor = predict[0]
    assert isinstance(tensor, np.ndarray)
