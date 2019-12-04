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

.. |coveralls| image:: https://coveralls.io/repos/zyfra/ebonite/badge.svg?branch=HEAD&service=github
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

.. |commits-since| image:: https://img.shields.io/github/commits-since/zyfra/ebonite/v0.3.1.svg
    :alt: Commits since latest release
    :target: https://github.com/zyfra/ebonite/compare/v0.3.1...master

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

First, create a Ebonite client.

.. code-block:: python

  from ebonite import Ebonite
  ebnt = Ebonite.local()

Second, create a task and push your model object with some sample data.

.. code-block:: python

   task = ebnt.get_or_create_task('my_project', 'my_task')
   model = task.create_and_push_model(clf, test_x, 'my_sklearn_clf')

You are awesome! Now you can load you model from this repo and do other wonderful stuff with it, for
example create a docker image.

Check out examples and documentation to learn more.


Documentation
=============
... is available `here <https://ebonite.readthedocs.io/en/latest/>`_

Supported libraries and repositories
====================================

* Machine Learning

  * scikit-learn

  * TensorFlow < 2

  * XGBoost

  * LightGBM

  * PyTorch

  * CatBoost

* Data

  * NumPy

  * pandas

  * images

* Repositories

  * SQLAlchemy

  * Amazon S3

* Serving

  * Flask



Contributing
============

Read `this <https://github.com/zyfra/ebonite/blob/master/CONTRIBUTING.rst>`_