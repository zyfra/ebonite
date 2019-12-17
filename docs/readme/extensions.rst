==================
Ebonite Extensions
==================

Ebonite can be extended in any way, just write the code.
But there are already some builtin extensions that provide integrations
with different python libraries. Those extensions loads automatically.

.. note:: Some of them loads if you have corresponding libraries installed, some of them loads only if you directly import corresponding library.

Extensions are loaded via :class:`~ebonite.ext.ext_loader.ExtensionLoader`.

Here are builtin extensions:

* :mod:`~ebonite.ext.catboost` - support for CatBoost library
* :mod:`~ebonite.ext.flask` - :class:`~ebonite.ext.flask.server.FlaskServer` server and helper function :func:`~ebonite.ext.flask.build_model_flask_docker`
* :mod:`~ebonite.ext.imageio` - support for working with image payload
* :mod:`~ebonite.ext.lightgbm` - support for LightGBM library
* :mod:`~ebonite.ext.numpy` - support for numpy data types
* :mod:`~ebonite.ext.pandas` - support for pandas data types
* :mod:`~ebonite.ext.s3` - s3 :class:`~ebonite.repository.ArtifactRepository` implementation
* :mod:`~ebonite.ext.sklearn` - support for scikit-learn models
* :mod:`~ebonite.ext.sqlalchemy` - sql :class:`~ebonite.repository.MetadataRepository` implementation
* :mod:`~ebonite.ext.tensorflow` - support for tensorflow models
* :mod:`~ebonite.ext.torch` - support for torch models
* :mod:`~ebonite.ext.xgboost` - support for xgboost models

