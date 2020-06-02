import socket

import pytest

from ebonite.core.objects.core import Model
from ebonite.runtime.server import HTTPServerConfig
from tests.client.test_func import func


@pytest.fixture
def model():
    model = Model.create(func, "kek", "Test Model")
    return model


def check_ebonite_port_free():
    host, port = HTTPServerConfig.host, HTTPServerConfig.port
    s = socket.socket()
    # With this option `bind` will fail only if other process actively listens on port
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((host, port))
    except OSError:
        raise OSError(f'Ebonite services start at port {port} but it\'s used by other process') from None
    finally:
        s.close()
