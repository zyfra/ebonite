
Sklearn model Example
=====================

This example will show you how to create ebonite model
object from trained sklearn model and then turn it
into flask service or docker container with
flask service.

First, run `python model_train.py` to train and save
model to local repository.

Then, run either `python start_service.py` to run
flask service, or `python model_create_image.py` to create
and run docker container.

After that, you can run `python client.py %some_number%`
to call your model or go to `http://localhost:9000/apidocs`
to view swagger UI