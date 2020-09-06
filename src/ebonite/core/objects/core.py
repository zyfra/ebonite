import datetime
import getpass
import json
import re
import tempfile
import time
import warnings
from abc import abstractmethod
from copy import copy
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from pyjackson import deserialize, serialize
from pyjackson.core import Comparable
from pyjackson.decorators import make_string, type_field

import ebonite.repository
from ebonite.client.expose import ExposedMethod
from ebonite.core import errors
from ebonite.core.analyzer.metric import MetricAnalyzer
from ebonite.core.analyzer.model import ModelAnalyzer
from ebonite.core.analyzer.requirement import RequirementAnalyzer
from ebonite.core.objects.artifacts import ArtifactCollection, CompositeArtifactCollection
from ebonite.core.objects.base import EboniteParams
from ebonite.core.objects.dataset_source import AbstractDataset, Dataset, DatasetSource, InMemoryDatasetSource
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.core.objects.metric import Metric
from ebonite.core.objects.requirements import AnyRequirements, Requirements, resolve_requirements
from ebonite.core.objects.wrapper import ModelWrapper, WrapperArtifactCollection
from ebonite.utils.index_dict import IndexDict, IndexDictAccessor
from ebonite.utils.log import logger
from ebonite.utils.module import get_python_version

AnyDataset = Union[str, AbstractDataset, DatasetSource, Any]
AnyMetric = Union[str, Metric, Any]


def _get_current_user():
    return getpass.getuser()


class ExposedObjectMethod(ExposedMethod):
    """Decorator for EboniteObject methods that will be exposed to Ebonite class by autogen

    :param name: name of the exposed method
    :param param_name: name of the first parameter
    :param param_type: type hint for the first parameter
    :param param_doc: docstring for the first parameter"""

    def __init__(self, name, param_name: str, param_type: str, param_doc: str = None):
        super().__init__(name)
        self.param_name = param_name
        self.param_type = param_type
        self.param_doc = param_doc

    def get_doc(self):
        doc = self.method.__doc__
        if self.param_doc is not None:
            if ':param' in doc:
                mark = ':param'
            elif ':' in doc:
                mark = ':'
            else:
                mark = None
            param_doc = f':param {self.param_name}: {self.param_doc}\n'
            if mark is not None:
                doc = re.sub(mark, param_doc + '        ' + mark, doc, count=1)
            else:
                doc += '\n\n        ' + param_doc + '        '
        return doc

    def generate_code(self):
        """Generates code for exposed Ebonite method"""
        declaration = self.get_declaration() \
            .replace(f'{self.name}(self', f'{self.name}(self, {self.param_name}: {self.param_type}')
        fields = self.get_signature().args
        result = f'''{self.param_name}.{self.original_name}({', '.join(f.name for f in fields)})'''
        return f'''    {declaration}
        """"{self.get_doc()}"""
        return {result}'''


class WithMetadataRepository:
    """Intermediat abstract class for objects that can be binded to meta repository"""
    _id = None
    _meta: 'ebonite.repository.MetadataRepository' = None
    _nested_fields_meta: List[str] = []

    def bind_meta_repo(self, repo: 'ebonite.repository.MetadataRepository'):
        self._meta = repo
        for field in self._nested_fields_meta:
            for obj in getattr(self, field).values():
                obj.bind_meta_repo(repo)
        return self

    def unbind_meta_repo(self):
        for field in self._nested_fields_meta:
            for obj in getattr(self, field).values():
                obj.unbind_meta_repo()
        del self._meta
        self._id = None

    @property
    def has_meta_repo(self):
        return self._meta is not None

    def _check_meta(self, saved=True):
        """Checks if object is binded to meta repo

        :param saved: force object to be also saved (have id)"""
        if (self._id is None and saved) or not self.has_meta_repo:
            raise errors.UnboundObjectError('{} is not bound to meta repository'.format(self))


class WithArtifactRepository:
    """Intermediat abstract class for objects that can be binded to artifact repository"""
    _art: 'ebonite.repository.ArtifactRepository' = None
    _nested_fields_art: List[str] = []

    def bind_artifact_repo(self, repo: 'ebonite.repository.ArtifactRepository'):
        self._art = repo
        for field in self._nested_fields_art:
            for obj in getattr(self, field).values():
                obj.bind_artifact_repo(repo)
        return self

    def unbind_artifact_repo(self):
        for field in self._nested_fields_art:
            for obj in getattr(self, field).values():
                obj.unbind_artifact_repo()
        del self._art

    @property
    def has_artifact_repo(self):
        return self._art is not None


class WithDatasetRepository:
    """Intermediat abstract class for objects that can be binded to dataset repository"""
    _dataset: 'ebonite.repository.DatasetRepository' = None
    _nested_fields_dataset: List[str] = []

    def bind_dataset_repo(self, repo: 'ebonite.repository.DatasetRepository'):
        self._dataset = repo
        for field in self._nested_fields_dataset:
            for obj in getattr(self, field).values():
                obj.bind_dataset_repo(repo)
        return self

    def unbind_dataset_repo(self):
        for field in self._nested_fields_dataset:
            for obj in getattr(self, field).values():
                obj.unbind_dataset_repo()
        del self._dataset

    @property
    def has_dataset_repo(self):
        return self._dataset is not None


class EboniteObject(Comparable, WithMetadataRepository, WithArtifactRepository):
    """
    Base class for high level ebonite objects.
    These objects can be binded to metadata repository and/or to artifact repository

    :param id: object id
    :param name: object name
    :param author: user that created that object
    :param creation_date: date when this object was created
    """

    def __init__(self, id: int, name: str, author: str = None, creation_date: datetime.datetime = None):
        self._id = id
        self.name = name
        self.author = author or _get_current_user()
        self.creation_date = creation_date or datetime.datetime.utcnow()  # TODO local timezone

    @property
    def id(self) -> int:
        return self._id

    def bind_as(self, other: 'EboniteObject'):
        if other.has_meta_repo:
            self.bind_meta_repo(other._meta)
        if other.has_artifact_repo:
            self.bind_artifact_repo(other._art)
        return self

    @abstractmethod
    def save(self):
        """Saves object state to metadata repository"""

    @abstractmethod
    def has_children(self):
        """Checks if object has existing relationship"""


