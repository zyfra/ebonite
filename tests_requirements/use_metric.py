from pyjackson import read

from ebonite.core.objects.metric import Metric

if __name__ == '__main__':
    metric: Metric = read('metric.json', Metric)

    assert metric.evaluate(1, 3) == 14
