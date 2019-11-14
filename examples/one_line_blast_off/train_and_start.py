"""This module will train a sklearn linear regression model and save it to local repository"""

import pandas as pd
from sklearn.linear_model import LinearRegression

from ebonite.build.builder.base import use_local_installation
from ebonite.build.helpers import create_service_from_model


def train_model():
    """This function simulates general data scientist's work.
    It produces trained model and data sample for this model."""
    reg = LinearRegression()
    data = pd.DataFrame([[1, 1], [2, 1]], columns=['a', 'b'])
    reg.fit(data, [1, 0])
    return reg, data


def main():
    #  obtain trained model and data sample
    reg, data = train_model()

    #  this changes docker image builder behaviour to get ebonite from local installation instead of pip
    #  1. for developing reasons 2. we dont have ebonite on pip yet
    with use_local_installation():
        create_service_from_model('my_model', reg, data, task_name='my_task',
                                  service_name='magic-one-line-ebnt-service', run_service=True)


if __name__ == '__main__':
    main()
