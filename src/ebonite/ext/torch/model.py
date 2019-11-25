import contextlib
import os
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

    @ModelWrapper.with_model
    @contextlib.contextmanager
    def dump(self) -> ArtifactCollection:
        """
        Dumps `torch.nn.Module` instance to :class:`.InMemoryBlob` and creates :class:`.ArtifactCollection` from it

        :return: context manager with :class:`~ebonite.core.objects.ArtifactCollection`
        """
        buffer = BytesIO()
        torch.save(self.model, buffer)
        yield Blobs({self.model_file_name: InMemoryBlob(buffer.getvalue())})

    def load(self, path):
        """
        Loads `torch.nn.Module` instance from path

        :param path: path to load from
        """
        with open(os.path.join(path, self.model_file_name), 'rb') as f:
            self.model = torch.load(f)

    @ModelWrapper.with_model
    def predict(self, data):
        """
        Runs `torch.nn.Module` and returns output tensor values

        :param data: data to predict
        :return: prediction
        """
        return self.model(data)


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

    def process(self, obj) -> ModelWrapper:
        """
        Creates :class:`TorchModelWrapper` for PyTorch model object

        :param obj: obj to process
        :return: :class:`TorchModelWrapper` instance
        """
        return TorchModelWrapper().bind_model(obj)
