import contextlib
import os
import random
import sys
from typing import Type

import pytest

from ebonite.ext.ext_loader import Extension, ExtensionLoader
from ebonite.utils import fs
from ebonite.utils.importing import import_module, module_imported


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


@pytest.fixture
def temp_module_factory():
    modules = []

    def inner(text=''):
        module = 'sys'
        while module_imported(module):
            name = f'temp_module_{random.randint(0, 10 ** 6)}'
            module_path = fs.current_module_path(name) + '.py'
            with open(module_path, 'w') as f:
                f.write(text)
            modules.append(module_path)
            module = f'tests.ext.{name}'
        return module

    try:
        yield inner
    finally:
        for path in modules:
            os.remove(path)


@pytest.fixture
def two_temp_modules(temp_module_factory):
    module1 = temp_module_factory()
    module2 = temp_module_factory()

    assert not module_imported(module1)
    assert not module_imported(module2)
    return module1, module2


def test_extension_loader__force(ext_loader, two_temp_modules):
    module1, module2 = two_temp_modules
    ext_loader.builtin_extensions[module1] = Extension(module1, [module2], force=True)

    ext_loader.load_all()

    assert module_imported(module1)
    assert module_imported(module2)


def test_extension_loader__lazy(ext_loader, two_temp_modules):
    module1, module2 = two_temp_modules

    ext_loader.builtin_extensions[module1] = Extension(module1, [module2], force=False)

    ext_loader.load_all()

    assert not module_imported(module1)
    assert not module_imported(module2)

    import_module(module2)  # noqa

    assert module_imported(module1)
    assert module_imported(module2)


@pytest.mark.kek
def test_extension_loader__lazy_defered(ext_loader, two_temp_modules, temp_module_factory):
    module1, module2 = two_temp_modules

    ext_loader.builtin_extensions[module1] = Extension(module1, [module2], force=False)

    ext_loader.load_all()

    assert not module_imported(module1)
    assert not module_imported(module2)

    module3 = temp_module_factory(f'import {module2}')
    import_module(module3)  # noqa

    assert module_imported(module1)
    assert module_imported(module2)
