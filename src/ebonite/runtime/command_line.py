from ebonite import config
from ebonite.runtime.interface import InterfaceLoader
from ebonite.runtime.server import Server
from ebonite.utils.log import rlogger


def start_runtime(loader=None, server=None):
    """
    Starts Ebonite runtime for given (optional) loader and (optional) server

    :param loader: loader of model to start Ebonite runtime for,
        if not given class specified in :attr:`.config.Runtime.LOADER` is used
    :param server: server to use for Ebonite runtime, default is a flask-based server,
        if not given class specified in :attr:`.config.Runtime.SERVER` is used
    :return: nothing
    """

    if not isinstance(server, Server):
        server = config.Runtime.SERVER
        server = Server.get(server)

    if not isinstance(loader, InterfaceLoader):
        loader = config.Runtime.LOADER
        loader = InterfaceLoader.get(loader)

    rlogger.info(f'Starting Ebonite runtime with loader %s and server %s ...',
                 type(loader).__name__,
                 type(server).__name__)
    server.start(loader)