def _with_meta(saved=True):
    """
    Decorator for methods to check that object is binded to meta repo

    :param saved: method to apply decorator
    """

    def dec(method):
        @wraps(method)
        def inner(self: EboniteObject, *args, **kwargs):
            self._check_meta(saved)
            return method(self, *args, **kwargs)

        return inner

    return dec(saved) if callable(saved) else dec


def _with_artifact(method):
    """
    Decorator for methods to check that object is binded to artifact repo

    :param method: method to apply decorator
    :return: decorated method
    """

    @wraps(method)
    def inner(self: EboniteObject, *args, **kwargs):
        if not self.has_artifact_repo:
            raise errors.UnboundObjectError('{} is not bound to artifact repository'.format(self))
        return method(self, *args, **kwargs)

    return inner


def _with_dataset(method):
    """
    Decorator for methods to check that object is binded to dataset repo

    :param method: method to apply decorator
    :return: decorated method
    """

    @wraps(method)
    def inner(self: WithDatasetRepository, *args, **kwargs):
        if not self.has_dataset_repo:
            raise errors.UnboundObjectError('{} is not bound to dataset repository'.format(self))
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
    _nested_fields_meta = _nested_fields_art = ['_tasks']

    def __init__(self, name: str, id: int = None, author: str = None, creation_date: datetime.datetime = None):
        super().__init__(id, name, author, creation_date)
        self._tasks: IndexDict[Task] = IndexDict('id', 'name')
        self.tasks: IndexDictAccessor[Task] = IndexDictAccessor(self._tasks)

    @_with_meta
    @ExposedObjectMethod(name='delete_project', param_name='project', param_type='Project',
                         param_doc='project to delete')
    def delete(self, cascade: bool = False):
        """
        Deletes project and(if required) all tasks associated with it from metadata repository

        :param cascade: whether should project be deleted with all associated tasks
        :return: Nothing
        """
        if cascade:
            for task in self._meta.get_tasks(self):  # TODO cacheing?
                self.delete_task(task, cascade=cascade)
                # task.delete(cascade=cascade) # FIXME
        self._meta.delete_project(self)

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
        return task.bind_as(self)

    @_with_meta
    def add_tasks(self, tasks: List['Task']):
        """
        Add multiple tasks and save them to meta repo

        :param tasks: tasks to add
        """
        for t in tasks:
            self.add_task(t)

    @_with_meta
    def delete_task(self, task: 'Task', cascade: bool = False):
        """
        Remove task from this project and delete it from meta repo

        :param cascade: whether task should be deleted with all nested objects
        :param task: task to delete
        """
        if task.id not in self._tasks:
            raise errors.NonExistingTaskError(task)
        del self._tasks[task.id]
        task.delete(cascade)
        task.project_id = None

    @_with_meta
    def save(self):
        self._meta.save_project(self)

    def has_children(self):
        return len(self.tasks) > 0

    def __repr__(self):
        return """Project '{name}', {td} tasks""".format(name=self.name, td=len(self.tasks))


class EvaluationSet(EboniteParams):
    """Represents a set of objects for evaluation

    :param input_dataset: name of the input dataset
    :param output_dataset: name of the output dataset
    :param metrics: list of metric names"""

    def __init__(self, input_dataset: str, output_dataset: str, metrics: List[str]):
        self.output_dataset = output_dataset
        self.metrics = metrics
        self.input_dataset = input_dataset

    def get(self, task: 'Task', cache=True) -> Tuple[DatasetSource, DatasetSource, Dict[str, Metric]]:
        """Loads actual datasets and metrics from task

        :param task: task to load from
        :param cache: wheter to cache datasets"""
        input = task.datasets[self.input_dataset]
        output = task.datasets[self.output_dataset]
        if cache:
            input = input.cache()
            output = output.cache()
        return input, output, {m: task.metrics[m] for m in self.metrics}


