from abc import abstractmethod
from collections import namedtuple
from warnings import warn

from pyjackson import deserialize, serialize

import ebonite
from ebonite.runtime.interface.base import InterfaceDescriptor, InterfaceMethodDescriptor
from ebonite.utils.log import logger


class BaseClient:
    """
    Base class for clients of Ebonite runtime.

    User method calls are transparently proxied to :class:`ebonite.runtime.interface.base.Interface` deployed on
    :class:`ebonite.runtime.server.base.Server`.
    PyJackson is always used for serialization of inputs and deserialization of outputs.
    """

    def __init__(self):
        self.methods = {}

        iface: InterfaceDescriptor = self._interface_factory()

        if ebonite.__version__ != iface.version:
            warn(f"Server Ebonite version {iface.version}, client Ebonite version {ebonite.__version__}")

        for method in iface.methods:
            self.methods[method.name] = _bootstrap_method(method)

    @abstractmethod
    def _interface_factory(self) -> InterfaceDescriptor:
        """
        Takes interface deployed on server to validate method calls at client side and
        correctly (de)serialize inputs/outputs via PyJackson

        :return: :class:`InterfaceDescriptor` describing supported methods
        """

        pass

    @abstractmethod
    def _call_method(self, name, args):
        """
        Performs method call at server side

        :param name: name of method to call
        :param args: `dict` of (name, value) mappings for arguments. Values are PyJackson-serialized objects.
        :return: method return value which should be PyJackson deserializable.
        """

        pass

    def __getattr__(self, name):
        if name not in self.methods:
            raise KeyError(f'{name} method is not exposed by server')
        return _MethodCall(self.base_url, self.methods[name], self._call_method)


_Argument = namedtuple('Argument', ('name', 'type'))
_Method = namedtuple('Method', ('name', 'args', 'out_type'))


class _MethodCall:
    def __init__(self, base_url, method: _Method, call_method):
        self.base_url = base_url
        self.method = method
        self.call_method = call_method

    def __call__(self, *args, **kwargs):
        if args and kwargs:
            raise ValueError('Parameters should be passed either in positional or in keyword fashion, not both')
        if len(args) > len(self.method.args) or len(kwargs) > len(self.method.args):
            raise ValueError(f'Too much parameters given, expected: {len(self.method.args)}')

        data = {}
        for i, arg in enumerate(self.method.args):
            obj = None
            if len(args) > i:
                obj = args[i]
            if arg.name in kwargs:
                obj = kwargs[arg.name]
            if obj is None:
                raise ValueError(f'Parameter with name "{arg.name}" (position {i}) should be passed')

            data[arg.name] = serialize(obj, arg.type)

        logger.debug('Calling server method "%s", args: %s ...', self.method.name, data)
        out = self.call_method(self.method.name, data)
        logger.debug('Server call returned %s', out)
        return deserialize(out, self.method.out_type)


def _bootstrap_method(method: InterfaceMethodDescriptor):
    logger.debug(f'Bootstraping server method "%s" with %s argument(s)...', method.name, len(method.args))
    args = []
    for arg_name, arg_type in method.args.items():
        args.append(_Argument(arg_name, arg_type))

    return _Method(method.name, args, method.out_type)
