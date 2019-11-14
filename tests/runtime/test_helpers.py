from ebonite.runtime import Interface
from ebonite.runtime.helpers import run_model_server
from ebonite.runtime.server import Server


def test_run_test_model_server(created_model):
    class MockServer(Server):
        def __init__(self):
            self.runned = False

        def run(self, executor: Interface):
            self.runned = True

    server = MockServer()
    run_model_server(created_model, server)
    assert server.runned
