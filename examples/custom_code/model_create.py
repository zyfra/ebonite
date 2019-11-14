"""This model creates ebonite model from fucntion run imported from other module"""

import pandas as pd
from examples.custom_code._custom_code import run_my_model

from ebonite import Ebonite


def main():
    #  create local ebonite client. This client stores metadata and artifacts on local fs.
    #  clear=True means it will erase previous data (this is for demo purposes)
    ebnt = Ebonite.local(clear=True)

    #  create a Task, container for models
    task = ebnt.get_or_create_task('custom_code_project', 'custom_code_task')

    #  create sample data
    data = pd.DataFrame([{'value': 1}])
    #  create model with name 'custom_code_model' from function 'run_my_model' and pandas data sample
    #  and push this model to repository
    task.create_and_push_model(run_my_model, data, 'custom_code_model')


if __name__ == '__main__':
    main()
