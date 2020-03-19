import os
import shutil
from typing import Union

from pyjackson import read, write
from pyjackson.utils import resolve_subtype

from ebonite.core.errors import ExistingModelError
from ebonite.core.objects import Image, Model, RuntimeEnvironment, RuntimeInstance, Task
from ebonite.repository.artifact import ArtifactRepository
from ebonite.repository.artifact.inmemory import InMemoryArtifactRepository
from ebonite.repository.artifact.local import LocalArtifactRepository
from ebonite.repository.metadata import MetadataRepository
from ebonite.repository.metadata.base import ProjectVar, TaskVar
from ebonite.repository.metadata.local import LocalMetadataRepository
from ebonite.utils.log import logger


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

    def push_model(self, model: Model, task: Task = None) -> Model:
        """
        Pushes :py:class:`~ebonite.core.objects.Model` instance into metadata and artifact repositories

        :param model: :py:class:`~ebonite.core.objects.Model` instance
        :param task: :py:class:`~ebonite.core.objects.Task` instance to save model to. Optional if model already has task
        :return: same saved :py:class:`~ebonite.core.objects.Model` instance
        """
        if model.id is not None:
            raise ExistingModelError(model)
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

    def delete_model(self, model: Model, force=False):
        """
        Deletes :py:class:`~ebonite.core.objects.Model` instance from metadata and artifact repositories

        :param model: model instance to delete
        :param force: whether model artifacts' deletion errors should be ignored, default is false
        """
        if model.artifact is not None:
            try:
                self.artifact_repo.delete_artifact(model)
            except:  # noqa
                if force:
                    logger.warning("Unable to delete artifacts associated with model: '%s'", model, exc_info=1)
                else:
                    raise

        self.meta_repo.delete_model(model)
        model.task_id = None

    def get_or_create_task(self, project_name: str, task_name: str) -> Task:
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
                  load_artifacts: bool = True) -> Model:
        """
        Load model from repository

        :param model_name: model name to load
        :param task: :py:class:`~ebonite.core.objects.Task` instance or task name to load model from
        :param project: :py:class:`~ebonite.core.objects.Project` instance or project name to load task from
        :param load_artifacts: if True, load model artifact into wrapper
        :return: :py:class:`~ebonite.core.objects.Model` instance
        """
        model: Model = self.meta_repo.get_model_by_name(model_name, task, project)
        if model is not None and load_artifacts:
            model.load()
        return model

    def build_service(self, name: str, model: Model, **kwargs) -> Image:
        """
        Builds image of model service and stores it to repository

        :param name: name of image to build
        :param model: model to wrap into service
        :return: :class:`~ebonite.core.objects.Image` instance representing built image
        """
        if 'server' not in kwargs:  # by default we use uwsgi flask server
            from ebonite.ext.flask.helpers import build_model_flask_docker
            kwargs = {k: v for k, v in kwargs.items() if k in {'force_overwrite', 'debug'}}
            image = build_model_flask_docker(name, model, **kwargs)
        else:
            from ebonite.build import build_model_docker
            image = build_model_docker(name, model, **kwargs)
        return self.meta_repo.create_image(image)

    def get_image(self, name: str, model: Model) -> Image:
        """
        Load image from repository

        :param name: image name to load
        :param model: :py:class:`~ebonite.core.objects.Model` instance to load image from
        :return: loaded :py:class:`~ebonite.core.objects.Image` instance
        """
        return self.meta_repo.get_image_by_name(name, model)

    def push_environment(self, environment: RuntimeEnvironment) -> RuntimeEnvironment:
        """
        Pushes runtime environment to repository

        :param environment: environment to push
        :return: same environment bound to repository
        """
        return self.meta_repo.create_environment(environment)

    def get_environment(self, name: str) -> RuntimeEnvironment:
        """
        Load runtime environment from repository

        :param name: name of environment to load
        :return: loaded :py:class:`~ebonite.core.objects.RuntimeEnvironment` instance
        """
        return self.meta_repo.get_environment_by_name(name)

    def run_service(self, name: str, image: Image, environment: RuntimeEnvironment = None, **kwargs) -> RuntimeInstance:
        """
        Runs model service and stores it to repository

        :param name: name of instance to run
        :param image: image to run instance from
        :param environment: environment to run instance in, if no given `localhost` is used
        :return: :class:`~ebonite.core.objects.RuntimeInstance` instance representing run instance
        """
        env_name = 'localhost'
        if environment is None:
            environment = self.get_environment(env_name)
        if environment is None:
            environment = self.push_environment(RuntimeEnvironment(env_name))

        params = {k: v for k, v in kwargs.items() if k in {'ports_mapping'}}

        instance = RuntimeInstance(name, params=params)
        instance.image = image
        instance.environment = environment
        instance = self.meta_repo.create_instance(instance)

        from ebonite.build import run_docker_img, DockerImage
        run_docker_img(name, DockerImage.from_core_image(image), environment.get_uri(),
                       detach=kwargs.get('detach', True), **params)

        return instance

    def build_and_run_service(self, name: str, model: Model, environment: RuntimeEnvironment = None,
                              **kwargs) -> RuntimeInstance:
        """
        Builds image of model service, immediately runs service and stores both image and instance to repository

        :param name: name of image and instance to be built and run respectively
        :param model: model to wrap into service
        :param environment: environment to run instance in, if no given `localhost` is used
        :return: :class:`~ebonite.core.objects.RuntimeInstance` instance representing run instance
        """
        image = self.build_service(name, model, **kwargs)
        return self.run_service(name, image, environment, **kwargs)

    def get_instance(self, name: str, image: Image, environment: RuntimeEnvironment) -> RuntimeInstance:
        """
        Loads service instance from repository

        :param name: name of instance to load
        :param image: image of instance to load
        :param environment: environment of instance to load
        :return: loaded :class:`~ebonite.core.objects.RuntimeInstance` instance
        """
        return self.meta_repo.get_instance_by_name(name, image, environment)

    def is_service_running(self, instance: RuntimeInstance) -> bool:
        """
        Checks whether instance is running

        :param instance: instance to check
        :return: "is running" flag
        """
        from ebonite.build import is_docker_container_running
        if not instance.has_meta_repo:
            # unbound instances could not be running: they are either not yet started or already stopped
            return False
        return is_docker_container_running(instance.name, instance.environment.get_uri())

    def stop_service(self, instance: RuntimeInstance):
        """
        Stops instance of model service and deletes it from repository

        :param instance: instance to stop
        :return: nothing
        """
        from ebonite.build import stop_docker_container
        stop_docker_container(instance.name, instance.environment.get_uri())

        self.meta_repo.delete_instance(instance)

    @classmethod
    def local(cls, path=None, clear=False) -> 'Ebonite':
        """
        Get an instance of :class:`~ebonite.Ebonite` that stores metadata and artifacts on local filesystem

        :param path: path to storage dir. If None, `.ebonite` dir is used
        :param clear: if True, erase previous data from storage
        """
        path = path or '.ebonite'
        if clear and os.path.exists(path):
            shutil.rmtree(path)
        meta_repo = LocalMetadataRepository(os.path.join(path, 'metadata.json'))
        artifact_repo = LocalArtifactRepository(os.path.join(path, 'artifacts'))
        return Ebonite(meta_repo, artifact_repo)

    @classmethod
    def inmemory(cls) -> 'Ebonite':
        """
        Get an instance of :class:`~ebonite.Ebonite` with inmemory repositories
        """
        return Ebonite(LocalMetadataRepository(), InMemoryArtifactRepository())

    @classmethod
    def custom_client(cls, metadata: Union[str, MetadataRepository], artifact: Union[str, ArtifactRepository],
                      meta_kwargs: dict = None, artifact_kwargs: dict = None) -> 'Ebonite':
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
    def from_config_file(cls, filepath) -> 'Ebonite':
        """
        Read and create Ebonite instance from config file

        :param filepath: path to read config from
        :return: :class:`~ebonite.Ebonite` instance
        """
        return read(filepath, Ebonite)

    def save_client_config(self, filepath):
        """
        Save current client config to a file

        :param filepath: path to file
        """
        write(filepath, self, Ebonite)
