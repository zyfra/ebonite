import datetime
import getpass
import tempfile
from copy import copy
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from pyjackson import deserialize, serialize
from pyjackson.core import Comparable
from pyjackson.decorators import make_string

import ebonite.repository
from ebonite import client
from ebonite.core import errors
from ebonite.core.analyzer.model import ModelAnalyzer
from ebonite.core.objects.artifacts import ArtifactCollection, CompositeArtifactCollection
from ebonite.core.objects.requirements import AnyRequirements, Requirements, resolve_requirements
from ebonite.core.objects.wrapper import ModelWrapper, WrapperArtifactCollection
from ebonite.utils.index_dict import IndexDict, IndexDictAccessor
from ebonite.utils.module import get_object_requirements, get_python_version


def _get_current_user():
    return getpass.getuser()


class EboniteObject(Comparable):
    """
    Base class for high level ebonite objects.
    These objects can be binded to metadata repository and/or to artifact repository

    :param id: object id
    :param name: object name
    :param author: user that created that object
    :param creation_date: date when this object was created
    """
    _meta: 'ebonite.repository.MetadataRepository' = None
    _art: 'ebonite.repository.ArtifactRepository' = None

    def __init__(self, id: str, name: str, author: str = None, creation_date: datetime.datetime = None):
        self._id = id
        self.name = name
        self.author = author or _get_current_user()
        self.creation_date = creation_date or datetime.datetime.utcnow()  # TODO local timezone

    def bind_meta_repo(self, repo: 'ebonite.repository.MetadataRepository'):
        self._meta = repo

    def unbind_meta_repo(self):
        del self._meta
        self._id = None

    @property
    def has_meta_repo(self):
        return self._meta is not None

    def bind_artifact_repo(self, repo: 'ebonite.repository.ArtifactRepository'):
        self._art = repo

    def unbind_artifact_repo(self):
        del self._art

    @property
    def has_artifact_repo(self):
        return self._art is not None

    def bind_client(self, cl: 'client.Ebonite'):
        self.bind_artifact_repo(cl.artifact_repo)
        self.bind_meta_repo(cl.meta_repo)

    @property
    def id(self):
        return self._id


def _with_meta(method):
    """
    Decorator for methods to check that object is binded to meta repo

    :param method: method to apply decorator
    :return: decorated method
    """

    @wraps(method)
    def inner(self: EboniteObject, *args, **kwargs):
        if self.id is None or not self.has_meta_repo:
            raise errors.UnboundObjectError('{} is not bound to meta repository'.format(self))
        return method(self, *args, **kwargs)

    return inner


def _with_artifact(method):
    """
    Decorator for methods to check that object is binded to artifact repo

    :param method: method to apply decorator
    :return: decorated method
    """

    @wraps(method)
    def inner(self: EboniteObject, *args, **kwargs):
        if self.id is None or not self.has_artifact_repo:
            raise errors.UnboundObjectError('{} is not bound to artifact repository'.format(self))
        return method(self, *args, **kwargs)

    return inner


