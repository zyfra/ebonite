from typing import Union

from ebonite.core.objects import Image, Model, Pipeline, Project, RuntimeEnvironment, RuntimeInstance, Task

ProjectIntStr = Union[Project, int, str]
TaskIntStr = Union[Task, int, str]
ModelIntStr = Union[Model, int, str]
PipelineIntStr = Union[Pipeline, int, str]
RuntimeEnvironmentIntStr = Union[RuntimeEnvironment, int, str]
RuntimeInstanceIntStr = Union[RuntimeInstance, int, str]
ImageIntStr = Union[Image, int, str]


class EboniteError(Exception):
    """
    General Ebonite error
    """


class MetadataError(EboniteError):
    """
    General Ebonite Metadata Error
    """


class ExistingProjectError(MetadataError):
    def __init__(self, project: ProjectIntStr):
        project = project.name if isinstance(project, Project) else project
        super(ExistingProjectError, self).__init__('Project with name "{}" already exists'.format(project))


class NonExistingProjectError(MetadataError):
    def __init__(self, project: ProjectIntStr):
        project = project.name if isinstance(project, Project) else project
        if isinstance(project, int):
            super(NonExistingProjectError, self).__init__('Project with id "{}" does not exist'.format(project))
        else:
            super(NonExistingProjectError, self).__init__('Project with name "{}" does not exist'.format(project))


class ExistingTaskError(MetadataError):
    def __init__(self, task: TaskIntStr):
        task = task.name if isinstance(task, Task) else task
        super(ExistingTaskError, self).__init__('Task with name "{}" already exists'.format(task))


class NonExistingTaskError(MetadataError):
    def __init__(self, task: TaskIntStr):
        task = task.name if isinstance(task, Task) else task
        if isinstance(task, int):
            super(NonExistingTaskError, self).__init__('Task with id "{}" does not exist'.format(task))
        else:
            super(NonExistingTaskError, self).__init__('Task with name "{}" does not exist'.format(task))


class TaskWithoutIdError(MetadataError):
    def __init__(self, task: TaskIntStr):
        task = task.name if isinstance(task, Task) else task
        super(TaskWithoutIdError, self).__init__('Task "{}" id is None'.format(task))


class ExistingModelError(MetadataError):
    def __init__(self, model: ModelIntStr):
        model = model.name if isinstance(model, Model) else model
        super(ExistingModelError, self).__init__('Model with name "{}" already exists'.format(model))


class NonExistingModelError(MetadataError):
    def __init__(self, model: ModelIntStr):
        model = model.name if isinstance(model, Model) else model
        if isinstance(model, int):
            super(NonExistingModelError, self).__init__('Model with id "{}" does not exist'.format(model))
        else:
            super(NonExistingModelError, self).__init__('Model with name "{}" does not exist'.format(model))


class ExistingPipelineError(MetadataError):
    def __init__(self, pipeline: PipelineIntStr):
        pipeline = pipeline.name if isinstance(pipeline, Pipeline) else pipeline
        super(ExistingPipelineError, self).__init__('Pipeline with name "{}" already exists'.format(pipeline))


class NonExistingPipelineError(MetadataError):
    def __init__(self, pipeline: PipelineIntStr):
        pipeline = pipeline.name if isinstance(pipeline, Model) else pipeline
        if isinstance(pipeline, int):
            super(NonExistingPipelineError, self).__init__('Pipeline with id "{}" does not exist'.format(pipeline))
        else:
            super(NonExistingPipelineError, self).__init__('Pipeline with name "{}" does not exist'.format(pipeline))


class ExistingImageError(MetadataError):
    def __init__(self, image: ImageIntStr):
        image = image.name if isinstance(image, Image) else image
        super(ExistingImageError, self).__init__('Image with name "{}" already exists'.format(image))


class NonExistingImageError(MetadataError):
    def __init__(self, image: ImageIntStr):
        image = image.name if isinstance(image, Image) else image
        if isinstance(image, int):
            super(NonExistingImageError, self).__init__('Image with id "{}" does not exist'.format(image))
        else:
            super(NonExistingImageError, self).__init__('Image with name "{}" does not exist'.format(image))


class ExistingEnvironmentError(MetadataError):
    def __init__(self, environment: RuntimeEnvironmentIntStr):
        environment = environment.name if isinstance(environment, RuntimeEnvironment) else environment
        super(ExistingEnvironmentError, self).__init__('Environment with name "{}" already exists'.format(environment))


class NonExistingEnvironmentError(MetadataError):
    def __init__(self, environment: RuntimeEnvironmentIntStr):
        environment = environment.name if isinstance(environment, RuntimeEnvironment) else environment
        if isinstance(environment, int):
            super(NonExistingEnvironmentError, self).__init__(
                'Environment with id "{}" does not exist'.format(environment))
        else:
            super(NonExistingEnvironmentError, self).__init__(
                'Environment with name "{}" does not exist'.format(environment))


