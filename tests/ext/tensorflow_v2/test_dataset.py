import numpy as np
import pytest
import tensorflow as tf
from pyjackson import dumps, loads
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.runtime.openapi.spec import type_to_schema


@pytest.fixture
def tftt(tensor_data):
    return _analyze(tensor_data)


@pytest.fixture
def tftt_3d(tensor_data):
    return _analyze(tf.tile(tf.expand_dims(tensor_data, -1), [1, 1, 20]))


def _analyze(tensor):
    # force loading of dataset hooks
    import ebonite.ext.tensorflow_v2  # noqa

    return DatasetAnalyzer.analyze(tensor)


@pytest.mark.skipif(tf.__version__.split('.')[0] != '2', reason="requires tensorflow 2.x")
def test_feed_dict_type__self_serialization(tftt):
    from ebonite.ext.tensorflow_v2 import TFTensorDatasetType

    assert issubclass(tftt, TFTensorDatasetType)
    assert tftt.requirements.modules == ['tensorflow']
    payload = dumps(tftt)
    tftt2 = loads(payload, DatasetType)
    assert tftt == tftt2


@pytest.mark.skipif(tf.__version__.split('.')[0] != '2', reason="requires tensorflow 2.x")
def test_feed_dict_type__serialization(tftt, tensor_data):
    payload = dumps(tensor_data, tftt)
    tensor_data2 = loads(payload, tftt)

    tf.assert_equal(tensor_data, tensor_data2)


@pytest.mark.skipif(tf.__version__.split('.')[0] != '2', reason="requires tensorflow 2.x")
@pytest.mark.parametrize('obj', [
    1,                                                                    # wrong type
    tf.convert_to_tensor(np.random.random((100,)), dtype=tf.float32),     # wrong rank
    tf.convert_to_tensor(np.random.random((100, 16)), dtype=tf.float32),  # wrong shape
    tf.convert_to_tensor(np.random.random((100, 32)), dtype=tf.float64),  # wrong value type
])
def test_feed_dict_serialize_failure(tftt, obj):
    with pytest.raises(SerializationError):
        tftt.serialize(obj)


@pytest.mark.skipif(tf.__version__.split('.')[0] != '2', reason="requires tensorflow 2.x")
@pytest.mark.parametrize('obj', [
    1,                       # wrong type
    [1] * 32,                # wrong rank
    [[1] * 16] * 100,        # wrong shape
    [['1'] * 32] * 100       # wrong value type
])
def test_feed_dict_deserialize_failure(tftt, obj):
    with pytest.raises(DeserializationError):
        tftt.deserialize(obj)


@pytest.mark.skipif(tf.__version__.split('.')[0] != '2', reason="requires tensorflow 2.x")
def test_feed_dict_type__openapi_schema_3d(tftt_3d):
    assert type_to_schema(tftt_3d) == {
        'items': {
            'items': {
                'items': {'type': 'number'},
                'maxItems': 20,
                'minItems': 20,
                'type': 'array'
            },
            'maxItems': 32,
            'minItems': 32,
            'type': 'array'
        },
        'type': 'array'
    }
