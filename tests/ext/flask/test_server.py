import json
import os
import tempfile

import pytest
from pyjackson.core import ArgList, Field

from ebonite.core.objects import DatasetType
from ebonite.ext.flask.server import FlaskServer, WrongArgumentsError
from ebonite.runtime import Interface
from ebonite.runtime.interface import ExecutionError, expose


class StrDataset(DatasetType):
    def get_spec(self) -> ArgList:
        return [Field('', str, False)]

    type = 'str_type'

    def deserialize(self, obj: dict) -> object:
        return obj

    def serialize(self, instance: object) -> dict:
        return instance


@pytest.fixture
def client():
    server = FlaskServer()
    app = server._create_app()

    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True

    with app.test_client() as client:
        client.flask_server = server
        yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


def test_health(client):
    assert client.get('/health').data == b'OK'


def test_create_interface_routes(client):
    class MyInterface(Interface):
        @expose
        def method(self, argument: StrDataset()) -> StrDataset():
            return argument + 'a'

    server: FlaskServer = client.flask_server
    server._prepare_app(client.application, MyInterface())

    resp = client.post('/method',
                       data=json.dumps({'argument': 'a' * 5}),
                       content_type='application/json').get_json()
    assert resp == {'ok': True, 'data': 'a' * 6}


def test_errors(client):
    class MyInterface(Interface):
        @expose
        def method(self, argument: StrDataset()) -> StrDataset():
            raise ExecutionError('message')

    server: FlaskServer = client.flask_server
    server._prepare_app(client.application, MyInterface())

    r = client.post('/method',
                    data=json.dumps({'nonexisting': 'a'}),
                    content_type='application/json')
    assert r.status_code == 400
    resp = r.get_json()
    assert resp == {'ok': False, 'error': WrongArgumentsError(['argument'], ['nonexisting']).error()}

    r = client.post('/method',
                    data=json.dumps({'argument': 'a'}),
                    content_type='application/json')
    assert r.status_code == 400
    resp = r.get_json()
    assert resp == {'ok': False, 'error': 'message'}
