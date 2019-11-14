import inspect
from abc import abstractmethod
from types import ModuleType
from typing import List, Type

from ebonite.utils.abc_utils import is_abstract_method
from ebonite.utils.log import logger
from ebonite.utils.module import get_object_base_module

ANALYZER_FIELD = '_analyzer'


class Hook:
    """
    Base class for Hooks
    """

    @abstractmethod
    def can_process(self, obj) -> bool:
        """
        Must return True if obj can be processed by this hook

        :param obj: object to analyze
        :return: True or False
        """
        pass

    @abstractmethod
    def must_process(self, obj) -> bool:
        """
        Must return True if obj must be processed by this hook. "must" means you sure that no other hook should handle
        this object, for example this hook is for sklearn objects and obj is exactly that.

        :param obj: object to analyze
        :return: True or False
        """
        pass

    @abstractmethod
    def process(self, obj):
        """
        Analyzes obj and returns result. Result type is determined by specific Hook class sub-hierarchy

        :param obj: object to analyze
        :return: analysis result
        """
        pass

    def __init_subclass__(cls, **kwargs):
        if hasattr(cls, '__init__'):
            init = getattr(cls, '__init__')
            argspec = inspect.getfullargspec(init)
            if len(argspec.args) > 1:
                raise ValueError('Hook type [{}] cannot have __init__ with arguments'.format(cls.__name__))

        if not is_abstract_method(cls.process):
            for b in reversed(cls.__bases__):
                analyzer = getattr(b, ANALYZER_FIELD, None)
                if analyzer is not None:
                    analyzer.hooks.append(cls())
                    logger.debug('Registering %s to %s', cls.__name__, analyzer.__name__)
                    break
            else:
                raise ValueError(
                    '{} defines process method, but dont have any parents with attached Analyzer'.format(cls))
        super(Hook, cls).__init_subclass__(**kwargs)


# noinspection PyAbstractClass
class CanIsAMustHookMixin(Hook):
    """
    Mixin for cases when can_process equals to must_process
    """

    def can_process(self, obj) -> bool:
        """Returns same as :meth:`Hook.must_process`"""
        return self.must_process(obj)


# noinspection PyAbstractClass
class TypeHookMixin(CanIsAMustHookMixin):
    """
    Mixin for cases when hook must process objects of certain types
    """
    valid_types: List[Type] = None

    def must_process(self, obj) -> bool:
        """Returns True if obj is instance of one of valid types"""
        return any(isinstance(obj, t) for t in self.valid_types)


class BaseModuleHookMixin(CanIsAMustHookMixin, Hook):
    """
    Mixin for cases when hook must process all objects with certain base modules
    """

    @abstractmethod
    def is_valid_base_module_name(self, module_name: str) -> bool:
        """
        Must return True if module_name is valid for this hook

        :param module_name: module name
        :return: True or False
        """
        pass

    def is_valid_base_module(self, base_module: ModuleType) -> bool:
        """
        Returns True if module is valid

        :param base_module: module object
        :return: True or False
        """
        if base_module is None:
            return False
        return self.is_valid_base_module_name(base_module.__name__)

    def must_process(self, obj):
        """Returns True if obj has valid base module"""
        return self.is_valid_base_module(get_object_base_module(obj))


class LibHookMixin(BaseModuleHookMixin):
    """
    Mixin for cases when hook must process all objects with certain base module
    """
    base_module_name = None

    def is_valid_base_module_name(self, base_module: str) -> bool:
        return base_module == self.base_module_name


def analyzer_class(hook_type: type, return_type: type):
    """
    Function to create separate hook hierarchies for analyzing different objects

    :param hook_type: Subtype of :py:class:`Hook`
    :param return_type: Type that this hierarchy will use as analysis result
    :return: Analyzer type
    """
    if hasattr(hook_type, ANALYZER_FIELD):
        raise ValueError('{} hook already have analyzer'.format(hook_type))

    class Analyzer:
        f"""
        Analyzer for {hook_type.__name__} hooks
        """
        hooks: List[hook_type] = []

        @classmethod
        def analyze(cls, obj) -> return_type:
            f"""
            Run {hook_type.__name__} hooks to analyze obj

            :param obj: objects to analyze
            :return: Instance of {return_type.__name__}
            """
            hooks = []
            for hook in cls.hooks:
                if hook.must_process(obj):
                    logger.debug('processing class %s with %s', type(obj).__name__, hook.__class__.__name__)
                    return hook.process(obj)
                elif hook.can_process(obj):
                    hooks.append(hook)

            if not hooks:
                raise ValueError(
                    f'No suitable {hook_type.__name__} for object '
                    f'[{type(obj).__name__}] {obj}. Registered hooks: {cls.hooks}')
            elif len(hooks) > 1:
                raise ValueError(f'Multiple suitable hooks for object {obj} ({hooks})')

            return hooks[0].process(obj)

    Analyzer.__name__ = '{}Analyzer'.format(hook_type.__name__)
    setattr(hook_type, ANALYZER_FIELD, Analyzer)
    return Analyzer
