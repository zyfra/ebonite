import contextlib
import os
import tempfile
import typing

import lightgbm as lgb

from ebonite.core.analyzer.base import TypeHookMixin
from ebonite.core.analyzer.model import ModelHook
from ebonite.core.objects import ModelWrapper
from ebonite.core.objects.artifacts import Blobs, LocalFileBlob
from ebonite.core.objects.wrapper import FilesContextManager


class LightGBMModelWrapper(ModelWrapper):
    """
    :class:`.ModelWrapper` implementation for `lightgbm.Booster` type
    """
    model_path = 'model.lgb'

    @contextlib.contextmanager
    @ModelWrapper.with_model
    def _dump(self) -> FilesContextManager:
        model: lgb.Booster = self.model
        with tempfile.TemporaryDirectory(prefix='ebonite_lightgbm_dump') as f:
            path = os.path.join(f, self.model_path)
            model.save_model(path)
            yield Blobs({self.model_path: LocalFileBlob(path)})

    def _load(self, path):
        model_file = os.path.join(path, self.model_path)
        self.model = lgb.Booster(model_file=model_file)

    def _exposed_methods_mapping(self) -> typing.Dict[str, str]:
        return {
            'predict': '_predict'
        }

    @ModelWrapper.with_model
    def _predict(self, data):
        if isinstance(data, lgb.Dataset):
            data = data.data
        return self.model.predict(data)


class LightGBMModelHook(ModelHook, TypeHookMixin):
    """
    :class:`.ModelHook` implementation for `lightgbm.Booster` type
    """
    valid_types = [lgb.Booster]

    def process(self, obj, **kwargs) -> ModelWrapper:
        return LightGBMModelWrapper().bind_model(obj, **kwargs)
