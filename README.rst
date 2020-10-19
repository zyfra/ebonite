.. image:: ebonite.jpg
.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs| |slack|
    * - tests
      - | |build| |coveralls|
    * - package
      - | |version| |wheel| |downloads| |supported-versions|
        | |commits-since|

.. |docs| image:: https://readthedocs.org/projects/ebonite/badge/?style=flat
    :target: https://readthedocs.org/projects/ebonite
    :alt: Documentation Status

.. |build| image:: https://github.com/zyfra/ebonite/workflows/tox/badge.svg
    :alt: Actions Status
    :target: https://github.com/zyfra/ebonite/actions

.. |requires| image:: https://requires.io/github/zyfra/ebonite/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/zyfra/ebonite/requirements/?branch=master

.. |coveralls| image:: https://coveralls.io/repos/github/zyfra/ebonite/badge.svg?branch=master
    :alt: Coverage Status
    :target: https://coveralls.io/r/zyfra/ebonite

.. |codecov| image:: https://codecov.io/github/zyfra/ebonite/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/zyfra/ebonite

.. |landscape| image:: https://landscape.io/github/zyfra/ebonite/master/landscape.svg?style=flat
    :target: https://landscape.io/github/zyfra/ebonite/master
    :alt: Code Quality Status

.. |version| image:: https://img.shields.io/pypi/v/ebonite.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/ebonite

.. |downloads| image:: https://pepy.tech/badge/ebonite
    :alt: PyPI downloads
    :target: https://pepy.tech/project/ebonite

.. |slack| image:: https://img.shields.io/badge/ODS-slack-red
    :alt: ODS slack channel
    :target: https://app.slack.com/client/T040HKJE3/CR1K8N2KA

.. |commits-since| image:: https://img.shields.io/github/commits-since/zyfra/ebonite/v0.7.0.svg
    :alt: Commits since latest release
    :target: https://github.com/zyfra/ebonite/compare/v0.7.0...dev

.. |wheel| image:: https://img.shields.io/pypi/wheel/ebonite.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/ebonite

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/ebonite.svg
    :alt: Supported versions
    :target: https://pypi.org/project/ebonite

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/ebonite.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/ebonite


.. end-badges


Ebonite is a machine learning lifecycle framework.
It allows you to persist your models and reproduce them (as services or in general).

Installation
============

::

    pip install ebonite

Quickstart
=============

Before you start with Ebonite you need to have your model.
This could be a model from your favorite library (list of supported libraries is below) or
just a custom Python function working with typical machine learning data.

.. code-block:: python

  import numpy as np
  def clf(data):
    return (np.sum(a, axis=-1) > 1).astype(np.int32)

Moreover, your custom function can wrap a model from some library.
This gives you flexibility to use not only pure ML models but rule-based ones (e.g., as a service stub at project start)
and hybrid (ML with pre/postprocessing) ones which are often applied to solve real world problems.

When a model is prepared you should create an Ebonite client.

.. code-block:: python

  from ebonite import Ebonite
  ebnt = Ebonite.local()

Then create a task and push your model object with some sample data.
Sample data is required for Ebonite to determine structure of inputs and outputs for your model.

.. code-block:: python

   task = ebnt.get_or_create_task('my_project', 'my_task')
   model = task.create_and_push_model(clf, test_x, 'my_clf')

You are awesome! Now your model is safely persisted in a repository.

Later on in other Python process you can load your model from this repository and do some wonderful stuff with it,
e.g., create a Docker image named `my_service` with an HTTP service wrapping your model.

.. code-block:: python

  from ebonite import Ebonite
  ebnt = Ebonite.local()
  task = ebnt.get_or_create_task('my_project', 'my_task')
  model = client.get_model('my_clf', task)
  client.build_image('my_service', model)

Check out examples (in `examples <examples/>`_  directory) and documentation to learn more.


Documentation
=============
... is available `here <https://ebonite.readthedocs.io/en/latest/>`_

Examples
========
... are available in this `folder </examples/>`_.
Here are some of them:

* `Jupyter Notebook guide </examples/notebook_tutorial/ebonite_tutorial.ipynb>`_
* `Scikit-learn guide </examples/sklearn_model/>`_
* `TensorFlow 2.0 </examples/tensorflow_v2_example/>`_
* etc.

Supported libraries and repositories
====================================

* Models

  * your arbitrary Python function

  * scikit-learn

  * TensorFlow (1.x and 2.x)

  * XGBoost

  * LightGBM

  * PyTorch

  * CatBoost

* Model input / output data

  * NumPy

  * pandas

  * images

* Model repositories

  * in-memory

  * local filesystem

  * SQLAlchemy

  * Amazon S3

* Serving

  * Flask

  * aiohttp

Create an issue if you need support for something other than that!


Contributing
============

Read `this <CONTRIBUTING.rst>`_
