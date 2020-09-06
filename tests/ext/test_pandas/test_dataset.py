import json
from datetime import datetime

import pandas as pd
import pytest
from pyjackson import deserialize, serialize
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.core.objects import DatasetType
from ebonite.ext.pandas import DataFrameType
from ebonite.ext.pandas.dataset import (pd_type_from_string, python_type_from_pd_string_repr, python_type_from_pd_type,
                                        string_repr_from_pd_type)
from tests.ext.test_pandas.conftest import PD_DATA_FRAME, PD_DATA_FRAME_INDEX, PD_DATA_FRAME_MULTIINDEX, pandas_assert

for_all_dtypes = pytest.mark.parametrize('dtype', PD_DATA_FRAME.dtypes, ids=[str(d) for d in PD_DATA_FRAME.dtypes])


@for_all_dtypes
def test_string_repr_from_pd_type(dtype):
    assert isinstance(string_repr_from_pd_type(dtype), str)


@for_all_dtypes
def test_python_type_from_pd_type(dtype):
    python_type_from_pd_type(dtype)


@for_all_dtypes
def test_pd_type_from_string(dtype):
    pd_type_from_string(string_repr_from_pd_type(dtype))


@for_all_dtypes
def test_python_type_from_pd_string_repr(dtype):
    python_type_from_pd_string_repr(string_repr_from_pd_type(dtype))


@pytest.mark.parametrize('df_type_fx', ['df_type2', 'df_type'])
def test_df_type(df_type_fx, request):
    df_type = request.getfixturevalue(df_type_fx)
    assert issubclass(df_type, DataFrameType)

    obj = serialize(df_type)
    new_df_type = deserialize(obj, DatasetType)

    assert df_type == new_df_type


def test_dataframe_type(df_type, data):
    assert df_type.requirements.modules == ['pandas']

    obj = serialize(data, df_type)
    payload = json.dumps(obj)
    loaded = json.loads(payload)
    data2 = deserialize(loaded, df_type)

    assert data.equals(data2)


@pytest.mark.parametrize('obj', [
    {'a': [1, 2], 'b': [1, 2]},  # not a dataframe
    pd.DataFrame([{'a': 1}, {'a': 2}])  # wrong columns
])
def test_dataframe_serialize_failure(df_type, obj):
    with pytest.raises(SerializationError):
        df_type.serialize(obj)


@pytest.mark.parametrize('obj', [
    1,  # not a dict
    {},  # no `values` key
    {'values': [{'a': 1}, {'a': 2}]}  # wrong columns
])
def test_dataframe_deserialize_failure(df_type, obj):
    with pytest.raises(DeserializationError):
        df_type.deserialize(obj)


def test_unordered_columns(df_type, data):
    data_rev = data[list(reversed(data.columns))]
    obj = serialize(data_rev, df_type)
    data2 = deserialize(obj, df_type)

    assert data.equals(data2), f'{data} \n!=\n{data2}'
    assert data2 is not data


def test_datetime():
    data = pd.DataFrame([{'a': 1, 'b': datetime.now()}, {'a': 2, 'b': datetime.now()}])
    df_type = DatasetAnalyzer.analyze(data)
    assert issubclass(df_type, DataFrameType)

    obj = serialize(data, df_type)
    payload = json.dumps(obj)
    loaded = json.loads(payload)
    data2 = deserialize(loaded, df_type)

    assert data.equals(data2)
    assert data2 is not data


@pytest.mark.parametrize('df', [PD_DATA_FRAME, PD_DATA_FRAME_INDEX, PD_DATA_FRAME_MULTIINDEX])
def test_all(df):
    df_type = DatasetAnalyzer.analyze(df)

    obj = serialize(df, df_type)
    payload = json.dumps(obj)
    loaded = json.loads(payload)
    data = deserialize(loaded, df_type)

    assert df is not data
    pandas_assert(data, df)


@pytest.mark.parametrize('df', [PD_DATA_FRAME, PD_DATA_FRAME_INDEX, PD_DATA_FRAME_MULTIINDEX])
def test_all_filtered(df):
    df = df[~df['bool']]
    df_type = DatasetAnalyzer.analyze(df)

    obj = serialize(df, df_type)
    payload = json.dumps(obj)
    loaded = json.loads(payload)
    data = deserialize(loaded, df_type)

    assert df is not data
    pandas_assert(data, df)