@make_string('id', 'name')
class Task(EboniteObject, WithDatasetRepository):
    """
    Task is a collection of models

    :param id: task id
    :param name: task name
    :param project_id: parent project id for this task
    :param author: user that created that task
    :param creation_date: date when this task was created
    """
    _nested_fields_meta = _nested_fields_art = ['_models', '_pipelines', '_images']

    def __init__(self, name: str, id: int = None, project_id: int = None,
                 author: str = None, creation_date: datetime.datetime = None,
                 datasets: Dict[str, DatasetSource] = None,
                 metrics: Dict[str, Metric] = None,
                 evaluation_sets: Dict[str, EvaluationSet] = None):
        super().__init__(id, name, author, creation_date)
        self.evaluation_sets = evaluation_sets or {}
        self.datasets = datasets or {}
        self.metrics = metrics or {}
        self.project_id = project_id
        self._models: IndexDict[Model] = IndexDict('id', 'name')
        self.models: IndexDictAccessor[Model] = IndexDictAccessor(self._models)
        self._pipelines: IndexDict[Pipeline] = IndexDict('id', 'name')
        self.pipelines: IndexDictAccessor[Pipeline] = IndexDictAccessor(self._pipelines)
        self._images: IndexDict[Image] = IndexDict('id', 'name')
        self.images: IndexDictAccessor[Image] = IndexDictAccessor(self._images)

    @property
    @_with_meta
    def project(self):
        p = self._meta.get_project_by_id(self.project_id)
        if p is None:
            raise errors.NonExistingProjectError(self.project_id)
        return p.bind_artifact_repo(self._art)

    @project.setter
    def project(self, project: Project):
        if not isinstance(project, Project):
            raise ValueError('{} is not Project'.format(project))
        self.project_id = project.id
        self.bind_as(project)

    @_with_meta
    @ExposedObjectMethod(name='delete_task', param_name='task', param_type='Task', param_doc='task to delete')
    def delete(self, cascade: bool = False):
        """
        Deletes task from metadata

        :param cascade: whether should task be deleted with all associated objects
        :return: Nothing
        """
        if cascade:
            for model in self._meta.get_models(self):
                self.delete_model(model.bind_artifact_repo(self._art))
            for image in self._meta.get_images(self):
                self.delete_image(image, cascade=cascade)
            for pipeline in self._meta.get_pipelines(self):
                self.delete_pipeline(pipeline)

        for dataset in self.datasets:
            self.delete_dataset(dataset, force=True, save=False)

        self._meta.delete_task(self)

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
        return model.bind_as(self)

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

        model.delete(force)
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
        model.bind_as(self)
        model = model.push(self)
        self._models.add(model)
        return model

    @_with_meta
    def add_pipeline(self, pipeline: 'Pipeline'):
        """
        Add model to task and save it to meta repo

        :param pipeline: pipeline to add
        """
        if pipeline.task_id is not None and pipeline.task_id != self.id:
            raise errors.MetadataError('Pipeline is already in task {}. Delete it first'.format(pipeline.task_id))

        pipeline.task_id = self.id
        self._meta.save_pipeline(pipeline)
        self._pipelines.add(pipeline)

    @_with_meta
    def add_pipelines(self, pipelines: List['Pipeline']):
        """
        Add multiple models and save them to meta repo

        :param pipelines: pipelines to add
        """
        for m in pipelines:
            self.add_pipeline(m)

    @_with_meta
    def delete_pipeline(self, pipeline: 'Pipeline'):
        """
        Remove model from this task and delete it from meta repo

        :param pipeline: pipeline to delete
        """
        pipeline_id = pipeline.id
        if pipeline_id not in self._pipelines:
            raise errors.NonExistingPipelineError(pipeline)

        pipeline.delete()
        del self._pipelines[pipeline_id]
        pipeline.task_id = None

    @_with_meta
    def add_image(self, image: 'Image'):
        """
        Add image for model and save it to meta repo

        :param image: image to add
        """
        if image.task_id is not None and image.task_id != self.id:
            raise errors.MetadataError('Image is already in task {}. Delete it first'.format(image.task_id))

        image.task_id = self.id
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
    def delete_image(self, image: 'Image', meta_only: bool = False, cascade: bool = False):
        """
        Remove image from this model and delete it from meta repo

        :param image: image to delete
        :param meta_only: should image be deleted only from metadata
        :param cascade: whether image should be deleted with all instances
        """
        if image.id not in self._images:
            raise errors.NonExistingImageError(image)
        del self._images[image.id]
        image.delete(meta_only=meta_only, cascade=cascade)
        image.task_id = None

    @_with_meta
    def save(self):
        """Saves task to meta repository and pushes unsaved datasets to dataset repository"""
        self.push_datasets()
        self._meta.save_task(self)

    def has_children(self):
        return len(self.models) > 0 or len(self.pipelines) > 0 or len(self.images) > 0

    def _resolve_dataset(self, dataset: AnyDataset, name: str) -> str:
        """Resolves existing dataset or creates a new one

        :param dataset: dataset name, Dataset, DatasetSource or raw data object
        :param name: name for dataset if it is new
        """
        if isinstance(dataset, str):
            if dataset not in self.datasets:
                raise ValueError(f'no dataset named {dataset} in task {self}')  # TODO maybe ohter error?
            return dataset

        self.add_dataset(name, dataset)
        return name

    def _resolve_metric(self, metric: AnyMetric, name: str):
        """Resolves existing metric or creates a new one

        :param metric: metric name, Metric or raw metric object
        :param name: name for metric if it is new
        """
        if isinstance(metric, str):
            if metric not in self.metrics:
                raise ValueError(f'no metric named {metric} in task {self}')  # TODO maybe ohter error?
            return metric
        self.add_metric(name, metric)
        return name

    def add_evaluation(self, name: str,
                       data: AnyDataset,
                       target: AnyDataset,
                       metrics: Union[AnyMetric, List[AnyMetric]]):
        """Adds new evaluation set to this task

        :param name: name of the evaluation set
        :param data: input dataset for evaluation
        :param target: ground truth for input data
        :param metrics: one or more metrics to measure
        """
        if name in self.evaluation_sets:
            raise errors.EboniteError(f'evalset {name} already in task {self}')
        data = self._resolve_dataset(data, f'{name}_input')
        target = self._resolve_dataset(target, f'{name}_output')
        if not isinstance(metrics, list):
            metrics = [metrics]
        metrics = [self._resolve_metric(m, f'{name}_{i}') for i, m in enumerate(metrics)]
        self.evaluation_sets[name] = EvaluationSet(data, target, metrics)

    def delete_evaluation(self, name: str, save: bool = True):
        """Deletes evaluation set from task

        :param name: name of the evaluation to delete
        :param save: also update task metadata in repo
        """
        if save:
            self._check_meta()

        if name not in self.evaluation_sets:
            raise errors.EboniteError(f'cannot delete evalset from task {self}: no evalset with name {name}')
        del self.evaluation_sets[name]
        if save:
            self.save()

    @_with_dataset
    def add_dataset(self, name, dataset: Union[DatasetSource, AbstractDataset, Any]):
        """Adds new dataset to this task

        :param name: name of the dataset
        :param dataset: Dataset, DatasetSource or raw dataset object
        """
        if name in self.datasets:
            raise errors.EboniteError(f'dataset {name} already in task {self}')
        if not isinstance(dataset, DatasetSource):
            if not isinstance(dataset, AbstractDataset):
                dataset = Dataset.from_object(dataset)
            dataset = dataset.to_inmemory_source()
        self.datasets[name] = dataset

    @_with_dataset
    def push_datasets(self):
        """Pushes all unsaved datasets to dataset repository"""
        for name, dataset in list(self.datasets.items()):
            if isinstance(dataset, InMemoryDatasetSource):
                self.datasets[name] = self._dataset.save(f'{self.id}/{name}', dataset.read())

    @_with_dataset
    def delete_dataset(self, name: str, force: bool = False, save: bool = True):
        """Deletes dataset from task with artifacts

        :param name: name of the dataset to delete
        :param force: wheter to check evalsets that use this dataset and remove them or raise error
        :param save: also update task metadata in repo
        """
        if name not in self.datasets:
            raise errors.EboniteError(f'cannot delete dataset from {self}: no dataset with name {name}')
        if save:
            self._check_meta()
        evalsets = {n: es for n, es in self.evaluation_sets.items() if
                    name in (es.input_dataset, es.output_dataset)}
        if len(evalsets) > 0 and not force:
            raise errors.EboniteError(
                f'cannot delete dataset from {self}: it is used by evalsets {list(evalsets.keys())}'
                f'remove them or set force=True')
        try:
            self._dataset.delete(f'{self.id}/{name}')
        except errors.NoSuchDataset:
            pass  # already deleted or was not saved
        del self.datasets[name]
        for es in evalsets.keys():
            self.delete_evaluation(es, save)
        if save:
            self.save()

    def add_metric(self, name, metric: Union[Metric, Any]):
        """Adds metric to this task

        :param name: name of the metric
        :param metric: Metric or raw metric object
        """
        if name in self.metrics:
            raise errors.EboniteError(f'metric {name} already in task {self}')
        if not isinstance(metric, Metric):
            metric = MetricAnalyzer.analyze(metric)
        # TODO checks
        self.metrics[name] = metric

    def delete_metric(self, name: str, force: bool = False, save: bool = True):
        """Deletes metric from task

        :param name: name of the metric to delete
        :param force: wheter to check evalsets that use this metric and remove them or raise error
        :param save: also update task metadata in repo
        """
        if name not in self.metrics:
            raise errors.EboniteError(f'cannot delete metric from {self}: no metric with name {name}')
        if save:
            self._check_meta()
        evalsets = {n: es for n, es in self.evaluation_sets.items() if
                    name in es.metrics}

        if len(evalsets) > 0 and not force:
            raise errors.EboniteError(
                f'cannot delete metric from {self}: it is used by evalsets {list(evalsets.keys())}'
                f'remove them or set force=True')
        del self.metrics[name]
        for es in evalsets.keys():
            self.delete_evaluation(es, save)
        if save:
            self.save()

    def evaluate_all(self, force=False, save_result=True) -> Dict[str, 'EvaluationResult']:
        """Evaluates all viable pairs of evalsets and models/pipelines

        :param force: force reevaluate already evaluated
        :param save_result: save evaluation results to meta"""
        result = {}
        timestamp = time.time()
        for name, evalset in self.evaluation_sets.items():
            input, output, metrics = evalset.get(self, cache=True)
            for model in self._models.values():
                evaluate = model.evaluate(input, output, metrics, evaluation_name=name,
                                          timestamp=timestamp, force=force, save=save_result)
                if isinstance(evaluate, dict):
                    for method, res in evaluate.items():
                        result[f'{model.name}.{method}'] = res
                elif isinstance(evaluate, EvaluationResult):
                    result[model.name] = evaluate
            for pipeline in self._pipelines.values():
                evaluate = pipeline.evaluate(input, output, metrics, evaluation_name=name,
                                             timestamp=timestamp, force=force, save=save_result)
                if evaluate is not None:
                    result[pipeline.name] = evaluate
        return result


