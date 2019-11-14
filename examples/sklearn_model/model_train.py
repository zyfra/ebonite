"""This module will train a sklearn linear regression model and save it to local repository"""
from typing import Tuple

import pandas as pd
from sklearn.linear_model import LinearRegression

import ebonite


def train_model() -> Tuple[LinearRegression, pd.DataFrame]:
    """This function simulates general data scientist's work.
    It produces trained model and data sample for this model."""
    reg = LinearRegression()
    data = pd.DataFrame([[1, 1], [2, 1]], columns=['a', 'b'])
    reg.fit(data, [1, 0])
    return reg, data


def main():
    #  obtain trained model and data sample
    reg, data = train_model()

    #  create local ebonite client. This client stores metadata and artifacts on local fs.
    #  clear=True means it will erase previous data (this is for demo purposes)
    ebnt = ebonite.Ebonite.local()

    #  create a Task, container for models
    task = ebnt.get_or_create_task('my_project', 'regression_is_my_profession')
    #  create model named 'mymodel' from sklearn model object and pandas data sample
    #  then push it to repositories. this will create .ebonite dir with metadata.json and artifacts dir
    #  metadata will contain everything ebonite knows about this model and artifacts will contain model.pkl binary
    task.create_and_push_model(reg, data, 'mymodel')


if __name__ == '__main__':
    main()
