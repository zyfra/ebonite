import numpy as np
import pytest
import tensorflow as tf
from pyjackson import dumps, loads
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.dataset_type import DatasetType


@pytest.fixture
def fdt(tensor):
    # force loading of dataset hooks
    import ebonite.ext.tensorflow  # noqa

    return DatasetAnalyzer.analyze({tensor: np.array([[1]]), 'a': np.array([[1]])})


@pytest.mark.tf_v1
@pytest.mark.skipif(tf.__version__.split('.')[0] != '1', reason="requires tensorflow 1.x")
def test_feed_dict_type__self_serialization(fdt, tensor):
    from ebonite.ext.tensorflow import FeedDictDatasetType

    assert issubclass(fdt, FeedDictDatasetType)
    assert set(fdt.requirements.modules) == {'tensorflow', 'numpy'}
    payload = dumps(fdt)
    fdt2 = loads(payload, DatasetType)
    assert fdt == fdt2


@pytest.mark.tf_v1
@pytest.mark.skipif(tf.__version__.split('.')[0] != '1', reason="requires tensorflow 1.x")
def test_feed_dict_type__key_error(tensor):
    with pytest.raises(ValueError):
        DatasetAnalyzer.analyze({tensor: np.array([[1]]), 1: 1})


@pytest.mark.tf_v1
@pytest.mark.skipif(tf.__version__.split('.')[0] != '1', reason="requires tensorflow 1.x")
def test_feed_dict_type__serialization(tensor):
    obj = {tensor: np.array([[1]])}
    fdt = DatasetAnalyzer.analyze(obj)

    payload = dumps(obj, fdt)
    obj2 = loads(payload, fdt)

    assert obj[tensor] == obj2[tensor.name]


@pytest.mark.tf_v1
@pytest.mark.skipif(tf.__version__.split('.')[0] != '1', reason="requires tensorflow 1.x")
@pytest.mark.parametrize('obj', [
    1,                       # wrong type
    {1: 1, 2: 2},            # wrong key types
    {'b': 1, 'a': 2},        # wrong keys set
    {'weight:0': 1, 'a': 2}  # wrong value types
])
def test_feed_dict_serialize_failure(fdt, obj):
    with pytest.raises(SerializationError):
        fdt.serialize(obj)


@pytest.mark.tf_v1
@pytest.mark.skipif(tf.__version__.split('.')[0] != '1', reason="requires tensorflow 1.x")
@pytest.mark.parametrize('obj', [
    1,                       # wrong type
    {1: 1, 2: 2},            # wrong key types
    {'b': 1, 'a': 2},        # wrong keys set
    {'weight:0': 1, 'a': 2}  # wrong value types
])
def test_feed_dict_deserialize_failure(fdt, obj):
    with pytest.raises(DeserializationError):
        fdt.deserialize(obj)
