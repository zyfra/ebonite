
Tensorflow Example
=====================

This example will show you how to create ebonite model
object from tensorflow graph and then turn it
into flask service or docker container with
flask service.

Run `python train_and_serve.py` to train and serve
model as flask service.


After that, you can run `python client.py %some_number%`
to call your model or go to `http://localhost:9000/apidocs`
to view swagger UI