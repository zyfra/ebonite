import os

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


model_params = ['a', 'b']
predict_params = ['c', 'd']
mdl = Model('', MockModelWrapper(), input_meta=DataFrameType(model_params), output_meta=DataFrameType(predict_params))
exposed_methods = ['predict']


class PrintServer(Server):
    def run(self, executor: Interface):
        assert executor.exposed_methods() == exposed_methods
        predict_args = executor.exposed_method_args('predict')[0]
        assert issubclass(predict_args.type, DataFrameType)
        assert list(predict_args.type.columns) == model_params


class MockModel:
    last_args = None

    def predict(self, *args, **kwargs):
        MockModel.last_args = (args, kwargs)


class MockLoader(InterfaceLoader):
    def load(self) -> Interface:
        mdl.wrapper.bind_model(MockModel())
        return model_interface(mdl)


def test_runtime():
    os.environ[SERVER_ENV] = PrintServer.classpath
    os.environ[LOADER_ENV] = MockLoader.classpath
    start_runtime()
