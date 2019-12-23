import numpy as np

from ebonite.client.helpers import create_model
from ebonite.ext.sklearn import SklearnModelWrapper


def test_create_model(sklearn_model_obj, pandas_data):
    model = create_model(sklearn_model_obj, pandas_data)

    assert model is not None
    assert isinstance(model.wrapper, SklearnModelWrapper)
    assert model.wrapper.exposed_methods == {'predict', 'predict_proba'}

    input_meta, output_meta = model.wrapper.method_signature('predict')
    assert input_meta.columns == list(pandas_data)
    assert output_meta.real_type == np.ndarray
    assert output_meta.shape == (None,)

    input_meta, output_meta = model.wrapper.method_signature('predict_proba')
    assert input_meta.columns == list(pandas_data)
    assert output_meta.real_type == np.ndarray
    assert output_meta.shape == (None, 2)

    assert {'numpy', 'sklearn', 'pandas'}.issubset(model.requirements.modules)
