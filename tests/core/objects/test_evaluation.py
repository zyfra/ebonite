import typing

import numpy as np
import pytest

from ebonite.core.objects import Model, ModelWrapper
from ebonite.core.objects.artifacts import Blobs
from ebonite.core.objects.core import EvaluationResults
from ebonite.core.objects.metric import Metric
from ebonite.core.objects.wrapper import PickleModelIO


class EvalModelWrapper(ModelWrapper):

    def _exposed_methods_mapping(self) -> typing.Dict[str, str]:
        return {'predict1': 'predict1', 'predict2': 'predict2', 'predict3': 'predict3'}

    def predict1(self, data):
        return np.mean(data, axis=1)

    def predict2(self, data):
        return np.mean(data, axis=1)

    def predict3(self, data):
        return np.mean(data, axis=1) >= 0.5


@pytest.fixture
def float_data():
    return np.ones((5, 10)) * 0.3


@pytest.fixture
def float_target(float_data):
    return np.mean(float_data, axis=1)


@pytest.fixture
def float_target2(float_target):
    return 1. - float_target


@pytest.fixture
def bool_target(float_target):
    return float_target >= .5


@pytest.fixture
def eval_model(float_data):
    return Model('model', EvalModelWrapper(PickleModelIO()).bind_model('None', input_data=float_data), Blobs({}))


@pytest.fixture
def eval_model_saved(eval_model, task_saved):
    return task_saved.push_model(eval_model)


@pytest.fixture
def eval_pipeline(eval_model_saved: Model):
    pipeline = eval_model_saved.as_pipeline('predict1')
    pipeline.name = 'pipeline'
    return pipeline


class AccMetric(Metric):
    def evaluate(self, truth, prediction):
        return np.sum(truth == prediction) / len(truth)


@pytest.fixture
def accuracy_metric():
    return AccMetric()


class MaeMetric(Metric):
    def evaluate(self, truth: np.ndarray, prediction):
        return np.mean(np.abs(truth.astype(float) - prediction.astype(float)))


@pytest.fixture
def mae_metric():
    return MaeMetric()


@pytest.fixture
def task_with_evals(task_saved, eval_model_saved, eval_pipeline, float_data, float_target, float_target2, bool_target,
                    accuracy_metric, mae_metric):
    task_saved.add_pipeline(eval_pipeline)

    task_saved.add_metric('accuracy_score', accuracy_metric)
    task_saved.add_metric('mean_absolute_error', mae_metric)
    task_saved.add_evaluation('test_float1', float_data, float_target, ['accuracy_score', 'mean_absolute_error'])
    task_saved.add_evaluation('test_float2', float_data, float_target2, ['accuracy_score', 'mean_absolute_error'])
    task_saved.add_evaluation('test_bool', float_data, bool_target, ['accuracy_score', 'mean_absolute_error'])

    task_saved.save()
    return task_saved


def _check_float_eval(result: EvaluationResults, name: str, good):
    assert name in result
    eval = result[name]
    assert len(eval.results) == 1
    scores1 = eval.latest.scores
    assert 'accuracy_score' in scores1
    assert scores1['accuracy_score'] == (1 if good else 0)
    assert 'mean_absolute_error' in scores1
    if good:
        assert scores1['mean_absolute_error'] == 0
    else:
        assert scores1['mean_absolute_error'] > 0


def test_task_evaluation(task_with_evals):
    task_with_evals.evaluate_all()
    pipeline = task_with_evals._meta.get_pipeline_by_name('pipeline', task_with_evals)

    _check_float_eval(pipeline.evaluations, 'test_float1', True)
    _check_float_eval(pipeline.evaluations, 'test_float2', False)
    assert 'test_bool' not in pipeline.evaluations

    model = task_with_evals._meta.get_model_by_name('model', task_with_evals)

    assert 'predict1' in model.evaluations
    predict1 = model.evaluations['predict1']

    _check_float_eval(predict1, 'test_float1', True)
    _check_float_eval(predict1, 'test_float2', False)
    assert 'test_bool' not in predict1

    assert 'predict2' in model.evaluations
    predict2 = model.evaluations['predict2']

    _check_float_eval(predict2, 'test_float1', True)
    _check_float_eval(predict2, 'test_float2', False)
    assert 'test_bool' not in predict2

    assert 'predict3' in model.evaluations
    predict3 = model.evaluations['predict3']

    assert 'test_float1' not in predict3
    assert 'test_float2' not in predict3
    _check_float_eval(predict3, 'test_bool', True)


def test_evaluation_no_save(task_with_evals):
    task_with_evals.evaluate_all(save_result=False)
    pipeline = task_with_evals._meta.get_pipeline_by_name('pipeline', task_with_evals)
    assert len(pipeline.evaluations) == 0
    model = task_with_evals._meta.get_model_by_name('model', task_with_evals)
    assert len(model.evaluations) == 0


def test_reevaluation(task_with_evals):
    task_with_evals.evaluate_all()
    task_with_evals.evaluate_all()
    pipeline = task_with_evals._meta.get_pipeline_by_name('pipeline', task_with_evals)
    assert len(pipeline.evaluations['test_float1'].results) == 1
    model = task_with_evals._meta.get_model_by_name('model', task_with_evals)
    assert len(model.evaluations['predict1']['test_float1'].results) == 1


def test_reevaluation_force(task_with_evals):
    task_with_evals.evaluate_all()
    task_with_evals.evaluate_all(force=True)
    pipeline = task_with_evals._meta.get_pipeline_by_name('pipeline', task_with_evals)
    assert len(pipeline.evaluations['test_float1'].results) == 2
    model = task_with_evals._meta.get_model_by_name('model', task_with_evals)
    assert len(model.evaluations['predict1']['test_float1'].results) == 2


def test_wrong_evaluation_raise(task_with_evals):
    pipeline = task_with_evals._meta.get_pipeline_by_name('pipeline', task_with_evals)
    with pytest.raises(ValueError):
        pipeline.evaluate_set('aaa')
    with pytest.raises(ValueError):
        pipeline.evaluate_set('test_bool',  raise_on_error=True)

    model = task_with_evals._meta.get_model_by_name('model', task_with_evals)
    with pytest.raises(ValueError):
        model.evaluate_set('aaa')
    with pytest.raises(ValueError):
        model.evaluate_set('test_bool', method_name='predict1', raise_on_error=True)
