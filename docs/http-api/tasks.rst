Tasks
=====

Get list of tasks
-----------------

Request
^^^^^^^

.. code-block::

  GET /tasks?project_id=1

* `project_id`: id of project to get tasks for

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

  GET /tasks/<:id>

* `id`: id of task to get

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

  POST /tasks

.. code-block:: json

  {
    "name": "first task",
    "project_id": 1
  }

Response
^^^^^^^^^^^^^^

* `201`:

.. code-block:: json

  {
    "name": "first task",
    "id": 1,
    "project_id": 1,
    "author": "user_name",
    "creation_date": "1970-01-01 00:00:00.000000 "
  }

* `400`: if task with given name already exists in given project


Update task
-----------

Request
^^^^^^^

.. code-block::

  PATCH /tasks/<:id>

* `id`: id of task to update

.. code-block:: json

  {
    "name": "first task",
    "project_id": 1
  }

Response
^^^^^^^^^^^^^^

* `204`: OK
* `404`: if given task doesn't exist


Delete task
-----------

Request
^^^^^^^

.. code-block::

  DELETE /tasks/<:id>?cascade=1

* `id`: id of task to delete
* `cascade`: (optional, default - `0`) delete cascadely (with referenced models, etc)

Response
^^^^^^^^^^^^^^

* `204`: OK
* `400`: if `cascade` is not `1` and given task has models in it
* `404`: if given task doesn't exist
