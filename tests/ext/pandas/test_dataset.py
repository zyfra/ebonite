import pandas as pd
from pyjackson import deserialize, serialize

from ebonite.ext.pandas import DataFrameType


def test_dataframe_type():
    data = pd.DataFrame([{'a': 1, 'b': 1}, {'a': 2, 'b': 2}])

    df_type = DataFrameType(['a', 'b'])

    obj = serialize(data, df_type)
    data2 = deserialize(obj, df_type)

    assert data.equals(data2)
