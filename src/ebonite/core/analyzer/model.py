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
    def process(self, obj) -> ModelWrapper:
        pass

    def get_requirements(self, obj) -> Requirements:
        return get_object_requirements(obj)


ModelAnalyzer = analyzer_class(ModelHook, ModelWrapper)


class CallableMethodModelHook(ModelHook):
    """
    Hook for processing functions
    """
    def process(self, obj) -> ModelWrapper:
        return CallableMethodModelWrapper().bind_model(obj)

    def can_process(self, obj) -> bool:
        return callable(obj)

    def must_process(self, obj) -> bool:
        return False
