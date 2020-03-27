Instances
=========

Get list of instances
---------------------

Request
^^^^^^^

.. code-block::

  GET /instances?image_id=1&environment_id=1

* `image_id`: id of image to get instances for
* `environment_id`: id of environment to get instances for

Response
^^^^^^^^

* `200`:

.. code-block:: json

  [
    {
      "name": "first instance",
      "id": 1,
      "image_id": 1,
      "environment_id": 1,
      "params": {
        "name": "yellow submarine",
        "ports_mapping": {"9000": 80},
        "type": "ebonite.build.docker.DockerContainer"
      },
      "status": "ok|failed",
      "author": "user_name",
      "creation_date": "1970-01-01 00:00:00.000000 "
    }
  ]

Get instance
------------

Request
^^^^^^^

.. code-block::

  GET /instances/<:id>

* `id`: id of instance to get

Response
^^^^^^^^

* `200`:

.. code-block:: json

  {
    "name": "first instance",
    "id": 1,
    "image_id": 1,
    "environment_id": 1,
    "params": {
      "name": "yellow submarine",
      "ports_mapping": {"9000": 80},
      "type": "ebonite.build.docker.DockerContainer"
    },
    "status": "ok|failed",
    "author": "user_name",
    "creation_date": "1970-01-01 00:00:00.000000 "
  }

* `404`: if given instance doesn't exist


Run instance
------------

Request
^^^^^^^

.. code-block::

  POST /instances

.. code-block:: json

  {
    "name": "first instance",
    "image_id": 1,
    "environment_id": 1,
    "params": {
      "name": "yellow submarine",
      "ports_mapping": {"9000": 80},
      "type": "ebonite.build.docker.DockerContainer"
    }
  }

Response
^^^^^^^^^^^^^^

* `201`:

.. code-block:: json

  {
    "name": "first instance",
    "id": 1,
    "image_id": 1,
    "environment_id": 1,
    "params": {
      "name": "yellow submarine",
      "ports_mapping": {"9000": 80},
      "type": "ebonite.build.docker.DockerContainer"
    },
    "status": "ok|failed",
    "author": "user_name",
    "creation_date": "1970-01-01 00:00:00.000000 "
  }

* `400`: if instance with given name, image and environment already exists


Update instance
---------------

Request
^^^^^^^

.. code-block::

  PATCH /instances/<:id>

* `id`: id of instance to update

.. code-block:: json

  {
    "name": "first instance"
  }

Response
^^^^^^^^^^^^^^

* `204`: OK
* `404`: if given instance doesn't exist


Delete instance
---------------

Request
^^^^^^^

.. code-block::

  DELETE /instances/<:id>

* `id`: id of instance to delete

Response
^^^^^^^^^^^^^^

* `204`: OK
* `404`: if given instance doesn't exist