class _InTask(EboniteObject):
    """Intermediate abstract class for object inside task"""

    def __init__(self, id: int, name: str,
                 author: str = None, creation_date: datetime.datetime = None,
                 task_id: int = None):
        super().__init__(id, name, author, creation_date)
        self.task_id = task_id

    @property
    @_with_meta
    def task(self):
        t = self._meta.get_task_by_id(self.task_id)
        if t is None:
            raise errors.NonExistingTaskError(self.task_id)
        return t.bind_artifact_repo(self._art)

    @task.setter
    def task(self, task: Task):
        if not isinstance(task, Task):
            raise ValueError('{} is not Task'.format(task))
        self.task_id = task.id
        self.bind_as(task)


@make_string
class EvaluationResult(EboniteParams):
    """Represents result of evaluation of one evalset on multiple evaluatable objects

    :param scores: mapping 'metric' -> 'score'
    :param timestamp: time of evaluation
    """

    def __init__(self, timestamp: float, scores: Dict[str, float] = None):
        self.timestamp = timestamp
        self.scores = scores or {}


@make_string
class EvaluationResultCollection(EboniteParams):
    """Collection of evaluation results for single evalset

    :param results: list of results"""

    def __init__(self, results: List[EvaluationResult] = None):
        self.results = results or []

    def add(self, result: EvaluationResult):
        if result != self.latest:
            self.results.append(result)

    @property
    def latest(self) -> Optional[EvaluationResult]:
        if len(self.results) == 0:
            return
        return max(self.results, key=lambda r: r.timestamp)


EvaluationResults = Dict[str, EvaluationResultCollection]  # Evaluation results for all evalsets
MultipleResults = Dict[str, EvaluationResult]  # Evaluation results for multiple objects but one evalset


class _WrapperMethodAccessor:
    """Class to access ModelWrapper methods from model

    :param model: model to access
    :param method_name: name of the wrapper method"""

    def __init__(self, model: 'Model', method_name: str):
        if model.wrapper.methods is None or method_name not in model.wrapper.exposed_methods:
            raise AttributeError(f'{model} does not have {method_name} method')
        self.model = model
        self.method_name = method_name

    def __call__(self, data):
        return self.model.wrapper.call_method(self.method_name, data)


