"""This example shows how to use ebonite with tensorflow>=2.0.0"""

import numpy as np
import tensorflow as tf

import ebonite
from ebonite.runtime import run_model_server


def train_regression():
    """This function emulates data scientist's work. It produces a trained regression model and
    some sample data in numpy format"""
    learning_rate = 0.01
    training_epochs = 10
    n_samples = 20

    weight = 0.5
    bias = -2

    rng = np.random

    train_X = rng.uniform(-10, 10, (n_samples,))
    train_Y = train_X * weight + bias + rng.uniform(-0.1, 0.1, train_X.shape)

    model = tf.keras.models.Sequential([tf.keras.layers.Dense(1)])

    model.compile(optimizer=tf.keras.optimizers.SGD(learning_rate),
                  loss=tf.keras.losses.MeanSquaredError(),
                  metrics=['mse'])

    model.fit(train_X, train_Y, batch_size=1, epochs=training_epochs)

    train_mse = model.evaluate(train_X, train_Y)[0]
    print('train mse', train_mse)

    test_X = rng.uniform(-10, 10, (n_samples,))
    test_Y = test_X * weight + bias

    test_mse = model.evaluate(test_X, test_Y)[0]
    print('test mse', test_mse)

    return model, test_X


def main():
    #  obtain TF Keras model and test data
    tf_keras_model, test_data = train_regression()

    #  create model 'tf_v2_model' from TF Keras model and test data
    model = ebonite.create_model(tf_keras_model, test_data, 'tf_v2_model')

    # run flask service with this model
    run_model_server(model)
    # now you can use client.py to call this service or go to http://localhost:9000/apidocs to view swagger ui


if __name__ == '__main__':
    main()
