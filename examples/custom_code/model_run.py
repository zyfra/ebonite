"""This module loads created ebonite model and then creates and runs docker container made from this model"""

import ebonite
from ebonite.core.objects.core import Model, Task


def main():
    #  create local ebonite client
    ebnt = ebonite.Ebonite.local()

    # get task
    task: Task = ebnt.get_or_create_task('custom_code_project', 'custom_code_task')

    # get saved model
    model: Model = ebnt.get_model(task=task, model_name='custom_code_model')

    # build docker container from model
    image = ebnt.create_image(model, 'custom_code_model_container', builder_args={'force_overwrite': True})

    # run docker container
    ebnt.create_instance(image, 'custom_code_model_container', port_mapping={9000: 9000}).run(detach=False)
    # now you can use client.py to call this service or go to http://localhost:9000/apidocs to view swagger ui


if __name__ == '__main__':
    main()
