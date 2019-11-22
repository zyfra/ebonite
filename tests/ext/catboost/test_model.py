import numpy as np
import pytest
from catboost import CatBoostClassifier

from ebonite.core.analyzer.model import ModelAnalyzer


@pytest.fixture
def catboost_model(pandas_data):
    return CatBoostClassifier(iterations=1).fit(pandas_data, [1, 0])


def test_catboost_model_wrapper(catboost_model, pandas_data, tmpdir):
    # this import is required to ensure that CatBoost model wrapper is registered
    import ebonite.ext.catboost  # noqa

    cbmw = ModelAnalyzer.analyze(catboost_model)

    assert cbmw.model is catboost_model

    with cbmw.dump() as artifact:
        artifact.materialize(tmpdir)
    cbmw.load(tmpdir)

    assert cbmw.model is not catboost_model

    np.testing.assert_array_almost_equal(catboost_model.predict(pandas_data), cbmw.model.predict(pandas_data))
