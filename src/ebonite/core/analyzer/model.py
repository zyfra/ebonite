from abc import abstractmethod

from ebonite.core.analyzer.base import Hook, analyzer_class
from ebonite.core.objects.requirements import Requirements
from ebonite.core.objects.wrapper import CallableMethodModelWrapper, ModelWrapper
from ebonite.utils.module import get_object_requirements


class ModelHook(Hook):
    """
    Base hook type for :py:class:`ModelAnalyzer`.
    Analysis result is an instance of :class:`~ebonite.core.objects.ModelWrapper`
    """

    @abstractmethod
    def process(self, obj, **kwargs) -> ModelWrapper:
        pass  # pragma: no cover

    def get_requirements(self, obj) -> Requirements:
        return get_object_requirements(obj)


ModelAnalyzer = analyzer_class(ModelHook, ModelWrapper)


class BindingModelHook(ModelHook):
    """
    Binding model hook which `process` by first creating corresponding model wrapper (by means of a subclass) and
    then binding created wrapper to given model object
    """

    def process(self, obj, **kwargs) -> ModelWrapper:
        return self._wrapper_factory().bind_model(obj, **kwargs)

    @abstractmethod
    def _wrapper_factory(self) -> ModelWrapper:
        pass  # pragma: no cover


class CallableMethodModelHook(BindingModelHook):
    """
    Hook for processing functions
    """
    def _wrapper_factory(self) -> ModelWrapper:
        return CallableMethodModelWrapper()

    def can_process(self, obj) -> bool:
        return callable(obj)

    def must_process(self, obj) -> bool:
        return False
