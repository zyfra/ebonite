from typing import Dict

from ebonite.runtime.interface import Interface


def merge(ifaces: Dict[str, Interface]) -> Interface:
    """
    Helper to produce composite interface from a number of interfaces.
    Exposes all methods of all given interfaces via given prefixes.

    :param ifaces: dict with (prefix, interface) mappings
    :return: composite interface
    """
    class MergedInterface(Interface):
        for name, iface in ifaces.items():
            for exposed in iface.exposed_methods():
                locals()['{}-{}'.format(name, exposed)] = getattr(iface, exposed)

    return MergedInterface()
