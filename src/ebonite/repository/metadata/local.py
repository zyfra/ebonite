import copy
import os
import uuid
from typing import Dict, List, Optional, Tuple

import pyjackson

from ebonite.core.errors import (ExistingImageError, ExistingModelError, ExistingProjectError, ExistingTaskError,
                                 NonExistingImageError, NonExistingModelError, NonExistingProjectError,
                                 NonExistingTaskError)
from ebonite.core.objects.core import Image, Model, Project, Task
from ebonite.repository.metadata.base import MetadataRepository, ModelVar, ProjectVar, TaskVar, bind_to_self
from ebonite.utils.log import logger

_Projects = Dict[str, Project]
_Tasks = Dict[str, Task]
_Models = Dict[str, Model]
_Images = Dict[str, Image]


class _LocalContainer:
    def __init__(self, projects: _Projects, tasks: _Tasks, models: _Models, images: _Images):
        self.projects: _Projects = {}
        self.project_name_index: Dict[str, str] = {}
        self.tasks: _Tasks = {}
        self.task_name_index: Dict[Tuple[str, str], str] = {}
        self.models: _Models = {}
        self.model_name_index: Dict[Tuple[str, str], str] = {}
        self.images: _Images = {}
        self.image_name_index: Dict[Tuple[str, str], str] = {}

        for p in projects.values():
            self.add_project(p)

        for t in tasks.values():
            self.add_task(t)

        for m in models.values():
            self.add_model(m)

        for i in images.values():
            self.add_image(i)

    def add_project(self, project: Project):
        assert project.id is not None
        self.projects[project.id] = project
        self.project_name_index[project.name] = project.id

    def get_project_by_id(self, project_id):
        return self.projects.get(project_id)

    def get_project_by_name(self, name: str):
        return self.get_project_by_id(self.project_name_index.get(name, None))

    def remove_project(self, project_id, recursive):
        project = self.projects.pop(project_id, None)
        if recursive:
            for t in project.tasks.keys():
                self.remove_task(t, True)
        del self.project_name_index[project.name]
        return project

    def add_task(self, task: Task):
        assert task.id is not None
        self.tasks[task.id] = task
        self.task_name_index[(task.project_id, task.name)] = task.id
        self.projects[task.project_id]._tasks.add(task)

    def get_task_by_id(self, task_id):
        return self.tasks.get(task_id)

    def get_task_by_name(self, project_id: str, name: str):
        return self.get_task_by_id(self.task_name_index.get((project_id, name), None))

    def remove_task(self, task_id, recursive):
        task = self.tasks.pop(task_id, None)
        if recursive:
            for m in task.models.keys():
                self.remove_model(m)
        self.task_name_index.pop((task.project_id, task.name), None)
        return task

    def add_model(self, model: Model):
        assert model.id is not None
        self.models[model.id] = model
        self.model_name_index[(model.task_id, model.name)] = model.id
        self.tasks[model.task_id]._models.add(model)

    def get_model_by_id(self, model_id):
        return self.models.get(model_id, None)

    def get_model_by_name(self, task_id: str, name: str):
        return self.get_model_by_id(self.model_name_index.get((task_id, name), None))

    def remove_model(self, model_id):
        model = self.models.pop(model_id, None)
        self.model_name_index.pop((model.task_id, model.name), None)
        return model

    def add_image(self, image: Image):
        assert image.id is not None
        self.images[image.id] = image
        self.image_name_index[(image.model_id, image.name)] = image.id
        self.models[image.model_id]._images.add(image)

    def get_image_by_id(self, image_id):
        return self.images.get(image_id, None)

    def get_image_by_name(self, model_id: str, name: str):
        return self.get_image_by_id(self.image_name_index.get((model_id, name), None))

    def remove_image(self, image_id):
        image = self.images.pop(image_id, None)
        self.image_name_index.pop((image.model_id, image.name), None)
        return image


