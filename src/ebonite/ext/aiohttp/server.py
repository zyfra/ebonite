import uuid

import yaml
from aiohttp import web
from aiohttp_swagger import setup_swagger

from ebonite.runtime.interface import Interface
from ebonite.runtime.interface.base import InterfaceDescriptor
from ebonite.runtime.openapi.spec import create_spec
from ebonite.runtime.server import BaseHTTPServer, HTTPServerConfig, MalformedHTTPRequestException
from ebonite.utils.log import rlogger


def create_executor_function(interface: Interface, method: str, spec: dict):
    """
    Creates a view function for specific interface method

    :param interface: :class:`.Interface` instance
    :param method: method name
    :param spec: openapi spec for this instance
    :return: callable view function
    """

    async def ef(request):
        ebonite_id = str(uuid.uuid4())
        rlogger.debug('Headers for [%s]: %s', request.headers)

        try:
            if request.content_type == 'application/json':
                request_data = BaseHTTPServer._deserialize_json(interface, method, await request.json())
            else:
                request_data = {k: v.file for k, v in dict(await request.post()).items()}

            result = BaseHTTPServer._execute_method(interface, method, request_data, ebonite_id)

            if isinstance(result, bytes):
                return web.Response(body=result, content_type='image/png')
            return web.json_response(result)
        except MalformedHTTPRequestException as e:
            return web.json_response(e.response_body(), status=e.code())

    ef.__doc__ = f"\n---\n{yaml.dump(spec)}\n"

    return ef


def create_interface_routes(app, interface: Interface):
    for method in interface.exposed_methods():
        sig = interface.exposed_method_signature(method)
        rlogger.debug('registering %s with input type %s and output type %s', method, sig.args, sig.output)

        spec = create_spec(method, sig)
        executor_function = create_executor_function(interface, method, spec)
        app.router.add_post('/' + method, executor_function)


def create_schema_route(app, interface: Interface):
    schema = InterfaceDescriptor.from_interface(interface).to_dict()
    rlogger.debug('Creating /interface.json route with schema: %s', schema)
    app.router.add_get('/interface.json', lambda request: web.json_response(schema))


def create_misc_routes(app):
    async def redirect_to_swagger(request):
        raise web.HTTPFound('/apidocs')

    app.router.add_get('/health', lambda request: web.Response(body='OK'))
    app.router.add_get('/', redirect_to_swagger)


class AIOHTTPServer(BaseHTTPServer):
    def __init__(self):
        # we do not reference real aiohttp objects here and this breaks `get_object_requirements`
        import aiohttp_swagger
        self.__requires = aiohttp_swagger
        super().__init__()

    def run(self, interface: Interface):
        app = web.Application()
        create_interface_routes(app, interface)
        create_schema_route(app, interface)
        create_misc_routes(app)
        setup_swagger(app, swagger_url="/apidocs", ui_version=3)

        rlogger.debug('Running aiohttp on %s:%s', HTTPServerConfig.host, HTTPServerConfig.port)
        web.run_app(app, host=HTTPServerConfig.host, port=HTTPServerConfig.port)