@make_string('id', 'name')
class Project(EboniteObject):
    """
    Project is a collection of tasks

    :param id: project id
    :param name: project name
    :param author: user that created that project
    :param creation_date: date when this project was created
    """

    def __init__(self, name: str, id: str = None, author: str = None, creation_date: datetime.datetime = None):
        super().__init__(id, name, author, creation_date)
        self._tasks: IndexDict[Task] = IndexDict('id', 'name')
        self.tasks: IndexDictAccessor[Task] = IndexDictAccessor(self._tasks)

    @_with_meta
    def add_task(self, task: 'Task'):
        """
        Add task to project and save it to meta repo

        :param task: task to add
        """
        if task.project_id is not None and task.project_id != self.id:
            raise errors.MetadataError('Task is already in project {}. Delete it first'.format(task.project_id))

        task.project_id = self.id
        self._meta.save_task(task)
        self._tasks.add(task)

    @_with_meta
    def add_tasks(self, tasks: List['Task']):
        """
        Add multiple tasks and save them to meta repo

        :param tasks: tasks to add
        """
        for t in tasks:
            self.add_task(t)

    @_with_meta
    def delete_task(self, task: 'Task'):
        """
        Remove task from this project and delete it from meta repo

        :param task: task to delete
        """
        if task.id not in self._tasks:
            raise errors.NonExistingTaskError(task)
        del self._tasks[task.id]
        self._meta.delete_task(task)
        task.project_id = None

    def __repr__(self):
        return """Project '{name}', {td} tasks""".format(name=self.name, td=len(self.tasks))

    def bind_meta_repo(self, repo: 'ebonite.repository.MetadataRepository'):
        super(Project, self).bind_meta_repo(repo)
        for task in self._tasks.values():
            task.bind_meta_repo(repo)

    def bind_artifact_repo(self, repo: 'ebonite.repository.ArtifactRepository'):
        super(Project, self).bind_artifact_repo(repo)
        for task in self._tasks.values():
            task.bind_artifact_repo(repo)


@make_string('id', 'name')
class Task(EboniteObject):
    """
    Task is a collection of models

    :param id: task id
    :param name: task name
    :param project_id: parent project id for this task
    :param author: user that created that task
    :param creation_date: date when this task was created
    """

    def __init__(self, name: str, id: str = None, project_id: str = None,
                 author: str = None, creation_date: datetime.datetime = None):
        super().__init__(id, name, author, creation_date)
        self.project_id = project_id
        # self.metrics = metrics TODO
        # self.sample_data = sample_data
        self._models: IndexDict[Model] = IndexDict('id', 'name')
        self.models: IndexDictAccessor[Model] = IndexDictAccessor(self._models)

    def __str__(self):
        return self.name

    @property
    def project(self):
        raise AttributeError('Cant access project of unbound task')

    @project.setter
    def project(self, project: Project):
        if not isinstance(project, Project):
            raise ValueError('{} is not Project'.format(project))
        self.project_id = project.id

    @_with_meta
    def add_model(self, model: 'Model'):
        """
        Add model to task and save it to meta repo

        :param model: model to add
        """
        if model.task_id is not None and model.task_id != self.id:
            raise errors.MetadataError('Model is already in task {}. Delete it first'.format(model.task_id))

        model.task_id = self.id
        self._meta.save_model(model)
        self._models.add(model)

    @_with_meta
    def add_models(self, models: List['Model']):
        """
        Add multiple models and save them to meta repo

        :param models: models to add
        """
        for m in models:
            self.add_model(m)

    @_with_meta
    def delete_model(self, model: 'Model', force=False):
        """
        Remove model from this task and delete it from meta repo

        :param model: model to delete
        :param force: whether model artifacts' deletion errors should be ignored, default is false
        """
        model_id = model.id
        if model_id not in self._models:
            raise errors.NonExistingModelError(model)

        client.Ebonite(self._meta, self._art).delete_model(model, force)
        del self._models[model_id]

    #  ##########API############
    @_with_meta
    @_with_artifact
    def create_and_push_model(self, model_object, input_data, model_name: str = None, **kwargs) -> 'Model':
        """
        Create :class:`Model` instance from model object and push it to repository

        :param model_object: model object to build Model from
        :param input_data: input data sample to determine structure of inputs and outputs for given model
        :param model_name: name for model
        :param kwargs: other :meth:`~Model.create` arguments
        :return: created :class:`Model`
        """
        model = Model.create(model_object, input_data, model_name, **kwargs)
        return self.push_model(model)

    @_with_meta
    @_with_artifact
    def push_model(self, model: 'Model') -> 'Model':
        """
        Push :class:`Model` instance to task repository

        :param model: :class:`Model` to push
        :return: same pushed :class:`Model`
        """
        model = client.Ebonite(self._meta, self._art).push_model(model, self)
        self._models.add(model)
        return model

    def bind_meta_repo(self, repo: 'ebonite.repository.MetadataRepository'):
        super(Task, self).bind_meta_repo(repo)
        for model in self._models.values():
            model.bind_meta_repo(repo)

    def bind_artifact_repo(self, repo: 'ebonite.repository.ArtifactRepository'):
        super(Task, self).bind_artifact_repo(repo)
        for model in self._models.values():
            model.bind_artifact_repo(repo)


