import contextlib
import os
import tempfile

from catboost import CatBoostClassifier
from pyjackson.decorators import make_string

from ebonite.core.analyzer.base import CanIsAMustHookMixin
from ebonite.core.analyzer.model import ModelHook
from ebonite.core.objects.artifacts import ArtifactCollection, Blobs, InMemoryBlob
from ebonite.core.objects.wrapper import ModelWrapper


class CatBoostModelWrapper(ModelWrapper):
    """
    :class:`ebonite.core.objects.ModelWrapper` for CatBoost models.
    `.model` attribute is a `catboost.CatBoostClassifier` instance
    """
    type = 'catboost_model_wrapper'
    model_file_name = 'model.pth'

    @ModelWrapper.with_model
    @contextlib.contextmanager
    def dump(self) -> ArtifactCollection:
        """
        Dumps `catboost.CatBoostClassifier` instance to :class:`.InMemoryBlob` and creates :class:`.ArtifactCollection` from it

        :return: context manager with :class:`~ebonite.core.objects.ArtifactCollection`
        """
        model_file = tempfile.mktemp()
        self.model.save_model(model_file)
        with open(model_file, mode='rb') as f:
            yield Blobs({self.model_file_name: InMemoryBlob(f.read())})

    def load(self, path):
        """
        Loads `catboost.CatBoostClassifier` instance from path

        :param path: path to load from
        """
        self.model = CatBoostClassifier()
        self.model.load_model(os.path.join(path, self.model_file_name))

    @ModelWrapper.with_model
    def predict(self, data):
        """
        Runs `catboost.CatBoostClassifier` and returns predictions

        :param data: data to predict
        :return: prediction
        """
        return self.model.predict(data)


@make_string(include_name=True)
class CatBoostModelHook(ModelHook, CanIsAMustHookMixin):
    """
    Hook for CatBoost models
    """

    def must_process(self, obj) -> bool:
        """
        Returns `True` if object is `catboost.CatBoostClassifier`

        :param obj: obj to check
        :return: `True` or `False`
        """
        return isinstance(obj, CatBoostClassifier)

    def process(self, obj) -> ModelWrapper:
        """
        Creates :class:`CatBoostModelWrapper` for CatBoost model object

        :param obj: obj to process
        :return: :class:`CatBoostModelWrapper` instance
        """
        return CatBoostModelWrapper().bind_model(obj)
