import requests

from ebonite.runtime.client.base import BaseClient
from ebonite.runtime.interface.base import InterfaceDescriptor


class HTTPClient(BaseClient):
    """
    Simple implementation of HTTP-based Ebonite runtime client.

    Interface definition is acquired via HTTP GET call to `/interface.json`,
    method calls are performed via HTTP POST calls to `/<name>`.

    :param host: host of server to connect to, if no host given connects to host `localhost`
    :param port: port of server to connect to, if no port given connects to port 9000
    """
    def __init__(self, host=None, port=None):
        self.base_url = f'http://{host or "localhost"}:{port or 9000}'
        super().__init__()

    def _interface_factory(self) -> InterfaceDescriptor:
        resp = requests.get(f'{self.base_url}/interface.json')
        resp.raise_for_status()
        return InterfaceDescriptor.from_dict(resp.json())

    def _call_method(self, name, args):
        ret = requests.post(f'{self.base_url}/{name}', json=args)
        ret.raise_for_status()
        return ret.json()['data']
