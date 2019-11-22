import numpy as np
import pytest
from catboost import CatBoostClassifier, CatBoostRegressor

from ebonite.core.analyzer.model import ModelAnalyzer


@pytest.fixture
def catboost_params(tmpdir):
    return {'iterations': 1, 'train_dir': str(tmpdir)}


@pytest.fixture
def catboost_classifier(pandas_data, catboost_params):
    return CatBoostClassifier(**catboost_params).fit(pandas_data, [1, 0])


@pytest.fixture
def catboost_regressor(pandas_data, catboost_params):
    return CatBoostRegressor(**catboost_params).fit(pandas_data, [1, 0])


@pytest.mark.parametrize('catboost_model', ['catboost_classifier', 'catboost_regressor'])
def test_catboost_model_wrapper(catboost_model, pandas_data, tmpdir, request):
    catboost_model = request.getfixturevalue(catboost_model)

    # this import is required to ensure that CatBoost model wrapper is registered
    import ebonite.ext.catboost  # noqa

    cbmw = ModelAnalyzer.analyze(catboost_model)
    assert cbmw.model is catboost_model

    with cbmw.dump() as artifact:
        artifact.materialize(tmpdir)

    cbmw.unbind()
    with pytest.raises(ValueError):
        cbmw.predict(pandas_data)

    cbmw.load(tmpdir)
    assert cbmw.model is not catboost_model

    np.testing.assert_array_almost_equal(catboost_model.predict(pandas_data), cbmw.predict(pandas_data))