class ExistingInstanceError(MetadataError):
    def __init__(self, instance: RuntimeInstanceIntStr):
        instance = instance.name if isinstance(instance, RuntimeInstance) else instance
        super(ExistingInstanceError, self).__init__('Instance with name "{}" already exists'.format(instance))


class NonExistingInstanceError(MetadataError):
    def __init__(self, instance: RuntimeInstanceIntStr):
        instance = instance.name if isinstance(instance, RuntimeInstance) else instance
        if isinstance(instance, int):
            super(NonExistingInstanceError, self).__init__('Instance with id "{}" does not exist'.format(instance))
        else:
            super(NonExistingInstanceError, self).__init__('Instance with name "{}" does not exist'.format(instance))


class TaskNotInProjectError(MetadataError):
    def __init__(self, task: Task):
        super(TaskNotInProjectError, self).__init__("Can't save task {} without project".format(task.name))


class ModelNotInTaskError(MetadataError):
    def __init__(self, model: Model):
        super(ModelNotInTaskError, self).__init__("Can't save model {} without task".format(model.name))


class PipelineNotInTaskError(MetadataError):
    def __init__(self, pipeline: Pipeline):
        super(PipelineNotInTaskError, self).__init__("Can't save pipeline {} without task".format(pipeline.name))


class ImageNotInTaskError(MetadataError):
    def __init__(self, image: Image):
        super(ImageNotInTaskError, self).__init__("Can't save image {} without task".format(image.name))


class InstanceNotInImageError(MetadataError):
    def __init__(self, instance: RuntimeInstance):
        super(InstanceNotInImageError, self).__init__(f"Can't save instance {instance.name} without image")


class InstanceNotInEnvironmentError(MetadataError):
    def __init__(self, instance: RuntimeInstance):
        super(InstanceNotInEnvironmentError, self).__init__(f"Can't save instance {instance.name} without environment")


class ModelWithoutIdError(MetadataError):
    def __init__(self, model: ModelIntStr):
        model = model.name if isinstance(model, Model) else model
        super(ModelWithoutIdError, self).__init__('Model "{}" id is None'.format(model))


class UnboundObjectError(MetadataError):
    pass


class ProjectWithTasksError(MetadataError):
    def __init__(self, project: Project):
        project = project.name if isinstance(project, Project) else project
        super(ProjectWithTasksError, self).__init__(f'Project {project} has foreign key and can not be deleted')


class TaskWithFKError(MetadataError):
    def __init__(self, task: Task):
        task = task.name if isinstance(task, Project) else task
        super(TaskWithFKError, self).__init__(f'Task {task} has foreign key and can not be deleted')


class ImageWithInstancesError(MetadataError):
    def __init__(self, image: Image):
        image = image.name if isinstance(image, Image) else image
        super(ImageWithInstancesError, self).__init__(f'Image {image} has foreign key and can not be deleted')


class EnvironmentWithInstancesError(MetadataError):
    def __init__(self, environment: RuntimeEnvironment):
        environment = environment.name if isinstance(environment, RuntimeEnvironment) else environment
        super(EnvironmentWithInstancesError, self).__init__(f'Environment {environment} '
                                                            f'has foreign key and can not be deleted')


class UnknownMetadataError(MetadataError):
    def __init__(self):
        super(UnknownMetadataError, self).__init__('Unknown error during query execution')


class DatasetError(EboniteError):
    """
    Base class for exceptions in :class:`~ebonite.repository.dataset.DatasetRpository`
    """


class NoSuchDataset(DatasetError):
    def __init__(self, dataset_id, repo, e=None):
        super(NoSuchDataset, self).__init__(f'No dataset with id {dataset_id} found in {repo}', e)


class DatasetExistsError(DatasetError):
    def __init__(self, dataset_id, repo, e=None):
        super(DatasetExistsError, self).__init__(f'Dataset with id {dataset_id} already in {repo}', e)


class ArtifactError(EboniteError):
    """
    Base class for exceptions in :class:`ArtifactRepository`
    """


class NoSuchArtifactError(ArtifactError):
    """
    Exception which is thrown if artifact is not found in the repository
    """

    def __init__(self, artifact_id, repo):
        super(NoSuchArtifactError, self).__init__(f'No artifact with id {artifact_id} found in {repo}')


class ArtifactExistsError(ArtifactError):
    """
    Exception which is thrown if artifact already exists in the repository
    """

    def __init__(self, artifact_id, repo):
        super(ArtifactExistsError, self).__init__(f'Artifact with id {artifact_id} already in {repo}')
