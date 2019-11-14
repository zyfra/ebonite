"""This example shows how you can use ebonite to wrap your sklearn model into flask service"""
from ebonite import Ebonite
from ebonite.runtime import run_model_server


def main():
    #  create local ebonite client. This client stores metadata and artifacts on local fs.
    ebnt = Ebonite.local()

    model = ebnt.get_model(project='my_project', task='regression_is_my_profession', model_name='mymodel')

    # run flask service with this model
    run_model_server(model)
    # now you can use client.py to call this service or go to http://localhost:9000/apidocs to view swagger ui


if __name__ == '__main__':
    main()
