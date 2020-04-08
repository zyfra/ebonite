import contextlib
import os
import typing
from io import BytesIO

import torch
from pyjackson.decorators import make_string

from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.model import BindingModelHook
from ebonite.core.objects.artifacts import ArtifactCollection, Blobs, InMemoryBlob
from ebonite.core.objects.wrapper import ModelIO, ModelWrapper


class TorchModelIO(ModelIO):
    """
    :class:`ebonite.core.objects.ModelIO` for PyTorch models
    """
    model_file_name = 'model.pth'
    model_jit_file_name = 'model.jit.pth'

    @contextlib.contextmanager
    def dump(self, model) -> ArtifactCollection:
        """
        Dumps `torch.nn.Module` instance to :class:`.InMemoryBlob` and creates :class:`.ArtifactCollection` from it

        :return: context manager with :class:`~ebonite.core.objects.ArtifactCollection`
        """
        is_jit = isinstance(model, torch.jit.ScriptModule)
        save = torch.jit.save if is_jit else torch.save
        model_name = self.model_jit_file_name if is_jit else self.model_file_name

        buffer = BytesIO()
        save(model, buffer)
        yield Blobs({model_name: InMemoryBlob(buffer.getvalue())})

    def load(self, path):
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
            return load(f)


class TorchModelWrapper(ModelWrapper):
    """
    :class:`ebonite.core.objects.ModelWrapper` for PyTorch models. `.model` attribute is a `torch.nn.Module` instance
    """
    def __init__(self):
        super().__init__(TorchModelIO())

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
class TorchModelHook(BindingModelHook, TypeHookMixin):
    """
    Hook for PyTorch models
    """
    valid_types = [torch.nn.Module]

    def _wrapper_factory(self) -> ModelWrapper:
        """
        Creates :class:`TorchModelWrapper` for PyTorch model object

        :return: :class:`TorchModelWrapper` instance
        """
        return TorchModelWrapper()
