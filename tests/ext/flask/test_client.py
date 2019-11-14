import json

import numpy as np
import pytest
import responses
from pandas import DataFrame
from requests.exceptions import HTTPError

from ebonite.ext.flask.client import HTTPClient

interface_json = '''
{
  "methods":[
    {
      "args":{"vector":{"columns":["a","b"],"type":"pandas_df"}},
      "name":"predict",
      "out_type":{"dtype":"float64","shape":[2],"type":"numpy_ndarray"}}],
  "version":"0.2.0"
}
'''


@pytest.fixture
def data_frame():
    return DataFrame([[1, 2], [2, 1]], columns=['a', 'b'])


@pytest.fixture
def ndarray():
    return np.asarray([0.7, 0.3], dtype=np.float64)


@responses.activate
def test_http_client__arg_ok(data_frame, ndarray):
    _mock_interface_json()
    _mock_predict()
    assert np.array_equal(HTTPClient().predict(data_frame), ndarray)


@responses.activate
def test_http_client__kwarg_ok(data_frame, ndarray):
    _mock_interface_json()
    _mock_predict()
    assert np.array_equal(HTTPClient().predict(vector=data_frame), ndarray)


@responses.activate
def test_http_client__no_interface():
    responses.add(responses.GET, 'http://localhost:9000/interface.json',
                  json='', status=404)
    with pytest.raises(HTTPError):
        HTTPClient().go()


@responses.activate
def test_http_client__unknown_method():
    _mock_interface_json()
    with pytest.raises(KeyError):
        HTTPClient().go()


@responses.activate
def test_http_client__less_args():
    _mock_interface_json()
    with pytest.raises(ValueError):
        HTTPClient().predict()


@responses.activate
def test_http_client__mixed_args():
    _mock_interface_json()
    with pytest.raises(ValueError):
        HTTPClient().predict(1, k=1)


@responses.activate
def test_http_client__wrong_args():
    _mock_interface_json()
    with pytest.raises(ValueError):
        HTTPClient().predict(k=1)


@responses.activate
def test_http_client__excessive_kwargs():
    _mock_interface_json()
    with pytest.raises(ValueError):
        HTTPClient().predict(vector=1, k=1)


@responses.activate
def test_http_client__excessive_args():
    _mock_interface_json()
    with pytest.raises(ValueError):
        HTTPClient().predict(1, 1)


@responses.activate
def test_http_client__wrong_arg_type():
    _mock_interface_json()
    # pyjackson serializers raise unpredictable exceptions
    with pytest.raises(Exception):
        HTTPClient().predict(1)


def _mock_interface_json():
    responses.add(responses.GET, 'http://localhost:9000/interface.json',
                  json=json.loads(interface_json), status=200)


def _mock_predict():
    responses.add(responses.POST, 'http://localhost:9000/predict',
                  json={'data': [0.7, 0.3]}, status=200)
