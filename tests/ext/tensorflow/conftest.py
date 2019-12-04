import pytest
import tensorflow as tf


@pytest.fixture
def graph():
    return tf.Graph()


@pytest.fixture
def tensor(graph):
    with graph.as_default():
        return tf.placeholder('float', (1, 1), name="weight")


@pytest.fixture
def second_tensor(graph):
    with graph.as_default():
        return tf.placeholder(tf.float32, [1, 2], name='second')
