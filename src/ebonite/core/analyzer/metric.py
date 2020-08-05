from abc import abstractmethod

from ebonite.core.analyzer import Hook, analyzer_class
from ebonite.core.analyzer.base import LibHookMixin
from ebonite.core.objects.metric import CallableMetric, CallableMetricWrapper, LibFunctionMetric, Metric


class MetricHook(Hook):
    """
    Base hook type for :class:`DatasetAnalyzer`.
    Analysis result is an instance of :class:`~ebonite.core.objects.DatasetType`
    """

    @abstractmethod
    def process(self, obj, **kwargs) -> Metric:
        """
        Analyzes obj and returns result. Result type is determined by specific Hook class sub-hierarchy

        :param obj: object to analyze
        :param kwargs: additional information to be used for analysis
        :return: analysis result
        """
        pass  # pragma: no cover


MetricAnalyzer = analyzer_class(MetricHook, Metric)


class LibFunctionMixin(MetricHook, LibHookMixin):
    invert = False
    default_args = {}

    def get_args(self, obj):
        return self.default_args

    def process(self, obj, **kwargs) -> Metric:
        return LibFunctionMetric(f'{obj.__module__}.{obj.__name__}', self.get_args(obj), invert_input=self.invert)


class CallableMetricHook(MetricHook):
    def process(self, obj, **kwargs) -> Metric:
        return CallableMetric(CallableMetricWrapper.from_callable(obj))

    def can_process(self, obj) -> bool:
        return callable(obj)

    def must_process(self, obj) -> bool:
        return False
