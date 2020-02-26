from ebonite.core.objects import core


class EboniteError(Exception):
    """
    General Ebonite error
    """
    pass


class MetadataError(EboniteError):
    """
    General Ebonite Metadata Error
    """
    pass


class ExistingProjectError(MetadataError):
    def __init__(self, project: 'core.Project'):
        project = project.name if isinstance(project, core.Project) else project
        super(ExistingProjectError, self).__init__('Project with name "{}" already exists'.format(project))


class NonExistingProjectError(MetadataError):
    def __init__(self, project: 'core.Project'):
        project = project.name if isinstance(project, core.Project) else project
        super(NonExistingProjectError, self).__init__('Project with name "{}" does not exist'.format(project))


class ExistingTaskError(MetadataError):
    def __init__(self, task: 'core.Task'):
        task = task.name if isinstance(task, core.Task) else task
        super(ExistingTaskError, self).__init__('Task with name "{}" already exists'.format(task))


class NonExistingTaskError(MetadataError):
    def __init__(self, task: 'core.Task'):
        task = task.name if isinstance(task, core.Task) else task
        super(NonExistingTaskError, self).__init__('Task with name "{}" does not exist'.format(task))


class TaskWithoutIdError(MetadataError):
    def __init__(self, task: 'core.Task'):
        task = task.name if isinstance(task, core.Task) else task
        super(TaskWithoutIdError, self).__init__('Task "{}" id is None'.format(task))


class ExistingModelError(MetadataError):
    def __init__(self, model: 'core.Model'):
        model = model.name if isinstance(model, core.Model) else model
        super(ExistingModelError, self).__init__('Model with name "{}" already exists'.format(model))


class NonExistingModelError(MetadataError):
    def __init__(self, model: 'core.Model'):
        model = model.name if isinstance(model, core.Model) else model
        super(NonExistingModelError, self).__init__('Model with name "{}" does not exist'.format(model))


class ExistingImageError(MetadataError):
    def __init__(self, image: 'core.Image'):
        image = image.name if isinstance(image, core.Image) else image
        super(ExistingImageError, self).__init__('Image with name "{}" already exists'.format(image))


class NonExistingImageError(MetadataError):
    def __init__(self, image: 'core.Image'):
        image = image.name if isinstance(image, core.Image) else image
        super(NonExistingImageError, self).__init__('Image with name "{}" does not exist'.format(image))


class ExistingEnvironmentError(MetadataError):
    def __init__(self, environment: 'core.RuntimeEnvironment'):
        environment = environment.name if isinstance(environment, core.RuntimeEnvironment) else environment
        super(ExistingEnvironmentError, self).__init__('Environment with name "{}" already exists'.format(environment))


class NonExistingEnvironmentError(MetadataError):
    def __init__(self, environment: 'core.RuntimeEnvironment'):
        environment = environment.name if isinstance(environment, core.RuntimeEnvironment) else environment
        super(NonExistingEnvironmentError, self).__init__('Environment with name "{}" does not exist'.format(environment))


class ExistingInstanceError(MetadataError):
    def __init__(self, instance: 'core.RuntimeInstance'):
        instance = instance.name if isinstance(instance, core.RuntimeInstance) else instance
        super(ExistingInstanceError, self).__init__('Instance with name "{}" already exists'.format(instance))


class NonExistingInstanceError(MetadataError):
    def __init__(self, instance: 'core.RuntimeInstance'):
        instance = instance.name if isinstance(instance, core.RuntimeInstance) else instance
        super(NonExistingInstanceError, self).__init__('Instance with name "{}" does not exist'.format(instance))


class TaskNotInProjectError(MetadataError):
    def __init__(self, task: 'core.Task'):
        super(TaskNotInProjectError, self).__init__("Can't save task {} without project".format(task.name))


class ModelNotInTaskError(MetadataError):
    def __init__(self, model: 'core.Model'):
        super(ModelNotInTaskError, self).__init__("Can't save model {} without task".format(model.name))


class ImageNotInModelError(MetadataError):
    def __init__(self, image: 'core.Image'):
        super(ImageNotInModelError, self).__init__("Can't save image {} without model".format(image.name))


class InstanceNotInImageError(MetadataError):
    def __init__(self, instance: 'core.RuntimeInstance'):
        super(InstanceNotInImageError, self).__init__(f"Can't save instance {instance.name} without image")


class InstanceNotInEnvironmentError(MetadataError):
    def __init__(self, instance: 'core.RuntimeInstance'):
        super(InstanceNotInEnvironmentError, self).__init__(f"Can't save instance {instance.name} without environment")


class ModelWithoutIdError(MetadataError):
    def __init__(self, model: 'core.Model'):
        model = model.name if isinstance(model, core.Model) else model
        super(ModelWithoutIdError, self).__init__('Model "{}" id is None'.format(model))


class UnboundObjectError(MetadataError):
    pass
