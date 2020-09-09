from pyjackson import dumps, serialize, load
from ebonite.ext.numpy.dataset import NumpyDTypeSerializer, NumpyNdarrayDatasetType
import numpy as np
import requests
from ebonite.ext.flask.client import HTTPClient


arr = np.random.random(19)
print(arr)
r = requests.post('http://127.0.0.1:9000//model_gmc1_lgb_plotnost_sliva_melnitsy_1_9_gmts_1_2_predict',
                  json={'vector': arr})
print(r.text)