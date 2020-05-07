# EBNT-142 too many Tensorflow deprecation warnings
def fix_warnings():  # noqa
    import logging  # noqa
    import warnings  # noqa
    logging.getLogger("tensorflow").setLevel(logging.CRITICAL)  # noqa
    warnings.filterwarnings('ignore', category=FutureWarning)  # noqa
    warnings.filterwarnings('ignore', category=DeprecationWarning)  # noqa
fix_warnings()  # noqa


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
