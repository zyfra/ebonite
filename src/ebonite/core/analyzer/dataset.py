from abc import abstractmethod

from ebonite.core.analyzer.base import Hook, analyzer_class
from ebonite.core.objects.dataset_type import (PRIMITIVES, DatasetType, DictDatasetType, FilelikeDatasetType,
                                               ListDatasetType, PrimitiveDatasetType, TupleDatasetType,
                                               TupleLikeListDatasetType)


class DatasetHook(Hook):
    """
    Base hook type for :py:class:`DatasetAnalyzer`.
    Analysis result is an instance of :class:`~ebonite.core.objects.DatasetType`
    """
    @abstractmethod
    def process(self, obj, **kwargs) -> DatasetType:
        """
        Analyzes obj and returns result. Result type is determined by specific Hook class sub-hierarchy

        :param obj: object to analyze
        :param kwargs: additional information to be used for analysis
        :return: analysis result
        """
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

    def process(self, obj, **kwargs) -> DatasetType:
        return PrimitiveDatasetType(type(obj).__name__)


class OrderedCollectionHookDelegator(DatasetHook):
    """
    Hook for list/tuple data
    """
    def can_process(self, obj) -> bool:
        return isinstance(obj, (list, tuple))

    def must_process(self, obj) -> bool:
        return False

    def process(self, obj, **kwargs) -> DatasetType:
        if isinstance(obj, tuple):
            return TupleDatasetType([DatasetAnalyzer.analyze(o) for o in obj])

        py_types = {type(o) for o in obj}
        if len(obj) <= 1 or len(py_types) > 1:
            return TupleLikeListDatasetType([DatasetAnalyzer.analyze(o) for o in obj])

        if not py_types.intersection(PRIMITIVES):  # py_types is guaranteed to be singleton set here
            return TupleLikeListDatasetType([DatasetAnalyzer.analyze(o) for o in obj])

        # optimization for large lists of same primitive type elements
        return ListDatasetType(DatasetAnalyzer.analyze(obj[0]), len(obj))


class DictHookDelegator(DatasetHook):
    """
    Hook for dict data
    """
    def can_process(self, obj) -> bool:
        return isinstance(obj, dict)

    def must_process(self, obj) -> bool:
        return False

    def process(self, obj, **kwargs) -> DatasetType:
        try:
            items = {k: DatasetAnalyzer.analyze(o) for k, o in obj.items()}
        except ValueError:
            raise ValueError(f"Cant process {obj} with DictHookDelegator")
        return DictDatasetType(items)


class FilelikeDatasetHook(DatasetHook):
    """
    Hook for file-like objects
    """
    def process(self, obj, **kwargs) -> DatasetType:
        return FilelikeDatasetType()

    def can_process(self, obj) -> bool:
        return hasattr(obj, 'read') and callable(obj.read)

    def must_process(self, obj) -> bool:
        return False
