import contextlib
from typing import List, Optional, Type, TypeVar

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ebonite.core.errors import (ExistingModelError, ExistingProjectError, ExistingTaskError, NonExistingModelError,
                                 NonExistingProjectError, NonExistingTaskError)
from ebonite.core.objects.core import EboniteObject, Model, Project, Task
from ebonite.repository.metadata import MetadataRepository
from ebonite.repository.metadata.base import ProjectVar, TaskVar, bind_to_self
from ebonite.utils.log import logger

from .models import Attaching, Base, SModel, SProject, STask, update_attrs

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
