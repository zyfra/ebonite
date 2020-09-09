import itertools
import uuid
from io import BytesIO

from ebonite.config import Config, Core, Param
from ebonite.runtime.interface import Interface
from ebonite.runtime.interface.base import InterfaceDescriptor
from ebonite.runtime.openapi.spec import create_spec
from ebonite.runtime.server import BaseHTTPServer, HTTPServerConfig, MalformedHTTPRequestException
from ebonite.utils.fs import current_module_path
from ebonite.utils.log import rlogger

current_app = None


def create_executor_function(interface: Interface, method: str):
    """
    Creates a view function for specific interface method

    :param interface: :class:`.Interface` instance
    :param method: method name
    :return: callable view function
    """
    from flask import g, jsonify, request, send_file

    def ef():
        try:
            if request.content_type == 'application/json':
                request_data = BaseHTTPServer._deserialize_json(interface, method, request.json)
            else:
                request_data = dict(itertools.chain(request.form.items(), request.files.items()))

            result = BaseHTTPServer._execute_method(interface, method, request_data, g.ebonite_id)

            if isinstance(result, bytes):
                return send_file(BytesIO(result), mimetype='image/png')
            return jsonify(result)
        except MalformedHTTPRequestException as e:
            return jsonify(e.response_body()), e.code()

    ef.__name__ = method

    return ef


def _register_method(app, interface, method_name, signature):
    from flasgger import swag_from

    swag = swag_from(create_spec(method_name, signature, str(Interface), interface.exposed_method_docs(method_name)))
    executor_function = swag(create_executor_function(interface, method_name))
    app.add_url_rule('/' + method_name, method_name, executor_function, methods=['POST'])


def create_interface_routes(app, interface: Interface):
    for method in interface.exposed_methods():
        sig = interface.exposed_method_signature(method)
        rlogger.debug('registering %s with input type %s and output type %s', method, sig.args, sig.output)
        _register_method(app, interface, method, sig)


def create_schema_route(app, interface: Interface):
    from flask import jsonify

    schema = InterfaceDescriptor.from_interface(interface).to_dict()
    rlogger.debug('Creating /interface.json route with schema: %s', schema)
    app.add_url_rule('/interface.json', 'schema', lambda: jsonify(schema))


class FlaskConfig(Config):
    run_flask = Param('run_flask', default='true', parser=bool)


if Core.DEBUG:
    FlaskConfig.log_params()

PREBUILD_PATH = current_module_path('prebuild')
BASE_IMAGE_TEMPLATE = 'zyfraai/flask:{}'


def prebuild_hook(python_version):
    from ebonite.ext.docker.prebuild import prebuild_image
    prebuild_image(PREBUILD_PATH, BASE_IMAGE_TEMPLATE, python_version)


class FlaskServer(BaseHTTPServer):
    """
    Flask- and Flasgger-based :class:`.BaseHTTPServer` implementation
    """

    additional_sources = [
        current_module_path('build', 'app.py')  # replace stub in base image
    ]

    additional_options = {'docker': {
        'templates_dir': current_module_path('build'),
        'base_image': lambda python_version: BASE_IMAGE_TEMPLATE.format(python_version),
        'run_cmd': False,  # base image has already specified command
        'prebuild_hook': prebuild_hook
    }}

    def _create_app(self):
        from flasgger import Swagger
        from flask import Flask, g, redirect, request

        app = Flask(__name__)
        app.config['SWAGGER'] = {
            'uiversion': 3,
            'openapi': '3.0.2'
        }
        Swagger(app)

        @app.route('/health')
        def health():
            return 'OK'

        @app.route('/')
        def root():
            return redirect('/apidocs')

        @app.before_request
        def log_request_info():
            g.ebonite_id = str(uuid.uuid4())
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
        global current_app
        app = self._create_app()
        self._prepare_app(app, interface)

        current_app = app
        if FlaskConfig.run_flask:
            rlogger.debug('Running flask on %s:%s', HTTPServerConfig.host, HTTPServerConfig.port)
            app.run(HTTPServerConfig.host, HTTPServerConfig.port)
        else:
            rlogger.debug('Skipping direct flask application run')


def main():
    from ebonite.ext.docker.prebuild import prebuild_missing_images
    prebuild_missing_images(PREBUILD_PATH, BASE_IMAGE_TEMPLATE)


if __name__ == '__main__':
    main()
