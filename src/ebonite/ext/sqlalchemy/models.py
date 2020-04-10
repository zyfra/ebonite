from abc import abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar

from pyjackson import dumps, loads
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from ebonite.core.objects.artifacts import ArtifactCollection
from ebonite.core.objects.core import Image, Model, Project, RuntimeEnvironment, RuntimeInstance, Task
from ebonite.core.objects.requirements import Requirements

SQL_OBJECT_FIELD = '_sqlalchemy_object'


def json_column():
    return Column(Text)


def safe_loads(payload, as_class):
    return loads(payload, Optional[as_class])


def sqlobject(obj):
    return getattr(obj, SQL_OBJECT_FIELD, None)


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
        pass  # pragma: no cover

    @abstractmethod
    def to_obj(self) -> T:
        pass  # pragma: no cover


Base = declarative_base()


class SProject(Base, Attaching):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    author = Column(String, unique=False, nullable=False)
    creation_date = Column(DateTime, unique=False, nullable=False)

    tasks = relationship("STask", back_populates="project")

    def to_obj(self) -> Project:
        p = Project(self.name, id=self.id, author=self.author, creation_date=self.creation_date)
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
    name = Column(String, unique=False, nullable=False)
    author = Column(String, unique=False, nullable=False)
    creation_date = Column(DateTime, unique=False, nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)

    project = relationship("SProject", back_populates="tasks")
    models = relationship("SModel", back_populates="task")

    __table_args__ = (UniqueConstraint('name', 'project_id', name='tasks_name_and_ref'),)

    def to_obj(self) -> Task:
        task = Task(id=self.id,
                    name=self.name,
                    author=self.author,
                    creation_date=self.creation_date,
                    project_id=self.project_id)
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

    name = Column(String, unique=False, nullable=False)
    author = Column(String, unique=False, nullable=False)
    creation_date = Column(DateTime, unique=False, nullable=False)
    wrapper = Column(Text)

    artifact = Column(Text)
    requirements = Column(Text)
    description = Column(Text)
    params = Column(Text)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    task = relationship("STask", back_populates="models")
    images = relationship("SImage", back_populates="model")

    __table_args__ = (UniqueConstraint('name', 'task_id', name='models_name_and_ref'),)

    def to_obj(self) -> Model:
        model = Model(name=self.name,
                      wrapper_meta=safe_loads(self.wrapper, dict),
                      author=self.author,
                      creation_date=self.creation_date,
                      artifact=safe_loads(self.artifact, ArtifactCollection),
                      requirements=safe_loads(self.requirements, Requirements),
                      description=self.description,
                      params=safe_loads(self.params, Dict[str, Any]),
                      id=self.id,
                      task_id=self.task_id)
        for image in self.images:
            model._images.add(image.to_obj())
        return self.attach(model)

    @classmethod
    def get_kwargs(cls, model: Model) -> dict:
        return dict(id=model.id,
                    name=model.name,
                    author=model.author,
                    creation_date=model.creation_date,
                    wrapper=dumps(model.wrapper_meta),
                    artifact=dumps(model.artifact),
                    requirements=dumps(model.requirements),
                    description=model.description,
                    params=dumps(model.params),
                    task_id=model.task_id,
                    images=[SImage.from_obj(i) for i in model.images.values()])


class SImage(Base, Attaching):
    __tablename__ = 'images'

    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String, unique=False, nullable=False)
    author = Column(String, unique=False, nullable=False)
    creation_date = Column(DateTime, unique=False, nullable=False)

    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    model = relationship("SModel", back_populates="images")

    params = Column(Text)

    __table_args__ = (UniqueConstraint('name', 'model_id', name='image_name_and_ref'),)

    def to_obj(self) -> Image:
        image = Image(name=self.name,
                      author=self.author,
                      creation_date=self.creation_date,
                      id=self.id,
                      model_id=self.model_id,
                      params=safe_loads(self.params, Image.Params))
        return self.attach(image)

    @classmethod
    def get_kwargs(cls, image: Image) -> dict:
        return dict(id=image.id,
                    name=image.name,
                    author=image.author,
                    creation_date=image.creation_date,
                    model_id=image.model_id,
                    params=dumps(image.params))


class SRuntimeEnvironment(Base, Attaching):
    __tablename__ = 'environments'

    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String, unique=True, nullable=False)
    author = Column(String, unique=False, nullable=False)
    creation_date = Column(DateTime, unique=False, nullable=False)

    params = Column(Text)

    def to_obj(self) -> RuntimeEnvironment:
        environment = RuntimeEnvironment(
            name=self.name,
            author=self.author,
            creation_date=self.creation_date,
            id=self.id,
            params=safe_loads(self.params, RuntimeEnvironment.Params))
        return self.attach(environment)

    @classmethod
    def get_kwargs(cls, environment: RuntimeEnvironment) -> dict:
        return dict(id=environment.id,
                    name=environment.name,
                    author=environment.author,
                    creation_date=environment.creation_date,
                    params=dumps(environment.params))


class SRuntimeInstance(Base, Attaching):
    __tablename__ = 'instances'

    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String, unique=False, nullable=False)
    author = Column(String, unique=False, nullable=False)
    creation_date = Column(DateTime, unique=False, nullable=False)

    image_id = Column(Integer, ForeignKey('images.id'), nullable=False)
    environment_id = Column(Integer, ForeignKey('environments.id'), nullable=False)

    params = Column(Text)

    __table_args__ = (UniqueConstraint('name', 'image_id', 'environment_id', name='instance_name_and_ref'),)

    def to_obj(self) -> RuntimeInstance:
        instance = RuntimeInstance(
            name=self.name,
            author=self.author,
            creation_date=self.creation_date,
            id=self.id,
            image_id=self.image_id,
            environment_id=self.environment_id,
            params=safe_loads(self.params, RuntimeInstance.Params))
        return self.attach(instance)

    @classmethod
    def get_kwargs(cls, instance: RuntimeInstance) -> dict:
        return dict(id=instance.id,
                    name=instance.name,
                    author=instance.author,
                    creation_date=instance.creation_date,
                    image_id=instance.image_id,
                    environment_id=instance.environment_id,
                    params=dumps(instance.params))
