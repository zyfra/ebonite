import numpy as np
import pytest
from pyjackson import dumps, loads
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.ext.numpy.dataset import NumpyNdarrayDatasetType, NumpyNumberDatasetType


@pytest.fixture
def nat():
    return DatasetAnalyzer.analyze(np.array([[1, 2], [3, 4]]))


def test_number():
    ndt = DatasetAnalyzer.analyze(np.float32(.5))
    assert issubclass(ndt, NumpyNumberDatasetType)
    assert ndt.requirements.modules == ['numpy']
    payload = dumps(ndt)
    ndt2 = loads(payload, DatasetType)
    assert ndt == ndt2


def test_ndarray(nat):
    assert issubclass(nat, NumpyNdarrayDatasetType)
    assert nat.requirements.modules == ['numpy']
    payload = dumps(nat)
    nat2 = loads(payload, DatasetType)

    assert nat == nat2


@pytest.mark.parametrize('obj', [
    {},                                            # wrong type
    np.array([[1, 2], [3, 4]], dtype=np.float32),  # wrong data type
    np.array([1, 2])                               # wrong shape
])
def test_ndarray_serialize_failure(nat, obj):
    with pytest.raises(SerializationError):
        nat.serialize(obj)


@pytest.mark.parametrize('obj', [
    {},             # wrong type
    [[1, 2], [3]],  # illegal array
    [[1, 2, 3]]     # shape
])
def test_ndarray_deserialize_failure(nat, obj):
    with pytest.raises(DeserializationError):
        nat.deserialize(obj)
