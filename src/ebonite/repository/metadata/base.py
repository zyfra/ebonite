from abc import abstractmethod
from functools import wraps
from typing import List, Optional, Sequence, TypeVar, Union

from pyjackson.decorators import type_field

from ebonite.core import errors
from ebonite.core.objects import core

Project = 'core.Project'
Task = 'core.Task'
Model = 'core.Model'

T = TypeVar('T')
NameOrIdOrObject = Union[str, T]
ProjectVar = NameOrIdOrObject['core.Project']
TaskVar = NameOrIdOrObject['core.Task']
ModelVar = NameOrIdOrObject['core.Model']


def bind_to_self(method):
    """
    Decorator for methods which binds method result to metadata repository contained in `self` reference.

    :param method: method to decorate
    :return: decorated method
    """

    @wraps(method)
    def inner(self, *args, **kwargs):
        res = method(self, *args, **kwargs)
        if isinstance(res, core.EboniteObject):
            res.bind_meta_repo(self)
        elif isinstance(res, Sequence):
            for o in res:
                o.bind_meta_repo(self)
        return res

    return inner


@type_field('type')
class MetadataRepository:
    """
    Abstract base class for persistent repositories of metadata (:class:`core.Project`, :class:`core.Task`, etc)
    """

    type = None

    @abstractmethod
    def get_projects(self) -> List['core.Project']:
        """
        Gets all projects in the repository

        :return: all projects in the repository
        """
        pass

    @abstractmethod
    def get_project_by_name(self, name: str) -> Optional['core.Project']:
        """
        Finds project in the repository by name

        :param name: name of the project to return
        :return: found project if exists or `None`
        """
        pass

    @abstractmethod
    def get_project_by_id(self, id: str) -> Optional['core.Project']:
        """
        Finds project in the repository by identifier

        :param id: project id
        :return: found project if exists or `None`
        """
        pass

    @abstractmethod
    def create_project(self, project: Project) -> Project:
        """
        Creates the project and all its tasks.

        :param project: project to create
        :return: created project
        :exception: :exc:`errors.ExistingProjectError` if given project has the same name as existing one.
        """
        pass

    @abstractmethod
    def update_project(self, project: Project) -> Project:
        """
        Updates the project and all its tasks.

        :param project: project to update
        :return: updated project
        :exception: :exc:`errors.NonExistingProjectError` if given project doesn't exist in the repository
        """
        pass

    @abstractmethod
    def delete_project(self, project: Project):
        """
        Deletes the project and all tasks.

        :param project: project to delete
        :return: nothing
        :exception: :exc:`errors.NonExistingProjectError` if given project doesn't exist in the repository
        """
        pass

    def save_project(self, project: Project) -> Project:
        """
        Saves project into the repository

        :param project: project to save
        :return: saved project
        :exception: :exc:`errors.ExistingProjectError` if given project has the same name as existing one.
        """
        existing_project = self.get_project_by_name(project.name)
        if project.id is None and existing_project is None:
            return self.create_project(project)
        elif existing_project is not None:
            if project.id is None or existing_project.id != project.id:
                raise errors.ExistingProjectError(existing_project)
        return self.update_project(project)

    def get_or_create_project(self, name: str) -> Project:
        """
        Creates a project if not exists or gets existing project otherwise.

        :param name: project name
        :return: project
        """
        project = self.get_project_by_name(name)
        if project is None:
            project = core.Project(name)
            project = self.create_project(project)
        return project

    @abstractmethod
    def get_tasks(self, project: ProjectVar) -> List['core.Task']:
        """
        Gets a list of tasks for given project

        :param project: project to search for tasks in
        :return: project tasks
        """

        pass

    @abstractmethod
    def get_task_by_name(self, project: ProjectVar, task_name: str) -> Optional['core.Task']:
        """
        Finds task with given name in given project

        :param project: project to search for task in
        :param task_name: expected name of task
        :return: task if exists or `None`
        """

        pass

    @abstractmethod
    def get_task_by_id(self, id: str) -> Optional['core.Task']:
        """
        Finds task with given id

        :param id: id of task to search for
        :return: task if exists or `None`
        """

        pass

    def get_or_create_task(self, project: str, task_name: str) -> Task:
        """
        Creates a task if not exists or gets existing task otherwise.

        :param project: project to search/create task in
        :param task_name: expected name of task
        :return: created/found task
        """

        project = self.get_or_create_project(project)
        task = self.get_task_by_name(project, task_name)
        if task is None:
            task = core.Task(task_name, project_id=project.id)
            task = self.create_task(task)
        return task

    @abstractmethod
    def create_task(self, task: Task) -> Task:
        """
        Creates task in a repository

        :param task: task to create
        :return: created task
        :exception: :class:`errors.ExistingTaskError` if given task has the same name and project as existing one
        """

        pass

    @abstractmethod
    def update_task(self, task: Task) -> Task:
        """
        Updates task in a repository.

        :param task: task to update
        :return: updated task
        :exception: :exc: `errors.NonExistingTaskError` if given tasks doesn't exist in the repository
        """

        pass

    @abstractmethod
    def delete_task(self, task: Task):
        """
        Deletes the task and all its models.

        :param task: task to delete
        :return: nothing
        :exception: :exc: `errors.NonExistingTaskError` if given tasks doesn't exist in the repository
        """

        pass

    def save_task(self, task: Task) -> Task:
        """
        Saves task into repository

        :param task: task
        :return: saved task
        :exception: :class:`errors.ExistingTaskError` if given task has the same name and project as existing one
        """

        if task.project_id is None:
            raise ValueError("A project is not assigned to the task {}".format(task))

        existing_task = self.get_task_by_name(task.project_id, task.name)
        if task.id is None and existing_task is None:
            return self.create_task(task)
        elif existing_task is not None:
            if task.id is None or existing_task.id != task.id:
                raise errors.ExistingTaskError(existing_task)
        return self.update_task(task)

    @abstractmethod
    def get_models(self, task: TaskVar, project: ProjectVar = None) -> List['core.Model']:
        """
        Gets a list of models in given project and task

        :param task: task to search for models in
        :param project: project to search for models in
        :return: found models
        """

        pass

    @abstractmethod
    def get_model_by_name(self, model_name, task: TaskVar, project: ProjectVar = None) -> Optional['core.Model']:
        """
        Finds model by name in given task and project.

        :param model_name: expected model name
        :param task: task to search for model in
        :param project: project to search for model in
        :return: found model if exists or `None`
        """

        pass

    @abstractmethod
    def get_model_by_id(self, id: str) -> Optional['core.Model']:
        """
        Finds model by identifier.

        :param id: expected model id
        :return: found model if exists or `None`
        """

        pass

    @abstractmethod
    def create_model(self, model: Model) -> Model:
        """
        Creates model in the repository

        :param model: model to create
        :return: created model
        :exception: :exc:`errors.ExistingModelError` if given model has the same name and task as existing one
        """
        pass

    @abstractmethod
    def update_model(self, model: Model) -> Model:
        """
        Updates model in the repository

        :param model: model to update
        :return: updated model
        :exception: :exc:`errors.NonExistingModelError` if given model doesn't exist in the repository
        """

        pass

    @abstractmethod
    def delete_model(self, model: Model):
        """
        Deletes model from the repository

        :param model: model to delete
        :return: nothing
        :exception: :exc:`errors.NonExistingModelError` if given model doesn't exist in the repository
        """

        pass

    def save_model(self, model: Model) -> Model:
        """
        Saves model in the repository

        :param model: model to save
        :return: saved model
        :exception: :exc:`errors.ExistingModelError` if given model has the same name and task as existing one
        """

        if model.task_id is None:
            raise ValueError("A task is not assigned to the model {}".format(model))

        existing_model = self.get_model_by_name(model.name, model.task_id)

        if model.id is None and existing_model is None:
            return self.create_model(model)
        elif existing_model is not None:
            if model.id is None or existing_model.id != model.id:
                raise errors.ExistingModelError(model)
        return self.update_model(model)

    def _resolve_project(self, project: ProjectVar) -> Optional['core.Project']:
        if isinstance(project, core.Project):
            project = project.id or project.name
        return self.get_project_by_id(project) or self.get_project_by_name(project)

    def _resolve_task(self, task: TaskVar, project: ProjectVar = None) -> Optional['core.Task']:
        if isinstance(task, core.Task):
            return task
        # task is task_id
        resolved = self.get_task_by_id(task)
        if resolved is not None:
            return resolved
        else:
            # task is task name
            if project is None:
                raise ValueError('Cannot resolve task without project')
            return self.get_task_by_name(project, task)

    def _validate_project(self, project: Project):
        pass

    def _validate_task(self, task: Task):
        if task.project_id is None:
            raise errors.TaskNotInProjectError(task)

    def _validate_model(self, model: Model):
        if model.task_id is None:
            raise errors.ModelNotInTaskError(model)
