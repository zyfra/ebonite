from abc import abstractmethod

from ebonite.runtime.interface import Interface, InterfaceLoader
from ebonite.runtime.utils import registering_type
from ebonite.utils.log import rlogger

_ServerBase = registering_type('server')


class Server(_ServerBase):
    """
    Base class for Ebonite servers
    """

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

        pass

    def start(self, loader: InterfaceLoader):
        """
        Starts server "execution" for given loader: loads an interface and "executes" it

        :param loader: loader to take interface from
        :return: nothing
        """

        interface = loader.load()
        rlogger.info('Running server %s', self)
        return self.run(interface)
