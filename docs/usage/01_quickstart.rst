==========
Quickstart
==========

Ebonite can be used to reproduce arbitrary machine learning model in different environments.

.. note::
    Don't forget to install requirements for this example: ``pip install pandas scikit-learn flask flasgger``

For instance, you can train sklearn model:

.. literalinclude:: ../../examples/sklearn_model/model_train.py
   :linenos:
   :language: python
   :lines: 13-15

To use ebonite you need to create Ebonite client:

.. literalinclude:: ../../examples/sklearn_model/model_train.py
   :linenos:
   :language: python
   :lines: 25
..

Now you need to create task to push your model into:

.. literalinclude:: ../../examples/sklearn_model/model_train.py
   :linenos:
   :language: python
   :lines: 28,32
..

Great, now you can reproduce this model in different environment using this code:

.. literalinclude:: ../../examples/sklearn_model/start_service.py
   :linenos:
   :language: python
   :lines: 9
..

And start a server that processes inference request like this:

.. literalinclude:: ../../examples/sklearn_model/start_service.py
   :linenos:
   :language: python
   :lines: 12-13
..

Or create and start a docker container like this:

.. literalinclude:: ../../examples/sklearn_model/model_create_image.py
   :linenos:
   :language: python
   :lines: 18
..

This code can be found in `examples/sklearn_model.py`
