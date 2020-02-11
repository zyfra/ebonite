import numpy as np
import pytest
import tensorflow as tf


@pytest.fixture
def np_data():
    return np.random.random((100, 32))


@pytest.fixture
def tensor_data(np_data):
    return tf.convert_to_tensor(np_data, dtype=tf.float32)
