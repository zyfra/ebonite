import contextlib
import typing

from ebonite.core.analyzer.model import BindingModelHook
from ebonite.core.objects.artifacts import Blobs
from ebonite.core.objects.wrapper import FilesContextManager, ModelIO, ModelWrapper

# In order for you to use extensions you have to define class describing IO of your model,
# model wrapper that is describing what behaviour you expect in service that will be built with ebonite and Hook,
# so ebonite can see the models as part of it's code


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
