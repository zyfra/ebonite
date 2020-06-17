Changelog
=========

Current release candidate
-------------------------

0.6.2 (2020-06-18)
------------------

* Minor bugfixes

0.6.1 (2020-06-15)
------------------

* Deleted accidental debug 'print' call :/

0.6.0 (2020-06-12)
------------------

* Prebuilt flask server images for faster image build
* More and better methods in Ebonite client
* Pipelines - chain Models methods into one Model-like objects
* Refactioring of image and instance API
* Rework of pandas DatasetType: now with column types, even non-primitive (e.g. datetimes)
* Helper functions for stanalone docker build/run
* Minor bugfixes and features


0.5.2 (2020-05-16)
------------------

* Fixed dependency inspection to include wrapper dependencies
* Fixed s3 repo to fail with subdirectories
* More flexible way to add parameters for instance running (e.g. docker run arguments)
* Added new type of Requirement to represent unix packages - for example, libgomp for xgboost
* Minor tweaks

0.5.1 (2020-04-16)
------------------

* Minor fixes and examples update

0.5.0 (2020-04-10)
------------------

* Built Docker images and running Docker containers along with their metadata are now persisted in metadata repository
* Added possibility to track running status of Docker container via Ebonite client
* Implemented support for pushing built images to remote Docker registry
* Improved testing of metadata repositories and Ebonite client and fixed discovered bugs in them
* Fixed bug with failed transactions not being rolled back
* Fixed bug with serialization of complex models some component of which could not be pickled
* Decomposed model IO from model wrappers
* bytes are now used for binary datasets instead of file-like objects
* Eliminated build_model_flask_docker in favor of Server-driven abstraction
* Sped up PickleModelIO by avoiding ModelAnalyzer calls for non-model objects
* Sped up Model.create by calling model methods with given input data just once
* Dataset types and model wrappers expose their runtime requirements

0.4.0 (2020-02-17)
------------------

* Implemented asyncio-based server via aiohttp library
* Implemented support for Tensorflow 2.x models
* Changed default type of base python docker image to "slim"
* Added 'description' and 'params' fields to Model. 'description' is a text field and 'params' is a dict with arbitrary keys
* Fixed bug with building docker image with different python version that the Model was created with

0.3.5 (2020-01-31)
------------------

* Fixed critical bug with wrapper_meta

0.3.4 (2020-01-31)
------------------

* Fixed bug with deleting models from tasks
* Support working with model meta without requiring installation of all model dependencies
* Added region argument for s3 repository
* Support for delete_model in Ebonite client
* Support for force flag in delete_model which deletes model even if artifacts could not be deleted

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
