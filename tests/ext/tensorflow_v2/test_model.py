import numpy as np
import pytest
import tensorflow as tf

from ebonite.core.analyzer.model import ModelAnalyzer


@pytest.fixture
def bi_np_data(np_data):
    return [np_data, np_data]


@pytest.fixture
def bi_tensor_data(tensor_data):
    return [tensor_data, tensor_data]


@pytest.fixture
def mixed_data(np_data, tensor_data):
    return [np_data, tensor_data]


@pytest.fixture
def labels():
    return np.random.random((100, 10))


@pytest.fixture
def simple_net(np_data, labels):
    model = tf.keras.Sequential()
    model.add(tf.keras.layers.Dense(64, activation='relu'))
    model.add(tf.keras.layers.Dense(10))

    model.compile(optimizer=tf.keras.optimizers.Adam(0.01),
                  loss=tf.keras.losses.CategoricalCrossentropy(from_logits=True),
                  metrics=['accuracy'])
    model.fit(np_data, labels, epochs=1, batch_size=50)

    return model


@pytest.fixture
def complex_net(bi_np_data, labels):
    class Net(tf.keras.Model):
        def __init__(self):
            super().__init__(self)
            self.left = tf.keras.layers.Dense(50, activation='relu')
            self.right = tf.keras.layers.Dense(50, activation='tanh')
            self.clf = tf.keras.layers.Dense(10)

        def call(self, inputs, training=None, mask=None):
            left_output, right_output = self.left(inputs[0]), self.right(inputs[1])
            clf_input = tf.concat([left_output, right_output], -1)
            return self.clf(clf_input)

    model = Net()

    model.compile(optimizer=tf.keras.optimizers.Adam(0.01),
                  loss=tf.keras.losses.CategoricalCrossentropy(from_logits=True),
                  metrics=['accuracy'])
    model.fit(bi_np_data, labels, epochs=1, batch_size=50)

    return model


class _Wrapper:
    def __init__(self, net):
        self.net = net

    def __call__(self, input_data):
        return self.net.predict(input_data)


@pytest.fixture
def wrapped_net(simple_net):
    return _Wrapper(simple_net)


@pytest.mark.skipif(tf.__version__.split('.')[0] != '2', reason="requires tensorflow 2.x")
@pytest.mark.parametrize("net,input_data", [
    ("simple_net", "np_data"),
    ("simple_net", "tensor_data"),
    ("complex_net", "bi_np_data"),
    ("complex_net", "bi_tensor_data"),
    ("complex_net", "mixed_data"),
    ("wrapped_net", "np_data"),
    ("wrapped_net", "tensor_data")
])
def test_model_wrapper(net, input_data, tmpdir, request):
    # force loading of dataset and model hooks
    import ebonite.ext.tensorflow_v2  # noqa

    net = request.getfixturevalue(net)
    input_data = request.getfixturevalue(input_data)

    orig_pred = net(input_data) if callable(net) else net.predict(input_data)

    tmw = ModelAnalyzer.analyze(net, input_data=input_data)

    assert tmw.model is net

    expected_requirements = {'tensorflow', 'numpy'}
    assert set(tmw.requirements.modules) == expected_requirements

    prediction = tmw.call_method('predict', input_data)

    np.testing.assert_array_equal(orig_pred, prediction)

    with tmw.dump() as artifact:
        artifact.materialize(tmpdir)

    tmw.unbind()
    with pytest.raises(ValueError):
        tmw.call_method('predict', input_data)

    tmw.load(tmpdir)

    assert tmw.model is not net

    prediction2 = tmw.call_method('predict', input_data)

    np.testing.assert_array_equal(prediction, prediction2)

    assert set(tmw.requirements.modules) == expected_requirements
