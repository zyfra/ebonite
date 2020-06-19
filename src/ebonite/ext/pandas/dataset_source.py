import io
import typing
from typing import Any, Dict, Tuple

import pandas as pd

from ebonite.core.objects.artifacts import ArtifactCollection, LazyBlob
from ebonite.core.objects.dataset_source import Dataset, DatasetReader, DatasetWriter


class PandasFormat:
    FORMATS: Dict[str, Tuple[typing.Callable, typing.Callable, typing.Type[typing.IO]]] = {
        'csv': (pd.read_csv, pd.DataFrame.to_csv, io.StringIO),
        'json': (pd.read_json, pd.DataFrame.to_json, io.StringIO),
        'html': (pd.read_html, pd.DataFrame.to_html, io.StringIO),
        'excel': (pd.read_excel, pd.DataFrame.to_excel, io.BytesIO),
        'hdf': (pd.read_hdf, pd.DataFrame.to_hdf, io.BytesIO),
        'feather': (pd.read_feather, pd.DataFrame.to_feather, io.BytesIO),
        'parquet': (pd.read_parquet, pd.DataFrame.to_parquet, io.BytesIO),
        'stata': (pd.read_stata, pd.DataFrame.to_stata, io.BytesIO),
        'pickle': (pd.read_pickle, pd.DataFrame.to_pickle, io.BytesIO),
    }

    def __init__(self, format: str, kwargs: Dict[str, Any] = None):
        if format not in self.FORMATS:
            raise ValueError(f'Unknown format {format}')
        self.format = format
        self.kwargs = kwargs or {}

    def read(self, file_or_path):
        return self.FORMATS[self.format][0](file_or_path, **self.kwargs)

    def write(self, dataframe) -> typing.IO:
        _, writer, buf = self.FORMATS[self.format]
        buf = buf()
        writer(dataframe, buf, **self.kwargs)
        return buf


class PandasReader(DatasetReader):
    def __init__(self, format: PandasFormat):
        self.format = format

    def read(self, artifacts: ArtifactCollection) -> Dataset:
        with self.blob.bytestream() as b:
            return Dataset.from_object(self.format.read(b))


class PandasWriter(DatasetWriter):
    def __init__(self, format: PandasFormat):
        self.format = format

    def write(self, dataset: Dataset) -> Tuple[DatasetReader, ArtifactCollection]:
        blob = LazyBlob(lambda: self.format.write(dataset.data))
        return PandasReader(self.format), ArtifactCollection.from_blobs({'data': blob})

# class PandasJdbcDatasetSource(_PandasDatasetSource):
#     def __init__(self, dataset_type: DatasetType, table: str, connection: str,
#                  kwargs: Dict[str, Any] = None):
#         super().__init__(dataset_type, kwargs)
#         self.connection = connection
#         self.table = table
#
#     def _read(self):
#         return pd.read_sql_table(self.table, self.connection, **self.kwargs)
