import itertools
import uuid

import flask
from flasgger import Swagger, swag_from, validate
from flask import jsonify, request, send_file
from pyjackson import deserialize

from ebonite.config import Config, Param
from ebonite.runtime.interface import ExecutionError, Interface
from ebonite.runtime.interface.base import InterfaceDescriptor
from ebonite.runtime.openapi.spec import create_spec
from ebonite.runtime.server import Server
from ebonite.utils.log import rlogger

VALIDATE = False


class FlaskServerError(Exception):
    def code(self):
        return 400

    def error(self):
        return self.args[0]

    def to_response(self):
        return jsonify({'ok': False, 'error': self.error()}), self.code()


class WrongArgumentsError(FlaskServerError):
    def __init__(self, expected, actual):
        self.expected = expected
        self.actual = actual

    def error(self):
        return 'Invalid request: arguments are [{}], got [{}]'.format(', '.join(self.actual), ', '.join(self.expected))


def _extract_request_data(method_args):
    """

    :param method_args:
    :return:
    """
    args = {a.name: a for a in method_args}
    if request.content_type == 'application/json':
        request_data = request.json
        try:
            request_data = {k: deserialize(v, args[k].type) for k, v in request_data.items()}
        except KeyError:
            raise WrongArgumentsError(args.keys(), request_data.keys())
    else:
        request_data = dict(itertools.chain(request.form.items(), request.files.items()))
    rlogger.debug('Got request[%s] with data %s', flask.g.ebonite_id, request_data)
    return request_data


def create_executor_function(interface: Interface, method: str, spec: dict):
    """
    Creates a view function for specific interface method

    :param interface: :class:`.Interface` instance
    :param method: method name
    :param spec: openapi spec for this instance
    :return: callable view function
    """

    def ef():
        data = _extract_request_data(interface.exposed_method_args(method))
        try:
            result = interface.execute(method, data)
            if hasattr(result, 'read'):
                rlogger.debug('Got response for [%s]: <binary content>', flask.g.ebonite_id)
                return send_file(result, attachment_filename=getattr(result, 'name', None))
            response = {'ok': True, 'data': result}
            rlogger.debug('Got response for [%s]: %s', flask.g.ebonite_id, response)
            if VALIDATE:
                validate(response, specs=spec, definition='response_{}'.format(method))
            return jsonify(response)
        except ExecutionError as e:
            raise FlaskServerError(*e.args)

    ef.__name__ = method
    return ef


def _register_method(app, interface, method_name, signature):
    spec = create_spec(method_name, signature)

    executor_function = create_executor_function(interface, method_name, spec)
    swag = swag_from(spec, validation=VALIDATE)
    executor_function = swag(executor_function)

    app.add_url_rule('/' + method_name, method_name, executor_function, methods=['POST'])


def create_interface_routes(app, interface: Interface):
    for method in interface.exposed_methods():
        sig = interface.exposed_method_signature(method)
        rlogger.debug('registering %s with input type %s and output type %s', method, sig.args, sig.output)
        _register_method(app, interface, method, sig)


def create_schema_route(app, interface: Interface):
    schema = InterfaceDescriptor.from_interface(interface).to_dict()
    rlogger.debug('Creating /interface.json route with schema: %s', schema)
    app.add_url_rule('/interface.json', 'schema', lambda: jsonify(schema))


class FlaskConfig(Config):
    host = Param('host', default='0.0.0.0', parser=str)
    port = Param('port', default='9000', parser=int)


class FlaskServer(Server):
    """
    HTTP-based Ebonite runtime server.

    Interface definition is exposed for clients via HTTP GET call to `/interface.json`,
    method calls - via HTTP POST calls to `/<name>`,
    server health check - via HTTP GET call to `/health`.

    Host to which server binds is configured via `EBONITE_HOST` environment variable:
    default is `0.0.0.0` which means any local or remote, for rejecting remote connections use `localhost` instead.

    Port to which server binds to is configured via `EBONITE_PORT` environment variable: default is 9000.
    """

    def __init__(self):
        # we do not reference real Flask/Flasgger objects here and this breaks `get_object_requirements`
        self.__requires = Swagger
        super().__init__()

    def _create_app(self):
        app = flask.Flask(__name__)
        Swagger(app)

        @app.errorhandler(FlaskServerError)
        def handle_bad_request(e: FlaskServerError):
            return e.to_response()

        @app.route('/health')
        def health():
            return 'OK'

        @app.before_request
        def log_request_info():
            flask.g.ebonite_id = str(uuid.uuid4())
            app.logger.debug('Headers: %s', request.headers)
            app.logger.debug('Body: %s', request.get_data())

        return app

    def _prepare_app(self, app, interface):
        create_interface_routes(app, interface)
        create_schema_route(app, interface)

    def run(self, interface: Interface):
        """
        Starts flask service

        :param interface: runtime interface to expose via HTTP
        """
        app = self._create_app()
        self._prepare_app(app, interface)
        app.run(FlaskConfig.host, FlaskConfig.port)