@make_string('id', 'name')
class Model(EboniteObject):
    """
    Model contains metadata for machine learning model

    :param name: model name
    :param wrapper: :class:`~ebonite.core.objects.wrapper.ModelWrapper` instance for this model
    :param artifact: :class:`~ebonite.core.objects.ArtifactCollection` instance with model artifacts
    :param requirements: :class:`~ebonite.core.objects.Requirements` instance with model requirements
    :param id: model id
    :param task_id: parent task_id
    :param author: user that created that model
    :param creation_date: date when this model was created
    """

    PYTHON_VERSION = 'python_version'

    def __init__(self, name: str, wrapper_meta: Optional[dict] = None,
                 artifact: 'ArtifactCollection' = None,
                 requirements: Requirements = None,
                 params: Dict[str, Any] = None,
                 description: str = None,
                 id: str = None,
                 task_id: str = None,
                 author: str = None, creation_date: datetime.datetime = None):
        super().__init__(id, name, author, creation_date)

        self.description = description
        self.params = params or {}
        self._wrapper = None
        self._wrapper_meta = None
        if isinstance(wrapper_meta, ModelWrapper):
            self._wrapper = wrapper_meta
        elif isinstance(wrapper_meta, dict):
            self._wrapper_meta = wrapper_meta

        self.requirements = requirements
        self.transformer = None
        self.task_id = task_id
        self._persisted_artifacts = artifact
        self._unpersisted_artifacts: Optional[ArtifactCollection] = None

        self._images: IndexDict[Image] = IndexDict('id', 'name')
        self.images: IndexDictAccessor[Image] = IndexDictAccessor(self._images)

    def load(self):
        """
        Load model artifacts into wrapper
        """
        with tempfile.TemporaryDirectory(prefix='ebonite_run_') as tmpdir:
            self.artifact.materialize(tmpdir)
            self.wrapper.load(tmpdir)

    def ensure_loaded(self):
        """
        Ensure that wrapper has loaded model object
        """
        if self.wrapper.model is None:
            self.load()

    @property
    def wrapper(self) -> 'ModelWrapper':
        if self._wrapper is None:
            if self._wrapper_meta is None:
                raise ValueError("Either 'wrapper' or 'wrapper_meta' should be provided")
            self._wrapper = deserialize(self._wrapper_meta, ModelWrapper)
        return self._wrapper

    @wrapper.setter
    def wrapper(self, wrapper: ModelWrapper):
        if self._wrapper_meta is not None:
            raise ValueError("'wrapper' could be provided for models with no 'wrapper_meta' specified only")
        self._wrapper = wrapper

    def with_wrapper(self, wrapper: ModelWrapper):
        """
        Bind wrapper instance to this Model

        :param wrapper: :class:`~ebonite.core.objects.wrapper.ModelWrapper` instance
        :return: self
        """
        self.wrapper = wrapper
        return self

    @property
    def wrapper_meta(self) -> dict:
        """
        :return: pyjackson representation of :class:`~ebonite.core.objects.wrapper.ModelWrapper` for this model: e.g.,
          this provides possibility to move a model between repositories without its dependencies being installed
        """
        if self._wrapper_meta is None:
            if self._wrapper is None:
                raise ValueError("Either 'wrapper' or 'wrapper_meta' should be provided")
            self._wrapper_meta = serialize(self._wrapper)
        return self._wrapper_meta

    @wrapper_meta.setter
    def wrapper_meta(self, meta: dict):
        if self._wrapper is not None:
            raise ValueError("'wrapper_meta' could be provided for models with no 'wrapper' specified only")
        self._wrapper_meta = meta

    def with_wrapper_meta(self, wrapper_meta: dict):
        """
        Bind wrapper_meta dict to this Model

        :param wrapper_meta: dict with serialized :class:`~ebonite.core.objects.wrapper.ModelWrapper` instance
        :return: self
        """
        self.wrapper_meta = wrapper_meta
        return self

    # this property is needed for pyjackson to serialize model, it is coupled with __init__
    @property
    def artifact(self) -> 'ArtifactCollection':
        """
        :return: persisted artifacts if any
        """
        return self._persisted_artifacts

    @property
    def artifact_any(self) -> 'ArtifactCollection':
        """
        :return: artifacts in any state (persisted or not)
        """
        arts = [a for a in [self._persisted_artifacts, self._unpersisted_artifacts] if a is not None]
        return CompositeArtifactCollection(arts) if len(arts) != 1 else arts[0]

    @property
    def artifact_req_persisted(self) -> 'ArtifactCollection':
        """
        Similar to `artifact` but checks that no unpersisted artifacts are left

        :return: persisted artifacts if any
        """
        if self._unpersisted_artifacts is not None:
            raise ValueError('Model has unpersisted artifacts')
        return self._persisted_artifacts

    def attach_artifact(self, artifact: 'ArtifactCollection'):
        """
        :param artifact: artifacts to attach to model in an unpersisted state
        """
        if self._unpersisted_artifacts is not None:
            self._unpersisted_artifacts += artifact
        else:
            self._unpersisted_artifacts = artifact

    def persist_artifacts(self, persister: Callable[['ArtifactCollection'], 'ArtifactCollection']):
        """
        Model artifacts persisting workflow

        :param persister: external object which stores model artifacts
        """
        artifact = self._persisted_artifacts

        if self._unpersisted_artifacts is None:
            if artifact is None:
                raise ValueError('Model has no artifacts')
        else:
            if artifact is None:
                artifact = self._unpersisted_artifacts
            else:
                artifact += self._unpersisted_artifacts

        self._persisted_artifacts = persister(artifact)
        self._unpersisted_artifacts = None

    def without_artifacts(self) -> 'Model':
        """
        :return: copy of the model with no artifacts attached
        """
        no_artifacts = copy(self)
        no_artifacts._persisted_artifacts = None
        no_artifacts._unpersisted_artifacts = None
        return no_artifacts

    @classmethod
    def create(cls, model_object, input_data, model_name: str = None,
               additional_artifacts: ArtifactCollection = None, additional_requirements: AnyRequirements = None,
               custom_wrapper: ModelWrapper = None, custom_artifact: ArtifactCollection = None,
               custom_requirements: AnyRequirements = None) -> 'Model':
        """
        Creates Model instance from arbitrary model objects and sample of input data

        :param model_object: The model object to analyze.
        :param input_data: Input data sample to determine structure of inputs and outputs for given model object.
        :param model_name: The model name.
        :param additional_artifacts: Additional artifact.
        :param additional_requirements: Additional requirements.
        :param custom_wrapper: Custom model wrapper.
        :param custom_artifact: Custom artifact collection to replace all other.
        :param custom_requirements: Custom requirements to replace all other.
        :returns: :py:class:`Model`
        """
        wrapper: ModelWrapper = custom_wrapper or ModelAnalyzer.analyze(model_object, input_data=input_data)
        name = model_name or _generate_model_name(wrapper)

        artifact = custom_artifact or WrapperArtifactCollection(wrapper)
        if additional_artifacts is not None:
            artifact += additional_artifacts

        if custom_requirements is not None:
            requirements = resolve_requirements(custom_requirements)
        else:
            requirements = get_object_requirements(model_object)
            requirements += get_object_requirements(input_data)
            for method in wrapper.exposed_methods:
                output_data = wrapper.call_method(method, input_data)
                requirements += get_object_requirements(output_data)

        if additional_requirements is not None:
            requirements += additional_requirements
        model = Model(name, wrapper, None, requirements, {cls.PYTHON_VERSION: get_python_version()})
        model._unpersisted_artifacts = artifact
        return model

    @property
    def id(self):
        return self._id

    @property
    def task(self):
        raise AttributeError('Cant access task of unbound model')

    @task.setter
    def task(self, task: Task):
        if not isinstance(task, Task):
            raise ValueError('{} is not Task'.format(task))
        self.task_id = task.id

    def bind_meta_repo(self, repo: 'ebonite.repository.MetadataRepository'):
        super(Model, self).bind_meta_repo(repo)
        for image in self._images.values():
            image.bind_meta_repo(repo)

    @_with_meta
    def add_image(self, image: 'Image'):
        """
        Add image for model and save it to meta repo

        :param image: image to add
        """
        if image.model_id is not None and image.model_id != self.id:
            raise errors.MetadataError('Image is already in model {}. Delete it first'.format(image.model_id))

        image.model_id = self.id
        self._meta.save_image(image)
        self._images.add(image)

    @_with_meta
    def add_images(self, images: List['Image']):
        """
        Add multiple images for model and save them to meta repo

        :param images: images to add
        """
        for image in images:
            self.add_image(image)

    @_with_meta
    def delete_image(self, image: 'Image'):
        """
        Remove image from this model and delete it from meta repo

        :param image: image to delete
        """
        if image.id not in self._images:
            raise errors.NonExistingImageError(image)
        del self._images[image.id]
        self._meta.delete_image(image)
        image.model_id = None


