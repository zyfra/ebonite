import inspect
import io
import os
import re
import sys
import threading
import warnings
from collections import namedtuple
from functools import wraps
from pickle import PicklingError
from types import FunctionType, LambdaType, MethodType, ModuleType
from typing import Mapping, MutableSequence

import requests
from isort.finders import FindersManager
from isort.settings import default

from ebonite.core.objects.requirements import (MODULE_PACKAGE_MAPPING, CustomRequirement, InstallableRequirement,
                                               Requirements)
from ebonite.utils import importing
from ebonite.utils.log import logger
from ebonite.utils.pickling import EbonitePickler

PYTHON_BASE = os.path.dirname(threading.__file__)


def analyze_module_imports(module_path):
    module = importing.import_module(module_path)
    requirements = set()
    for name, obj in module.__dict__.items():
        if isinstance(obj, ModuleType):
            mod = obj
        else:
            mod = get_object_base_module(obj)
        requirements.add(get_module_repr(mod))

    return requirements


def check_pypi_module(module_name, module_version=None, raise_on_error=False, warn_on_error=True):
    """
    Checks that module with given name and (optionally) version exists in PyPi repository.

    :param module_name: name of module to look for in PyPi
    :param module_version: (optional) version of module to look for in PyPi
    :param raise_on_error: raise `ValueError` if module is not found in PyPi instead of returning `False`
    :param warn_on_error: print a warning if module is not found in PyPi
    :return: `True` if module found in PyPi, `False` otherwise
    """
    r = requests.get('https://pypi.org/pypi/{}/json'.format(module_name))
    if r.status_code != 200:
        msg = 'Cant find package {} in PyPi'.format(module_name)
        if raise_on_error:
            raise ValueError(msg)
        elif warn_on_error:
            warnings.warn(msg)
        return False
    if module_version is not None and module_version not in r.json()['releases']:
        msg = 'Cant find package version {}=={} in PyPi'.format(module_name, module_version)
        if raise_on_error:
            raise ImportError(msg)
        elif warn_on_error:
            warnings.warn(msg)
        return False
    return True


def get_object_base_module(obj: object) -> ModuleType:
    """
    Determines base module of module given object comes from.

    >>> import numpy
    >>> get_object_base_module(numpy.random.Generator)
    <module 'numpy' from '...'>

    Essentially this function is a combination of :func:`get_object_module` and :func:`get_base_module`.

    :param obj: object to determine base module for
    :return: Python module object for base module
    """
    mod = inspect.getmodule(obj)
    return get_base_module(mod)


def get_base_module(mod: ModuleType):
    """
    Determines base module for given module.

    >>> import numpy
    >>> get_base_module(numpy.random)
    <module 'numpy' from '...'>

    :param mod: Python module object to determine base module for
    :return: Python module object for base module
    """
    if mod is None:
        mod = inspect.getmodule(type(mod))
    if mod is None:
        return None
    base, _sep, _stem = mod.__name__.partition('.')
    return sys.modules[base]


def get_object_module(obj: object) -> ModuleType:
    '''
    Determines module given object comes from

    >>> import numpy
    >>> get_object_module(numpy.ndarray)
    <module 'numpy' from '...'>

    :param obj: obj to determine module it comes from
    :return: Python module object for object module
    '''
    return inspect.getmodule(obj)


def _create_section(section):
    def is_section(cls: 'ISortModuleFinder', module: str):
        cls.init()
        if module in cls.instance.module2section:
            mod_section = cls.instance.module2section[module]
        else:
            mod_section = cls.instance.finder.find(module)
            cls.instance.module2section[module] = mod_section
        return mod_section == section

    return is_section


