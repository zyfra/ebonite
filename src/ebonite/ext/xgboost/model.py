import contextlib
import os
import tempfile
import typing

import xgboost

from ebonite.core.analyzer.base import TypeHookMixin
from ebonite.core.analyzer.model import BindingModelHook
from ebonite.core.objects.artifacts import Blobs, LocalFileBlob
from ebonite.core.objects.wrapper import FilesContextManager, LibModelWrapperMixin, ModelIO, ModelWrapper


class XGBoostModelIO(ModelIO):
    """
    :class:`~.ModelIO` implementation for XGBoost models
    """
    model_path = 'model.xgb'

    @contextlib.contextmanager
    def dump(self, model: xgboost.Booster) -> FilesContextManager:
        with tempfile.TemporaryDirectory(prefix='ebonite_xgboost_dump') as f:
            path = os.path.join(f, self.model_path)
            model.save_model(path)
            yield Blobs({self.model_path: LocalFileBlob(path)})

    def load(self, path):
        model = xgboost.Booster()
        model.load_model(os.path.join(path, self.model_path))
        return model


class XGBoostModelWrapper(LibModelWrapperMixin):
    """
    :class:`~.ModelWrapper` implementation for XGBoost models
    """
    libraries = [xgboost]

    def __init__(self):
        super().__init__(XGBoostModelIO())

    def _exposed_methods_mapping(self) -> typing.Dict[str, str]:
        return {
            'predict': '_predict'
        }

    @ModelWrapper.with_model
    def _predict(self, data):
        if not isinstance(data, xgboost.DMatrix):
            data = xgboost.DMatrix(data)
        return self.model.predict(data)


class XGBoostModelHook(BindingModelHook, TypeHookMixin):
    """
    :class:`.ModelHook` implementation for `xgboost.Booster` objects
    """
    valid_types = [xgboost.Booster]

    def _wrapper_factory(self) -> ModelWrapper:
        return XGBoostModelWrapper()
