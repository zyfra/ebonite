Environments
============

Get list of environments
------------------------

Request
^^^^^^^

.. code-block::

  GET /environments

Response
^^^^^^^^

* `200`:

.. code-block:: json

  [
    {
      "name": "first environment",
      "id": 1,
      "author": "user_name",
      "creation_date": "1970-01-01 00:00:00.000000 ",
      "params": {
        "host": "localhost:1234",
        "type": "ebonite.build.docker.DockerHost"
      }
    }
  ]

Get environment
---------------

Request
^^^^^^^

.. code-block::

  GET /environments/<:id>

* `id`: id of environment to get

Response
^^^^^^^^

* `200`:

.. code-block:: json

  {
    "name": "first environment",
    "id": 1,
    "author": "user_name",
    "creation_date": "1970-01-01 00:00:00.000000 ",
    "params": {
      "host": "localhost:1234",
      "type": "ebonite.build.docker.DockerHost"
    }
  }

* `404`: if given environment doesn't exist


Create environment
------------------

Request
^^^^^^^

.. code-block::

  POST /environments

.. code-block:: json

  {
    "name": "first environment",
    "params": {
      "host": "localhost:1234",
      "type": "ebonite.build.docker.DockerHost"
    }
  }

Response
^^^^^^^^^^^^^^

* `201`:

.. code-block:: json

  {
    "name": "first environment",
    "id": 1,
    "author": "user_name",
    "creation_date": "1970-01-01 00:00:00.000000 ",
    "params": {
      "host": "localhost:1234",
      "type": "ebonite.build.docker.DockerHost"
    }
  }

* `400`: if environment with given name already exists


Update environment
------------------

Request
^^^^^^^

.. code-block::

  PATCH /environments/<:id>

* `id`: id of environment to update

.. code-block:: json

  {
    "name": "first environment"
  }

Response
^^^^^^^^^^^^^^

* `204`: OK
* `404`: if given environment doesn't exist


Delete environment
------------------

Request
^^^^^^^

.. code-block::

  DELETE /environments/<:id>?cascade=1

* `id`: id of environment to delete
* `cascade`: (optional, default - `0`) delete cascadely (with instances running in given environment)

Response
^^^^^^^^^^^^^^

* `204`: OK
* `400`: if `cascade` is not `1` and given environment has running instances in it
* `404`: if given environment doesn't exist