class ISortModuleFinder:
    """
    Determines type of module: standard library (:meth:`ISortModuleFinder.is_stdlib`) or
    third party (:meth:`ISortModuleFinder.is_thirdparty`).
    This class uses `isort` library heuristics with some modifications.
    """
    instance: 'ISortModuleFinder' = None

    def __init__(self):
        config = default.copy()
        config['known_first_party'].append('ebonite')
        config['known_standard_library'].extend(
            ['opcode', 'nturl2path',  # pytest requirements missed by isort
             'pkg_resources',  # EBNT-112: workaround for imports from setup.py (see docker_builder.py)
             'posixpath',
             'pydevconsole', 'pydevd_tracing', 'pydev_ipython.matplotlibtools', 'pydev_console.protocol',
             'pydevd_file_utils', 'pydevd_plugins.extensions.types.pydevd_plugins_django_form_str', 'pydev_console',
             'pydev_ipython', 'pydevd_plugins.extensions.types.pydevd_plugin_numpy_types',
             'pydevd_plugins.extensions.types.pydevd_helpers', 'pydevd_plugins', 'pydevd_plugins.extensions.types',
             'pydevd_plugins.extensions', 'pydev_ipython.inputhook'])  # "built-in" pydev (and pycharm) modules
        section_names = config['sections']
        sections = namedtuple('Sections', section_names)(*[name for name in section_names])
        self.finder = FindersManager(config, sections)
        self.module2section = {}

    @classmethod
    def init(cls):
        if cls.instance is None:
            cls.instance = cls()

    is_stdlib = classmethod(_create_section('STDLIB'))
    is_thirdparty = classmethod(_create_section('THIRDPARTY'))


def is_private_module(mod: ModuleType):
    '''
    Determines that given module object represents private module.

    :param mod: module object to use
    :return: boolean flag
    '''
    return mod.__name__.startswith('_')


def is_pseudo_module(mod: ModuleType):
    '''
    Determines that given module object represents pseudo (aka Python "magic") module.

    :param mod: module object to use
    :return: boolean flag
    '''
    return mod.__name__.startswith('__') and mod.__name__.endswith('__')


def is_extension_module(mod: ModuleType):
    '''
    Determines that given module object represents native code extension module.

    :param mod: module object to use
    :return: boolean flag
    '''
    try:
        path = mod.__file__
        return any(path.endswith(ext) for ext in {'.so', '.pyd'})
    except AttributeError:
        return True


def is_installable_module(mod: ModuleType):
    '''
    Determines that given module object represents PyPi-installable (aka third party) module.

    :param mod: module object to use
    :return: boolean flag
    '''
    return ISortModuleFinder.is_thirdparty(mod.__name__)
    # return hasattr(mod, '__file__') and mod.__file__.startswith(PYTHON_BASE) and 'site-packages' in mod.__file__


def is_builtin_module(mod: ModuleType):
    '''
    Determines that given module object represents standard library (aka builtin) module.

    :param mod: module object to use
    :return: boolean flag
    '''
    return ISortModuleFinder.is_stdlib(mod.__name__)
    # if mod.__name__ == 'builtins':
    #     return True
    # return not hasattr(mod, '__file__') or (
    #         mod.__file__.startswith(PYTHON_BASE) and 'site-packages' not in mod.__file__)


def is_local_module(mod: ModuleType):
    '''
    Determines that given module object represents local module.
    Local module is a module (Python file) which is not from standard library and not installed via pip.

    :param mod: module object to use
    :return: boolean flag
    '''
    return not is_builtin_module(mod) and not is_installable_module(mod) and not is_extension_module(mod)


def is_from_installable_module(obj: object):
    '''
    Determines that given object comes from PyPi-installable (aka third party) module.

    :param mod: module object to use
    :return: boolean flag
    '''
    return is_installable_module(get_object_base_module(obj))


def get_module_version(mod: ModuleType):
    '''
    Determines version of given module object.

    :param mod: module object to use
    :return: version as `str` or `None` if version could not be determined
    '''
    try:
        return mod.__version__
    except AttributeError:
        for name in os.listdir(os.path.dirname(mod.__file__)):
            m = re.match(re.escape(mod.__name__) + '-(.+)\\.dist-info', name)
            if m:
                return m.group(1)
        return None


def get_package_name(mod: ModuleType) -> str:
    '''
    Determines PyPi package name for given module object

    :param mod: module object to use
    :return: name as `str`
    '''
    if mod is None:
        raise ValueError('mod must not be None')
    name = mod.__name__
    return MODULE_PACKAGE_MAPPING.get(name, name)


def get_module_repr(mod: ModuleType, validate_pypi=False) -> str:
    '''
    Builds PyPi `requirements.txt`-compatible representation of given module object

    :param mod: module object to use
    :param validate_pypi: if `True` (default is `False`) perform representation validation in PyPi repository
    :return: representation as `str`
    '''
    if mod is None:
        raise ValueError('mod must not be None')
    mod_name = get_package_name(mod)
    mod_version = get_module_version(mod)
    rpr = '{}=={}'.format(mod_name, mod_version)
    if validate_pypi:
        check_pypi_module(mod_name, mod_version, raise_on_error=True)
    return rpr


