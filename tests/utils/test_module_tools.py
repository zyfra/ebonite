from ebonite.utils.importing import import_module
from ebonite.utils.module import (get_module_repr, get_module_version, get_object_module, is_builtin_module,
                                  is_extension_module, is_installable_module, is_local_module, is_private_module,
                                  is_pseudo_module)


class Obj:
    pass


def test_module_representation():
    from setup import setup_args
    for module in setup_args['install_requires']:
        mod_name = module.split('==')[0]
        try:
            mod = import_module(mod_name)
            assert module == get_module_repr(mod)
        except (ImportError, NameError):
            continue


def test_is_installed_module():
    import pickle
    import builtins
    import requests
    import opcode
    assert not is_installable_module(pickle)
    assert not is_installable_module(builtins)
    assert not is_installable_module(opcode)
    assert is_installable_module(requests), requests.__file__

    ebnt_module = get_object_module(get_object_module)
    assert not is_installable_module(ebnt_module)


def test_is_builtin_module():
    import pickle
    import builtins
    import requests
    import opcode
    assert is_builtin_module(pickle)
    assert is_builtin_module(builtins)
    assert is_builtin_module(opcode)
    assert not is_builtin_module(requests), requests.__file__

    ebnt_module = get_object_module(get_object_module)
    assert not is_builtin_module(ebnt_module)


def test_is_private_module():
    import pickle as p
    import _datetime as d

    assert not is_private_module(p)
    assert is_private_module(d)


def test_is_pseudo_module():
    import pickle
    import __future__

    assert not is_pseudo_module(pickle)
    assert is_pseudo_module(__future__)


def test_is_extension_module():
    import pickle
    import _datetime
    import _ctypes

    assert not is_extension_module(pickle)
    assert is_extension_module(_datetime)
    assert is_extension_module(_ctypes)


def test_is_local_module():
    import pickle
    import requests
    import sys

    assert not is_local_module(sys)
    assert not is_local_module(pickle)
    assert not is_local_module(requests)
    assert is_local_module(sys.modules[__name__])


def test_module_version():
    # we do not check for concrete version as they could differ
    assert get_module_version(import_module('numpy')) is not None
    assert get_module_version(import_module('dill')) is not None
    # responses doesn't have __version__ attr, thus heuristics should be applied here
    assert get_module_version(import_module('responses')) is not None
