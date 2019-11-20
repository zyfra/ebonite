import numpy as np
import pytest
import xgboost


@pytest.fixture
def dmatrix():
    return xgboost.DMatrix(np.linspace(0, 10).reshape((-1, 1)), label=np.linspace(5, 15).reshape((-1, 1)))
