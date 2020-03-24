Projects
========

Get list of projects
--------------------

Request
^^^^^^^

.. code-block::

  GET /projects

Response
^^^^^^^^

* `200`:

.. code-block:: json

  [
    {
      "name": "first project",
      "id": 1,
      "author": "user_name",
      "creation_date": "1970-01-01 00:00:00.000000 "
    }
  ]

Get project
-----------

Request
^^^^^^^

.. code-block::

  GET /projects/1

Response
^^^^^^^^

* `200`:

.. code-block:: json

  {
    "name": "first project",
    "id": 1,
    "author": "user_name",
    "creation_date": "1970-01-01 00:00:00.000000 "
  }

* `404`: if given project doesn't exist


Create project
--------------

Request
^^^^^^^

.. code-block::

  POST /projects

.. code-block:: json

  {
    "name": "first project"
  }

Response
^^^^^^^^^^^^^^

* `201`:

.. code-block:: json

  {
    "name": "first project",
    "id": 1,
    "author": "user_name",
    "creation_date": "1970-01-01 00:00:00.000000 "
  }

* `400`: if project with given name already exists


Delete project
--------------

Request
^^^^^^^

.. code-block::

  DELETE /projects/1?cascade=1

* `cascade`: (optional, default - `0`) delete cascadely (with referenced tasks, models, etc)

Response
^^^^^^^^^^^^^^

* `204`: OK
* `400`: if `cascade` is not `1` and given project has tasks in it
* `404`: if given project doesn't exist
