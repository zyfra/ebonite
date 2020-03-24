Tasks
=====

Get list of tasks
-----------------

Request
^^^^^^^

.. code-block::

  GET /tasks?project_id=1

Response
^^^^^^^^

* `200`:

.. code-block:: json

  [
    {
      "name": "first task",
      "id": 1,
      "project_id": 1,
      "author": "user_name",
      "creation_date": "1970-01-01 00:00:00.000000 "
    }
  ]

* `404`: if given project doesn't exist


Get task
--------

Request
^^^^^^^

.. code-block::

  GET /tasks/1

Response
^^^^^^^^

* `200`:

.. code-block:: json

  {
    "name": "first task",
    "id": 1,
    "project_id": 1,
    "author": "user_name",
    "creation_date": "1970-01-01 00:00:00.000000 "
  }

* `404`: if given task doesn't exist


Create task
-----------

Request
^^^^^^^

.. code-block::

  PUT /tasks

.. code-block:: json

  {
    "name": "first task",
    "project_id": 1
  }

Response
^^^^^^^^^^^^^^

* `200`:

.. code-block:: json

  {
    "name": "first task",
    "id": 1,
    "project_id": 1,
    "author": "user_name",
    "creation_date": "1970-01-01 00:00:00.000000 "
  }

* `400`: if task with given name already exists in given project


Delete task
-----------

Request
^^^^^^^

.. code-block::

  DELETE /tasks/1?cascade=1

* `cascade`: (optional, default - `0`) delete cascadely (with referenced models, etc)

Response
^^^^^^^^^^^^^^

* `200`: OK
* `400`: if `cascade` is not `1` and given task has models in it
* `404`: if given task doesn't exist
