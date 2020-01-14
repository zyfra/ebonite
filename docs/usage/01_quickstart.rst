==========
Quickstart
==========

Ebonite can be used to reproduce arbitrary machine learning model in different environments.

.. note::
    Don't forget to install requirements for this example: ``pip install pandas scikit-learn flask flasgger``

For instance, you can train sklearn model
(`code <https://github.com/zyfra/ebonite/blob/master/examples/sklearn_model/model_train.py#L13>`_):

.. literalinclude:: ../../examples/sklearn_model/model_train.py
   :linenos:
   :language: python
   :lines: 13-15

To use ebonite you need to create Ebonite client
(`code <https://github.com/zyfra/ebonite/blob/master/examples/sklearn_model/model_train.py#L25>`_):

.. literalinclude:: ../../examples/sklearn_model/model_train.py
   :linenos:
   :language: python
   :lines: 25
..

Now you need to create task to push your model into
(`code <https://github.com/zyfra/ebonite/blob/master/examples/sklearn_model/model_train.py#L28>`_):

.. literalinclude:: ../../examples/sklearn_model/model_train.py
   :linenos:
   :language: python
   :lines: 28,32
..

Great, now you can reproduce this model in different environment using this code
(`code <https://github.com/zyfra/ebonite/blob/master/examples/sklearn_model/start_service.py#L9>`_):

.. literalinclude:: ../../examples/sklearn_model/start_service.py
   :linenos:
   :language: python
   :lines: 9
..

And start a server that processes inference request like this
(`code <https://github.com/zyfra/ebonite/blob/master/examples/sklearn_model/start_service.py#L12>`_):

.. literalinclude:: ../../examples/sklearn_model/start_service.py
   :linenos:
   :language: python
   :lines: 12-13
..

Or create and start a docker container like this
(`code <https://github.com/zyfra/ebonite/blob/master/examples/sklearn_model/model_create_image.py#L18>`_):

.. literalinclude:: ../../examples/sklearn_model/model_create_image.py
   :linenos:
   :language: python
   :lines: 18
..

Full code can be found in
`examples/sklearn_model <https://github.com/zyfra/ebonite/tree/master/examples/sklearn_model>`_.
