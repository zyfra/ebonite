Models
======

Get list of models
------------------

Request
^^^^^^^

.. code-block::

  GET /models?task_id=1

* `task_id`: id of task to get models for

Response
^^^^^^^^

* `200`:

.. code-block:: json

  [
    {
      "name": "first model",
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
    }
  ]

* `404`: if given task doesn't exist


Get model
---------

Request
^^^^^^^

.. code-block::

  GET /models/<:id>

* `id`: id of model to get

Response
^^^^^^^^

* `200`:

.. code-block:: json

  {
    "name": "first model",
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
  }

* `404`: if given task doesn't exist


Get model artifact
------------------

Request
^^^^^^^

.. code-block::

  GET /models/<:id>/artifacts/<:name>

* `id`: id of model to get artifacts for
* `name`: name of artifact to get

Response
^^^^^^^^^^^^^^

* `200`: OK

.. code-block:: application/octet-stream

<artifact binary content>

* `404`: if given model or artifact doesn't exist


Update model
------------

Request
^^^^^^^

.. code-block::

  PATCH /models/<:id>

* `id`: id of model to update

.. code-block:: json

  {
    "name": "first model"
  }

Response
^^^^^^^^^^^^^^

* `204`: OK
* `404`: if given model doesn't exist


Delete model
------------

Request
^^^^^^^

.. code-block::

  DELETE /models/<:id>?cascade=1

* `id`: id of model to delete
* `cascade`: (optional, default - `0`) delete cascadely (with referenced images, etc)

Response
^^^^^^^^^^^^^^

* `204`: OK
* `400`: if `cascade` is not `1` and given model has images in it
* `404`: if given model doesn't exist
