import lightgbm as lgb
import numpy as np
import pytest
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.ext.lightgbm.dataset import LightGBMDatasetType
from ebonite.ext.numpy import NumpyNdarrayDatasetType
from ebonite.ext.pandas import DataFrameType
from ebonite.runtime.openapi import spec


@pytest.fixture
def dtype_np(dataset_np):
    return DatasetAnalyzer.analyze(dataset_np)


@pytest.fixture
def dtype_df(dataset_df):
    return DatasetAnalyzer.analyze(dataset_df)


def test_hook_np(dtype_np):
    assert set(dtype_np.requirements.modules) == {'lightgbm', 'numpy'}
    assert issubclass(dtype_np, LightGBMDatasetType)
    assert issubclass(dtype_np.inner, NumpyNdarrayDatasetType)


def test_hook_df(dtype_df):
    assert set(dtype_df.requirements.modules) == {'lightgbm', 'pandas'}
    assert issubclass(dtype_df, LightGBMDatasetType)
    assert issubclass(dtype_df.inner, DataFrameType)


def test_serialize__np(dtype_np, np_payload):
    ds = lgb.Dataset(np_payload)
    payload = dtype_np.serialize(ds)
    assert payload == np_payload.tolist()

    with pytest.raises(SerializationError):
        dtype_np.serialize({'abc': 123})  # wrong type


def test_deserialize__np(dtype_np, np_payload):
    ds = dtype_np.deserialize(np_payload)
    assert isinstance(ds, lgb.Dataset)
    assert np.all(ds.data == np_payload)

    with pytest.raises(DeserializationError):
        dtype_np.deserialize([[1], ['abc']])  # illegal matrix


def test_serialize__df(dtype_df, df_payload):
    ds = lgb.Dataset(df_payload)
    payload = dtype_df.serialize(ds)
    assert payload['values'] == df_payload.to_dict('records')


def test_deserialize__df(dtype_df, df_payload):
    ds = dtype_df.deserialize({'values': df_payload})
    assert isinstance(ds, lgb.Dataset)
    assert ds.data.equals(df_payload)


def test_np__schema(dtype_np):
    schema = spec.type_to_schema(dtype_np)

    assert schema == {'items': {'items': {'type': 'number'},
                                'maxItems': 1,
                                'minItems': 1,
                                'type': 'array'},
                      'type': 'array'}


def test_df__schema(dtype_df):
    schema = spec.type_to_schema(dtype_df)
    assert schema == {'properties': {'values': {'items': {'properties': {'a': {'type': 'number'}},
                                                          'required': ['a'],
                                                          'type': 'object'},
                                                'type': 'array'}},
                      'required': ['values'],
                      'type': 'object'}
