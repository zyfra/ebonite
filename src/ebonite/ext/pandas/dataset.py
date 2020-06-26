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
    """Returns string representation of pandas dtype"""
    return dtype.name


def pd_type_from_string(string_repr):
    """Creates pandas dtype from string representation"""
    try:
        return np_type_from_string(string_repr)
    except ValueError:
        for dtype, pattern in PD_EXT_TYPES.items():
            if pattern.match(string_repr) is not None:
                return dtype.construct_from_string(string_repr)
        raise ValueError(f'unknown pandas dtype {string_repr}')


def python_type_from_pd_type(pd_type: np.dtype):
    """Returns python builtin type that corresponds to pandas dtype"""
    if isinstance(pd_type, np.dtype):  # or (isinstance(pd_type, type) and pd_type.__module__ == 'numpy'):
        return python_type_from_np_type(pd_type)
    return str


def python_type_from_pd_string_repr(string_repr: str) -> type:
    """Returns python type from pandas dtype string representation"""
    pd_type = pd_type_from_string(string_repr)
    return python_type_from_pd_type(pd_type)


def need_string_value(dtype):
    """Returns true if dtype must be cast to str for serialization"""
    return not isinstance(dtype, np.dtype) or dtype.type in (np.datetime64, np.object_)


class PandasDFHook(TypeHookMixin, DatasetHook):
    """
    :class:`.DatasetHook` implementation for `pandas.DataFrame` which uses :class:`DataFrameType`
    """

    valid_types = [pd.DataFrame]

    def process(self, obj: pd.DataFrame, **kwargs) -> DatasetType:
        if has_index(obj):
            index_cols, obj = _reset_index(obj)
        else:
            index_cols = []

        return DataFrameType(list(obj.columns), [string_repr_from_pd_type(d) for d in obj.dtypes], index_cols)


class _PandasDatasetType(LibDatasetTypeMixin):
    """Intermidiate class for pandas DatasetType implementations

    :param columns: list of column names (including index)
    :param dtypes: list of string representations of pandas dtypes of columns
    :param index_cols: list of column names that are used as index"""
    libraries = [pd]

    def __init__(self, columns: List[str], dtypes: List[str], index_cols: List[str]):
        self.index_cols = index_cols
        self.columns = columns
        self.dtypes = dtypes

    @cached_property
    def actual_dtypes(self):
        """List of pandas dtypes for columns"""
        return [pd_type_from_string(s) for s in self.dtypes]

    def _validate_columns(self, df: pd.DataFrame, exc_type):
        """Validates that df has correct columns"""
        if set(df.columns) != set(self.columns):
            raise exc_type(f'given dataframe has columns: {list(df.columns)}, expected: {self.columns}')

    def _validate_dtypes(self, df: pd.DataFrame, exc_type):
        """Validates that df has correct column dtypes"""
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


def has_index(df: pd.DataFrame):
    """Returns true if df has non-trivial index"""
    return not isinstance(df.index, pd.RangeIndex)


def _reset_index(df: pd.DataFrame):
    """Transforms indexes to columns"""
    index_name = df.index.name or ''  # save it for future renaming
    cols = set(df.columns)
    df = df.reset_index()  # can rename indexes if they didnt have a name
    index_cols = [c for c in df.columns if c not in cols]  # get new columns - they were index columns
    if len(index_cols) == 1:
        df = df.rename({index_cols[0]: index_name}, axis=1)
        index_cols = [index_name]
    return index_cols, df


def reset_index(df: pd.DataFrame, return_copied=False):
    """Transforms indexes to columns if index is non-trivial"""
    if has_index(df):
        _, df = _reset_index(df)
        if return_copied:
            return True, df
        return df
    if return_copied:
        return False, df
    return df


class DataFrameType(_PandasDatasetType):
    """
    :class:`.DatasetType` implementation for `pandas.DataFrame`
    """

    real_type = pd.DataFrame

    def deserialize(self, obj):
        self._check_type(obj, dict, DeserializationError)
        try:
            ret = pd.DataFrame.from_records(obj['values'])
        except (ValueError, KeyError):
            raise DeserializationError(f'given object: {obj} could not be converted to dataframe')

        self._validate_columns(ret, DeserializationError)  # including index columns
        ret = self.align_types(ret)  # including index columns
        self._validate_dtypes(ret, DeserializationError)
        return self.align_index(ret)

    def align_types(self, df):
        """Restores column order and casts columns to expected types"""
        df = df[self.columns]
        for col, expected, dtype in zip(self.columns, self.actual_dtypes, df.dtypes):
            if expected != dtype:
                df[col] = df[col].astype(expected)
        return df

    def align_index(self, df):
        """Transform index columns to actual indexes"""
        if len(self.index_cols) > 0:
            df = df.set_index(self.index_cols)
        return df

    def align(self, df):
        return self.align_index(self.align_types(df))

    def serialize(self, instance: pd.DataFrame):
        self._check_type(instance, pd.DataFrame, SerializationError)
        is_copied, instance = reset_index(instance, return_copied=True)

        self._validate_columns(instance, SerializationError)
        self._validate_dtypes(instance, SerializationError)

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
        return SeriesType(self.columns, self.dtypes, self.index_cols)

    def get_writer(self):
        from ebonite.ext.pandas.dataset_source import PandasWriter, PandasFormatCsv
        return PandasWriter(PandasFormatCsv())  # TODO env configuration
