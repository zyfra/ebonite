import io
from abc import abstractmethod
from typing import Any, Dict

import pandas as pd

from ebonite.core.objects import DatasetType
from ebonite.core.objects.artifacts import Blob, LazyBlob
from ebonite.core.objects.dataset_source import Dataset, DatasetSource, DatasetWriter


class _PandasDatasetSource(DatasetSource):
    def __init__(self, dataset_type: DatasetType, kwargs: Dict[str, Any] = None):  # TODO better target
        super().__init__(dataset_type)
        self.kwargs = kwargs or {}
        self._data = None

    def get(self):
        return self.data

    @property
    def data(self) -> pd.DataFrame:
        if self._data is None:
            self._data = self._read()
        return self._data

    @abstractmethod
    def _read(self) -> pd.DataFrame:
        pass

    def read(self) -> Dataset:
        data = self._read()
        # TODO type validation
        return Dataset(data, self.dataset_type)


class PandasBlobDatasetSource(_PandasDatasetSource):
    FORMATS = {
        'csv': pd.read_csv,
        'json': pd.read_json,
        'html': pd.read_html,
        'excel': pd.read_excel,
        'hdf': pd.read_hdf,
        'feather': pd.read_feather,
        'parquet': pd.read_parquet,
        'stata': pd.read_stata,
        'sas': pd.read_sas,
        'pickle': pd.read_pickle,
    }

    def __init__(self, format: str, blob: Blob, dataset_type: DatasetType, kwargs: Dict[str, Any] = None):
        super().__init__(dataset_type, kwargs)
        self.blob = blob
        self.format = format

    def _read(self) -> pd.DataFrame:
        if self.format not in self.FORMATS:
            raise ValueError('Unknown format {}'.format(self.format))
        with self.blob.bytestream() as b:
            return self.FORMATS[self.format](b, **self.kwargs)


class PandasJdbcDatasetSource(_PandasDatasetSource):
    def __init__(self, dataset_type: DatasetType, table: str, connection: str,
                 kwargs: Dict[str, Any] = None):
        super().__init__(dataset_type, kwargs)
        self.connection = connection
        self.table = table

    def _read(self):
        return pd.read_sql_table(self.table, self.connection, **self.kwargs)


class CsvBlobPandasWriter(DatasetWriter):
    def write(self, dataset: Dataset) -> DatasetSource:
        def source():
            buf = io.BytesIO()
            dataset.data.to_csv(buf, header=True, index=False)
            return buf

        blob = LazyBlob(source)
        return PandasBlobDatasetSource('csv', blob, dataset.dataset_type)
