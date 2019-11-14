
Sklearn one line model Example
==============================

This example will show you how to create ebonite model
object from trained sklearn model and then turn it
into docker container with
flask service in ONE LINE of code.

First, run `python train_and_run.py` to train model, save
it to local repository and run it as a service.

After that, you can run `python client.py %some_number%`
to call your model or go to `http://localhost:9000/apidocs`
to view swagger UI