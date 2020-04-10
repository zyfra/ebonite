import contextlib
import os
import tempfile
import typing

import lightgbm as lgb

from ebonite.core.analyzer.base import TypeHookMixin
from ebonite.core.analyzer.model import BindingModelHook
from ebonite.core.objects.artifacts import Blobs, LocalFileBlob
from ebonite.core.objects.wrapper import FilesContextManager, LibModelWrapperMixin, ModelIO, ModelWrapper


class LightGBMModelIO(ModelIO):
    """
    :class:`.ModelIO` implementation for `lightgbm.Booster` type
    """
    model_path = 'model.lgb'

    @contextlib.contextmanager
    def dump(self, model: lgb.Booster) -> FilesContextManager:
        with tempfile.TemporaryDirectory(prefix='ebonite_lightgbm_dump') as f:
            path = os.path.join(f, self.model_path)
            model.save_model(path)
            yield Blobs({self.model_path: LocalFileBlob(path)})

    def load(self, path):
        model_file = os.path.join(path, self.model_path)
        return lgb.Booster(model_file=model_file)


class LightGBMModelWrapper(LibModelWrapperMixin):
    """
    :class:`.ModelWrapper` implementation for `lightgbm.Booster` type
    """
    libraries = [lgb]

    def __init__(self):
        super().__init__(LightGBMModelIO())

    def _exposed_methods_mapping(self) -> typing.Dict[str, str]:
        return {
            'predict': '_predict'
        }

    @ModelWrapper.with_model
    def _predict(self, data):
        if isinstance(data, lgb.Dataset):
            data = data.data
        return self.model.predict(data)


class LightGBMModelHook(BindingModelHook, TypeHookMixin):
    """
    :class:`.ModelHook` implementation for `lightgbm.Booster` type
    """
    valid_types = [lgb.Booster]

    def _wrapper_factory(self) -> ModelWrapper:
        return LightGBMModelWrapper()
