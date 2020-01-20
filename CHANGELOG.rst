Changelog
=========

Current release candidate
-------------------------

* Fixed bug with deleting models from tasks

0.3.3 (2020-01-10)
------------------

* Eliminated tensorflow warnings. Added more tests for providers/loaders. Fixed bugs in multi-model provider/builder.
* Improved documentation
* Eliminate useless "which docker" check which fails on Windows hosts
* Perform redirect from / to Swagger API docs in Flask server
* Support for predict_proba method in ML model
* Do not fix first dimension size for numpy arrays and torch tensors
* Support for Pytorch JIT (TorchScript) models
* Bump tensorflow from 1.14.0 to 1.15.0
* Added more tests

0.3.2 (2019-12-04)
------------------

* Multi-model interface bug fixes

0.3.1 (2019-12-04)
------------------

* Minor bug fixes

0.3.0 (2019-11-27)
------------------

* Added support for LightGBM models
* Added support for XGBoost models
* Added support for PyTorch models
* Added support for CatBoost models
* Added uwsgi server for flask containers

0.2.1 (2019-11-19)
------------------

* Minor bug fixes

0.2.0 (2019-11-14)
------------------

* First release on PyPI.
