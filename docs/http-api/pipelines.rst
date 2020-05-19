Pipelines
============

Get list of pipelines
------------------------

Request
^^^^^^^

.. code-block::

    GET /pipelines?task_id=1

* `task_id`: id of task to get pipelines for

Response
^^^^^^^^

* `200`:

.. code-block:: json

  [
    {
    "name": "pipe_1",
    "id": 1,
    "task_id": 1,
    "creation_date": "1970-01-01 00:00:00.000000 ",
    "author": "user_name",
    "input_data": "array",
    "output_data": "array",
    "steps": [
        {"model_name": "model1", "method_name": "method1"},
        {"model_name": "model2", "method_name": "method2"}
        ],
    "models":
        { "model1":{
          "name": "model1",
          "id": 1,
          "task_id": 1,
          "author": "user_name",
          "creation_date": "1970-01-01 00:00:00.000000 ",
          "wrapper_meta": {"type": "ebonite.ext.sklearn.model.SklearnModelWrapper"},
          "requirements": [
            {"module": "numpy", "version": "1.17.3", "type": "installable"},
            {"module": "sklearn", "version": "0.22", "type": "installable"}
          ],
          "params": {"python_version": "3.7.5"},
          "artifacts": ["model.pkl", "methods.json"]
        },
        "model2":{
          "name": "model2",
          "id": 2,
          "task_id": 1,
          "author": "user_name",
          "creation_date": "1970-01-01 00:00:00.000000 ",
          "wrapper_meta": {"type": "ebonite.ext.sklearn.model.SklearnModelWrapper"},
          "requirements": [
            {"module": "numpy", "version": "1.17.3", "type": "installable"},
            {"module": "sklearn", "version": "0.22", "type": "installable"}
          ],
          "params": {"python_version": "3.7.5"},
          "artifacts": ["model.pkl", "methods.json"]
        }
      }
    }
  ]

* `404`: if given task doesn't exist

Get pipeline
------------

Request
^^^^^^^

.. code-block::

  GET /pipelines/<:id>

* `id`: id of pipeline to get

Response
^^^^^^^^

* `200`:

.. code-block:: json

    {
    "name": "pipe_1",
    "id": 1,
    "task_id": 1,
    "creation_date": "1970-01-01 00:00:00.000000 ",
    "author": "user_name",
    "input_data": "array",
    "output_data": "array",
    "steps": [
        {"model_name": "model1", "method_name": "method1"},
        {"model_name": "model2", "method_name": "method2"}
        ],
    "models":
        { "model1":{
          "name": "model1",
          "id": 1,
          "task_id": 1,
          "author": "user_name",
          "creation_date": "1970-01-01 00:00:00.000000 ",
          "wrapper_meta": {"type": "ebonite.ext.sklearn.model.SklearnModelWrapper"},
          "requirements": [
            {"module": "numpy", "version": "1.17.3", "type": "installable"},
            {"module": "sklearn", "version": "0.22", "type": "installable"}
          ],
          "params": {"python_version": "3.7.5"},
          "artifacts": ["model.pkl", "methods.json"]
        },
        "model2":{
          "name": "model2",
          "id": 2,
          "task_id": 1,
          "author": "user_name",
          "creation_date": "1970-01-01 00:00:00.000000 ",
          "wrapper_meta": {"type": "ebonite.ext.sklearn.model.SklearnModelWrapper"},
          "requirements": [
            {"module": "numpy", "version": "1.17.3", "type": "installable"},
            {"module": "sklearn", "version": "0.22", "type": "installable"}
          ],
          "params": {"python_version": "3.7.5"},
          "artifacts": ["model.pkl", "methods.json"]
        }
      }
    }

Update pipeline
---------------

Request
^^^^^^^

.. code-block::

  PATCH /pipelines/<:id>

* `id`: id of pipeline to update

.. code-block:: json

  {
    "name": "first pipeline"
  }

Response
^^^^^^^^^^^^^^

* `204`: OK
* `404`: if given pipeline doesn't exist

Delete pipeline
---------------

Request
^^^^^^^

.. code-block::

  DELETE /pipelines/<:id>

* `id`: id of pipeline to delete

Response
^^^^^^^^^^^^^^

* `204`: OK
* `404`: if given pipeline doesn't exist

