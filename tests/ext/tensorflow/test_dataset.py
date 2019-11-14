import numpy as np
import pytest
import tensorflow as tf
from pyjackson import dumps, loads

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.ext.tensorflow import FeedDictDatasetType


def test_feed_dict_type__self_serialization():
    tensor = tf.placeholder('float', (1, 1), name="weight")
    fdt = DatasetAnalyzer.analyze({tensor: np.array([[1]]), 'a': np.array([[1]])})
    assert issubclass(fdt, FeedDictDatasetType)
    payload = dumps(fdt)
    fdt2 = loads(payload, DatasetType)
    assert fdt == fdt2


def test_feed_dict_type__key_error():
    tensor = tf.placeholder('float', (1, 1), name="weight")
    with pytest.raises(ValueError):
        DatasetAnalyzer.analyze({tensor: np.array([[1]]), 1: 1})


def test_feed_dict_type__serialization():
    tensor = tf.placeholder('float', (1, 1), name="weight")
    obj = {tensor: np.array([[1]])}
    fdt = DatasetAnalyzer.analyze(obj)

    payload = dumps(obj, fdt)
    obj2 = loads(payload, fdt)

    assert obj[tensor] == obj2[tensor.name]
