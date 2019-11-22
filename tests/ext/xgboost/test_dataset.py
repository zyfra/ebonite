import pytest
import xgboost

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.ext.xgboost.dataset import DMatrixDatasetType
from ebonite.runtime.openapi import spec


@pytest.fixture
def dtype_np(dmatrix_np):
    return DatasetAnalyzer.analyze(dmatrix_np)


@pytest.fixture
def dtype_df(dmatrix_df):
    return DatasetAnalyzer.analyze(dmatrix_df)


def test_hook_np(dtype_np):
    assert issubclass(dtype_np, DMatrixDatasetType)
    assert dtype_np.is_from_list


def test_hook_df(dtype_df):
    assert issubclass(dtype_df, DMatrixDatasetType)
    assert not dtype_df.is_from_list
    assert dtype_df.feature_names == ['a']


def test_serialize__np(dtype_np, np_payload):
    dmatrix = xgboost.DMatrix(np_payload)
    with pytest.raises(RuntimeError):
        dtype_np.serialize(dmatrix)


def test_deserialize__np(dtype_np, np_payload):
    dmatrix = dtype_np.deserialize(np_payload)
    assert isinstance(dmatrix, xgboost.DMatrix)


def test_deserialize__df(dtype_df, df_payload):
    dmatrix = dtype_df.deserialize(df_payload)
    assert isinstance(dmatrix, xgboost.DMatrix)


def test_np__schema(dtype_np):
    schema = spec.type_to_schema(dtype_np)

    assert schema == {
        'items': {'type': 'number'},
        'maxItems': 1,
        'minItems': 1,
        'type': 'array'
    }


def test_df__schema(dtype_df):
    schema = spec.type_to_schema(dtype_df)
    assert schema == {'properties': {'a': {'type': 'integer'}}, 'required': ['a'], 'type': 'object'}