@make_string('id', 'name')
class Model(_InTask):
    """
    Model contains metadata for machine learning model

    :param name: model name
    :param wrapper_meta: :class:`~ebonite.core.objects.wrapper.ModelWrapper` instance for this model
    :param artifact: :class:`~ebonite.core.objects.ArtifactCollection` instance with model artifacts
    :param requirements: :class:`~ebonite.core.objects.Requirements` instance with model requirements
    :param params: dict with arbitrary parameters. Must be json-serializable
    :param description: text description of this model
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
                 id: int = None,
                 task_id: int = None,
                 author: str = None, creation_date: datetime.datetime = None,
                 evaluations: Dict[str, EvaluationResults] = None):
        super().__init__(id, name, author, creation_date, task_id)

        self.evaluations = evaluations or {}
        self.description = description
        self.params = params or {}
        try:
            json.dumps(self.params)
        except TypeError:
            raise ValueError('"params" argument must be json-serializable')
        self._wrapper = None
        self._wrapper_meta = None
        if isinstance(wrapper_meta, ModelWrapper):
            self._wrapper = wrapper_meta
        elif isinstance(wrapper_meta, dict):
            self._wrapper_meta = wrapper_meta

        self.requirements = requirements
        self._persisted_artifacts = artifact
        self._unpersisted_artifacts: Optional[ArtifactCollection] = None

    def load(self):
        """
        Load model artifacts into wrapper
        """
        if get_python_version() != self.params.get(self.PYTHON_VERSION):
            warnings.warn(f'Loading model from different python version {self.params.get(self.PYTHON_VERSION)}')
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
               params: Dict[str, Any] = None, description: str = None,
               additional_artifacts: ArtifactCollection = None, additional_requirements: AnyRequirements = None,
               custom_wrapper: ModelWrapper = None, custom_artifact: ArtifactCollection = None,
               custom_requirements: AnyRequirements = None) -> 'Model':
        """
        Creates Model instance from arbitrary model objects and sample of input data

        :param model_object: The model object to analyze.
        :param input_data: Input data sample to determine structure of inputs and outputs for given model object.
        :param model_name: The model name.
        :param params: dict with arbitrary parameters. Must be json-serializable
        :param description: text description of this model
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
            requirements = wrapper.requirements

        if additional_requirements is not None:
            requirements += additional_requirements

        requirements = RequirementAnalyzer.analyze(requirements)
        params = params or {}
        params[cls.PYTHON_VERSION] = params.get(cls.PYTHON_VERSION, get_python_version())
        # noinspection PyTypeChecker
        model = Model(name, wrapper, None, requirements, params, description)
        model._unpersisted_artifacts = artifact
        return model

    @_with_meta
    @_with_artifact
    @ExposedObjectMethod('delete_model', 'model', 'Model', 'model to delete')
    def delete(self, force: bool = False):
        """
        Deletes model from metadata and artifact repositories

        :param force: whether model artifacts' deletion errors should be ignored, default is false
        :return: Nothing
        """
        if self.artifact is not None:
            try:
                self._art.delete_model_artifact(self)
            except:  # noqa
                if force:
                    logger.warning("Unable to delete artifacts associated with model: '%s'", self, exc_info=1)
                else:
                    raise

        self._meta.delete_model(self)
        self.task_id = None

    @_with_meta(saved=False)
    @_with_artifact
    def push(self, task: Task = None) -> 'Model':
        """
        Pushes :py:class:`~ebonite.core.objects.Model` instance into metadata and artifact repositories

        :param task: :py:class:`~ebonite.core.objects.Task` instance to save model to. Optional if model already has
        task
        :return: same saved :py:class:`~ebonite.core.objects.Model` instance
        """
        if self.id is not None:
            raise errors.ExistingModelError(self)
        if task is not None:
            if self.task_id is not None:
                if self.task_id != task.id:
                    raise ValueError('This model is already in task {}'.format(self.task_id))
            else:
                self.task = task

        self._meta.create_model(self)  # save model to get model.id
        try:
            self._art.push_model_artifacts(self)
        except:  # noqa
            self._meta.delete_model(self)
            raise

        return self._meta.save_model(self)

    def as_pipeline(self, method_name=None) -> 'Pipeline':
        """Create Pipeline that consists of this model's single method

        :param method_name: name of the method. can be omitted if model has only one method
        """
        method_name = self.wrapper.resolve_method(method_name)
        method = self.wrapper.methods[method_name]
        pipeline = Pipeline(f'{self.name}.{method_name}',
                            [], method[1], method[2], task_id=self.task_id).append(self, method_name)
        return pipeline

    def __getattr__(self, item: str):
        if item.startswith('__') and item.endswith('__') and item != '__call__':
            # no special dunder attributes
            raise AttributeError()
        return _WrapperMethodAccessor(self, item)

    @_with_meta
    @_with_artifact
    def save(self):
        """Saves model to metadata repo and pushes unpersisted artifacts"""
        if self._unpersisted_artifacts is not None:
            self._art.push_model_artifacts(self)
        self._meta.save_model(self)

    def has_children(self):
        return False

    @_with_meta
    def evaluate_set(self, evalset: Union[str, EvaluationSet],
                     evaluation_name: str = None, method_name: str = None,
                     timestamp=None, save=True, force=False,
                     raise_on_error=False) -> Optional[EvaluationResult]:
        """Evaluates this model

        :param evalset: evalset or it's name
        :param evaluation_name: name of this evaluation
        :param method_name: name of wrapper method. If none, all methods with consistent datatypes will be evaluated
        :param timestamp: time of the evaluation (defaults to now)
        :param save: save results to meta
        :param force: force reevalute
        :param raise_on_error: raise error if datatypes are incorrect or just return
        """
        task = self.task
        if isinstance(evalset, str):
            try:
                evaluation_name = evaluation_name or evalset
                evalset = task.evaluation_sets[evalset]
            except KeyError:
                raise ValueError(f'No evalset {evalset} in {task}')
        input, output, metrics = evalset.get(task, False)
        return self.evaluate(input, output, metrics, evaluation_name, method_name, timestamp, save, force,
                             raise_on_error)

    def evaluate(self, input: DatasetSource, output: DatasetSource, metrics: Dict[str, Metric],
                 evaluation_name: str = None, method_name: str = None,
                 timestamp=None, save=True, force=False,
                 raise_on_error=False) -> Optional[Union[EvaluationResult, Dict[str, EvaluationResult]]]:
        """Evaluates this model

        :param input: input data
        :param output: target
        :param metrics: dict of metrics to evaluate
        :param evaluation_name: name of this evaluation
        :param method_name: name of wrapper method. If none, all methods with consistent datatypes will be evaluated
        :param timestamp: time of the evaluation (defaults to now)
        :param save: save results to meta
        :param force: force reevalute
        :param raise_on_error: raise error if datatypes are incorrect or just return
        """
        if method_name is None:
            methods = self.wrapper.match_methods_by_type(input.dataset_type, output.dataset_type)
            if len(methods) == 0:
                if raise_on_error:
                    raise ValueError('incompatible dataset types for evaluation')
                return
        else:
            method_name = self.wrapper.resolve_method(method_name)
            tin, tout = self.wrapper.method_signature(method_name)
            if tin != input.dataset_type or tout != output.dataset_type:
                if raise_on_error:
                    raise ValueError('incompatible dataset types for evaluation')
                return
            methods = [method_name]

        if save:
            if evaluation_name is None:
                raise ValueError('Provide evaluation_name to save evaluation or set save = False')
            self._check_meta(True)
        results: Dict[str, EvaluationResult] = {}  # method -> result
        timestamp = timestamp or time.time()

        for method_name in methods:
            self.evaluations.setdefault(method_name, {})
            if evaluation_name in self.evaluations[method_name] and not force:
                results[method_name] = self.evaluations[method_name][evaluation_name].latest
                continue

            call = self.wrapper.call_method(method_name, input.read().data)
            scores = {}
            for mname, metric in metrics.items():
                scores[mname] = metric.evaluate(output.read().data, call)
            results[method_name] = EvaluationResult(timestamp, scores)

        if save:
            for method_name, result in results.items():
                self.evaluations[method_name].setdefault(evaluation_name, EvaluationResultCollection())
                self.evaluations[method_name][evaluation_name].add(result)
            self.save()

        if len(results) == 1:
            return list(results.values())[0]
        return results


