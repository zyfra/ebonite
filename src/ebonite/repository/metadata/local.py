import copy
import os
from typing import Dict, List, Optional, Set, Tuple, Union

import pyjackson

from ebonite.core.errors import (EnvironmentWithInstancesError, ExistingEnvironmentError, ExistingImageError,
                                 ExistingInstanceError, ExistingModelError, ExistingProjectError, ExistingTaskError,
                                 ImageWithInstancesError, ModelWithImagesError, NonExistingEnvironmentError,
                                 NonExistingImageError, NonExistingInstanceError, NonExistingModelError,
                                 NonExistingProjectError, NonExistingTaskError, ProjectWithTasksError,
                                 TaskWithModelsError)
from ebonite.core.objects.core import Image, Model, Project, RuntimeEnvironment, RuntimeInstance, Task
from ebonite.repository.metadata.base import MetadataRepository, ModelVar, ProjectVar, TaskVar, bind_to_self
from ebonite.utils.log import logger

_Projects = Dict[int, Project]
_Tasks = Dict[int, Task]
_Models = Dict[int, Model]
_Images = Dict[int, Image]
_Environments = Dict[int, RuntimeEnvironment]
_Instances = Dict[int, RuntimeInstance]


class _LocalContainer:
    def __init__(self, next_project_id: int = 0, projects: _Projects = None,
                 next_task_id: int = 0, tasks: _Tasks = None,
                 next_model_id: int = 0, models: _Models = None,
                 next_image_id: int = 0, images: _Images = None,
                 next_environment_id: int = 0, environments: _Environments = None,
                 next_instance_id: int = 0, instances: _Instances = None):
        self.next_project_id = next_project_id
        self.projects: _Projects = {}
        self.project_name_index: Dict[str, int] = {}
        self.next_task_id = next_task_id
        self.tasks: _Tasks = {}
        self.task_name_index: Dict[Tuple[int, str], int] = {}
        self.next_model_id = next_model_id
        self.models: _Models = {}
        self.model_name_index: Dict[Tuple[int, str], int] = {}
        self.next_image_id = next_image_id
        self.images: _Images = {}
        self.image_name_index: Dict[Tuple[int, str], int] = {}
        self.next_environment_id = next_environment_id
        self.environments: _Environments = {}
        self.environment_name_index: Dict[str, int] = {}
        self.next_instance_id = next_instance_id
        self.instances: _Instances = {}
        self.instance_name_index: Dict[Tuple[int, int, str], int] = {}
        self.instance_index: Dict[Tuple[int, int], Set[int]] = {}
        self.image_instance: Dict[int, Set[int]] = {}
        self.environment_instance: Dict[int, Set[int]] = {}

        for p in (projects or {}).values():
            self.add_project(p)

        for t in (tasks or {}).values():
            self.add_task(t)

        for m in (models or {}).values():
            self.add_model(m)

        for i in (images or {}).values():
            self.add_image(i)

        for e in (environments or {}).values():
            self.add_environment(e)

        for i in (instances or {}).values():
            self.add_instance(i)

    def get_and_increment(self, name):
        next_id = getattr(self, name)
        setattr(self, name, next_id + 1)
        return next_id

    def add_project(self, project: Project):
        assert project.id is not None
        self.projects[project.id] = project
        self.project_name_index[project.name] = project.id

    def get_project_by_id(self, project_id):
        return self.projects.get(project_id)

    def get_project_by_name(self, name: str):
        return self.get_project_by_id(self.project_name_index.get(name, None))

    def remove_project(self, project_id):
        project = self.projects.pop(project_id, None)
        del self.project_name_index[project.name]
        return project

    def add_task(self, task: Task):
        assert task.id is not None
        self.tasks[task.id] = task
        self.task_name_index[(task.project_id, task.name)] = task.id
        self.projects[task.project_id]._tasks.add(task)

    def get_task_by_id(self, task_id):
        return self.tasks.get(task_id)

    def get_task_by_name(self, project_id: int, name: str):
        return self.get_task_by_id(self.task_name_index.get((project_id, name), None))

    def remove_task(self, task_id):
        task = self.tasks.pop(task_id, None)

        self.task_name_index.pop((task.project_id, task.name), None)
        return task

    def add_model(self, model: Model):
        assert model.id is not None
        self.models[model.id] = model
        self.model_name_index[(model.task_id, model.name)] = model.id
        self.tasks[model.task_id]._models.add(model)

    def get_model_by_id(self, model_id):
        return self.models.get(model_id, None)

    def get_model_by_name(self, task_id: int, name: str):
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

    def get_image_by_name(self, model_id: int, name: str):
        return self.get_image_by_id(self.image_name_index.get((model_id, name), None))

    def remove_image(self, image_id):
        image = self.images.pop(image_id, None)
        self.image_name_index.pop((image.model_id, image.name), None)
        return image

    def add_environment(self, environment: RuntimeEnvironment):
        assert environment.id is not None
        self.environments[environment.id] = environment
        self.environment_name_index[environment.name] = environment.id

    def get_environment_by_id(self, environment_id):
        return self.environments.get(environment_id)

    def get_environment_by_name(self, name: str):
        return self.get_environment_by_id(self.environment_name_index.get(name, None))

    def remove_environment(self, environment_id):
        environment = self.environments.pop(environment_id, None)
        del self.environment_name_index[environment.name]
        return environment

    def add_instance(self, instance: RuntimeInstance):
        assert instance.id is not None
        self.instances[instance.id] = instance
        self.instance_name_index[(instance.environment_id, instance.image_id, instance.name)] = instance.id
        self.instance_index.setdefault((instance.environment_id, instance.image_id), set()).add(instance.id)
        self.environment_instance.setdefault(instance.environment_id, set()).add(instance.id)
        self.image_instance.setdefault(instance.image_id, set()).add(instance.id)

    def get_instance_by_id(self, instance_id: int):
        return self.instances.get(instance_id, None)

    def get_instance_by_name(self, environment_id: int, image_id: int, name: str):
        return self.get_instance_by_id(self.instance_name_index.get((environment_id, image_id, name), None))

    def get_instances(self, environment_id: int, image_id: int):
        return [self.get_instance_by_id(iid) for iid in self.instance_index.get((environment_id, image_id), set())]

    def get_instances_by_image_id(self, image_id):
        return [self.get_instance_by_id(iid) for iid in self.image_instance.get(image_id, set())]

    def get_instances_by_environment_id(self, environment_id):
        return [self.get_instance_by_id(iid) for iid in self.environment_instance.get(environment_id, set())]

    def remove_instance(self, instance_id: int):
        instance = self.instances.pop(instance_id, None)
        self.instance_name_index.pop((instance.environment_id, instance.image_id, instance.name), None)
        self.instance_index[(instance.environment_id, instance.image_id)].discard(instance_id)
        self.environment_instance[instance.environment_id].discard(instance_id)
        self.image_instance[instance.image_id].discard(instance_id)
        return instance


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

        self.data: _LocalContainer = _LocalContainer()
        self.load()
        self.save()

    def load(self):
        if self.path is not None and os.path.exists(self.path):
            with open(self.path, 'r', encoding='utf8') as f:
                logger.debug('Loading metadata from %s', self.path)
                self.data = pyjackson.load(f, _LocalContainer)
        else:
            self.data = _LocalContainer()

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
        project._id = self.data.get_and_increment('next_project_id')
        self.data.add_project(copy.deepcopy(project))
        self.save()
        return project

    def update_project(self, project: Project) -> Project:
        existing_project = self.get_project_by_id(project.id)
        if existing_project is None:
            raise NonExistingProjectError(project)

        self.data.remove_project(project.id)
        proj_copy = copy.deepcopy(project)
        self.data.add_project(proj_copy)
        for task in proj_copy.tasks.values():
            self.save_task(task)
        self.save()
        return project

    def delete_project(self, project: Project):
        try:
            if self.get_tasks(project):
                raise ProjectWithTasksError(project)
            self.data.remove_project(project.id)
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

        task._id = self.data.get_and_increment('next_task_id')
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

        self.data.remove_task(task.id)
        task_copy = copy.deepcopy(task)
        self.data.add_task(task_copy)
        for model in task_copy.models.values():
            self.save_model(model)
        self.save()
        return task

    def delete_task(self, task: Task):
        if task.id is None:
            raise NonExistingTaskError(task)
        if self.get_models(task):
            raise TaskWithModelsError(task)
        self.data.remove_task(task.id)
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

        model._id = self.data.get_and_increment('next_model_id')
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
        if self.get_images(model):
            raise ModelWithImagesError(model)
        self.data.remove_model(model.id)
        self.save()
        model.unbind_meta_repo()

    @bind_to_self
    def get_images(self, model: ModelVar, task: TaskVar = None, project: ProjectVar = None) -> List[Image]:
        model = self._resolve_model(model, task, project)
        return copy.deepcopy(list(model.images.values()))

    @bind_to_self
    def get_image_by_name(self, image_name, model: ModelVar, task: TaskVar = None, project: ProjectVar = None) -> \
            Optional[Image]:
        model = self._resolve_model(model, task, project)
        if model is None:
            return None
        return copy.deepcopy(self.data.get_image_by_name(model.id, image_name))

    @bind_to_self
    def get_image_by_id(self, id: int) -> Optional[Image]:
        return copy.deepcopy(self.data.get_image_by_id(id))

    @bind_to_self
    def create_image(self, image: Image) -> Image:
        self._validate_image(image)

        existing_model = self.get_model_by_id(image.model_id)
        if existing_model is None:
            raise NonExistingModelError(image.model_id)

        if self.get_image_by_name(image.name, existing_model) is not None:
            raise ExistingImageError(image)

        image._id = self.data.get_and_increment('next_image_id')
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
        if self.data.get_instances_by_image_id(image.id):
            raise ImageWithInstancesError(image)
        if image.id is None:
            raise NonExistingImageError(image)
        self.data.remove_image(image.id)
        self.save()
        image.unbind_meta_repo()

    @bind_to_self
    def get_environments(self) -> List[RuntimeEnvironment]:
        return copy.deepcopy([self.data.get_environment_by_id(e) for e in self.data.environments.keys()])

    @bind_to_self
    def get_environment_by_name(self, name) -> Optional[RuntimeEnvironment]:
        return copy.deepcopy(self.data.get_environment_by_name(name))

    @bind_to_self
    def get_environment_by_id(self, id: int) -> Optional[RuntimeEnvironment]:
        return copy.deepcopy(self.data.get_environment_by_id(id))

    @bind_to_self
    def create_environment(self, environment: RuntimeEnvironment) -> RuntimeEnvironment:
        self._validate_environment(environment)

        if self.get_environment_by_name(environment.name) is not None:
            raise ExistingEnvironmentError(environment)
        environment._id = self.data.get_and_increment('next_environment_id')
        self.data.add_environment(copy.deepcopy(environment))
        self.save()
        return environment

    def update_environment(self, environment: RuntimeEnvironment) -> RuntimeEnvironment:
        self._validate_environment(environment)

        existing_environment = self.get_environment_by_id(environment.id)
        if existing_environment is None:
            raise NonExistingEnvironmentError(environment)

        self.data.remove_environment(environment.id)
        self.data.add_environment(copy.deepcopy(environment))
        self.save()
        return environment

    def delete_environment(self, environment: RuntimeEnvironment):
        if self.data.get_instances_by_environment_id(environment.id):
            raise EnvironmentWithInstancesError(environment)
        try:
            self.data.remove_environment(environment.id)
            self.save()
            environment.unbind_meta_repo()
        except (KeyError, AttributeError):
            raise NonExistingEnvironmentError(environment)

    @bind_to_self
    def get_instances(self, image: Union[int, Image] = None, environment: Union[int, RuntimeEnvironment] = None) \
            -> List[RuntimeInstance]:
        if image is None and environment is None:
            raise ValueError('Image and environment were not provided to the function')
        if image is not None:
            image = image.id if isinstance(image, Image) else image
        if environment is not None:
            environment = environment.id if isinstance(environment, RuntimeEnvironment) else environment

        if image is not None and environment is not None:
            return self.data.get_instances(environment, image)
        elif image is not None:
            return self.data.get_instances_by_image_id(image)
        else:
            return self.data.get_instances_by_environment_id(environment)

    @bind_to_self
    def get_instance_by_name(self, instance_name, image: Union[int, Image],
                             environment: Union[int, RuntimeEnvironment]) -> Optional[RuntimeInstance]:
        image = image.id if isinstance(image, Image) else image
        environment = environment.id if isinstance(environment, RuntimeEnvironment) else environment
        return self.data.get_instance_by_name(environment, image, instance_name)

    @bind_to_self
    def get_instance_by_id(self, id: int) -> Optional[RuntimeInstance]:
        return self.data.get_instance_by_id(id)

    @bind_to_self
    def create_instance(self, instance: RuntimeInstance) -> RuntimeInstance:
        self._validate_instance(instance)

        image = self.get_image_by_id(instance.image_id)
        if image is None:
            raise NonExistingImageError(instance.image_id)

        environment = self.get_environment_by_id(instance.environment_id)
        if environment is None:
            raise NonExistingEnvironmentError(instance.environment_id)

        if self.get_instance_by_name(instance.name, image, environment) is not None:
            raise ExistingInstanceError(instance)

        instance._id = self.data.get_and_increment('next_instance_id')
        self.data.add_instance(copy.deepcopy(instance))
        self.save()
        return instance

    def update_instance(self, instance: RuntimeInstance) -> RuntimeInstance:
        self._validate_instance(instance)

        existing_instance = self.get_instance_by_id(instance.id)
        if existing_instance is None:
            raise NonExistingInstanceError(instance)

        self.data.remove_instance(instance.id)
        self.data.add_instance(copy.deepcopy(instance))
        self.save()
        return instance

    def delete_instance(self, instance: RuntimeInstance):
        try:
            self.data.remove_instance(instance.id)
            self.save()
            instance.unbind_meta_repo()
        except (KeyError, AttributeError):
            raise NonExistingInstanceError(instance)
