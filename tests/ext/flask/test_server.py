import os
import tempfile

import pytest
from flask import Flask

from ebonite.ext.flask.server import _setup_app, create_interface_routes
from ebonite.runtime import Interface
from ebonite.runtime.interface import expose


@pytest.fixture
def client():
    app = Flask(__name__)
    _setup_app(app)

    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


def test_health(client):
    assert client.get('/health').data == b'OK'


def test_create_interface_routes(client):
    class MyInterface(Interface):
        @expose
        def method(self, argument: str) -> int:
            return len(argument)

    create_interface_routes(client.application, MyInterface())

    resp = client.post('/method', data={'argument': 'a' * 5}).get_json()
    assert resp == {'ok': True, 'data': 5}