def _generate_name(prefix='', postfix=''):
    """Generates name from current date

    :param prefix: str to put before
    :param postfix: str to put after"""
    now = datetime.datetime.now()
    return f'{prefix}{now.strftime("%Y%m%d_%H_%M_%S_%f")}{postfix}'


def _generate_model_name(wrapper: ModelWrapper):
    """
    Generates name for Model instance

    :param wrapper: model wrapper
    :return: str
    """

    return _generate_name('{}_model_'.format(wrapper.type))


class PipelineStep(EboniteParams):
    """A class to represent one step of a Pipeline - a Model with one of its' methods name

    :param model_name: name of the Model (in the same Task as Pipeline object)
    :param method_name: name of the method in Model's wrapper to use"""

    def __init__(self, model_name: str, method_name: str):
        self.model_name = model_name
        self.method_name = method_name


@make_string('id', 'name')
class Pipeline(_InTask):
    """Pipeline is a class to represent a sequence of different Model's methods.
    They can be used to reuse different models (for example, pre-processing functions) in different pipelines.
    Pipelines must have exact same in and out data types as tasks they are in

    :param name: name of the pipeline
    :param steps: sequence of :class:`.PipelineStep`s the pipeline consists of
    :param input_data: datatype of input dataset
    :param output_data: datatype of output datset
    :param id: id of the pipeline
    :param author: author of the pipeline
    :param creation_date: date of creation
    :param task_id: task.id of parent task"""

    def __init__(self, name: str,
                 steps: List[PipelineStep],
                 input_data: DatasetType,
                 output_data: DatasetType,
                 id: int = None,
                 author: str = None, creation_date: datetime.datetime = None,
                 task_id: int = None,
                 evaluations: EvaluationResults = None):
        super().__init__(id, name, author, creation_date, task_id)
        self.evaluations = evaluations or {}
        self.output_data = output_data
        self.input_data = input_data
        self.steps = steps
        self.models: Dict[str, Model] = {}  # not using direct fk to models as it is pain

    @_with_meta
    @ExposedObjectMethod('delete_pipeline', 'pipeline', 'Pipeline', 'pipeline to delete')
    def delete(self):
        """Deletes pipeline from metadata"""
        self._meta.delete_pipeline(self)

    @_with_meta
    def load(self):
        task = self.task
        for step in self.steps:
            model = task.models(step.model_name)
            self.models[model.name] = model

    def run(self, data):
        """Applies sequence of pipeline steps to data

        :param data: data to apply pipeline to. must have type `Pipeline.input_data`
        :returns: processed data of type `Pipeline.output_data`"""
        for step in self.steps:
            model = self.models[step.model_name]
            data = model.wrapper.call_method(step.method_name, data)
        return data

    def append(self, model: Union[Model, _WrapperMethodAccessor], method_name: str = None):
        """Appends another Model to the sequence of this pipeline steps

        :param model: either Model instance, or model method (as in `model.method` where `method` is method name)
        :param method_name: if Model was provided in `model`, this should be method name.
        can be omitted if model have only one method"""
        # TODO datatype validaiton
        if isinstance(model, _WrapperMethodAccessor):
            method_name = model.method_name
            model = model.model
        method_name = model.wrapper.resolve_method(method_name)

        self.steps.append(PipelineStep(model.name, method_name))
        self.models[model.name] = model
        self.output_data = model.wrapper.methods[method_name][2]  # TODO change it to namedtuple
        return self

    @_with_meta
    def save(self):
        """Saves this pipeline to metadata repository"""
        self._meta.save_pipeline(self)

    def has_children(self):
        return False

    @_with_meta
    def evaluate_set(self, evalset: Union[str, EvaluationSet],
                     evaluation_name: str = None,
                     timestamp=None, save=True, force=False,
                     raise_on_error=False) -> Optional[EvaluationResult]:
        """Evaluates this pipeline

        :param evalset: evalset or it's name
        :param evaluation_name: name of this evaluation
        :param timestamp: time of the evaluation (defaults to now)
        :param save: save results to meta
        :param force: force reevalute
        :param raise_on_error: raise error if datatypes are incorrect or just return
        """
        task = self.task
        if isinstance(evalset, str):
            try:
                evaluation_name = evaluation_name or evalset
                evalset = task.evaluation_sets[evalset]
            except KeyError:
                raise ValueError(f'No evalset {evalset} in {task}')
        input, output, metrics = evalset.get(task, False)
        return self.evaluate(input, output, metrics, evaluation_name, timestamp, save, force, raise_on_error)

    def evaluate(self, input: DatasetSource, output: DatasetSource, metrics: Dict[str, Metric],
                 evaluation_name: str = None,
                 timestamp=None, save=True, force=False,
                 raise_on_error=False) -> Optional[EvaluationResult]:
        """Evaluates this pipeline

        :param input: input data
        :param output: target
        :param metrics: dict of metrics to evaluate
        :param evaluation_name: name of this evaluation
        :param timestamp: time of the evaluation (defaults to now)
        :param save: save results to meta
        :param force: force reevalute
        :param raise_on_error: raise error if datatypes are incorrect or just return
        """
        if evaluation_name in self.evaluations and not force:
            return self.evaluations[evaluation_name].latest
        if save:
            if evaluation_name is None:
                raise ValueError('Provide evaluation_name to save evaluation or set save = False')
            self._check_meta(True)
        timestamp = timestamp or time.time()

        if input.dataset_type == self.input_data and output.dataset_type == self.output_data:
            scores = {}
            call = self.run(input.read().data)
            for mname, metric in metrics.items():
                scores[mname] = metric.evaluate(output.read().data, call)
            result = EvaluationResult(timestamp, scores)
            if save:
                self.evaluations.setdefault(evaluation_name, EvaluationResultCollection())
                self.evaluations[evaluation_name].add(result)
                self.save()
            return result
        elif raise_on_error:
            raise ValueError('incompatible dataset types for evaluation')


