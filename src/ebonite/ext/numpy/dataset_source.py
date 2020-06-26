import io
from typing import Tuple

import numpy as np

from ebonite.core.objects import ArtifactCollection
from ebonite.core.objects.artifacts import LazyBlob
from ebonite.core.objects.dataset_source import Dataset
from ebonite.repository.dataset.artifact import DatasetReader, DatasetWriter

DATA_FILE = 'data.npz'
DATA_KEY = 'data'


def save_npz(data: np.array):
    buf = io.BytesIO()
    np.savez_compressed(buf, **{DATA_KEY: data})
    return buf


class NumpyNdarrayWriter(DatasetWriter):
    """DatasetWriter implementation for numpy ndarray"""

    def write(self, dataset: Dataset) -> Tuple[DatasetReader, ArtifactCollection]:
        return NumpyNdarrayReader(), ArtifactCollection.from_blobs(
            {DATA_FILE: LazyBlob(lambda: save_npz(dataset.data))})


class NumpyNdarrayReader(DatasetReader):
    """DatasetReader implementation for numpy ndarray"""

    def read(self, artifacts: ArtifactCollection) -> Dataset:
        with artifacts.blob_dict() as blobs:
            with blobs[DATA_FILE].bytestream() as f:
                data = np.load(f)[DATA_KEY]
        return Dataset.from_object(data)
