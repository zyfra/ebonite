import contextlib
import sys
from typing import Type

import pytest

from ebonite.ext.ext_loader import Extension, ExtensionLoader
from ebonite.utils.importing import module_imported


@pytest.fixture
def ext_loader() -> Type[ExtensionLoader]:
    class _MyLoader(ExtensionLoader):
        builtin_extensions = {}

    return _MyLoader


@contextlib.contextmanager
def unload_load(module_name):
    if module_imported(module_name):
        mod = sys.modules.pop(module_name)
        try:
            yield
        finally:
            sys.modules[module_name] = mod
    else:
        try:
            yield
        finally:
            sys.modules.pop(module_name, None)


def test_extension_loader__force(ext_loader):
    with unload_load('stat'), unload_load('pprint'):
        assert not module_imported('stat')
        assert not module_imported('pprint')

        ext_loader.builtin_extensions['stat'] = Extension('stat', ['pprint'], force=True)

        ext_loader.load_all()

        assert module_imported('stat')
        assert module_imported('pprint')


def test_extension_loader__lazy(ext_loader):
    with unload_load('marshal'), unload_load('dbm'):
        assert not module_imported('marshal')
        assert not module_imported('dbm')

        ext_loader.builtin_extensions['marshal'] = Extension('marshal', ['dbm'], force=False)

        ext_loader.load_all()

        assert not module_imported('marshal')
        assert not module_imported('dbm')

        import dbm  # noqa

        assert module_imported('marshal')
        assert module_imported('dbm')
