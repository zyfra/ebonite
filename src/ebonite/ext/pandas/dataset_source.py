import io
import os
import tempfile
import typing
from typing import Any, Dict, Tuple

import pandas as pd
from pyjackson.decorators import type_field

from ebonite.core.objects.artifacts import ArtifactCollection, LazyBlob
from ebonite.core.objects.dataset_source import Dataset
from ebonite.ext.pandas import DataFrameType
from ebonite.ext.pandas.dataset import has_index, reset_index
from ebonite.repository.dataset.artifact import DatasetReader, DatasetWriter

PANDAS_DATA_FILE = 'data.pd'


@type_field('type')
class PandasFormat:
    """ABC for reading and writing different formats supported in pandas

    :param read_args: additional arguments for reading
    :param write_args: additional arguments for writing
    """
    type: str = None
    read_func: typing.Callable = None
    write_func: typing.Callable = None
    buffer_type: typing.Type[typing.IO] = None

    def __init__(self, read_args: Dict[str, Any] = None, write_args: Dict[str, Any] = None):
        self.write_args = write_args or {}
        self.read_args = read_args or {}

    def read(self, file_or_path):
        """Read DataFrame

        :param file_or_path: source for read function"""
        kwargs = self.add_read_args()
        kwargs.update(self.read_args)
        return type(self).read_func(file_or_path, **kwargs)

    def write(self, dataframe) -> typing.IO:
        """Write DataFrame to buffer

        :param dataframe: DataFrame to write
        """
        buf = self.buffer_type()
        kwargs = self.add_write_args()
        kwargs.update(self.write_args)
        if has_index(dataframe):
            dataframe = reset_index(dataframe)
        type(self).write_func(dataframe, buf, **kwargs)
        return buf

    def add_read_args(self) -> Dict[str, Any]:
        """Fuction with additional read argumnets for child classes to override"""
        return {}

    def add_write_args(self) -> Dict[str, Any]:
        """Fuction with additional write argumnets for child classes to override"""
        return {}


class PandasFormatCsv(PandasFormat):
    type = 'csv'
    read_func = pd.read_csv
    write_func = pd.DataFrame.to_csv
    buffer_type = io.StringIO

    def add_write_args(self) -> Dict[str, Any]:
        return {'index': False}


class PandasFormatJson(PandasFormat):
    type = 'json'
    read_func = pd.read_json
    write_func = pd.DataFrame.to_json
    buffer_type = io.StringIO

    def add_write_args(self) -> Dict[str, Any]:
        return {'date_format': 'iso', 'date_unit': 'ns'}

    def read(self, file_or_path):
        # read_json creates index for some reason
        return super(PandasFormatJson, self).read(file_or_path).reset_index(drop=True)


class PandasFormatHtml(PandasFormat):
    type = 'html'
    read_func = pd.read_html
    write_func = pd.DataFrame.to_html
    buffer_type = io.StringIO

    def add_write_args(self) -> Dict[str, Any]:
        return {'index': False}

    def read(self, file_or_path):
        # read_html returns list of dataframes
        df = super(PandasFormatHtml, self).read(file_or_path)
        return df[0]


class PandasFormatExcel(PandasFormat):
    type = 'excel'
    read_func = pd.read_excel
    write_func = pd.DataFrame.to_excel
    buffer_type = io.BytesIO

    def add_write_args(self) -> Dict[str, Any]:
        return {'index': False}


class PandasFormatHdf(PandasFormat):
    type = 'hdf'
    read_func = pd.read_hdf
    write_func = pd.DataFrame.to_hdf
    buffer_type = io.BytesIO

    key = 'data'

    def add_write_args(self) -> Dict[str, Any]:
        return {'key': self.key}

    def write(self, dataframe) -> typing.IO:
        # to_hdf can write only to file or HDFStore, so there's that
        kwargs = self.add_write_args()
        kwargs.update(self.write_args)
        if has_index(dataframe):
            dataframe = reset_index(dataframe)
        path = tempfile.mktemp(suffix='.hd5', dir='.')  # tempfile.TemporaryDirectory breaks on windows for some reason
        try:
            type(self).write_func(dataframe, path, **kwargs)
            with open(path, 'rb') as f:
                return self.buffer_type(f.read())
        finally:
            os.unlink(path)

    def add_read_args(self) -> Dict[str, Any]:
        return {'key': self.key}

    def read(self, file_or_path):
        if not isinstance(file_or_path, str):
            path = tempfile.mktemp('.hd5', dir='.')
            try:
                with open(path, 'wb') as f:
                    f.write(file_or_path.read())
                df = super().read(path)
            finally:
                os.unlink(path)
        else:
            df = super().read(file_or_path)

        return df.reset_index(drop=True)


class PandasFormatFeather(PandasFormat):
    type = 'feather'
    read_func = pd.read_feather
    write_func = pd.DataFrame.to_feather
    buffer_type = io.BytesIO


class PandasFormatParquet(PandasFormat):
    type = 'parquet'
    read_func = pd.read_parquet
    write_func = pd.DataFrame.to_parquet
    buffer_type = io.BytesIO


# class PandasFormatStata(PandasFormat): # TODO int32 converts to int64 for some reason
#     type = 'stata'
#     read_func = pd.read_stata
#     write_func = pd.DataFrame.to_stata
#     buffer_type = io.BytesIO
#
#     def add_write_args(self) -> Dict[str, Any]:
#         return {'write_index': False}
#
# class PandasFormatPickle(PandasFormat): # TODO buffer closed error for some reason
#     type = 'pickle'
#     read_func = pd.read_pickle
#     write_func = pd.DataFrame.to_pickle
#     buffer_type = io.BytesIO


PANDAS_FORMATS = {f.type: f() for f in PandasFormat._subtypes.values() if f is not PandasFormat}


class PandasReader(DatasetReader):
    """DatasetReader for pandas dataframes

    :param format: PandasFormat instance to use
    :param data_type: DataFrameType to use for aliging read data
    """

    def __init__(self, format: PandasFormat, data_type: DataFrameType):
        self.data_type = data_type
        self.format = format

    def read(self, artifacts: ArtifactCollection) -> Dataset:
        with artifacts.blob_dict() as blobs, blobs[PANDAS_DATA_FILE].bytestream() as b:
            return Dataset.from_object(self.data_type.align(self.format.read(b)))


class PandasWriter(DatasetWriter):
    """DatasetWriter for pandas dataframes

    :param format: PandasFormat instance to use
    """

    def __init__(self, format: PandasFormat):
        self.format = format

    def write(self, dataset: Dataset) -> Tuple[DatasetReader, ArtifactCollection]:
        blob = LazyBlob(lambda: self.format.write(dataset.data))
        return PandasReader(self.format, dataset.dataset_type), ArtifactCollection.from_blobs({PANDAS_DATA_FILE: blob})
