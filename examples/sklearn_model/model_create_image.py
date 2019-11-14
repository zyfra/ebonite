"""This example shows how you can use ebonite to wrap your sklearn model into docker container"""

from ebonite import Ebonite
from ebonite.build.builder.base import use_local_installation


def main():
    #  create local ebonite client. This client stores metadata and artifacts on local fs.
    ebnt = Ebonite.local()

    task = ebnt.get_or_create_task('my_project', 'regression_is_my_profession')
    model = task.models('mymodel')

    #  this changes docker image builder behaviour to get ebonite from local installation instead of pip
    #  1. for developing reasons 2. we dont have ebonite on pip yet
    with use_local_installation():
        #  build docker image from model and run it
        ebnt.build_and_run_service("sklearn_model_service", model, detach=False, force_overwrite=True)
        # now you can use client.py to call this service or go to http://localhost:9000/apidocs to view swagger ui


if __name__ == '__main__':
    main()
