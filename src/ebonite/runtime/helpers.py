from ebonite.core.objects import core
from ebonite.runtime.command_line import start_runtime
from ebonite.runtime.interface import Interface
from ebonite.runtime.interface.ml_model import ModelLoader, model_interface
from ebonite.runtime.server import Server
from ebonite.utils.importing import module_importable


def run_model_server(model: 'core.Model', server: Server = None):
    """
    :func:`.start_runtime` wrapper helper which starts Ebonite runtime for given model and (optional) server

    :param model: model to start Ebonite runtime for
    :param server: server to use for Ebonite runtime, default is a flask-based server
    :return: nothing
    """

    if server is None:
        if module_importable('flask') and module_importable('flasgger'):
            from ebonite.ext.flask import FlaskServer
            server = FlaskServer()
        else:
            raise RuntimeError('You need to install flask and flasgger to use test flask server')

    class MockLoader(ModelLoader):
        def load(self) -> Interface:
            model.ensure_loaded()
            return model_interface(model)

    start_runtime(MockLoader(), server)
