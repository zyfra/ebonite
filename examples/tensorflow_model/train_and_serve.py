"""This example shows how to use ebonite with tensorflow<2.0.0"""

import logging
from typing import Dict, List, Tuple, Union

import numpy as np
import tensorflow as tf

import ebonite
from ebonite.runtime import run_model_server

tf_logger = logging.getLogger('tensorflow')
tf_logger.setLevel(logging.ERROR)


def train_regression() -> Tuple[tf.Session, Union[tf.Tensor, List[tf.Tensor]], Dict[tf.Tensor, np.array]]:
    """This function emulates data scientist's work. It produces a tf.Session with trained regression model and
    some sample data in feed_dict format"""
    learning_rate = 0.01
    training_epochs = 10
    n_samples = 20

    weight = 0.5
    bias = -2

    rng = np.random

    train_X = rng.uniform(-10, 10, (n_samples,))
    train_Y = train_X * weight + bias + rng.uniform(-0.1, 0.1, train_X.shape)

    X = tf.placeholder("float", name='X')
    Y = tf.placeholder("float", name='y')
    W = tf.Variable(rng.randn(), name="weight")
    b = tf.Variable(rng.randn(), name="bias")

    pred = tf.add(tf.multiply(X, W), b)
    mse = tf.reduce_sum(tf.pow(pred - Y, 2)) / (2 * n_samples)
    optimizer = tf.train.GradientDescentOptimizer(learning_rate).minimize(mse)

    sess = tf.Session()

    # Run the initializer
    sess.run(tf.global_variables_initializer())

    # Fit all training data
    for epoch in range(training_epochs):
        for (x, y) in zip(train_X, train_Y):
            sess.run(optimizer, feed_dict={X: x, Y: y})

    train_mse = sess.run(mse, feed_dict={X: train_X, Y: train_Y})
    print('train mse', train_mse)
    # Testing example
    test_X = rng.uniform(-10, 10, (n_samples,))
    test_Y = test_X * weight + bias
    test_mse = sess.run(mse, feed_dict={X: test_X, Y: test_Y})
    print('test mse', test_mse)
    return sess, pred, {X: test_X}


def main():
    #  obtain session, output tensor and feed_dict
    session, tensor, feed_dict = train_regression()

    #  in provided session, create model 'tf_model' from output tensor and sample data
    with session.as_default():
        model = ebonite.create_model(tensor, feed_dict, 'tf_model')

    # run flask service with this model
    run_model_server(model)
    # now you can use client.py to call this service or go to http://localhost:9000/apidocs to view swagger ui


if __name__ == '__main__':
    main()
