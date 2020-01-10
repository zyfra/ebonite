import contextlib
import typing

from ebonite.core.analyzer.model import ModelHook
from ebonite.core.objects.artifacts import Blobs
from ebonite.core.objects.wrapper import FilesContextManager, ModelWrapper


# TODO и тут бы больше описания
class MyModelWrapper(ModelWrapper):
    type = 'mymodel'

    @contextlib.contextmanager
    @ModelWrapper.with_model
    def _dump(self) -> FilesContextManager:
        yield Blobs({})

    def _load(self, path):
        return self.bind_model('ahaha')

    def _exposed_methods_mapping(self) -> typing.Dict[str, typing.Optional[str]]:
        return {
            'predict': '_predict'
        }

    def _predict(self, data):
        return data + 1


class MyModelHook(ModelHook):
    def can_process(self, obj) -> bool:
        return True

    def must_process(self, obj) -> bool:
        return True

    def process(self, obj, **kwargs) -> ModelWrapper:
        return MyModelWrapper().bind_model(obj, **kwargs)
