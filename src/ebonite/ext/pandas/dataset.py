import re
from typing import List, Union

import numpy as np
import pandas as pd
from pandas import Int64Dtype, SparseDtype, StringDtype
from pandas.core.dtypes.dtypes import (CategoricalDtype, DatetimeTZDtype, IntervalDtype, PandasExtensionDtype,
                                       PeriodDtype)
from pyjackson.core import ArgList, Field
from pyjackson.decorators import cached_property
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.core.analyzer.base import TypeHookMixin
from ebonite.core.analyzer.dataset import DatasetHook
from ebonite.core.objects.dataset_type import DatasetType, LibDatasetTypeMixin
from ebonite.ext.numpy.dataset import np_type_from_string, python_type_from_np_type

_PD_EXT_TYPES = {
    DatetimeTZDtype: r'datetime64.*',
    CategoricalDtype: r'category',
    PeriodDtype: r'[pP]eriod.*',
    SparseDtype: r'Sparse.*',
    IntervalDtype: r'[iI]nterval.*',
    Int64Dtype: r'U?Int\d*',
    StringDtype: r'string'
}
PD_EXT_TYPES = {dtype: re.compile(pattern) for dtype, pattern in
                _PD_EXT_TYPES.items()}


def string_repr_from_pd_type(dtype: Union[np.dtype, PandasExtensionDtype]) -> str:
    return dtype.name


def pd_type_from_string(string_repr):
    try:
        return np_type_from_string(string_repr)
    except ValueError:
        for dtype, pattern in PD_EXT_TYPES.items():
            if pattern.match(string_repr) is not None:
                return dtype.construct_from_string(string_repr)
        raise ValueError(f'unknown pandas dtype {string_repr}')


def python_type_from_pd_type(pd_type: np.dtype):
    if isinstance(pd_type, np.dtype):  # or (isinstance(pd_type, type) and pd_type.__module__ == 'numpy'):
        return python_type_from_np_type(pd_type)
    return str


def python_type_from_pd_string_repr(string_repr: str) -> type:
    pd_type = pd_type_from_string(string_repr)
    return python_type_from_pd_type(pd_type)


def need_string_value(dtype):
    return not isinstance(dtype, np.dtype) or dtype.type in (np.datetime64, np.object_)


class PandasDFHook(TypeHookMixin, DatasetHook):
    """
    :class:`.DatasetHook` implementation for `pandas.DataFrame` which uses :class:`DataFrameType`
    """

    valid_types = [pd.DataFrame]

    def process(self, obj: pd.DataFrame, **kwargs) -> DatasetType:
        return DataFrameType(list(obj.columns), [
            string_repr_from_pd_type(d) for d in obj.dtypes
        ])


class _PandasDatasetType(LibDatasetTypeMixin):
    libraries = [pd]

    def __init__(self, columns: List[str], dtypes: List[str]):
        self.columns = columns
        self.dtypes = dtypes

    @cached_property
    def actual_dtypes(self):
        return [pd_type_from_string(s) for s in self.dtypes]

    def _validate_columns(self, df: pd.DataFrame, exc_type):
        if set(df.columns) != set(self.columns):
            raise exc_type(f'given dataframe has columns: {list(df.columns)}, expected: {self.columns}')

    def _validate_dtypes(self, df: pd.DataFrame, exc_type):
        df = df[self.columns]
        for col, expected, dtype in zip(self.columns, self.dtypes, df.dtypes):
            pd_type = string_repr_from_pd_type(dtype)
            if expected != pd_type:
                raise exc_type(f'given dataframe has incorrect type {pd_type} in column {col}. Expected: {expected}')


class SeriesType(_PandasDatasetType):
    """
    :class:`.DatasetType` implementation for `pandas.Series` objects which stores them as built-in Python dicts

    """
    real_type = pd.Series

    def deserialize(self, obj):
        return pd.Series(obj)

    def serialize(self, instance: pd.Series):
        return instance.to_dict()

    def get_spec(self):
        return [Field(c, python_type_from_pd_string_repr(d), False) for c, d in zip(self.columns, self.dtypes)]


class DataFrameType(_PandasDatasetType):
    """
    :class:`.DatasetType` implementation for `pandas.DataFrame` objects which stores them as
    built-in Python dicts with the only key `values` and value in a form of records list.

    """
    real_type = pd.DataFrame

    def deserialize(self, obj):
        self._check_type(obj, dict, DeserializationError)
        try:
            ret = pd.DataFrame.from_records(obj['values'])
        except (ValueError, KeyError):
            raise DeserializationError(f'given object: {obj} could not be converted to dataframe')
        self._validate_columns(ret, DeserializationError)
        ret = ret[self.columns]
        for col, expected, dtype in zip(self.columns, self.actual_dtypes, ret.dtypes):
            if expected != dtype:
                ret[col] = ret[col].astype(expected)
        self._validate_dtypes(ret, DeserializationError)
        return ret

    def serialize(self, instance: pd.DataFrame):
        self._check_type(instance, pd.DataFrame, SerializationError)
        self._validate_columns(instance, SerializationError)
        self._validate_dtypes(instance, SerializationError)
        is_copied = False

        for col, dtype in zip(self.columns, self.actual_dtypes):
            if need_string_value(dtype):
                if not is_copied:
                    instance = instance.copy()
                    is_copied = True
                instance[col] = instance[col].astype('string')
        return {'values': (instance.to_dict('records'))}

    def get_spec(self) -> ArgList:
        return [Field('values', List[self.row_type], False)]

    @cached_property
    def row_type(self):
        return SeriesType(self.columns, self.dtypes)
