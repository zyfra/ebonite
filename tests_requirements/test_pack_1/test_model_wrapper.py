import typing

import numpy as np
from test_pack_1 import test_model

from ebonite.core.analyzer import TypeHookMixin
from ebonite.core.analyzer.model import BindingModelHook
from ebonite.core.objects.wrapper import ModelWrapper, PickleModelIO


class TestModelWrapper(ModelWrapper):
    """
    :class:`.ModelWrapper` implementation for `TestM` type
    """
    libraries = [test_model]

    def __init__(self):
        super().__init__(PickleModelIO())

    def _exposed_methods_mapping(self) -> typing.Dict[str, str]:
        return {
        }

    @ModelWrapper.with_model
    def _predict(self, data: np.array):
        return self.model.predict(data)

    @ModelWrapper.with_model
    def _predict_comp(self, data: np.array):
        return self.model.predict_comp(data)


class TestModelHook(BindingModelHook, TypeHookMixin):
    """
    :class:`.ModelHook` implementation for `TestM` type
    """
    valid_types = [test_model.TestM]

    def must_process(self, obj) -> bool:
        return True

    def _wrapper_factory(self) -> ModelWrapper:
        return TestModelWrapper()
