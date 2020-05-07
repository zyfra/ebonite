import contextlib
import random
import shutil
import sys
from pathlib import Path
from typing import Type

import pytest

import os
from ebonite.ext.ext_loader import Extension, ExtensionLoader
from ebonite.utils import fs
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


@pytest.fixture
def temp_module_factory():
    modules = []

    def inner():
        name = f'temp_module_{random.randint(0, 10 ** 6)}'
        module_name = name
        module_path = module_name + '.py'
        Path(module_path).touch()
        modules.append(module_path)
        return os.path.join('tests', 'ext', module_name).replace('/', '.')

    try:
        yield inner
    finally:
        for path in modules:
            os.remove(path)


def test_extension_loader__force(ext_loader, temp_module_factory):
    module1 = temp_module_factory()
    module2 = temp_module_factory()

    assert not module_imported(module1)
    assert not module_imported(module2)

    ext_loader.builtin_extensions[module1] = Extension(module1, [module2], force=True)

    ext_loader.load_all()

    assert module_imported(module1)
    assert module_imported(module2)


def test_extension_loader__lazy(ext_loader, temp_module_factory):
    module1 = temp_module_factory()
    module2 = temp_module_factory()
    assert not module_imported(module1)
    assert not module_imported(module2)

    ext_loader.builtin_extensions[module1] = Extension(module1, [module2], force=False)

    ext_loader.load_all()

    assert not module_imported(module1)
    assert not module_imported(module2)

    __import__(module2)  # noqa

    assert module_imported(module1)
    assert module_imported(module2)


def test_extension_loader__lazy_defered(ext_loader, temp_module_factory):
    module1 = temp_module_factory()
    module2 = temp_module_factory()
    assert not module_imported(module1)
    assert not module_imported(module2)

    ext_loader.builtin_extensions[module1] = Extension(module1, [module2], force=False)

    ext_loader.load_all()

    assert not module_imported(module1)
    assert not module_imported(module2)

    module3 = temp_module_factory()
    with open(f'{module3[len("tests.ext."):]}.py', 'w') as f:
        f.write(f'import {module2}')
    __import__(module3)  # noqa

    assert module_imported(module1)
    assert module_imported(module2)
