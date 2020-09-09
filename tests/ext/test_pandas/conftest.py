import io
from datetime import datetime, timezone

import pandas as pd
import pytest

from ebonite.core.analyzer.dataset import DatasetAnalyzer

PD_DATA_FRAME = pd.DataFrame([
    {'int': 1, 'str': 'a', 'float': .1, 'dt': datetime.now(), 'bool': True, 'dt_tz': datetime.now(timezone.utc)},
    {'int': 2, 'str': 'b', 'float': .2, 'dt': datetime.now(), 'bool': False, 'dt_tz': datetime.now(timezone.utc)}
])  # TODO other types

PD_DATA_FRAME_INDEX = PD_DATA_FRAME.set_index('int')
PD_DATA_FRAME_MULTIINDEX = PD_DATA_FRAME.set_index(['int', 'str'])


def df_to_str(df: pd.DataFrame):
    buf = io.StringIO()
    df.to_csv(buf)
    return buf.getvalue()


def pandas_assert(actual: pd.DataFrame, expected: pd.DataFrame):
    assert list(expected.columns) == list(actual.columns), 'different columns'
    assert expected.shape == actual.shape, 'different shapes'
    assert list(expected.dtypes) == list(actual.dtypes), 'different dtypes'
    assert list(expected.index) == list(actual.index), 'different indexes'
    assert df_to_str(expected) == df_to_str(actual), 'different str representation'
    assert expected.equals(actual), 'contents are not equal'


@pytest.fixture
def data():
    return pd.DataFrame([{'a': 1, 'b': 3, 'c': 5}, {'a': 2, 'b': 4, 'c': 6}])


@pytest.fixture
def data2():
    return PD_DATA_FRAME


@pytest.fixture
def df_type(data):
    return DatasetAnalyzer.analyze(data)


@pytest.fixture
def df_type2(data2):
    return DatasetAnalyzer.analyze(data2)


@pytest.fixture
def series_data(data2):
    return data2.iloc[0]


@pytest.fixture
def series_df_type(series_data):
    return DatasetAnalyzer.analyze(series_data)
