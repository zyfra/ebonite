import numpy as np

from ebonite.core.objects.dataset_source import Dataset
from tests.conftest import dataset_write_read_check


def test_ndarray_source():
    data = np.array([1, 2, 3])
    dataset = Dataset.from_object(data)
    dataset_write_read_check(dataset, custom_eq=np.array_equal)
