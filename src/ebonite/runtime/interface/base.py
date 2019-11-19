from abc import abstractmethod
from typing import Dict, List

from pyjackson import deserialize, serialize
from pyjackson.core import Comparable, Field, Signature
from pyjackson.utils import get_function_signature

from ebonite.core import objects
from ebonite.runtime.utils import registering_type


def expose(class_method):
    """
    Decorator which exposes given method into interface

    :param class_method: method to expose
    :return: given method with modifications
    """

    class_method.is_exposed = True
    return class_method


class ExecutionError(Exception):
    """
    Exception which is raised when interface method is executed with arguments incompatible to its signature
    """

    pass


class InterfaceMetaclass(type):
    """
    Metaclass for :class:`Interface` which keeps track of exposed methods
    """

    def __new__(cls, *args, **kwargs):
        newcls = super().__new__(cls, *args, **kwargs)
        newcls.exposed = dict()
        for name, attr in newcls.__dict__.items():
            if hasattr(attr, 'is_exposed') and getattr(attr, 'is_exposed'):
                newcls.exposed[name] = get_function_signature(attr)
        return newcls


class Interface(metaclass=InterfaceMetaclass):
    """
    Collection of executable methods with explicitly defined signatures
    """

    exposed: Dict[str, Signature] = {}

    def execute(self, method: str, args: Dict[str, object]):
        """
        Executes given method with given arguments

        :param method: method name to execute
        :param args: arguments to pass into method
        :return: method result
        """

        self._validate_args(method, args)
        f = getattr(self, method)
        return f(**args)

    def _validate_args(self, method: str, args: Dict[str, object]):
        needed_args = self.exposed_method_args(method)
        missing_args = [arg.name for arg in needed_args if arg.name not in args]
        if len(missing_args) > 0:
            raise ExecutionError('{} method {} missing args {}'.format(self, method, ', '.join(missing_args)))

    def exposed_methods(self):
        """
        Lists signatures of methods exposed by interface

        :return: list of signatures
        """

        return list(self.exposed.keys())

    def exposed_method_signature(self, method_name: str) -> Signature:
        """
        Gets signature of given method

        :param method_name: name of method to get signature for
        :return: signature
        """

        if method_name not in self.exposed:
            raise ExecutionError('Interface {} does not have method "{}"'.format(self, method_name))

        return self.exposed[method_name]

    def exposed_method_args(self, method_name: str) -> List[Field]:
        """
        Gets argument types of given method

        :param method_name: name of method to get argument types for
        :return: list of argument types
        """
        return self.exposed_method_signature(method_name).args

    def exposed_method_returns(self, method_name: str) -> Field:
        """
        Gets return type of given method

        :param method_name: name of method to get return type for
        :return: return type
        """

        return self.exposed_method_signature(method_name).output


class InterfaceMethodDescriptor(Comparable):
    """
    Descriptor of interface method: contains metadata only and couldn't execute method calls
    """

    # TODO support for types other then DatasetType, for example builtins
    def __init__(self, name: str, args: Dict[str, 'objects.DatasetType'], out_type: 'objects.DatasetType'):
        self.name = name
        self.args = args
        self.out_type = out_type

    @staticmethod
    def from_signature(name: str, signature: Signature):
        return InterfaceMethodDescriptor(name, {a.name: a.type for a in signature.args},
                                         signature.output.type)


# class _InterfaceMethodDescriptorSerializer(StaticSerializer):
#     real_type = InterfaceMethodDescriptor
#     @classmethod
#     def deserialize(cls, obj: dict) -> InterfaceMethodDescriptor:
#         return InterfaceMethodDescriptor(obj['name'],
#                                          {a['name']: deserialize(a['type'], DatasetType)for a in obj['args']},
#                                          deserialize(obj['out_type'], DatasetType))
#
#     @classmethod
#     def serialize(cls, instance: InterfaceMethodDescriptor) -> dict:


class InterfaceDescriptor(Comparable):
    """
    Descriptor of :class:`Interface`: contains metadata only and couldn't execute method calls
    """

    def __init__(self, methods: List[InterfaceMethodDescriptor], version: str):
        self.methods = methods
        self.version = version

    def to_dict(self):
        return serialize(self)

    @classmethod
    def from_dict(cls, d: dict):
        return deserialize(d, cls)

    @staticmethod
    def from_interface(interface: Interface):
        import ebonite
        return InterfaceDescriptor(
            [InterfaceMethodDescriptor.from_signature(name, interface.exposed_method_signature(name))
             for name in interface.exposed_methods()], ebonite.__version__)


_InterfaceLoaderBase = registering_type('loader')


class InterfaceLoader(_InterfaceLoaderBase):
    """
    Base class for loaders of :class:`Interface`
    """

    @abstractmethod
    def load(self) -> Interface:
        pass

    @staticmethod
    def get(class_path) -> 'InterfaceLoader':
        return _InterfaceLoaderBase.get(class_path)()
