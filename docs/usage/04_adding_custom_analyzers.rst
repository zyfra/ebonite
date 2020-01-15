==============================
Adding custom analyzers
==============================

To add support for new ML library or new types of data, you need to implement a hook for analyzer and the type it produces.

Model support
-------------

For models, you need to implement :class:`~ebonite.core.analyzer.model.ModelHook` and :class:`~ebonite.core.objects.wrapper.ModelWrapper`.
:class:`~ebonite.core.analyzer.model.ModelHook` should check an object if it is the object that you want to add support for (for example, check it's base module to be the library you providing support for). Result of :meth:`~ebonite.core.analyzer.model.ModelHook.process` must be an instance of :class:`~ebonite.core.objects.wrapper.ModelWrapper` implementation you provided.
In :class:`~ebonite.core.objects.wrapper.ModelWrapper` you must implement methods :meth:`~ebonite.core.objects.wrapper.ModelWrapper._dump`, :meth:`~ebonite.core.objects.wrapper.ModelWrapper._load` and :meth:`~ebonite.core.objects.wrapper.ModelWrapper._exposed_methods_mapping`.

Data type support
-----------------

For data types, you need to implement :class:`~ebonite.core.analyzer.dataset.DatasetHook` and :class:`~ebonite.core.objects.dataset_type.DatasetType`.
:class:`~ebonite.core.analyzer.dataset.DatasetHook` should check an object if it is the object that you want to add support for (for example, check it's base module to be the library you providing support for). Result of :meth:`~ebonite.core.analyzer.dataset.DatasetHook.process` must be an instance of :class:`~ebonite.core.objects.dataset_type.DatasetType` implementation you provided.
In :class:`~ebonite.core.objects.dataset_type.DatasetType` you must implement methods :meth:`~ebonite.core.objects.dataset_type.DatasetType.serialize`, :meth:`~ebonite.core.objects.dataset_type.DatasetType.deserialize` and :meth:`~ebonite.core.objects.dataset_type.DatasetType.get_spec`.

Tips
----

If you want better understating of what is going on, check some of the extensions, for example :mod:`~ebonite.ext.lightgbm` provides these implementations for both model and data type.

Also, check out :mod:`~ebonite.core.analyzer` for some convenient mixins.