def get_module_as_requirement(mod: ModuleType, validate_pypi=False) -> InstallableRequirement:
    '''
    Builds Ebonite representation of given module object

    :param mod: module object to use
    :param validate_pypi: if `True` (default is `False`) perform representation validation in PyPi repository
    :return: representation as :class:`.InstallableRequirement`
    '''
    mod_version = get_module_version(mod)
    if validate_pypi:
        mod_name = get_package_name(mod)
        check_pypi_module(mod_name, mod_version, raise_on_error=True)
    return InstallableRequirement(mod.__name__, mod_version)


def get_object_requirements_old(obj) -> Requirements:
    if isinstance(obj, MutableSequence):
        return sum(get_object_requirements_old(o) for o in obj)
    if isinstance(obj, Mapping):
        return sum(get_object_requirements_old(o) for o in obj.keys()) + \
               sum(get_object_requirements_old(o) for o in obj.values())
    mod = get_object_base_module(obj)

    if mod is None:
        raise ValueError('Cant determine object module')
    elif mod.__name__ == 'builtins':
        return Requirements()
    if not is_installable_module(mod):
        return Requirements([CustomRequirement(mod.__name__)])
    else:
        return Requirements([get_module_as_requirement(mod)])


def add_closure_inspection(f):
    @wraps(f)
    def wrapper(pickler: '_EboniteRequirementAnalyzer', obj):
        closure = inspect.getclosurevars(obj)
        for field in ['nonlocals', 'globals']:
            for o in getattr(closure, field).values():
                if isinstance(o, ModuleType):
                    pickler._add_requirement(o)
                else:
                    pickler.save(o)
        return f(pickler, obj)

    return wrapper


class _EboniteRequirementAnalyzer(EbonitePickler):
    ignoring = (
        'dill',
        'ebonite'
    )
    dispatch = EbonitePickler.dispatch.copy()

    add_closure_for = [FunctionType, MethodType, staticmethod, classmethod, LambdaType]
    dispatch.update({
        t: add_closure_inspection(EbonitePickler.dispatch[t]) for t in add_closure_for
    })

    def __init__(self, *args, **kwargs):
        super().__init__(io.BytesIO(), *args, **kwargs)  # TODO maybe patch memo and other stuff too
        self.framer.write = self.skip_write
        self.write = self.skip_write
        self.memoize = self.skip_write
        self.seen = set()
        self._modules = set()

    @property
    def custom_modules(self):
        return set(m for m in self._modules if not is_installable_module(m))

    def to_requirements(self):
        r = Requirements()

        for mod in sys.modules.values():
            if not self._should_ignore(mod) and is_local_module(mod):
                r.add(CustomRequirement.from_module(mod))

                # add imports of this local module
                for obj in mod.__dict__.values():
                    self._add_requirement(obj)

        for mod in self._modules:
            r.add(get_module_as_requirement(get_base_module(mod)))
        return r

    def _should_ignore(self, mod: ModuleType):
        return any(mod.__name__.startswith(i) for i in self.ignoring) or \
               is_private_module(mod) or is_pseudo_module(mod)

    def _add_requirement(self, obj_or_module):
        if not isinstance(obj_or_module, ModuleType):
            module = get_object_module(obj_or_module)
        else:
            module = obj_or_module

        if module is not None and not self._should_ignore(module) and is_installable_module(module):
            self._modules.add(module)

    def save(self, obj, save_persistent_id=True):
        if id(obj) in self.seen:
            return
        self.seen.add(id(obj))
        self._add_requirement(obj)
        try:
            return super(EbonitePickler, self).save(obj, save_persistent_id)
        except (TypeError, PicklingError) as e:
            # if object cannot be serialized, it's probably a C object and we don't need to go deeper
            logger.debug('Skipping dependency analysis for %s because of %s: %s', obj, type(e).__name__, e)

    def skip_write(self, *args, **kwargs):
        pass


def get_object_requirements(obj) -> Requirements:
    """
    Analyzes packages required for given object to perform its function.
    This function uses `pickle`/`dill` libraries serialization hooks internally.
    Thus result of this function depend on given object being serializable by `pickle`/`dill` libraries:
    all nodes in objects graph which can't be serialized are skipped and their dependencies are lost.

    :param obj: obj to analyze
    :return: :class:`.Requirements` object containing all required packages
    """
    a = _EboniteRequirementAnalyzer(recurse=True)
    a.dump(obj)
    return a.to_requirements()


if __name__ == '__main__':
    check_pypi_module('numpy', 2e3)
