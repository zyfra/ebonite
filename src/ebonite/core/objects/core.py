import datetime
import getpass
import tempfile
from copy import copy
from functools import wraps
from typing import Callable, List, Optional

from pyjackson.core import Comparable
from pyjackson.decorators import make_string

import ebonite.repository
from ebonite import client
from ebonite.core import errors
from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.analyzer.model import ModelAnalyzer
from ebonite.core.objects.artifacts import ArtifactCollection, CompositeArtifactCollection
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.core.objects.requirements import AnyRequirements, Requirements, resolve_requirements
from ebonite.core.objects.wrapper import ModelWrapper, WrapperArtifactCollection
from ebonite.repository.artifact import NoSuchArtifactError
from ebonite.utils.index_dict import IndexDict, IndexDictAccessor
from ebonite.utils.module import get_object_requirements


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
    def delete_model(self, model: 'Model'):
        """
        Remove model from this task and delete it from meta repo

        :param model: model to delete
        """
        if model.id not in self._models:
            raise errors.NonExistingModelError(model)

        del self._models[model.id]
        self._meta.delete_model(model)
        if self.has_artifact_repo:
            try:
                self._art.delete_artifact(model)
            except NoSuchArtifactError:
                pass
        model.task_id = None

    #  ##########API############
    @_with_meta
    @_with_artifact
    def create_and_push_model(self, model_object, input_data, model_name: str = None, **kwargs) -> 'Model':
        """
        Create :class:`Model` instance from model object and push it to repository

        :param model_object: model object to build Model from
        :param input_data: input data sample
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
        return client.Ebonite(self._meta, self._art).push_model(model, self)


@make_string('id', 'name')
class Model(EboniteObject):
    """
    Model contains metadata for machine learning model

    :param name: model name
    :param wrapper: :class:`~ebonite.core.objects.wrapper.ModelWrapper` instance for this model
    :param artifact: :class:`~ebonite.core.objects.ArtifactCollection` instance with model artifacts
    :param input_meta: :class:`~ebonite.core.objects.DatasetType` instance for model input
    :param output_meta: :class:`~ebonite.core.objects.DatasetType` instance for model output
    :param requirements: :class:`~ebonite.core.objects.Requirements` instance with model requirements
    :param id: model id
    :param task_id: parent task_id
    :param author: user that created that model
    :param creation_date: date when this model was created
    """

    def __init__(self, name: str, wrapper: ModelWrapper,
                 artifact: 'ArtifactCollection' = None, input_meta: DatasetType = None,
                 output_meta: DatasetType = None, requirements: Requirements = None, id: str = None,
                 task_id: str = None,
                 author: str = None, creation_date: datetime.datetime = None):
        super().__init__(id, name, author, creation_date)
        self.wrapper = wrapper

        self.output_meta = output_meta
        self.input_meta = input_meta
        self.requirements = requirements
        self.transformer = None
        self.task_id = task_id
        self._persisted_artifacts = artifact
        self._unpersisted_artifacts: Optional[ArtifactCollection] = None

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
               custom_input_meta: DatasetType = None, custom_output_meta: DatasetType = None, custom_prediction=None,
               custom_requirements: AnyRequirements = None) -> 'Model':
        """
        Creates Model instance from arbitrary model objects and sample of input data

        :param model_object: The model object to analyze.
        :param input_data: The image to run.
        :param model_name: The model name.
        :param additional_artifacts: Additional artifact.
        :param additional_requirements: Additional requirements.
        :param custom_wrapper: Custom model wrapper.
        :param custom_artifact: Custom artifact collection to replace all other.
        :param custom_input_meta: Custom input DatasetType.
        :param custom_output_meta: Custom output DatasetType.
        :param custom_prediction: Custom prediction output.
        :param custom_requirements: Custom requirements to replace all other.
        :returns: :py:class:`Model`
        """
        wrapper: ModelWrapper = custom_wrapper or ModelAnalyzer.analyze(model_object)
        name = model_name or _generate_model_name(wrapper)

        artifact = custom_artifact or WrapperArtifactCollection(wrapper)
        if additional_artifacts is not None:
            artifact += additional_artifacts

        input_meta = custom_input_meta or DatasetAnalyzer.analyze(input_data)
        prediction = custom_prediction or wrapper.predict(input_data)
        output_meta = custom_output_meta or DatasetAnalyzer.analyze(prediction)

        if custom_requirements is not None:
            requirements = resolve_requirements(custom_requirements)
        else:
            requirements = get_object_requirements(model_object)
            requirements += get_object_requirements(input_data)
            requirements += get_object_requirements(prediction)

        if additional_requirements is not None:
            requirements += additional_requirements
        model = Model(name, wrapper, None, input_meta, output_meta, requirements)
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


def _generate_model_name(wrapper: ModelWrapper):
    """
    Generates name for Model instance

    :param wrapper: model wrapper
    :return: str
    """
    now = datetime.datetime.now()
    return '{}_model_{}'.format(wrapper.type, now.strftime('%Y%m%d_%H_%M_%S'))
