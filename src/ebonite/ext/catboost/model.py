import contextlib
import os
import tempfile

import catboost
from catboost import CatBoostClassifier, CatBoostRegressor
from pyjackson.decorators import make_string

from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.model import BindingModelHook
from ebonite.core.objects.artifacts import ArtifactCollection, Blobs, LocalFileBlob
from ebonite.core.objects.wrapper import LibModelWrapperMixin, ModelIO, ModelWrapper


class CatBoostModelIO(ModelIO):
    """
    :class:`ebonite.core.objects.ModelIO` for CatBoost models.
    """
    classifier_file_name = 'clf.cb'
    regressor_file_name = 'rgr.cb'

    @contextlib.contextmanager
    def dump(self, model) -> ArtifactCollection:
        """
        Dumps `catboost.CatBoostClassifier` or `catboost.CatBoostRegressor` instance to :class:`.LocalFileBlob` and
        creates :class:`.ArtifactCollection` from it

        :return: context manager with :class:`~ebonite.core.objects.ArtifactCollection`
        """
        model_file = tempfile.mktemp()
        try:
            model.save_model(model_file)
            yield Blobs({self._get_model_file_name(model): LocalFileBlob(model_file)})
        finally:
            os.remove(model_file)

    def _get_model_file_name(self, model):
        if isinstance(model, CatBoostClassifier):
            return self.classifier_file_name
        return self.regressor_file_name

    def load(self, path):
        """
        Loads `catboost.CatBoostClassifier` or `catboost.CatBoostRegressor` instance from path

        :param path: path to load from
        """
        if os.path.exists(os.path.join(path, self.classifier_file_name)):
            model_type = CatBoostClassifier
        else:
            model_type = CatBoostRegressor

        model = model_type()
        model.load_model(os.path.join(path, self._get_model_file_name(model)))
        return model


class CatBoostModelWrapper(LibModelWrapperMixin):
    """
    :class:`ebonite.core.objects.ModelWrapper` for CatBoost models.
    `.model` attribute is a `catboost.CatBoostClassifier` or `catboost.CatBoostRegressor` instance
    """
    libraries = [catboost]

    def __init__(self):
        super().__init__(CatBoostModelIO())

    def _exposed_methods_mapping(self):
        ret = {
            'predict': 'predict'
        }
        if isinstance(self.model, CatBoostClassifier):
            ret['predict_proba'] = 'predict_proba'
        return ret


@make_string(include_name=True)
class CatBoostModelHook(BindingModelHook, TypeHookMixin):
    """
    Hook for CatBoost models
    """
    valid_types = [CatBoostClassifier,  CatBoostRegressor]

    def _wrapper_factory(self) -> ModelWrapper:
        """
        Creates :class:`CatBoostModelWrapper` for CatBoost model object

        :return: :class:`CatBoostModelWrapper` instance
        """
        return CatBoostModelWrapper()
