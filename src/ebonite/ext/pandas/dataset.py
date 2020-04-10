from typing import List

import pandas as pd
from pyjackson.core import ArgList, Field
from pyjackson.decorators import cached_property
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer.base import TypeHookMixin
from ebonite.core.analyzer.dataset import DatasetHook
from ebonite.core.objects.dataset_type import DatasetType, LibDatasetTypeMixin


class PandasHook(TypeHookMixin, DatasetHook):
    """
    :class:`.DatasetHook` implementation for `pandas.DataFrame` which uses :class:`DataFrameType`
    """

    valid_types = [pd.DataFrame]

    def process(self, obj, **kwargs) -> DatasetType:
        return DataFrameType(list(obj.columns))


class SeriesType(LibDatasetTypeMixin):
    """
    :class:`.DatasetType` implementation for `pandas.Series` objects which stores them as built-in Python dicts

    :param columns: list of columns names in dataset
    """

    real_type = pd.Series
    libraries = [pd]

    def __init__(self, columns: List[str]):
        self.columns = columns

    def deserialize(self, obj):
        return pd.Series(obj)

    def serialize(self, instance: pd.Series):
        return instance.to_dict()

    def get_spec(self):
        return [Field(c, float, False) for c in self.columns]  # TODO typing


class DataFrameType(LibDatasetTypeMixin):

    """
    :class:`.DatasetType` implementation for `pandas.DataFrame` objects which stores them as
    built-in Python dicts with the only key `values` and value in a form of records list.

    :param columns: list of columns names in dataset
    """
    real_type = pd.DataFrame
    libraries = [pd]

    def __init__(self, columns: List[str]):
        self.columns = columns

    def deserialize(self, obj):
        self._check_type(obj, dict, DeserializationError)
        try:
            ret = pd.DataFrame.from_records(obj['values'])
        except (ValueError, KeyError):
            raise DeserializationError(f'given object: {obj} could not be converted to dataframe')
        self._check_columns(ret, DeserializationError)
        return ret

    def serialize(self, instance: pd.DataFrame):
        self._check_type(instance, pd.DataFrame, SerializationError)
        self._check_columns(instance, SerializationError)
        return {'values': instance.to_dict('records')}

    def _check_columns(self, df, exc_type):
        if list(df.columns) != self.columns:
            raise exc_type(f'given dataframe has columns: {list(df.columns)}, expected: {self.columns}')

    def get_spec(self) -> ArgList:
        return [Field('values', List[self.row_type], False)]

    @cached_property
    def row_type(self):
        return SeriesType(self.columns)
