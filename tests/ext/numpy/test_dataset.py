import numpy as np
from pyjackson import dumps, loads

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects.dataset_type import DatasetType
from ebonite.ext.numpy.dataset import NumpyNdarrayDatasetType, NumpyNumberDatasetType


def test_number():
    ndt = DatasetAnalyzer.analyze(np.float32(.5))
    assert issubclass(ndt, NumpyNumberDatasetType)
    payload = dumps(ndt)
    ndt2 = loads(payload, DatasetType)
    assert ndt == ndt2


def test_ndarray():
    nat = DatasetAnalyzer.analyze(np.array([1, 2, 3]))
    assert issubclass(nat, NumpyNdarrayDatasetType)
    payload = dumps(nat)
    nat2 = loads(payload, DatasetType)

    assert nat == nat2
