import numpy as np
import pandas as pd
import pytest
import xgboost


@pytest.fixture
def np_payload():
    return np.linspace(0, 2).reshape((-1, 1))


@pytest.fixture
def dmatrix_np(np_payload):
    return xgboost.DMatrix(np_payload, label=np_payload)


@pytest.fixture
def df_payload():
    return pd.DataFrame([{'a': i} for i in range(2)])


@pytest.fixture
def dmatrix_df(df_payload):
    return xgboost.DMatrix(df_payload, label=np.linspace(0, 2).reshape((-1, 1)))
