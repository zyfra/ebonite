import lightgbm as lgb
import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def np_payload():
    return np.linspace(0, 2, 5).reshape((-1, 1))


@pytest.fixture
def dataset_np(np_payload):
    return lgb.Dataset(np_payload, label=np_payload.reshape((-1,)), free_raw_data=False)


@pytest.fixture
def df_payload():
    return pd.DataFrame([{'a': i} for i in range(2)])


@pytest.fixture
def dataset_df(df_payload):
    return lgb.Dataset(df_payload, label=np.linspace(0, 2).reshape((-1, 1)), free_raw_data=False)
