from typing import List

import pandas as pd
import pytest

from ebonite.core.objects.dataset_source import Dataset
from ebonite.ext.pandas.dataset_source import PANDAS_FORMATS, PandasReader, PandasWriter
from tests.conftest import dataset_write_read_check
from tests.ext.test_pandas.conftest import PD_DATA_FRAME, PD_DATA_FRAME_INDEX, PD_DATA_FRAME_MULTIINDEX, pandas_assert


def for_all_formats(exclude: List[str] = None):
    ex = exclude if isinstance(exclude, list) else []
    formats = [f for name, f in PANDAS_FORMATS.items() if name not in ex]
    mark = pytest.mark.parametrize('format', formats, ids=[f.type for f in formats])
    if isinstance(exclude, list):
        return mark
    return mark(exclude)


@for_all_formats
def test_simple_df(data, format):
    writer = PandasWriter(format)
    dataset_write_read_check(Dataset.from_object(data), writer, PandasReader, pd.DataFrame.equals)


@for_all_formats
def test_with_index(data, format):
    writer = PandasWriter(format)
    dataset_write_read_check(Dataset.from_object(data.set_index('a')), writer, PandasReader,
                             custom_assert=pandas_assert)


@for_all_formats
def test_with_multiindex(data, format):
    writer = PandasWriter(format)
    dataset_write_read_check(Dataset.from_object(data.set_index(['a', 'b'])), writer, PandasReader,
                             custom_assert=pandas_assert)


@for_all_formats(exclude=[
    'excel',  # Excel does not support datetimes with timezones
    'parquet',  # Casting from timestamp[ns] to timestamp[ms] would lose data
])
@pytest.mark.parametrize('data', [PD_DATA_FRAME, PD_DATA_FRAME_INDEX, PD_DATA_FRAME_MULTIINDEX])
def test_with_index_complex(data, format):
    writer = PandasWriter(format)
    dataset_write_read_check(Dataset.from_object(data), writer, PandasReader, custom_assert=pandas_assert)
