from abc import abstractmethod
from typing import Dict, List

from pyjackson import deserialize
from pyjackson.errors import DeserializationError, SerializationError

from ebonite.config import Config, Core, Param
from ebonite.runtime.interface import ExecutionError, Interface, InterfaceLoader
from ebonite.runtime.utils import registering_type
from ebonite.utils.log import rlogger

_ServerBase = registering_type('server')


class Server(_ServerBase):
    """
    Base class for Ebonite servers
    """
    additional_sources: List[str] = []
    additional_binaries: List[str] = []
    additional_envs: Dict[str, str] = {}
    additional_options: Dict[str, str] = {}

    @staticmethod
    def get(class_path) -> 'Server':
        """
        Gets a fresh instance of given server implementation

        :param class_path: full name of server implementation
        :return: server object
        """

        # importing.import_module(class_path)
        return _ServerBase.get(class_path)()

    @abstractmethod
    def run(self, executor: Interface):
        """
        Main server method which "executes" given interface. Should be implemented by subclasses.

        :param executor: interface to "execute"
        :return: nothing
        """

        pass  # pragma: no cover

    def start(self, loader: InterfaceLoader):
        """
        Starts server "execution" for given loader: loads an interface and "executes" it

        :param loader: loader to take interface from
        :return: nothing
        """

        interface = loader.load()
        rlogger.info('Running server %s', self)
        return self.run(interface)


class HTTPServerConfig(Config):
    host = Param('host', default='0.0.0.0', parser=str)
    port = Param('port', default='9000', parser=int)


if Core.DEBUG:
    HTTPServerConfig.log_params()


class MalformedHTTPRequestException(Exception):
    def __init__(self, message: str):
        self._message = message

    def code(self):
        return 400

    def response_body(self):
        return {'ok': False, 'error': self._message}


class BaseHTTPServer(Server):
    """
    HTTP-based Ebonite runtime server.

    Interface definition is exposed for clients via HTTP GET call to `/interface.json`,
    method calls - via HTTP POST calls to `/<name>`,
    server health check - via HTTP GET call to `/health`.

    Host to which server binds is configured via `EBONITE_HOST` environment variable:
    default is `0.0.0.0` which means any local or remote, for rejecting remote connections use `localhost` instead.

    Port to which server binds to is configured via `EBONITE_PORT` environment variable: default is 9000.
    """

    @staticmethod
    def _deserialize_json(interface: Interface, method: str, request_json: dict):
        args = {a.name: a for a in interface.exposed_method_args(method)}
        try:
            return {k: deserialize(v, args[k].type) for k, v in request_json.items()}
        except KeyError:
            raise MalformedHTTPRequestException(
                f'Invalid request: arguments are {set(args.keys())}, got {set(request_json.keys())}')
        except DeserializationError as e:
            raise MalformedHTTPRequestException(e.args[0])

    @staticmethod
    def _execute_method(interface: Interface, method: str, request_data, ebonite_id: str):
        rlogger.debug('Got request for [%s]: %s', ebonite_id, request_data)

        try:
            result = interface.execute(method, request_data)
        except (ExecutionError, SerializationError) as e:
            raise MalformedHTTPRequestException(e.args[0])

        if isinstance(result, bytes):
            rlogger.debug('Got response for [%s]: <binary content>', ebonite_id)
            return result

        rlogger.debug('Got response for [%s]: %s', result)
        return {'ok': True, 'data': result}