def _generate_model_name(wrapper: ModelWrapper):
    """
    Generates name for Model instance

    :param wrapper: model wrapper
    :return: str
    """
    now = datetime.datetime.now()
    return '{}_model_{}'.format(wrapper.type, now.strftime('%Y%m%d_%H_%M_%S'))


@make_string('id', 'name')
class Image(EboniteObject):
    def __init__(self, name: str, id: str = None,
                 model_id: str = None, params: Dict[str, Any] = None,
                 author: str = None, creation_date: datetime.datetime = None):
        super().__init__(id, name, author, creation_date)
        self.model_id = model_id
        self.params = params or {}

    @property
    def model(self) -> Model:
        raise AttributeError('Can\'t access model of unbound image')

    @model.setter
    def model(self, model: Model):
        if not isinstance(model, Model):
            raise ValueError('{} is not Model'.format(model))
        self.model_id = model.id


class RuntimeEnvironment(EboniteObject):
    def __init__(self, name: str, id: str = None,
                 host: str = None, port: int = None,
                 author: str = None, creation_date: datetime.datetime = None):
        super().__init__(id, name, author, creation_date)
        self.host = host
        self.port = port

    def get_uri(self) -> str:
        return f'{self.host}:{self.port}' if self.host else ''


class RuntimeInstance(EboniteObject):
    def __init__(self, name: str, id: str = None,
                 image_id: str = None, environment_id: str = None, params: Dict[str, Any] = None,
                 author: str = None, creation_date: datetime.datetime = None):
        super().__init__(id, name, author, creation_date)
        self.image_id = image_id
        self.environment_id = environment_id
        self.params = params or {}

    @property
    def image(self) -> Image:
        raise AttributeError('Can\'t access image of unbound instance')

    @image.setter
    def image(self, image: Image):
        if not isinstance(image, Image):
            raise ValueError(f'{image} is not Image')
        self.image_id = image.id

    @property
    def environment(self) -> RuntimeEnvironment:
        raise AttributeError('Can\'t access environment of unbound instance')

    @environment.setter
    def environment(self, environment: RuntimeEnvironment):
        if not isinstance(environment, RuntimeEnvironment):
            raise ValueError(f'{environment} is not RuntimeEnvironment')
        self.environment_id = environment.id
