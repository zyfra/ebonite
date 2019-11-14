"""This module loads created ebonite model and then creates and runs docker container made from this model"""

import ebonite.runtime.server.http
from ebonite.build import build_model_docker, run_docker_img
from ebonite.build.builder.base import use_local_installation
from ebonite.core.objects.core import Model, Task


def main():
    #  create local ebonite client
    ebnt = ebonite.Ebonite.local()

    # get task
    task: Task = ebnt.get_or_create_task('custom_code_project', 'custom_code_task')

    # get saved model
    model: Model = ebnt.get_model(task=task, model_name='custom_code_model')

    #  this changes docker image builder behaviour to get ebonite from local installation instead of pip
    #  1. for developing reasons 2. we dont have ebonite on pip yet
    with use_local_installation():
        # build docker container from model
        build_model_docker('custom_code_model_container', model, force_overwrite=True)

    # run docker conatainer
    run_docker_img('custom_code_model_container', 'custom_code_model_container', port_mapping={9000: 9000})
    # now you can use client.py to call this service or go to http://localhost:9000/apidocs to view swagger ui


if __name__ == '__main__':
    main()
