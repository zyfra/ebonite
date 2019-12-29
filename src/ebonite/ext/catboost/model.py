import contextlib
import os
import tempfile

from catboost import CatBoostClassifier, CatBoostRegressor
from pyjackson.decorators import make_string

from ebonite.core.analyzer.base import CanIsAMustHookMixin
from ebonite.core.analyzer.model import ModelHook
from ebonite.core.objects.artifacts import ArtifactCollection, Blobs, LocalFileBlob
from ebonite.core.objects.wrapper import ModelWrapper


class CatBoostModelWrapper(ModelWrapper):
    """
    :class:`ebonite.core.objects.ModelWrapper` for CatBoost models.
    `.model` attribute is a `catboost.CatBoostClassifier` or `catboost.CatBoostRegressor` instance
    """
    classifier_file_name = 'clf.cb'
    regressor_file_name = 'rgr.cb'

    @ModelWrapper.with_model
    @contextlib.contextmanager
    def _dump(self) -> ArtifactCollection:
        """
        Dumps `catboost.CatBoostClassifier` or `catboost.CatBoostRegressor` instance to :class:`.LocalFileBlob` and
        creates :class:`.ArtifactCollection` from it

        :return: context manager with :class:`~ebonite.core.objects.ArtifactCollection`
        """
        model_file = tempfile.mktemp()
        try:
            self.model.save_model(model_file)
            yield Blobs({self._get_model_file_name(): LocalFileBlob(model_file)})
        finally:
            os.remove(model_file)

    def _get_model_file_name(self):
        if isinstance(self.model, CatBoostClassifier):
            return self.classifier_file_name
        return self.regressor_file_name

    def _load(self, path):
        """
        Loads `catboost.CatBoostClassifier` or `catboost.CatBoostRegressor` instance from path

        :param path: path to load from
        """
        if os.path.exists(os.path.join(path, self.classifier_file_name)):
            model_type = CatBoostClassifier
        else:
            model_type = CatBoostRegressor

        self.model = model_type()
        self.model.load_model(os.path.join(path, self._get_model_file_name()))

    def _exposed_methods_mapping(self):
        ret = {
            'predict': 'predict'
        }
        if isinstance(self.model, CatBoostClassifier):
            ret['predict_proba'] = 'predict_proba'
        return ret


@make_string(include_name=True)
class CatBoostModelHook(ModelHook, CanIsAMustHookMixin):
    """
    Hook for CatBoost models
    """

    def must_process(self, obj) -> bool:
        """
        Returns `True` if object is `catboost.CatBoostClassifier` or `catboost.CatBoostRegressor`

        :param obj: obj to check
        :return: `True` or `False`
        """
        return isinstance(obj, (CatBoostClassifier,  CatBoostRegressor))

    def process(self, obj, **kwargs) -> ModelWrapper:
        """
        Creates :class:`CatBoostModelWrapper` for CatBoost model object

        :param obj: obj to process
        :return: :class:`CatBoostModelWrapper` instance
        """
        return CatBoostModelWrapper().bind_model(obj, **kwargs)
