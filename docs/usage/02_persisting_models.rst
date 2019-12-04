====================
Persisting Models
====================

After you got yourself a :class:`~ebonite.core.objects.core.Model` instance,
you can persist it to a repository. For that, you need a
:class:`~ebonite.core.objects.core.Task` instance to add model to.
:class:`~ebonite.core.objects.core.Task` is a container for models trained for
the same problem. For example, if you did some experiments, you'll push each
experiment as a :class:`~ebonite.core.objects.core.Model` to the same
:class:`~ebonite.core.objects.core.Task`.

Each :class:`~ebonite.core.objects.core.Task` belongs to a
:class:`~ebonite.core.objects.core.Project`, which is just container for tasks.


To create and persist projects, tasks and models, you need ebonite client, which
is and instance of :class:`~ebonite.Ebonite`. Ebonite client is a composition of
two repository implementations: :class:`~ebonite.repository.MetadataRepository`
and :class:`~ebonite.repository.ArtifactRepository`.

:class:`~ebonite.repository.MetadataRepository` is where all the metadata goes,
you look at it as a SQL database (we actually have an sql implementation).

:class:`~ebonite.repository.ArtifactRepository` is where all model binaries go.
It can be any file storage like s3, ftp and so on.


You can manually create client with ``Ebonite(metadata_repository, artifact_repository)``,
or use one of the factory methods: :func:`~ebonite.Ebonite.local` for local client
(metadata will just a json file, and artifacts will be just plain files in
local file system), :func:`~ebonite.Ebonite.inmemory` for in-memory repositories.

Also there is a :func:`~ebonite.Ebonite.custom_client` to setup your own repositories.

You can use ``MetadataRepository.type`` value as for metadata argument.

Available implementations:

* local - :class:`~ebonite.repository.metadata.local.LocalMetadataRepository`
* sqlalchemy - :class:`~ebonite.ext.sqlalchemy.SQLAlchemyMetaRepository`

You can use ``ArtifactRepository.type`` value as for artifact argument.

Available implementations:

* local - :class:`~ebonite.repository.artifact.local.LocalArtifactRepository`
* inmemory - :class:`~ebonite.repository.artifact.inmemory.InMemoryArtifactRepository`
* s3 - :class:`~ebonite.ext.s3.artifact.S3ArtifactRepository`


Let's create local ebonite client:

.. literalinclude:: ../../examples/sklearn_model/model_train.py
   :linenos:
   :language: python
   :lines: 25
..

Now, create project and task for our model:

.. literalinclude:: ../../examples/sklearn_model/model_train.py
   :linenos:
   :language: python
   :lines: 28
..

And push model into it:

.. literalinclude:: ../../examples/sklearn_model/model_train.py
   :linenos:
   :language: python
   :lines: 32
..

Now, if you take a look at ``.ebonite`` directory, you'll find a
``metadata.json`` file with your project, task and model.

Congratulations, you persisted your model. This process is absolutely
the same if you choose other repository implementations. Take a look at
`examples/remote_example <https://github.com/zyfra/ebonite/tree/master/examples/remote_example>`_
for an example with remote repositories.
