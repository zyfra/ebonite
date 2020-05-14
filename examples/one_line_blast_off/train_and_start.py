"""This module will train a sklearn linear regression model and save it to local repository"""

import pandas as pd
from sklearn.linear_model import LinearRegression

from ebonite import Ebonite


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

    ebnt = Ebonite.inmemory()

    ebnt.create_instance_from_model('my_model', reg, data, run_instance=True, detach=False)


if __name__ == '__main__':
    main()
