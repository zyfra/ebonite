"""This example shows how you can use ebonite to wrap your sklearn model into docker container"""

from ebonite import Ebonite


def main():
    #  create local ebonite client. This client stores metadata and artifacts on local fs.

    ebnt = Ebonite.local()

    task = ebnt.get_or_create_task('my_project', 'regression_is_my_profession')
    model = task.models('mymodel')

    #  build docker image from model and run it
    ebnt.build_and_run_instance(model, "sklearn_model_service",
                                runner_kwargs={'detach': False},
                                builder_kwargs={'force_overwrite': True},
                                instance_kwargs={'port_mapping': {9000: 9000}}
                                )
    # now you can use client.py to call this service or go to http://localhost:9000/apidocs to view swagger ui


if __name__ == '__main__':
    main()
