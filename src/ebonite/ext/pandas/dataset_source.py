from abc import abstractmethod
from typing import Any, Dict

import pandas as pd

from ebonite.core.objects import DatasetType
from ebonite.core.objects.artifacts import Blob
from ebonite.core.objects.dataset_source import DatasetSource


class PandasDataset(DatasetSource):
    def __init__(self, dataset_type: DatasetType, target_type: DatasetType):
        super().__init__(dataset_type, target_type)
        self._data = None

    def get(self):
        return self.data

    @property
    def data(self) -> pd.DataFrame:
        if self._data is None:
            self._data = self._read()
        return self._data

    @abstractmethod
    def _read(self):
        pass


class PandasBlobDataset(PandasDataset):
    FORMATS = {
        'csv': pd.read_csv,
        'json': pd.read_json,
        'html': pd.read_html,
        'excel': pd.read_excel,
        'hdf': pd.read_hdf,
        'feather': pd.read_feather,
        'parquet': pd.read_parquet,
        'msgpack': pd.read_msgpack,
        'stata': pd.read_stata,
        'sas': pd.read_sas,
        'pickle': pd.read_pickle,
    }

    def __init__(self, dataset_type: DatasetType, blob: Blob, format: str, kwargs: Dict[str, Any],
                 target_type: DatasetType = None):
        super().__init__(dataset_type, target_type)
        self.kwargs = kwargs
        self.format = format
        self.blob = blob

    def _read(self):
        if self.format not in self.FORMATS:
            raise ValueError('Unknown format {}'.format(self.format))
        with self.blob.bytestream() as b:
            return self.FORMATS[self.format](b, **self.kwargs)


class PandasJdbcDataset(PandasDataset):
    def __init__(self, dataset_type: DatasetType, target_type: DatasetType, table: str, connection: str,
                 kwargs: Dict[str, Any]):
        super().__init__(dataset_type, target_type)
        self.kwargs = kwargs
        self.connection = connection
        self.table = table

    def _read(self):
        return pd.read_sql_table(self.table, self.connection, **self.kwargs)
