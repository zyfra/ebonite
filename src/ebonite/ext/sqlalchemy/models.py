import uuid
from abc import abstractmethod
from typing import Optional, Type, TypeVar

from pyjackson import dumps, loads
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from ebonite.core.objects.artifacts import ArtifactCollection
from ebonite.core.objects.core import Model, Project, Task
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.core.objects.requirements import Requirements
from ebonite.core.objects.wrapper import ModelWrapper

SQL_OBJECT_FIELD = '_sqlalchemy_object'


def generate_uuid():
    return str(uuid.uuid4())


def json_column():
    return Column(Text)


def safe_loads(payload, as_class):
    return loads(payload, Optional[as_class])


def sqlobject(obj):
    return getattr(obj, SQL_OBJECT_FIELD, None)


def tostr(s: int):
    if s is None:
        return None
    return str(s)


def update_attrs(obj, **attrs):
    for name, value in attrs.items():
        setattr(obj, name, value)


T = TypeVar('T')
S = TypeVar('S', bound='Attaching')


class Attaching:
    id = ...
    name = ...

    def attach(self, obj):
        setattr(obj, SQL_OBJECT_FIELD, self)
        return obj

    @classmethod
    def from_obj(cls: Type[S], obj: T, new=False) -> S:
        kwargs = cls.get_kwargs(obj)
        existing = sqlobject(obj)
        if not new and existing is not None:
            update_attrs(existing, **kwargs)
            return existing
        return cls(**kwargs)

    @classmethod
    @abstractmethod
    def get_kwargs(cls, obj: T) -> dict:
        pass

    @abstractmethod
    def to_obj(self) -> T:
        pass


Base = declarative_base()


class SProject(Base, Attaching):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    author = Column(String, unique=False, nullable=False)
    creation_date = Column(DateTime, unique=False, nullable=False)

    tasks = relationship("STask", back_populates="project")

    def to_obj(self) -> Project:
        p = Project(self.name, id=tostr(self.id), author=self.author, creation_date=self.creation_date)
        for task in self.tasks:
            p._tasks.add(task.to_obj())
        return self.attach(p)

    @classmethod
    def get_kwargs(cls, project: Project) -> dict:
        return dict(id=project.id,
                    name=project.name,
                    author=project.author,
                    creation_date=project.creation_date,
                    tasks=[STask.from_obj(t) for t in project.tasks.values()])


class STask(Base, Attaching):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    author = Column(String, unique=False, nullable=False)
    creation_date = Column(DateTime, unique=False, nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)

    project = relationship("SProject", back_populates="tasks")
    models = relationship("SModel", back_populates="task")

    def to_obj(self) -> Task:
        task = Task(id=tostr(self.id),
                    name=self.name,
                    author=self.author,
                    creation_date=self.creation_date,
                    project_id=tostr(self.project_id))
        for model in self.models:
            task._models.add(model.to_obj())
        return self.attach(task)

    @classmethod
    def get_kwargs(cls, task: Task) -> dict:
        return dict(id=task.id,
                    name=task.name,
                    author=task.author,
                    creation_date=task.creation_date,
                    project_id=task.project_id,
                    models=[SModel.from_obj(m) for m in task.models.values()])


class SModel(Base, Attaching):
    __tablename__ = 'models'

    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String, unique=True, nullable=False)
    author = Column(String, unique=False, nullable=False)
    creation_date = Column(DateTime, unique=False, nullable=False)
    wrapper = Column(Text)

    artifact = Column(Text)
    input_meta = Column(Text)
    output_meta = Column(Text)
    requirements = Column(Text)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    task = relationship("STask", back_populates="models")

    def to_obj(self) -> Model:
        model = Model(name=self.name,
                      author=self.author,
                      creation_date=self.creation_date,
                      wrapper=safe_loads(self.wrapper, ModelWrapper),
                      artifact=safe_loads(self.artifact, ArtifactCollection),
                      input_meta=safe_loads(self.input_meta, DatasetType),
                      output_meta=safe_loads(self.output_meta, DatasetType),
                      requirements=safe_loads(self.requirements, Requirements),
                      id=tostr(self.id),
                      task_id=tostr(self.task_id))
        return self.attach(model)

    @classmethod
    def get_kwargs(cls, model: Model) -> dict:
        return dict(id=model.id,
                    name=model.name,
                    author=model.author,
                    creation_date=model.creation_date,
                    wrapper=dumps(model.wrapper),
                    artifact=dumps(model.artifact_req_persisted),
                    input_meta=dumps(model.input_meta),
                    output_meta=dumps(model.output_meta),
                    requirements=dumps(model.requirements),
                    task_id=model.task_id)
