import os
import tempfile

import pytest

from ebonite.ext.flask import server
from ebonite.runtime import Interface
from ebonite.runtime.interface import expose


@pytest.fixture
def client():
    db_fd, server.app.config['DATABASE'] = tempfile.mkstemp()
    server.app.config['TESTING'] = True

    with server.app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(server.app.config['DATABASE'])


def test_health(client):
    assert client.get('/health').data == b'OK'


def test_create_interface_routes(client):
    class MyInterface(Interface):
        @expose
        def method(self, argument: str) -> int:
            return len(argument)

    server.create_interface_routes(MyInterface())

    resp = client.post('/method', data={'argument': 'a' * 5}).get_json()
    assert resp == {'ok': True, 'data': 5}
