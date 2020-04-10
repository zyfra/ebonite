Images
======

Get list of images
------------------

Request
^^^^^^^

.. code-block::

  GET /images?model_id=1

* `model_id`: id of model to get images for

Response
^^^^^^^^

* `200`:

.. code-block:: json

  [
    {
      "name": "task_one/image_name:latest",
      "id": 1,
      "model_id": 1,
      "author": "user_name",
      "creation_date": "1970-01-01 00:00:00.000000 ",
      "params": {
        "type": "ebonite.build.docker.DockerImage",
        "name": "image_name",
        "tag": "latest",
        "repository": "task_one",
        "registry": {"type": "ebonite.build.docker.DefaultDockerRegistry"}
      }
    }
  ]

* `404`: if given model doesn't exist


Get image
---------

Request
^^^^^^^

.. code-block::

  GET /images/<:id>

* `id`: id of image to get

Response
^^^^^^^^

* `200`:

.. code-block:: json

  {
    "name": "task_one/image_name:latest",
    "id": 1,
    "model_id": 1,
    "author": "user_name",
    "creation_date": "1970-01-01 00:00:00.000000 ",
    "params": {
      "type": "ebonite.build.docker.DockerImage",
      "name": "image_name",
      "tag": "latest",
      "repository": "task_one",
      "registry": {"type": "ebonite.build.docker.DefaultDockerRegistry"}
    }
  }

* `404`: if given image doesn't exist


Build image
-----------

Request
^^^^^^^

.. code-block::

  POST /images

.. code-block:: json

  {
    "name": "image_name",
    "model_id": 1
  }

Response
^^^^^^^^^^^^^^

* `201`:

.. code-block:: json

  {
    "name": "image_name:latest",
    "id": 1,
    "model_id": 1,
    "author": "user_name",
    "creation_date": "1970-01-01 00:00:00.000000 ",
    "params": {
      "type": "ebonite.build.docker.DockerImage",
      "name": "image_name",
      "tag": "latest",
      "registry": {"type": "ebonite.build.docker.DefaultDockerRegistry"}
    }
  }

* `400`: if image with given name already exists for given model


Update image
------------

Request
^^^^^^^

.. code-block::

  PATCH /images/<:id>

* `id`: id of image to update

.. code-block:: json

  {
    "name": "first image"
  }

Response
^^^^^^^^^^^^^^

* `204`: OK
* `404`: if given image doesn't exist


Delete image
------------

Request
^^^^^^^

.. code-block::

  DELETE /images/<:id>?cascade=1

* `id`: id of image to delete
* `cascade`: (optional, default - `0`) delete cascadely (stops and deletes running instances of image)

Response
^^^^^^^^^^^^^^

* `204`: OK
* `400`: if `cascade` is not `1` and there is running instances of given image
* `404`: if given image doesn't exist
