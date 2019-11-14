from abc import abstractmethod
from functools import wraps
from typing import Union

from pyjackson import read, write
from pyjackson.utils import resolve_subtype

from ebonite.core import errors
from ebonite.core.objects import core
from ebonite.repository.artifact import ArtifactRepository
from ebonite.repository.artifact.inmemory import InMemoryArtifactRepository
from ebonite.repository.metadata import MetadataRepository
from ebonite.repository.metadata.base import ProjectVar, TaskVar
from ebonite.repository.metadata.local import LocalMetadataRepository


class Ebonite:
    """Main entry point for ebonite

    This is the client for Ebonite API. It can save, load and build Models, Tasks and Projects.
    Ebonite instance can be obtained from factory methods like :meth:`~ebonite.Ebonite.local` for local client,
    :meth:`~ebonite.Ebonite.inmemory` for inmemory client.

    You can save client config with :meth:`~ebonite.Ebonite.save_client_config` and
    later restore it with :meth:`~ebonite.Ebonite.from_config_file`

    :param meta_repo: :class:`~ebonite.repository.MetadataRepository` instance to save metadata
    :param artifact_repo: :class:`~ebonite.repository.ArtifactRepository` instance to save artifacts
    """

    def __init__(self, meta_repo: MetadataRepository, artifact_repo: ArtifactRepository):
        self.meta_repo = meta_repo
        self.artifact_repo = artifact_repo

    def push_model(self, model: 'core.Model', task: 'core.Task' = None) -> 'core.Model':
        """
        Pushes :py:class:`~ebonite.core.objects.Model` instance into metadata and artifact repositories

        :param model: :py:class:`~ebonite.core.objects.Model` instance
        :param task: :py:class:`~ebonite.core.objects.Task` instance to save model to. Optional if model already has task
        :return: same saved :py:class:`~ebonite.core.objects.Model` instance
        """
        if model.id is not None:
            raise errors.ExistingModelError(model)
        if task is not None:
            if model.task_id is not None:
                if model.task_id != task.id:
                    raise ValueError('This model is already in task {}'.format(model.task_id))
            else:
                model.task = task

        model = self.meta_repo.create_model(model)  # save model to get model.id
        try:
            self.artifact_repo.push_artifacts(model)
        except:  # noqa
            self.meta_repo.delete_model(model)
            raise

        model = self.meta_repo.save_model(model)
        return model

    def get_or_create_task(self, project_name, task_name) -> 'core.Task':
        """
        Load task from repository if it exists and create it otherwise

        :param project_name: project name to load task from
        :param task_name: task name to load
        :return: :py:class:`~ebonite.core.objects.Task` instance
        """
        task = self.meta_repo.get_or_create_task(project_name, task_name)
        task.bind_artifact_repo(self.artifact_repo)
        return task

    def get_model(self, model_name: str, task: TaskVar, project: ProjectVar = None,
                  load_artifacts: bool = True) -> 'core.Model':
        """
        Load model from repository

        :param model_name: model name to load
        :param task: :py:class:`~ebonite.core.objects.Task` instance or task name to load model from
        :param project: :py:class:`~ebonite.core.objects.Project` instance or project name to load task from
        :param load_artifacts: if True, load model artifact into wrapper
        :return: :py:class:`~ebonite.core.objects.Model` instance
        """
        model: 'core.Model' = self.meta_repo.get_model_by_name(model_name, task, project)
        if model is not None and load_artifacts:
            model.load()
        return model

    @abstractmethod
    def build_service(self, name: str, model: 'core.Model', **kwargs):
        pass

    @abstractmethod
    def run_service(self, name: str, ports_mapping, detach: bool = True):
        pass

    def build_and_run_service(self, name: str, model: 'core.Model', ports_mapping=None, detach: bool = True, **kwargs):
        self.build_service(name, model, **kwargs)
        self.run_service(name, ports_mapping, detach)

    @classmethod
    def local(cls, path=None, clear=False):
        """
        Get an instance of :class:`~ebonite.client.local.LocalClient`
        """
        from ebonite.client.local import LocalClient
        return LocalClient(path, clear)

    @classmethod
    def inmemory(cls):
        """
        Get an instance of :class:`~ebonite.Ebonite` with inmemory repositories
        """
        return Ebonite(LocalMetadataRepository(), InMemoryArtifactRepository())

    @classmethod
    def custom_client(cls, metadata: Union[str, MetadataRepository], artifact: Union[str, ArtifactRepository],
                      meta_kwargs: dict = None, artifact_kwargs: dict = None):
        """
        Create custom Ebonite client from metadata and artifact repositories.

        :param metadata: :class:`~ebonite.repository.MetadataRepository` instance or pyjackson subtype type name
        :param artifact: :class:`~ebonite.repository.ArtifactRepository` instance or pyjackson subtype type name
        :param meta_kwargs: kwargs for metadata repo __init__ if subtype type name was provided
        :param artifact_kwargs: kwargs for artifact repo __init__ if subtype type name was provided
        :return: :class:`~ebonite.Ebonite` instance
        """
        if isinstance(metadata, str):
            metadata_type = resolve_subtype(MetadataRepository, {'type': metadata})
            meta_kwargs = meta_kwargs or {}
            metadata = metadata_type(**meta_kwargs)

        if isinstance(artifact, str):
            artifact_type = resolve_subtype(ArtifactRepository, {'type': artifact})
            artifact_kwargs = artifact_kwargs or {}
            artifact = artifact_type(**artifact_kwargs)

        return Ebonite(metadata, artifact)

    @classmethod
    def from_config_file(cls, filepath):
        """
        Read and create Ebonite instance from config file
        :param filepath: path to read config from
        :return: :class:`~ebontie.Ebonite` instance
        """
        return read(filepath, Ebonite)

    def save_client_config(self, filepath):
        """
        Save current client config to a file
        :param filepath: path to file
        """
        write(filepath, self, Ebonite)


def ebonite_client(name, force=False):
    """Decorator for registering Ebonite child implementations as factory classmethods on :class:`ebonite.Ebonite`"""
    def inner(cls):
        if hasattr(Ebonite, name):
            if force:
                raise ValueError(f'Cant register client impl with name {name}: it shadows {getattr(Ebonite, name)}')
            else:
                return cls

        @wraps(cls.__init__)
        def factory(c, *args, **kwargs):
            return cls(*args, **kwargs)

        factory.__name__ = name
        setattr(Ebonite, name, classmethod(factory))
        return cls

    return inner