@type_field('type')
class Buildable(EboniteParams, WithMetadataRepository):
    """An abstract class that represents something that can be built by Builders
    Have default implementations for Models and Pipelines (and lists of them)
    """

    @abstractmethod
    def get_provider(self):
        """Abstract method to get a provider for this Buildable"""

    @property
    @abstractmethod
    def task(self) -> Optional[Task]:
        """property to get task (can be None, whick forces to provide task manually)"""


class RuntimeEnvironment(EboniteObject):
    """Represents and environment where you can build and deploy your services
    Actual type of environment depends on `.params` field type

    :param name: name of the environment
    :param id: id of the environment
    :param author: author of the enviroment
    :param creation_date: creation date of the enviroment
    :param params: :class:`.RuntimeEnvironment.Params` instance
    """

    @type_field('type')
    class Params(EboniteParams):
        """Abstract class that represents different types of environments"""
        default_runner = None
        default_builder = None

        def get_runner(self):
            """
            :return: Runner for this environment
            """
            return self.default_runner

        def get_builder(self):
            """
            :return: builder for this environment
            """
            return self.default_builder

    def __init__(self, name: str, id: int = None, params: Params = None,
                 author: str = None, creation_date: datetime.datetime = None):
        super().__init__(id, name, author, creation_date)
        self.params = params

    @_with_meta
    @ExposedObjectMethod('delete_environment', 'environment', 'RuntimeEnvironment', 'environment to delete')
    def delete(self, meta_only: bool = False, cascade: bool = False):
        """
        Deletes environment from metadata repository and(if required) stops associated instances

        :param meta_only: wheter to only delete metadata
        :param cascade: Whether should environment be deleted with all associated instances
        :return: Nothing
        """
        if cascade:
            instances = self._meta.get_instances(image=None, environment=self)
            for instance in instances:
                instance.delete(meta_only=meta_only)
        self._meta.delete_environment(self)

    @_with_meta
    def save(self):
        """Saves this env to metadata repository"""
        self._meta.save_environment(self)

    @_with_meta
    def has_children(self):
        return len(self._meta.get_instances(image=None, environment=self)) > 0


class _WithEnvironment(EboniteObject):
    """Utility class for objects with PK to :class:`.RuntimeEnvironment`"""

    def __init__(self, id: int, name: str, author: str = None, creation_date: datetime.datetime = None,
                 environment_id: int = None):
        super().__init__(id, name, author, creation_date)
        self.environment_id = environment_id
        self._environment: Optional[RuntimeEnvironment] = None

    @property
    def environment(self) -> RuntimeEnvironment:  # TODO caching
        if self._environment is not None:
            return self._environment
        if self.environment_id is None:
            raise errors.UnboundObjectError(f"{self} is not saved, cant access environment")
        self._check_meta()
        e = self._meta.get_environment_by_id(self.environment_id)
        if e is None:
            raise errors.NonExistingEnvironmentError(self.environment_id)
        e = e.bind_as(self)
        self._environment = e
        return self._environment

    @environment.setter
    def environment(self, environment: RuntimeEnvironment):
        if not isinstance(environment, RuntimeEnvironment):
            raise ValueError(f'{environment} is not RuntimeEnvironment')
        self.environment_id = environment.id
        self._environment = environment
        self.bind_as(environment)


class _WithBuilder(_WithEnvironment):
    builder = None

    def bind_builder(self, builder):
        self.builder = builder
        return self

    def unbind_builder(self):
        del self.builder

    @property
    def has_builder(self):
        return self.builder is not None


def _with_auto_builder(method):
    """
    Decorator for methods to check that object is binded to builder

    :param method: method to apply decorator
    :return: decorated method
    """

    @wraps(method)
    def inner(self: _WithBuilder, *args, **kwargs):
        if not self.has_builder:
            if not self.has_meta_repo:
                raise ValueError(f'{self} has no binded runner')
            self.bind_builder(self.environment.params.get_builder())
        return method(self, *args, **kwargs)

    return inner


