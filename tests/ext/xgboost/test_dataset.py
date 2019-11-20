import pytest
import xgboost

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.ext.xgboost.dataset import DMatrixDatasetType


@pytest.fixture
def dtype(dmatrix):
    return DatasetAnalyzer.analyze(dmatrix)


def test_hook(dtype):
    assert issubclass(dtype, DMatrixDatasetType)


def test_serialize(dtype: DMatrixDatasetType()):
    payload = [1, 2, 3, 4]
    dmatrix = xgboost.DMatrix(payload)
    with pytest.raises(RuntimeError):
        dtype.serialize(dmatrix)


def test_deserialize(dtype: DMatrixDatasetType()):
    payload = [1, 2, 3, 4]
    dmatrix = dtype.deserialize(payload)

    assert isinstance(dmatrix, xgboost.DMatrix)
