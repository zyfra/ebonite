from typing import Dict

from ebonite.runtime.interface import Interface


def merge(ifaces: Dict[str, Interface]) -> Interface:
    """
    Helper to produce composite interface from a number of interfaces.
    Exposes all methods of all given interfaces via given prefixes.

    :param ifaces: dict with (prefix, interface) mappings
    :return: composite interface
    """
    return _MergedInterface(ifaces)


class _MergedInterface(Interface):
    def __init__(self, ifaces):
        exposed = {**self.exposed}
        executors = {**self.executors}
        for pre, iface in ifaces.items():
            for meth in iface.exposed_methods():
                pre_meth = '{}-{}'.format(pre, meth)
                exposed[pre_meth] = iface.exposed_method_signature(meth)
                executors[pre_meth] = self._exec_factory(iface, meth)
        self.exposed = exposed
        self.executors = executors

    @staticmethod
    def _exec_factory(iface, method):
        def _exec(**kwargs):
            return iface.execute(method, kwargs)
        return _exec
