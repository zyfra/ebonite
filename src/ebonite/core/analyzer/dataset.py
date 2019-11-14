from abc import abstractmethod

from ebonite.core.analyzer.base import Hook, analyzer_class
from ebonite.core.objects.dataset_type import (PRIMITIVES, DatasetType, DictDatasetType, FilelikeDatasetType,
                                               ListDatasetType, PrimitiveDatasetType)


class DatasetHook(Hook):
    """
    Base hook type for :py:class:`DatasetAnalyzer`.
    Analysis result is an instance of :class:`~ebonite.core.objects.DatasetType`
    """
    @abstractmethod
    def process(self, obj) -> DatasetType:
        pass


DatasetAnalyzer = analyzer_class(DatasetHook, DatasetType)


class PrimitivesHook(DatasetHook):
    """
    Hook for primitive data, for example when you model outputs just one int
    """
    def can_process(self, obj):
        if type(obj) in PRIMITIVES:
            return True

    def must_process(self, obj):
        return False

    def process(self, obj) -> DatasetType:
        return PrimitiveDatasetType(type(obj).__name__)


class ListHookDelegator(DatasetHook):
    """
    Hook for list data
    """
    def can_process(self, obj) -> bool:
        return isinstance(obj, list)

    def must_process(self, obj) -> bool:
        return False

    def process(self, obj) -> DatasetType:
        return ListDatasetType([DatasetAnalyzer.analyze(o) for o in obj])


class DictHookDelegator(DatasetHook):
    """
    Hook for dict data
    """
    def can_process(self, obj) -> bool:
        return isinstance(obj, dict)

    def must_process(self, obj) -> bool:
        return False

    def process(self, obj) -> DatasetType:
        try:
            items = {k: DatasetAnalyzer.analyze(o) for k, o in obj.items()}
        except ValueError:
            raise ValueError(f"Cant process {obj} with DictHookDelegator")
        return DictDatasetType(items)


class FilelikeDatasetHook(DatasetHook):
    """
    Hook for file-like objects
    """
    def process(self, obj) -> DatasetType:
        return FilelikeDatasetType()

    def can_process(self, obj) -> bool:
        return hasattr(obj, 'read') and callable(obj.read)

    def must_process(self, obj) -> bool:
        return False