@make_string('id', 'name')
class Image(_WithBuilder):
    """Class that represents metadata for image built from Buildable
    Actual type of image depends on `.params` field type

    :param name: name of the image
    :param id: id of the image
    :param author: author of the image
    :parma creation_date: creation date of the image
    :param source: :class:`.Buildable` instance this image was built from
    :param params: :class:`.Image.Params` instance
    :param task_id: task.id this image belongs to
    :param environment_id: environment.id this image belongs to
    """

    @type_field('type')
    class Params(EboniteParams):
        """Abstract class that represents different types of images"""

    def __init__(self, name: Optional[str], source: Buildable, id: int = None,
                 params: Params = None,
                 author: str = None, creation_date: datetime.datetime = None,
                 task_id: int = None,
                 environment_id: int = None):
        super().__init__(id, name or _generate_name('ebnt_image_'), author, creation_date, environment_id)
        self.task_id = task_id
        self.source = source
        self.params = params

    @property
    @_with_meta
    def task(self):
        t = self._meta.get_task_by_id(self.task_id)
        if t is None:
            raise errors.NonExistingTaskError(self.task_id)
        return t.bind_artifact_repo(self._art)

    @task.setter
    def task(self, task: Task):
        if not isinstance(task, Task):
            raise ValueError('{} is not Task'.format(task))
        self.task_id = task.id
        self.bind_as(task)

    @_with_meta
    @ExposedObjectMethod('delete_image', 'image', 'Image', 'image ot delete')
    def delete(self, meta_only: bool = False, cascade: bool = False):
        """
        Deletes existing image from metadata repository and image provider

        :param meta_only: should image be deleted only from metadata
        :param cascade: whether to delete nested RuntimeInstances
        """
        if cascade:
            for instance in self._meta.get_instances(self):
                instance.delete(meta_only=meta_only)
        elif len(self._meta.get_instances(self)) > 0:
            raise errors.ImageWithInstancesError(self)

        if not meta_only:
            self.remove()
        self._meta.delete_image(self)

    def bind_meta_repo(self, repo: 'ebonite.repository.MetadataRepository'):
        super(Image, self).bind_meta_repo(repo)
        self.source.bind_meta_repo(repo)
        return self

    @_with_auto_builder
    def is_built(self) -> bool:
        """Checks if image was built and wasn't removed"""
        return self.builder.image_exists(self.params, self.environment.params)

    @_with_auto_builder
    def build(self, **kwargs):
        """Build this image

        :param kwargs: additional params for builder.build_image (depends on builder implementation)
        """
        self.builder.build_image(self.source, self.params, self.environment.params, **kwargs)
        if self.has_meta_repo:
            self._meta.save_image(self)
        return self

    @_with_auto_builder
    def remove(self, **kwargs):
        """remove this image (from environment, not from ebonite metadata)"""
        self.builder.delete_image(self.params, self.environment.params, **kwargs)

    @_with_meta
    def save(self):
        self._meta.save_image(self)

    def has_children(self):
        return False


class _WithRunner(_WithEnvironment):
    runner = None

    def bind_runner(self, runner):
        self.runner = runner
        return self

    def unbind_runner(self):
        del self.runner

    @property
    def has_runner(self):
        return self.runner is not None


def _with_auto_runner(method):
    """
    Decorator for methods to check that object is binded to runner

    :param method: method to apply decorator
    :return: decorated method
    """

    @wraps(method)
    def inner(self: '_WithRunner', *args, **kwargs):
        if not self.has_runner:
            if not self.has_meta_repo:
                raise ValueError(f'{self} has no binded runner')
            self.bind_runner(self.environment.params.get_runner())
        return method(self, *args, **kwargs)

    return inner


class RuntimeInstance(_WithRunner):
    """Class that represents metadata for instance running in environment
    Actual type of instance depends on `.params` field type

    :param name: name of the instance
    :param id: id of the instance
    :param author: author of the instance
    :parma creation_date: creation date of the instance
    :param image_id: id of base image for htis instance
    :param params: :class:`.RuntimeInstance.Params` instance
    """

    @type_field('type')
    class Params(EboniteParams):
        """Abstract class that represents different types of images"""

    def __init__(self, name: Optional[str], id: int = None,
                 image_id: int = None, environment_id: int = None, params: Params = None,
                 author: str = None, creation_date: datetime.datetime = None):
        super().__init__(id, name or _generate_name('ebnt_instance_'), author, creation_date, environment_id)
        self.image_id = image_id
        self.params = params

    @property
    @_with_meta
    def image(self) -> Image:
        i = self._meta.get_image_by_id(self.image_id)
        if i is None:
            raise errors.NonExistingImageError(self.image_id)
        return i.bind_artifact_repo(self._art)

    @image.setter
    def image(self, image: Image):
        if not isinstance(image, Image):
            raise ValueError(f'{image} is not Image')
        self.image_id = image.id
        self.bind_as(image)

    @_with_meta
    @ExposedObjectMethod('delete_instance', 'instance', 'RuntimeInstance', 'instance to delete')
    def delete(self, meta_only: bool = False):
        """
        Stops instance of model service and deletes it from repository

        :param meta_only: only remove from metadata, do not stop instance
        :return: nothing
        """
        if not meta_only:
            self.stop()
            self.remove()

        self._meta.delete_instance(self)

    @_with_auto_runner
    def run(self, **runner_kwargs) -> 'RuntimeInstance':
        """Run this instance

        :param runner_kwargs: additional params for runner.run (depends on runner implementation)
        """
        self.runner.run(self.params, self.image.params, self.environment.params, **runner_kwargs)
        if self.has_meta_repo:
            self._meta.save_instance(self)
        return self

    @_with_auto_runner
    def logs(self, **kwargs):
        """Get logs of this instance

        :param kwargs: parameters for runner `logs` method
        :yields: str logs from running instance
        """
        yield from self.runner.logs(self.params, self.environment.params, **kwargs)

    @_with_auto_runner
    def is_running(self, **kwargs) -> bool:
        """
        Checks whether instance is running

        :param kwargs: params for runner `is_running` method
        :return: "is running" flag
        """
        return self.runner.is_running(self.params, self.environment.params, **kwargs)

    @_with_auto_runner
    def stop(self, **kwargs):
        """Stops the instance

        :param kwargs: params for runner `stop` method
        """
        self.runner.stop(self.params, self.environment.params, **kwargs)

    @_with_auto_runner
    def exists(self, **kwargs) -> bool:
        """Checks if instance exists (it may be stopped)

        :param kwargs: params for runner `instance_exists` method"""
        return self.runner.instance_exists(self.params, self.environment.params, **kwargs)

    @_with_auto_runner
    def remove(self, **kwargs):
        """Removes the instance from environment (not from metadata)

         :param kwargs: params for runner `remove_instance` method"""
        self.runner.remove_instance(self.params, self.environment.params, **kwargs)

    @_with_meta
    def save(self):
        self._meta.save_instance(self)

    def has_children(self):
        return False
