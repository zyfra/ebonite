import numpy as np

import ebonite
from ebonite import Ebonite


def add_one(data):
    return data + 1


def main():
    #  create remote ebonite client. This client stores metadata in postgres and artifacts in s3
    ebnt = Ebonite.custom_client('sqlalchemy', 's3',
                                 meta_kwargs={'db_uri': 'postgresql://postgres:postgres@localhost:5435/ebonite'},
                                 artifact_kwargs={'endpoint': 'http://localhost:8008', 'bucket_name': 'ebonite'})
    # save client configuration for later use
    ebnt.save_client_config('client_config.json')
    #  obtain Task
    task = ebnt.get_or_create_task('my_project', 'my_task')

    #  remove model if it exists (for demo purposes)
    if task.models.contains('add_one_model'):
        model = task.models('add_one_model')
        task.delete_model(model)

    #  create model from function add_one and numpy array as data sample
    model = ebonite.create_model(add_one, np.array([0]), 'add_one_model')

    #  persist model
    task.push_model(model)


if __name__ == '__main__':
    main()
