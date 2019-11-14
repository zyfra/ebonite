from typing import List

import pandas as pd
from pyjackson.core import ArgList, Field
from pyjackson.decorators import cached_property

from ebonite.core.analyzer.base import TypeHookMixin
from ebonite.core.analyzer.dataset import DatasetHook
from ebonite.core.objects.dataset_type import DatasetType


class PandasHook(TypeHookMixin, DatasetHook):
    """
    :class:`.DatasetHook` implementation for `pandas.DataFrame` which uses :class:`DataFrameType`
    """

    valid_types = [pd.DataFrame]

    def process(self, obj) -> DatasetType:
        return DataFrameType(list(obj.columns))


class SeriesType(DatasetType):
    """
    :class:`.DatasetType` implementation for `pandas.Series` objects which stores them as built-in Python dicts

    :param columns: list of columns names in dataset
    """

    real_type = pd.Series
    type = 'pandas_series'

    def __init__(self, columns: List[str]):
        self.columns = columns

    def deserialize(self, obj):
        return pd.Series(obj)

    def serialize(self, instance: pd.Series):
        return instance.to_dict()

    def get_spec(self):
        return [Field(c, float, False) for c in self.columns]  # TODO typing


class DataFrameType(DatasetType):
    """
    :class:`.DatasetType` implementation for `pandas.DataFrame` objects which stores them as
    built-in Python dicts with the only key `values` and value in a form of records list.

    :param columns: list of columns names in dataset
    """

    type = 'pandas_df'
    real_type = pd.DataFrame

    def __init__(self, columns: List[str]):
        self.columns = columns

    def deserialize(self, obj):
        return pd.DataFrame.from_records(obj['values'])

    def serialize(self, instance: pd.DataFrame):
        return {'values': instance.to_dict('records')}

    def get_spec(self) -> ArgList:
        return [Field('values', List[self.row_type], False)]

    @cached_property
    def row_type(self):
        return SeriesType(self.columns)
