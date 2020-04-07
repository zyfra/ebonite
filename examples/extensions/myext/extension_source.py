import contextlib
import typing

from ebonite.core.analyzer.model import BindingModelHook
from ebonite.core.objects.artifacts import Blobs
from ebonite.core.objects.wrapper import FilesContextManager, ModelIO, ModelWrapper


# TODO и тут бы больше описания
class MyModelWrapper(ModelWrapper):
    type = 'mymodel'

    def __init__(self):
        super().__init__(MyModelIO())

    def _exposed_methods_mapping(self) -> typing.Dict[str, typing.Optional[str]]:
        return {
            'predict': '_predict'
        }

    def _predict(self, data):
        return data + 1


class MyModelIO(ModelIO):
    @contextlib.contextmanager
    def dump(self, model) -> FilesContextManager:
        yield Blobs({})

    def load(self, path):
        return 'ahaha'


class MyModelHook(BindingModelHook):
    def can_process(self, obj) -> bool:
        return True

    def must_process(self, obj) -> bool:
        return True

    def _wrapper_factory(self) -> ModelWrapper:
        return MyModelWrapper()
