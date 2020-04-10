import pytest
import tensorflow as tf

from ebonite.core.analyzer.model import ModelAnalyzer


@pytest.mark.tf_v1
@pytest.mark.skipif(tf.__version__.split('.')[0] != '1', reason="requires tensorflow 1.x")
def test_tf__single_tensor(graph, tensor, tmpdir):
    with graph.as_default():
        out = tf.layers.dense(tensor, 1, activation=tf.tanh)

    _check_model_wrapper(graph, out, {tensor.name: [[1]]}, tmpdir)


@pytest.mark.tf_v1
@pytest.mark.skipif(tf.__version__.split('.')[0] != '1', reason="requires tensorflow 1.x")
def test_tf__multiple_tensors(graph, tensor, second_tensor, tmpdir):
    with graph.as_default():
        cat = tf.concat([tensor, second_tensor], -1)
        out1 = tf.layers.dense(cat, 1, activation=tf.tanh)
        out2 = tf.layers.dense(cat, 1, activation=tf.sigmoid)

    _check_model_wrapper(graph, [out1, out2], {tensor.name: [[1]], second_tensor.name: [[1, 2]]}, tmpdir)


def _check_model_wrapper(graph, model, feed_dict, tmpdir):
    # this import is required to ensure that Tensorflow model wrapper is registered
    import ebonite.ext.tensorflow  # noqa

    with tf.Session(graph=graph) as session:
        session.run(tf.global_variables_initializer())
        # training here is just random initialization

        tmw = ModelAnalyzer.analyze(model, input_data=feed_dict)
        assert tmw.model.tensors is model

        expected_requirements = {'tensorflow', 'numpy'}
        assert set(tmw.requirements.modules) == expected_requirements

        pred = tmw.call_method('predict', feed_dict)

        with tmw.dump() as artifact:
            artifact.materialize(tmpdir)

        tmw.unbind()
        with pytest.raises(ValueError):
            tmw.call_method('predict', feed_dict)

    tmw.load(tmpdir)
    assert tmw.model is not model

    pred2 = tmw.call_method('predict', feed_dict)
    assert pred2 == pred

    assert set(tmw.requirements.modules) == expected_requirements
