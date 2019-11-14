
Example with remote repositories
================================

This example will show you how to use ebonite with
persistent remote repositories for metadata and artifacts.

.. note::
    Before you begin, ensure that you have all the
    requirements installed with

    `pip install -r requirements.txt`
..

First, run metadata and artifact stores mocks with
`docker-compose up -d`

Then, run `python model_create.py` to create and save
ebonite model to repository.

After that, you can run `python model_run.py` to start
model service. You can actually run it from anywhere your
repository containers are available.