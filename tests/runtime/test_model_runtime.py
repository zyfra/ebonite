import os
import typing

import pandas as pd

from ebonite.build.provider import LOADER_ENV, SERVER_ENV
from ebonite.core.objects.core import Model
from ebonite.core.objects.wrapper import ModelWrapper
from ebonite.ext.pandas import DataFrameType
from ebonite.runtime.command_line import start_runtime
from ebonite.runtime.interface import Interface, InterfaceLoader
from ebonite.runtime.interface.ml_model import model_interface
from ebonite.runtime.server import Server


class MockModelWrapper(ModelWrapper):
    type = 'test_wrapper2'

    def __init__(self):
        super().__init__(None)

    def _exposed_methods_mapping(self) -> typing.Dict[str, typing.Optional[str]]:
        return {
            'predict': 'predict'
        }


model_params = ['a', 'b']
predict_params = ['c', 'd']
mdl = Model('', MockModelWrapper())
exposed_methods = ['predict']


class PrintServer(Server):
    def run(self, executor: Interface):
        assert executor.exposed_methods() == exposed_methods
        predict_args = executor.exposed_method_args('predict')[0]
        assert issubclass(predict_args.type, DataFrameType)
        assert list(predict_args.type.columns) == model_params


class MockModel:
    def predict(self, *args, **kwargs):
        assert len(args) == 1
        assert list(args[0].columns) == model_params
        assert len(kwargs) == 0
        return pd.DataFrame([[1, 0], [0, 1]], columns=predict_params)


class MockLoader(InterfaceLoader):
    def load(self) -> Interface:
        mdl.wrapper.bind_model(MockModel(), input_data=pd.DataFrame([[1, 0], [0, 1]], columns=model_params))
        return model_interface(mdl)


def test_runtime():
    os.environ[SERVER_ENV] = PrintServer.classpath
    os.environ[LOADER_ENV] = MockLoader.classpath
    start_runtime()
