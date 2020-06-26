from ebonite.core.analyzer.metric import MetricAnalyzer, MetricHook
from ebonite.core.objects.metric import Metric


class MyMetric:
    def __init__(self, value: int = 0):
        self.value = value


class MyMetricType(Metric):
    def __init__(self, my: MyMetric):
        self.my = my

    def evaluate(self, truth, prediction):
        return self.my.value


class MyMetricHook(MetricHook):

    def process(self, obj, **kwargs) -> Metric:
        return MyMetricType(obj)

    def can_process(self, obj) -> bool:
        return isinstance(obj, MyMetric)

    def must_process(self, obj) -> bool:
        return self.can_process(obj)


def test_metric_analyzer():
    m = MyMetric(10)

    metric = MetricAnalyzer.analyze(m)

    assert isinstance(metric, Metric)
    assert metric.evaluate('a', 'b') == 10
