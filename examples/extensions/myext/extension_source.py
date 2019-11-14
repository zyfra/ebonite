import contextlib

from ebonite.core.analyzer.model import ModelHook
from ebonite.core.objects.artifacts import Blobs
from ebonite.core.objects.wrapper import FilesContextManager, ModelWrapper


# TODO и тут бы больше описания
class MyModelWrapper(ModelWrapper):
    type = 'mymodel'

    @contextlib.contextmanager
    @ModelWrapper.with_model
    def dump(self) -> FilesContextManager:
        yield Blobs({})

    def load(self, path):
        return self.bind_model('ahaha')

    @ModelWrapper.with_model
    def predict(self, data):
        return data + 1


class MyModelHook(ModelHook):
    def can_process(self, obj) -> bool:
        return True

    def must_process(self, obj) -> bool:
        return True

    def process(self, obj) -> ModelWrapper:
        return MyModelWrapper().bind_model(obj)
