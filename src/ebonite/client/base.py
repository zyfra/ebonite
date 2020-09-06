import os
import shutil
from typing import Dict, List, Optional, TypeVar, Union

from pyjackson import read, write
from pyjackson.utils import resolve_subtype

from ebonite.core.errors import ExistingImageError, ExistingInstanceError
from ebonite.core.objects import Image, Model, Pipeline, RuntimeEnvironment, RuntimeInstance, Task
from ebonite.core.objects.core import EboniteObject, Project, WithDatasetRepository
from ebonite.core.objects.dataset_source import Dataset
from ebonite.repository import DatasetRepository
from ebonite.repository.artifact import ArtifactRepository
from ebonite.repository.artifact.inmemory import InMemoryArtifactRepository
from ebonite.repository.artifact.local import LocalArtifactRepository
from ebonite.repository.dataset.artifact import ArtifactDatasetRepository
from ebonite.repository.metadata import MetadataRepository
from ebonite.repository.metadata.base import ProjectVar, TaskVar
from ebonite.repository.metadata.local import LocalMetadataRepository
from ebonite.runtime.server import Server
from ebonite.utils.importing import module_importable

T = TypeVar('T', bound=EboniteObject)


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

    default_server: Server = None
    default_env: RuntimeEnvironment = None

    def __init__(self, meta_repo: MetadataRepository, artifact_repo: ArtifactRepository,
                 dataset_repo: DatasetRepository = None):
        self.meta_repo = meta_repo
        self.artifact_repo = artifact_repo
        self.dataset_repo = dataset_repo or ArtifactDatasetRepository(self.artifact_repo)

    def _bind(self, obj: Optional[Union[T, List[T]]]) -> Optional[Union[T, List[T]]]:
        """Binds EboniteObject to meta and art repo of this client instance

        :param obj: subclass of EboniteObject instance or list of them
        """
        if obj is None:
            return
        if isinstance(obj, list):
            for o in obj:
                self._bind(o)
        else:

            obj.bind_meta_repo(self.meta_repo).bind_artifact_repo(self.artifact_repo)
            if isinstance(obj, WithDatasetRepository):
                obj.bind_dataset_repo(self.dataset_repo)
        return obj

    def push_model(self, model: Model, task: Task = None) -> Model:
        """
        Pushes :py:class:`~ebonite.core.objects.Model` instance into metadata and artifact repositories

        :param model: :py:class:`~ebonite.core.objects.Model` instance
        :param task: :py:class:`~ebonite.core.objects.Task` instance to save model to. Optional if model already has
        task
        :return: same saved :py:class:`~ebonite.core.objects.Model` instance
        """
        self._bind(model)
        return model.push(task)

    def create_model(self, model_object, model_input, model_name: str = None, *,
                     project_name: str = 'default_project', task_name: str = 'default_task', **kwargs):
        """
        This function creates ebonite model.
        Creates model, task and project (if needed) and pushes it to repo

        :param model_object: object containing model.
        :param model_input: model input.
        :param model_name: model name to create.
        :param project_name: project name.
        :param task_name: task name.
        :param kwargs: other arguments for model

        :return: :class:`~ebonite.core.objects.Model` instance representing
        """
        task = self.get_or_create_task(project_name, task_name)
        return task.create_and_push_model(model_object, model_input, model_name, **kwargs)

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
        return self._bind(model)

    def create_image(self, obj, name: str = None, task: Task = None, server: Server = None,
                     environment: RuntimeEnvironment = None,
                     debug=False, skip_build=False, builder_args: Dict[str, object] = None, **kwargs) -> Image:
        """
        Builds image of model service and stores it to repository

        :param obj: model/list of models/pipeline or any object that has existing Hook for it to wrap into service
        :param name: name of image to build
        :param task: task to put image into
        :param server: server to build image with
        :param environment: env to build for
        :param debug: flag to build debug image
        :param skip_build: wheter to skip actual image build
        :param builder_args: kwargs for image.build
        :param kwargs: additional kwargs for builder
        :return: :class:`~ebonite.core.objects.Image` instance representing built image
        """
        from ebonite.core.analyzer.buildable import BuildableAnalyzer

        if server is None:
            server = self.get_default_server()

        if environment is None:
            environment = self.get_default_environment()

        buildable = BuildableAnalyzer.analyze(obj, server=server, debug=debug).bind_meta_repo(self.meta_repo)
        task = task or buildable.task
        if task is None:
            raise ValueError(f'cannot infer task for buildable {buildable}, please provide it manually')
        if name is not None and self.meta_repo.get_image_by_name(name, task) is not None:
            raise ExistingImageError(name)

        builder = environment.params.get_builder()
        image = Image(name, buildable)
        image.params = builder.create_image(image.name, environment.params, **kwargs)
        image.task = task
        image.environment = environment
        self.meta_repo.create_image(image)
        if not skip_build:
            try:
                image.build(**(builder_args or {}))
            except Exception:
                self.meta_repo.delete_image(image)
                raise
        return self._bind(self.meta_repo.save_image(image))

    def create_instance(self, image: Image, name: str = None, environment: RuntimeEnvironment = None, run=False,
                        runner_kwargs: Dict[str, object] = None,
                        **instance_kwargs) -> RuntimeInstance:
        """
        Runs model service instance and stores it to repository

        :param image: image to run instance from
        :param name: name of instance to run
        :param environment: environment to run instance in, if no given `localhost` is used
        :param run:  whether to automatically run instance after creation
        :param runner_kwargs: additional parameters for runner
        :param instance_kwargs: additional parameters for instance
        :return: :class:`~ebonite.core.objects.RuntimeInstance` instance representing run instance
        """

        if environment is None:
            environment = self.get_default_environment()

        if name is not None and self.meta_repo.get_instance_by_name(name, image, environment) is not None:
            raise ExistingInstanceError(name)

        runner = environment.params.get_runner()

        instance = RuntimeInstance(name)

        instance.params = runner.create_instance(instance.name, **instance_kwargs)
        instance.image = image
        instance.environment = environment
        instance.bind_runner(runner)
        instance = self.meta_repo.create_instance(instance)
        if run:
            runner_kwargs = runner_kwargs or {}
            instance.run(**runner_kwargs)
        return self._bind(instance)

    def build_and_run_instance(self, obj, name: str = None, task: Task = None, environment: RuntimeEnvironment = None,
                               builder_kwargs: Dict[str, object] = None, runner_kwargs: Dict[str, object] = None,
                               instance_kwargs: Dict[str, object] = None) -> RuntimeInstance:
        """
        Builds image of model service, immediately runs service and stores both image and instance to repository

        :param obj: buildable object to wrap into service
        :param name: name of image and instance to be built and run respectively
        :param task: task to put image into
        :param environment: environment to run instance in, if no given `localhost` is used
        :param builder_kwargs: additional kwargs for builder
        :param runner_kwargs: additional parameters for runner. Full list can be seen in
                    https://docker-py.readthedocs.io/en/stable/containers.html
        :param instance_kwargs: additional parameters for instance
        :return: :class:`~ebonite.core.objects.RuntimeInstance` instance representing run instance
        """
        instance_kwargs = instance_kwargs or {}
        runner_kwargs = runner_kwargs or {}
        builder_kwargs = builder_kwargs or {}
        image = self.create_image(obj, name, task, environment=environment, builder_args=builder_kwargs)
        return self.create_instance(image, name, environment, **instance_kwargs).run(**runner_kwargs)

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

    def get_default_server(self):
        """
        :return: Default server implementation for this client
        """
        if self.default_server is None:
            from ebonite.ext.flask import FlaskServer
            self.default_server = FlaskServer()
        return self.default_server

    def get_default_environment(self):
        """
        Creates (if needed) and returns default runtime environment

        :return: saved instance of :class:`.RuntimeEnvironment`
        """
        if self.default_env is not None:
            return self.default_env
        env_name = 'docker_localhost'
        self.default_env = self.get_environment(env_name)
        if self.default_env is None:
            if not module_importable('docker'):
                raise RuntimeError("Can't build docker container: docker module is not installed. Install it "
                                   "with 'pip install docker'")

            from ebonite.ext.docker import DockerEnv
            self.default_env = RuntimeEnvironment(env_name, params=DockerEnv())
            self.default_env = self.push_environment(self.default_env)
        return self.default_env

    #  ########## AUTOGEN #####

    #  ########## AUTOGEN META #####

    def push_environment(self, environment: 'RuntimeEnvironment') -> RuntimeEnvironment:
        """
        Creates runtime environment in the repository

        :param environment: runtime environment to create
        :return: created runtime environment
        :exception: :exc:`.errors.ExistingEnvironmentError` if given runtime environment has the same name as existing
        """
        return self._bind(self.meta_repo.create_environment(environment))

    def get_environment(self, name: str) -> Optional[RuntimeEnvironment]:
        """
        Finds runtime environment by name.

        :param name: expected runtime environment name
        :return: found runtime environment if exists or `None`
        """
        return self._bind(self.meta_repo.get_environment_by_name(name))

    def get_environments(self) -> List[RuntimeEnvironment]:
        """
        Gets a list of runtime environments

        :return: found runtime environments
        """
        return self._bind(self.meta_repo.get_environments())

    def get_image(self, image_name: str, task: TaskVar, project: ProjectVar = None) -> Optional['Image']:
        """
        Finds image by name in given model, task and project.

        :param image_name: expected image name
        :param task: task to search for image in
        :param project: project to search for image in
        :return: found image if exists or `None`
        """
        return self._bind(self.meta_repo.get_image_by_name(image_name, task, project))

    def get_images(self, task: TaskVar, project: ProjectVar = None) -> List['Image']:
        """
        Gets a list of images in given model, task and project

        :param task: task to search for images in
        :param project: project to search for images in
        :return: found images
        """
        return self._bind(self.meta_repo.get_images(task, project))

    def get_instance(self, instance_name: str, image: Union[int, 'Image'],
                     environment: Union[int, 'RuntimeEnvironment']) -> Optional['RuntimeInstance']:
        """
        Finds instance by name in given image and environment.

        :param instance_name: expected instance name
        :param image: image (or id) to search for instance in
        :param environment: environment (or id) to search for instance in
        :return: found instance if exists or `None`
        """
        return self._bind(self.meta_repo.get_instance_by_name(instance_name, image, environment))

    def get_instances(self, image: Union[int, 'Image'] = None,
                      environment: Union[int, 'RuntimeEnvironment'] = None) -> List['RuntimeInstance']:
        """
        Gets a list of instances in given image or environment

        :param image: image (or id) to search for instances in
        :param environment: environment (or id) to search for instances in
        :return: found instances
        """
        return self._bind(self.meta_repo.get_instances(image, environment))

    def get_models(self, task: TaskVar, project: ProjectVar = None) -> List['Model']:
        """
        Gets a list of models in given project and task

        :param task: task to search for models in
        :param project: project to search for models in
        :return: found models
        """
        return self._bind(self.meta_repo.get_models(task, project))

    def get_or_create_project(self, name: str) -> Project:
        """
        Creates a project if not exists or gets existing project otherwise.

        :param name: project name
        :return: project
        """
        return self._bind(self.meta_repo.get_or_create_project(name))

    def get_or_create_task(self, project: str, task_name: str) -> Task:
        """
        Creates a task if not exists or gets existing task otherwise.

        :param project: project to search/create task in
        :param task_name: expected name of task
        :return: created/found task
        """
        return self._bind(self.meta_repo.get_or_create_task(project, task_name))

    def get_pipeline(self, pipeline_name: str, task: TaskVar,
                     project: ProjectVar = None) -> Optional['Pipeline']:
        """
        Finds model by name in given task and project.

        :param pipeline_name: expected pipeline name
        :param task: task to search for pipeline in
        :param project: project to search for pipeline in
        :return: found pipeline if exists or `None`
        """
        return self._bind(self.meta_repo.get_pipeline_by_name(pipeline_name, task, project))

    def get_pipelines(self, task: TaskVar, project: ProjectVar = None) -> List['Pipeline']:
        """
        Gets a list of pipelines in given project and task

        :param task: task to search for models in
        :param project: project to search for models in
        :return: found pipelines
        """
        return self._bind(self.meta_repo.get_pipelines(task, project))

    def get_project(self, name: str) -> Optional['Project']:
        """
        Finds project in the repository by name

        :param name: name of the project to return
        :return: found project if exists or `None`
        """
        return self._bind(self.meta_repo.get_project_by_name(name))

    def get_projects(self) -> List['Project']:
        """
        Gets all projects in the repository

        :return: all projects in the repository
        """
        return self._bind(self.meta_repo.get_projects())

    def get_task(self, project: ProjectVar, task_name: str) -> Optional['Task']:
        """
        Finds task with given name in given project

        :param project: project to search for task in
        :param task_name: expected name of task
        :return: task if exists or `None`
        """
        return self._bind(self.meta_repo.get_task_by_name(project, task_name))

    def get_tasks(self, project: ProjectVar) -> List['Task']:
        """
        Gets a list of tasks for given project

        :param project: project to search for tasks in
        :return: project tasks
        """
        return self._bind(self.meta_repo.get_tasks(project))

    #  ########## AUTOGEN META END #

    #  ########## AUTOGEN PROJECT #

    def delete_project(self, project: Project, cascade: bool = False):
        """"
        Deletes project and(if required) all tasks associated with it from metadata repository

        :param project: project to delete
        :param cascade: whether should project be deleted with all associated tasks
        :return: Nothing
        """
        return project.delete(cascade)

    #  ########## AUTOGEN PROJECT END #

    #  ########## AUTOGEN TASK #

    def delete_task(self, task: Task, cascade: bool = False):
        """"
        Deletes task from metadata

        :param task: task to delete
        :param cascade: whether should task be deleted with all associated objects
        :return: Nothing
        """
        return task.delete(cascade)

    #  ########## AUTOGEN TASK END #

    #  ########## AUTOGEN MODEL #

    def delete_model(self, model: Model, force: bool = False):
        """"
        Deletes model from metadata and artifact repositories

        :param model: model to delete
        :param force: whether model artifacts' deletion errors should be ignored, default is false
        :return: Nothing
        """
        return model.delete(force)

    #  ########## AUTOGEN MODEL END #

    #  ########## AUTOGEN PIPELINE #

    def delete_pipeline(self, pipeline: Pipeline):
        """"Deletes pipeline from metadata

        :param pipeline: pipeline to delete
        """
        return pipeline.delete()

    #  ########## AUTOGEN PIPELINE END #

    #  ########## AUTOGEN IMAGE #

    def delete_image(self, image: Image, meta_only: bool = False, cascade: bool = False):
        """"
        Deletes existing image from metadata repository and image provider

        :param image: image ot delete
        :param meta_only: should image be deleted only from metadata
        :param cascade: whether to delete nested RuntimeInstances
        """
        return image.delete(meta_only, cascade)

    #  ########## AUTOGEN IMAGE END #

    #  ########## AUTOGEN INSTANCE #

    def delete_instance(self, instance: RuntimeInstance, meta_only: bool = False):
        """"
        Stops instance of model service and deletes it from repository

        :param instance: instance to delete
        :param meta_only: only remove from metadata, do not stop instance
        :return: nothing
        """
        return instance.delete(meta_only)

    #  ########## AUTOGEN INSTANCE END #

    #  ########## AUTOGEN ENVIRONMENT #

    def delete_environment(self, environment: RuntimeEnvironment, meta_only: bool = False, cascade: bool = False):
        """"
        Deletes environment from metadata repository and(if required) stops associated instances

        :param environment: environment to delete
        :param meta_only: wheter to only delete metadata
        :param cascade: Whether should environment be deleted with all associated instances
        :return: Nothing
        """
        return environment.delete(meta_only, cascade)

    #  ########## AUTOGEN ENVIRONMENT END #

    #  ########## AUTOGEN END #

    def create_dataset(self, data, target=None):
        # TODO persisting to art repo?
        return Dataset.from_object(data)

    def create_metric(self, metric_obj):
        from ebonite.core.analyzer.metric import MetricAnalyzer
        return MetricAnalyzer.analyze(metric_obj)
