import pytest

from ebonite.utils.importing import import_module
from ebonite.utils.module import (analyze_module_imports, check_pypi_module, get_module_repr, get_module_version,
                                  get_object_module, is_builtin_module, is_ebonite_module, is_extension_module,
                                  is_installable_module, is_local_module, is_private_module, is_pseudo_module)


class Obj:
    pass


def test_analyze_module_imports():
    reqs = analyze_module_imports('tests.utils.test_module_tools')
    assert reqs == {get_module_repr(pytest)}


def test_check_pypi_module():
    assert check_pypi_module('numpy', '1.17.3')
    assert check_pypi_module('pandas')

    assert not check_pypi_module('my-super-module', warn_on_error=False)
    assert not check_pypi_module('pandas', '100.200.300', warn_on_error=False)

    with pytest.raises(ValueError):
        check_pypi_module('my-super-module', raise_on_error=True)

    with pytest.raises(ImportError):
        check_pypi_module('pandas', '100.200.300', raise_on_error=True)


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
    assert not is_local_module(sys.modules['__future__'])
    assert not is_local_module(sys.modules[is_local_module.__module__])


def test_is_ebonite_module():
    import sys
    import requests
    import ebonite
    from ebonite.utils import module

    assert is_ebonite_module(ebonite)
    assert is_ebonite_module(module)

    assert not is_ebonite_module(sys)
    assert not is_ebonite_module(requests)


def test_module_version():
    # we do not check for concrete version as they could differ
    assert get_module_version(import_module('numpy')) is not None
    assert get_module_version(import_module('dill')) is not None
    # responses doesn't have __version__ attr, thus heuristics should be applied here
    assert get_module_version(import_module('responses')) is not None
