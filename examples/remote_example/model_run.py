from ebonite import Ebonite
from ebonite.runtime.debug import run_test_model_server


def main():
    #  create remote ebonite client from saved configuration
    ebnt = Ebonite.from_config_file('client_config.json')
    model = ebnt.get_model('add_one_model', 'my_task', 'my_project')

    # run flask service with this model
    run_test_model_server(model)
    # now you can use client.py to call this service or go to http://localhost:9000/apidocs to view swagger ui


if __name__ == '__main__':
    main()
