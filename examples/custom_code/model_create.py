"""This model creates ebonite model from fucntion run imported from other module"""

import pandas as pd
from examples.custom_code._custom_code import run_my_model

from ebonite import Ebonite


def main():
    #  create local ebonite client. This client stores metadata and artifacts on local fs.
    #  clear=True means it will erase previous data (this is for demo purposes)
    ebnt = Ebonite.local(clear=True)

    #  create sample data
    data = pd.DataFrame([{'value': 1}])
    #  create model with name 'custom_code_model' from function 'run_my_model' and pandas data sample
    #  and push this model to repository
    ebnt.create_model('custom_code_model', run_my_model, data,
                      project_name='custom_code_project', task_name='custom_code_task')


if __name__ == '__main__':
    main()
