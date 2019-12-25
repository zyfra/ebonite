import contextlib
import os
import typing
from io import BytesIO

import torch
from pyjackson.decorators import make_string

from ebonite.core.analyzer.base import CanIsAMustHookMixin
from ebonite.core.analyzer.model import ModelHook
from ebonite.core.objects.artifacts import ArtifactCollection, Blobs, InMemoryBlob
from ebonite.core.objects.wrapper import ModelWrapper


class TorchModelWrapper(ModelWrapper):
    """
    :class:`ebonite.core.objects.ModelWrapper` for PyTorch models. `.model` attribute is a `torch.nn.Module` instance
    """
    model_file_name = 'model.pth'
    model_jit_file_name = 'model.jit.pth'

    @ModelWrapper.with_model
    @contextlib.contextmanager
    def _dump(self) -> ArtifactCollection:
        """
        Dumps `torch.nn.Module` instance to :class:`.InMemoryBlob` and creates :class:`.ArtifactCollection` from it

        :return: context manager with :class:`~ebonite.core.objects.ArtifactCollection`
        """
        is_jit = isinstance(self.model, torch.jit.ScriptModule)
        save = torch.jit.save if is_jit else torch.save
        model_name = self.model_jit_file_name if is_jit else self.model_file_name

        buffer = BytesIO()
        save(self.model, buffer)
        yield Blobs({model_name: InMemoryBlob(buffer.getvalue())})

    def _load(self, path):
        """
        Loads `torch.nn.Module` instance from path

        :param path: path to load from
        """
        model_path = os.path.join(path, self.model_jit_file_name)
        load = torch.jit.load
        if not os.path.exists(model_path):
            model_path = os.path.join(path, self.model_file_name)
            load = torch.load

        with open(model_path, 'rb') as f:
            self.model = load(f)

    def _exposed_methods_mapping(self) -> typing.Dict[str, str]:
        return {
            'predict': '_predict'
        }

    @ModelWrapper.with_model
    def _predict(self, data):
        if isinstance(data, torch.Tensor):
            return self.model(data)
        return self.model(*data)


@make_string(include_name=True)
class TorchModelHook(ModelHook, CanIsAMustHookMixin):
    """
    Hook for PyTorch models
    """

    def must_process(self, obj) -> bool:
        """
        Returns `True` if object is `torch.nn.Module`

        :param obj: obj to check
        :return: `True` or `False`
        """
        return isinstance(obj, torch.nn.Module)

    def process(self, obj, **kwargs) -> ModelWrapper:
        """
        Creates :class:`TorchModelWrapper` for PyTorch model object

        :param obj: obj to process
        :param kwargs: additional information to be used for analysis
        :return: :class:`TorchModelWrapper` instance
        """
        return TorchModelWrapper().bind_model(obj, **kwargs)
