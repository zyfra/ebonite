============
Ebonite Core
============

This module is responsible for model understanding and
model persisting.
If you just use vanilla ebonite, this is mainly what
you are working with.

Main model understanding API abstractions are

* :class:`~ebonite.core.analyzer.dataset.DatasetHook` - hook for dataset understanding

* :class:`~ebonite.core.objects.dataset_type.DatasetType` - dataset descriptor

* :class:`~ebonite.core.analyzer.model.ModelHook` - hook for model understanding

* :class:`~ebonite.core.objects.model_wrapper.ModelWrapper` - model wrapper for different ml libraries

Main model persisting abstractions are

* :class:`~ebonite.repository.MetadataRepository` - Repository to store model metadata (like sql database)

* :class:`~ebonite.repository.ArtifactRepository` - Repository to store model artifacts (like s3 or nexus)

