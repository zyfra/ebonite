import pandas as pd
import pytest
from pyjackson import deserialize, serialize
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.ext.pandas import DataFrameType


@pytest.fixture
def df_type():
    return DataFrameType(['a', 'b'])


def test_dataframe_type(df_type):
    assert df_type.requirements.modules == ['pandas']
    data = pd.DataFrame([{'a': 1, 'b': 1}, {'a': 2, 'b': 2}])

    obj = serialize(data, df_type)
    data2 = deserialize(obj, df_type)

    assert data.equals(data2)


@pytest.mark.parametrize('obj', [
    {'a': [1, 2], 'b': [1, 2]},         # not a dataframe
    pd.DataFrame([{'a': 1}, {'a': 2}])  # wrong columns
])
def test_dataframe_serialize_failure(df_type, obj):
    with pytest.raises(SerializationError):
        df_type.serialize(obj)


@pytest.mark.parametrize('obj', [
    1,                                # not a dict
    {},                               # no `values` key
    {'values': [{'a': 1}, {'a': 2}]}  # wrong columns
])
def test_dataframe_deserialize_failure(df_type, obj):
    with pytest.raises(DeserializationError):
        df_type.deserialize(obj)
