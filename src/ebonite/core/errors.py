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


class TaskNotInProjectError(MetadataError):
    def __init__(self, task: 'core.Task'):
        super(TaskNotInProjectError, self).__init__("Can't save task {} without project".format(task.name))


class ModelNotInTaskError(MetadataError):
    def __init__(self, model: 'core.Model'):
        super(ModelNotInTaskError, self).__init__("Can't save model {} without task".format(model.name))


class ModelWithoutIdError(MetadataError):
    def __init__(self, model: 'core.Model'):
        model = model.name if isinstance(model, core.Model) else model
        super(ModelWithoutIdError, self).__init__('Model "{}" id is None'.format(model))


class UnboundObjectError(MetadataError):
    pass
