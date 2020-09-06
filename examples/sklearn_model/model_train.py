"""This module will train a sklearn linear regression model and save it to local repository"""
from typing import Tuple

import pandas as pd
from sklearn.linear_model import LogisticRegression

import ebonite


def train_model() -> Tuple[LogisticRegression, pd.DataFrame]:
    """This function simulates general data scientist's work.
    It produces trained model and data sample for this model."""
    reg = LogisticRegression()
    data = pd.DataFrame([[1, 0], [0, 1]], columns=['a', 'b'])
    reg.fit(data, [1, 0])
    return reg, data


def main():
    #  obtain trained model and data sample
    reg, data = train_model()

    #  create local ebonite client. This client stores metadata and artifacts on local fs.
    #  clear=True means it will erase previous data (this is for demo purposes)
    ebnt = ebonite.Ebonite.local(clear=True)

    #  create model named 'mymodel' from sklearn model object and pandas data sample
    #  then push it to repositories. this will create .ebonite dir with metadata.json and artifacts dir
    #  metadata will contain everything ebonite knows about this model and artifacts will contain model.pkl binary
    ebnt.create_model(reg, data, model_name='mymodel',
                      project_name='my_project', task_name='regression_is_my_profession')


if __name__ == '__main__':
    main()
