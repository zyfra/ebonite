********
HTTP API
********

Projects
========

Get projects names
------------------

Request URL
^^^^^^^^^^^

.. code-block::

  GET /projects

Response body
^^^^^^^^^^^^^

.. code-block:: json

  [
    "first project name",
    "...",
    "last project name"
  ]

Get project details
-------------------

Request URL
^^^^^^^^^^^

.. code-block::

  GET /projects/<:pname>

Request arguments
^^^^^^^^^^^^^^^^^

* `pname` - project name

Response body
^^^^^^^^^^^^^

.. code-block:: json

  {
    "name": "project name",
    "author": "project author name",
    "creation_date": "project creation date as timestamp (seconds since epoch)"
  }

Response codes
^^^^^^^^^^^^^^

* `404` if such project doesn't exist

Delete project
--------------

Request URL
^^^^^^^^^^^

.. code-block::

  DELETE /projects/<:pname>

Request arguments
^^^^^^^^^^^^^^^^^

* `pname` - project name
* `cascade` - (optional) delete cascadely (with referenced tasks, models, etc)

Response codes
^^^^^^^^^^^^^^

* `400` if `cascade` is not `1` and given project has tasks in it
* `404` if such project doesn't exist


Tasks
=====

Get project tasks names
-----------------------

Request URL
^^^^^^^^^^^

.. code-block::

  GET /projects/<:pname>/tasks

Request arguments
^^^^^^^^^^^^^^^^^

* `pname` - project name

Response body
^^^^^^^^^^^^^

.. code-block:: json

  [
    "first task name",
    "...",
    "last task name"
  ]

Response codes
^^^^^^^^^^^^^^

* `404` if such project doesn't exist

Get task details
----------------

Request URL
^^^^^^^^^^^

.. code-block::

  GET /projects/<:pname>/tasks/<:tname>

Request arguments
^^^^^^^^^^^^^^^^^

* `pname` - project name
* `tname` - task name

Response body
^^^^^^^^^^^^^

.. code-block:: json

  {
    "project": "task project name",
    "name": "task name",
    "author": "task author name",
    "creation_date": "task creation date as timestamp (seconds since epoch)"
  }

Response codes
^^^^^^^^^^^^^^

* `404` if such project or task doesn't exist

Delete task
-----------

Request URL
^^^^^^^^^^^

.. code-block::

  DELETE /projects/<:pname>/tasks/<:tname>

Request arguments
^^^^^^^^^^^^^^^^^

* `pname` - project name
* `tname` - task name
* `cascade` - (optional) if `1` then delete cascadely (with referenced models, etc)

Response codes
^^^^^^^^^^^^^^

* `400` if `cascade` is not `1` and given task has models in it
* `404` if such project or task doesn't exist

Models
======

Get task models names
---------------------

Request URL
^^^^^^^^^^^

.. code-block::

  GET /projects/<:pname>/tasks/<:tname>/models

Request arguments
^^^^^^^^^^^^^^^^^

* `pname` - project name
* `tname` - task name
* `tags` - (optional) comma-separated list of tags which results are expected to have

Response body
^^^^^^^^^^^^^

.. code-block:: json

  [
    "first model name",
    "...",
    "last model name"
  ]

Response codes
^^^^^^^^^^^^^^

* `404` if such project or task doesn't exist

Get model details
-----------------

Request URL
^^^^^^^^^^^

.. code-block::

  GET /projects/<:pname>/tasks/<:tname>/models/<:mname>

Request arguments
^^^^^^^^^^^^^^^^^

* `pname` - project name
* `tname` - task name
* `mname` - model name

Response body
^^^^^^^^^^^^^

.. code-block:: json

  {
    "project": "model project name",
    "task": "model task name",
    "name": "model name",
    "author": "model author name",
    "creation_date": "model creation date as timestamp (seconds since epoch)",
    "tags": [
      "first model tag",
      "...",
      "last model tag"
    ],
    "artifacts": [
      "first model artifact name",
      "...",
      "last model artifact name"
    ]
  }

Response codes
^^^^^^^^^^^^^^

* `404` if such project, task or model doesn't exist

Get model artifact content
--------------------------

Request URL
^^^^^^^^^^^

.. code-block::

  GET /projects/<:pname>/tasks/<:tname>/models/<:mname>/artifacts/<:aname>

Request arguments
^^^^^^^^^^^^^^^^^

* `pname` - project name
* `tname` - task name
* `mname` - model name
* `aname` - artifact name

Response body
^^^^^^^^^^^^^

Artifact content

Response codes
^^^^^^^^^^^^^^

* `404` if such project, task, model or artifact doesn't exist

Update models tags
------------------

Request URL
^^^^^^^^^^^

.. code-block::

  PUT /projects/<:pname>/tasks/<:tname>/models/<:mname>/tags

Request arguments
^^^^^^^^^^^^^^^^^

* `pname` - project name
* `tname` - task name
* `mname` - model name

Request body
^^^^^^^^^^^^^

.. code-block:: json

  [
    "first model tag",
    "...",
    "last model tag"
  ]

Response codes
^^^^^^^^^^^^^^

* `404` if such project, task or model doesn't exist

Delete model
------------

Request URL
^^^^^^^^^^^

.. code-block::

  DELETE /projects/<:pname>/tasks/<:tname>/models/<:mname>

Request arguments
^^^^^^^^^^^^^^^^^

* `pname` - project name
* `tname` - task name
* `mname` - model name

Response codes
^^^^^^^^^^^^^^

* `404` if such project, task or model doesn't exist


Images
======

Get task images
---------------

Request URL
^^^^^^^^^^^

.. code-block::

  GET /projects/<:pname>/tasks/<:tname>/images

Request arguments
^^^^^^^^^^^^^^^^^

* `pname` - project name
* `tname` - task name

Response body
^^^^^^^^^^^^^

.. code-block:: json

  [
    {
      "image": "first image name in Docker registry",
      "model": "name of model for which first image is built"
    },
    {
      "image": "last image name in Docker registry",
      "model": "name of model for which last image is built"
    }
  ]

Response codes
^^^^^^^^^^^^^^

* `404` if such project or task doesn't exist

Build image for model
---------------------

Request URL
^^^^^^^^^^^

.. code-block::

  PUT /projects/<:pname>/tasks/<:tname>/models/<:mname>/image/<:iname>

Request arguments
^^^^^^^^^^^^^^^^^

* `pname` - project name
* `tname` - task name
* `mname` - model name
* `iname` - image name

Response codes
^^^^^^^^^^^^^^

* `400` if given image already exists and isn't related to given model
* `404` if such project, task or model doesn't exist


Environments
============




Instances
=========


