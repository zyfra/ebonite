import numpy as np

from ebonite.client.helpers import create_model
from ebonite.ext.sklearn import SklearnModelWrapper


def test_create_model(sklearn_model_obj, pandas_data):
    model = create_model(sklearn_model_obj, pandas_data)
    assert model is not None
    assert isinstance(model.wrapper, SklearnModelWrapper)
    assert model.input_meta.columns == list(pandas_data)

    assert model.output_meta.real_type == np.ndarray
    assert {'numpy', 'sklearn', 'pandas'}.issubset(model.requirements.modules)