class LocalMetadataRepository(MetadataRepository):
    """
    :class:`.MetadataRepository` implementation which stores metadata in a local filesystem as JSON file.

    Warning: file storage is completely overwritten on each update,
    thus this repository is not suitable for high-performance scenarios.

    :param path: path to json with the metadata, if `None` metadata is stored in-memory.
    """

    type = 'local'

    def __init__(self, path=None):
        self.path = path
        if self.path is not None:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)

        self.data: _LocalContainer = _LocalContainer({}, {}, {}, {})
        self.load()
        self.save()

    def load(self):
        if self.path is not None and os.path.exists(self.path):
            with open(self.path, 'r', encoding='utf8') as f:
                logger.debug('Loading metadata from %s', self.path)
                self.data = pyjackson.load(f, _LocalContainer)
        else:
            self.data = _LocalContainer({}, {}, {}, {})

    def save(self):
        if self.path is None:
            return
        with open(self.path, 'w', encoding='utf8') as f:
            logger.debug('Saving metadata to %s', self.path)
            pyjackson.dump(f, self.data)

    @bind_to_self
    def get_projects(self) -> List[Project]:
        return copy.deepcopy([self.data.get_project_by_id(p) for p in self.data.projects.keys()])

    @bind_to_self
    def get_project_by_name(self, name: str) -> Project:
        return copy.deepcopy(self.data.get_project_by_name(name))

    @bind_to_self
    def get_project_by_id(self, id) -> Project:
        return copy.deepcopy(self.data.get_project_by_id(id))

    @bind_to_self
    def create_project(self, project: Project) -> Project:
        if self.get_project_by_name(project.name) is not None:
            raise ExistingProjectError(project)
        project._id = str(uuid.uuid4())
        self.data.add_project(copy.deepcopy(project))
        self.save()
        return project

    def update_project(self, project: Project) -> Project:
        existing_project = self.get_project_by_id(project.id)
        if existing_project is None:
            raise NonExistingProjectError(project)

        self.data.remove_project(project.id, recursive=False)
        proj_copy = copy.deepcopy(project)
        self.data.add_project(proj_copy)
        for task in proj_copy.tasks.values():
            self.save_task(task)
        self.save()
        return project

    def delete_project(self, project: Project):
        try:
            self.data.remove_project(project.id, True)
            self.save()
            project.unbind_meta_repo()
        except (KeyError, AttributeError):
            raise NonExistingProjectError(project)

    @bind_to_self
    def get_tasks(self, project: ProjectVar) -> List[Task]:
        project = self._resolve_project(project)
        return copy.deepcopy(list(project.tasks.values()))

    @bind_to_self
    def get_task_by_name(self, project: ProjectVar, task_name: str) -> Optional[Task]:
        project = self._resolve_project(project)
        if project is None:
            return None
        return copy.deepcopy(self.data.get_task_by_name(project.id, task_name))

    @bind_to_self
    def get_task_by_id(self, id) -> Task:
        return copy.deepcopy(self.data.get_task_by_id(id))

    @bind_to_self
    def create_task(self, task: Task) -> Task:
        self._validate_task(task)

        existing_project = self.get_project_by_id(task.project_id)
        if existing_project is None:
            raise NonExistingProjectError(task.project_id)

        existing_task = self.get_task_by_name(existing_project, task.name)
        if existing_task is not None:
            raise ExistingTaskError(task)

        task._id = str(uuid.uuid4())
        self.data.add_task(copy.deepcopy(task))
        self.save()
        return task

    def update_task(self, task: Task) -> Task:
        if task.id is None or self.get_task_by_id(task.id) is None:
            raise NonExistingTaskError(task)
        self._validate_task(task)

        existing_project = self.get_project_by_id(task.project_id)
        if existing_project is None:
            raise NonExistingProjectError(task.project_id)

        self.data.remove_task(task.id, False)
        task_copy = copy.deepcopy(task)
        self.data.add_task(task_copy)
        for model in task_copy.models.values():
            self.save_model(model)
        self.save()
        return task

    def delete_task(self, task: Task):
        if task.id is None:
            raise NonExistingTaskError(task)
        self.data.remove_task(task.id, True)
        self.save()
        task.unbind_meta_repo()

    @bind_to_self
    def get_models(self, task: TaskVar, project: ProjectVar = None) -> List[Model]:
        task = self._resolve_task(task, project)
        return copy.deepcopy(list(task.models.values()))

    @bind_to_self
    def get_model_by_name(self, model_name: str, task: TaskVar, project: ProjectVar = None) -> Optional[Model]:
        task = self._resolve_task(task, project)
        if task is None:
            return None
        return copy.deepcopy(self.data.get_model_by_name(task.id, model_name))

    @bind_to_self
    def get_model_by_id(self, id) -> Model:
        return copy.deepcopy(self.data.get_model_by_id(id))

    @bind_to_self
    def create_model(self, model: Model) -> Model:
        self._validate_model(model)

        existing_task = self.get_task_by_id(model.task_id)
        if existing_task is None:
            raise NonExistingTaskError(model.task_id)

        if self.get_model_by_name(model.name, existing_task) is not None:
            raise ExistingModelError(model)

        model._id = str(uuid.uuid4())
        self.data.add_model(copy.deepcopy(model))
        self.save()
        return model

    def update_model(self, model: Model) -> Model:
        self._validate_model(model)

        task = self.get_task_by_id(model.task_id)
        if task is None:
            raise NonExistingTaskError(model.task_id)

        existing_model = self.get_model_by_id(model.id)
        if existing_model is None:
            raise NonExistingModelError(model)

        self.data.remove_model(model.id)
        model_copy = copy.deepcopy(model)
        self.data.add_model(model_copy)
        self.save()
        return model

    def delete_model(self, model: Model):
        if model.id is None:
            raise NonExistingModelError(model)
        self.data.remove_model(model.id)
        self.save()
        model.unbind_meta_repo()

    @bind_to_self
    def get_images(self, model: ModelVar, task: TaskVar = None, project: ProjectVar = None) -> List[Image]:
        model = self._resolve_model(model, task, project)
        return copy.deepcopy(list(model.images.values()))

    @bind_to_self
    def get_image_by_name(self, image_name, model: ModelVar, task: TaskVar = None, project: ProjectVar = None) -> Optional[Image]:
        model = self._resolve_model(model, task, project)
        if model is None:
            return None
        return copy.deepcopy(self.data.get_image_by_name(model.id, image_name))

    @bind_to_self
    def get_image_by_id(self, id: str) -> Optional[Image]:
        return copy.deepcopy(self.data.get_image_by_id(id))

    @bind_to_self
    def create_image(self, image: Image) -> Image:
        self._validate_image(image)

        existing_model = self.get_model_by_id(image.model_id)
        if existing_model is None:
            raise NonExistingModelError(image.model_id)

        if self.get_image_by_name(image.name, existing_model) is not None:
            raise ExistingImageError(image)

        image._id = str(uuid.uuid4())
        self.data.add_image(copy.deepcopy(image))
        self.save()
        return image

    def update_image(self, image: Image) -> Image:
        self._validate_image(image)

        existing_model = self.get_model_by_id(image.model_id)
        if existing_model is None:
            raise NonExistingModelError(image.model_id)

        existing_image = self.get_image_by_id(image.id)
        if existing_image is None:
            raise NonExistingImageError(image)

        self.data.remove_image(image.id)
        self.data.add_image(copy.deepcopy(image))
        self.save()
        return image

    def delete_image(self, image: Image):
        if image.id is None:
            raise NonExistingImageError(image)
        self.data.remove_image(image.id)
        self.save()
        image.unbind_meta_repo()
