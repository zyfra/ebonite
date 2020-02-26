import contextlib
from typing import List, Optional, Type, TypeVar, Union

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ebonite.core.errors import (ExistingEnvironmentError, ExistingImageError, ExistingInstanceError,
                                 ExistingModelError, ExistingProjectError, ExistingTaskError,
                                 NonExistingEnvironmentError, NonExistingImageError, NonExistingInstanceError,
                                 NonExistingModelError, NonExistingProjectError, NonExistingTaskError)
from ebonite.core.objects.core import EboniteObject, Image, Model, Project, RuntimeEnvironment, RuntimeInstance, Task
from ebonite.repository.metadata import MetadataRepository
from ebonite.repository.metadata.base import ModelVar, ProjectVar, TaskVar, bind_to_self
from ebonite.utils.log import logger

from .models import (Attaching, Base, SImage, SModel, SProject, SRuntimeEnvironment, SRuntimeInstance, STask,
                     update_attrs)

T = TypeVar('T', bound=EboniteObject)


class SQLAlchemyMetaRepository(MetadataRepository):
    """
    :class:`.MetadataRepository` implementation which stores metadata in SQL database via `sqlalchemy` library.

    :param db_uri: URI of SQL database to connect to
    """

    type = 'sqlalchemy'

    projects: Type[SProject] = SProject
    tasks: Type[STask] = STask
    models: Type[SModel] = SModel
    images: Type[SImage] = SImage
    environments: Type[SRuntimeEnvironment] = SRuntimeEnvironment
    instances: Type[SRuntimeInstance] = SRuntimeInstance

    def __init__(self, db_uri: str):
        self.db_uri = db_uri
        self._engine = create_engine(db_uri)
        Base.metadata.create_all(self._engine)
        self._Session = sessionmaker(bind=self._engine)
        self._active_session = None

    @contextlib.contextmanager
    def _session(self, commit=True) -> Session:
        if self._active_session is None:
            logger.debug('Creating session for %s', self.db_uri)
            self._active_session = self._Session()
            new_session = True
        else:
            new_session = False
        yield self._active_session
        if commit:
            self._active_session.commit()
        if new_session:
            self._active_session.close()
            self._active_session = None

    def _get_objects(self, object_type: Type[Attaching], add_filter=None) -> List:
        with self._session() as s:
            if add_filter is None:
                logger.debug('Getting %ss', object_type.__name__)
            else:
                logger.debug('Getting %ss with filter %s', object_type.__name__, add_filter)
            q = s.query(object_type)
            if add_filter:
                q = q.filter(add_filter)
            return [o.to_obj() for o in q.all()]

    def _get_object_by_name(self, object_type: Type[Attaching], name, add_filter=None):
        with self._session() as s:
            if add_filter is None:
                logger.debug('Getting %s with name %s', object_type.__name__, name)
            else:
                logger.debug('Getting %s with name %s with filter %s', object_type.__name__, name, add_filter)
            q = s.query(object_type).filter(object_type.name == name)
            if add_filter is not None:
                q = q.filter(add_filter)
            obj = q.first()
            if obj is None:
                return
            return obj.to_obj()

    def _get_sql_object_by_id(self, object_type: Type[Attaching], id: str):
        with self._session() as s:
            logger.debug('Getting %s[%s]', object_type.__name__, id)
            obj = s.query(object_type).filter(object_type.id == id).first()
            if obj is None:
                return
            return obj

    def _get_object_by_id(self, object_type: Type[Attaching], id: str):
        with self._session():
            sql_obj = self._get_sql_object_by_id(object_type, id)
            return sql_obj.to_obj() if sql_obj is not None else None

    def _create_object(self, object_type: Type[Attaching], obj: T, error_type) -> T:
        with self._session(False) as s:
            p = object_type.from_obj(obj, new=True)
            s.add(p)
            try:
                logger.debug('Inserting object %s', p)
                s.commit()
            except IntegrityError:
                raise error_type(obj)
            obj._id = str(p.id)
            return obj

    def _delete_object(self, object_type: Type[Attaching], obj, error_type):
        with self._session() as s:
            p = s.query(object_type).filter(object_type.id == obj.id).first()
            if p is None:
                raise error_type(obj)
            logger.debug('Deleting object %s', p)
            s.delete(p)

    @bind_to_self
    def get_projects(self) -> List[Project]:
        return self._get_objects(self.projects)

    @bind_to_self
    def get_project_by_name(self, name: str) -> Optional[Project]:
        return self._get_object_by_name(self.projects, name)

    @bind_to_self
    def get_project_by_id(self, id: str) -> Optional[Project]:
        return self._get_object_by_id(self.projects, id)

    @bind_to_self
    def create_project(self, project: Project) -> Project:
        self._validate_project(project)
        return self._create_object(self.projects, project, ExistingProjectError)

    def update_project(self, project: Project) -> Project:
        with self._session() as s:
            p: SProject = self._get_sql_object_by_id(self.projects, project.id)
            if p is None:
                raise NonExistingProjectError(project)
            kwargs = SProject.get_kwargs(project)
            kwargs.pop('tasks', None)

            update_attrs(p, **kwargs)
            s.commit()
            for t in p.tasks:
                tid = str(t.id)
                if tid in project.tasks:
                    self.update_task(project.tasks.get(tid))
                else:
                    project._tasks.add(t.to_obj())
            return project

    def delete_project(self, project: Project):
        self._delete_object(self.projects, project, NonExistingProjectError)
        project.unbind_meta_repo()

    @bind_to_self
    def get_tasks(self, project: ProjectVar) -> List[Task]:
        project = self._resolve_project(project)
        return self._get_objects(self.tasks, self.tasks.project_id == project.id)

    @bind_to_self
    def get_task_by_name(self, project: ProjectVar, task_name: str) -> Optional[Task]:
        p = self._resolve_project(project)
        if p is None:
            return None
        return self._get_object_by_name(self.tasks, task_name, self.projects.id == p.id)

    @bind_to_self
    def get_task_by_id(self, id: str) -> Optional[Task]:
        return self._get_object_by_id(self.tasks, id)

    @bind_to_self
    def create_task(self, task: Task) -> Task:
        self._validate_task(task)
        return self._create_object(self.tasks, task, ExistingTaskError)

    def update_task(self, task: Task) -> Task:
        with self._session(False) as s:
            t: STask = self._get_sql_object_by_id(self.tasks, task.id)
            if t is None:
                raise NonExistingTaskError(task)
            kwargs = STask.get_kwargs(task)
            kwargs.pop('models', None)
            update_attrs(t, **kwargs)
            s.commit()
            for m in t.models:
                mid = str(m.id)
                if mid in task.models:
                    self.update_model(task.models.get(mid))
                else:
                    task._models.add(m.to_obj())
            return task

    def delete_task(self, task: Task):
        self._delete_object(self.tasks, task, NonExistingTaskError)
        task.unbind_meta_repo()

    @bind_to_self
    def get_models(self, task: TaskVar, project: ProjectVar = None) -> List[Model]:
        task = self._resolve_task(task, project)
        return self._get_objects(self.models, self.models.task_id == task.id)

    @bind_to_self
    def get_model_by_name(self, model_name, task: TaskVar, project: ProjectVar = None) -> Optional[Model]:
        task = self._resolve_task(task, project)
        if task is None:
            return None
        return self._get_object_by_name(self.models, model_name, self.tasks.id == task.id)

    @bind_to_self
    def get_model_by_id(self, id: str) -> Optional[Model]:
        return self._get_object_by_id(self.models, id)

    @bind_to_self
    def create_model(self, model: Model) -> Model:
        self._validate_model(model)
        return self._create_object(self.models, model, ExistingModelError)

    def update_model(self, model: Model) -> Model:
        with self._session(False) as s:
            m = self._get_sql_object_by_id(self.models, model.id)
            if m is None:
                raise NonExistingModelError(model)
            update_attrs(m, **SModel.get_kwargs(model))
            s.commit()
            return model

    def delete_model(self, model: Model):
        self._delete_object(self.models, model, NonExistingModelError)
        model.unbind_meta_repo()

    @bind_to_self
    def get_images(self, model: ModelVar, task: TaskVar = None, project: ProjectVar = None) -> List[Image]:
        model = self._resolve_model(model, task, project)
        return self._get_objects(self.images, self.images.model_id == model.id)

    @bind_to_self
    def get_image_by_name(self, image_name, model: ModelVar, task: TaskVar = None, project: ProjectVar = None) -> Optional[Image]:
        model = self._resolve_model(model, task, project)
        if model is None:
            return None
        return self._get_object_by_name(self.images, image_name, self.models.id == model.id)

    @bind_to_self
    def get_image_by_id(self, id: str) -> Optional[Image]:
        return self._get_object_by_id(self.images, id)

    @bind_to_self
    def create_image(self, image: Image) -> Image:
        self._validate_image(image)
        return self._create_object(self.images, image, ExistingImageError)

    def update_image(self, image: Image) -> Image:
        with self._session(False) as s:
            i = self._get_sql_object_by_id(self.images, image.id)
            if i is None:
                raise NonExistingImageError(image)
            update_attrs(i, **SImage.get_kwargs(image))
            s.commit()
            return image

    def delete_image(self, image: Image):
        self._delete_object(self.images, image, NonExistingImageError)
        image.unbind_meta_repo()

    @bind_to_self
    def get_environments(self) -> List[RuntimeEnvironment]:
        return self._get_objects(self.environments)

    @bind_to_self
    def get_environment_by_name(self, name) -> Optional[RuntimeEnvironment]:
        return self._get_object_by_name(self.environments, name)

    @bind_to_self
    def get_environment_by_id(self, id: str) -> Optional[RuntimeEnvironment]:
        return self._get_object_by_id(self.environments, id)

    @bind_to_self
    def create_environment(self, environment: RuntimeEnvironment) -> RuntimeEnvironment:
        self._validate_environment(environment)
        return self._create_object(self.environments, environment, ExistingEnvironmentError)

    def update_environment(self, environment: RuntimeEnvironment) -> RuntimeEnvironment:
        with self._session(False) as s:
            i = self._get_sql_object_by_id(self.environments, environment.id)
            if i is None:
                raise NonExistingEnvironmentError(environment)
            update_attrs(i, **SRuntimeEnvironment.get_kwargs(environment))
            s.commit()
            return environment

    def delete_environment(self, environment: RuntimeEnvironment):
        self._delete_object(self.environments, environment, NonExistingEnvironmentError)
        environment.unbind_meta_repo()

    @bind_to_self
    def get_instances(self, image: Union[str, Image], environment: Union[str, RuntimeEnvironment]) \
            -> List[RuntimeInstance]:
        image = image.id if isinstance(image, Image) else image
        environment = environment.id if isinstance(environment, RuntimeEnvironment) else environment
        return self._get_objects(self.instances, self.images.id == image and self.environments.id == environment)

    @bind_to_self
    def get_instance_by_name(self, instance_name, image: Union[str, Image],
                             environment: Union[str, RuntimeEnvironment]) -> Optional[RuntimeInstance]:
        image = image.id if isinstance(image, Image) else image
        environment = environment.id if isinstance(environment, RuntimeEnvironment) else environment
        return self._get_object_by_name(self.instances, instance_name,
                                        self.images.id == image and self.environments.id == environment)

    @bind_to_self
    def get_instance_by_id(self, id: str) -> Optional[RuntimeInstance]:
        return self._get_object_by_id(self.instances, id)

    @bind_to_self
    def create_instance(self, instance: RuntimeInstance) -> RuntimeInstance:
        self._validate_instance(instance)
        return self._create_object(self.instances, instance, ExistingInstanceError)

    def update_instance(self, instance: RuntimeInstance) -> RuntimeInstance:
        with self._session(False) as s:
            i = self._get_sql_object_by_id(self.instances, instance.id)
            if i is None:
                raise NonExistingInstanceError(instance)
            update_attrs(i, **SRuntimeInstance.get_kwargs(instance))
            s.commit()
            return instance

    def delete_instance(self, instance: RuntimeInstance):
        self._delete_object(self.instances, instance, NonExistingInstanceError)
        instance.unbind_meta_repo()
