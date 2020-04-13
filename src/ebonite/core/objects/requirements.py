import base64
import glob
import itertools
import json
import os
import zlib
from types import ModuleType
from typing import Dict, List, Union

from pyjackson.decorators import make_string, type_field

from ebonite.core.objects.base import EboniteParams

# TODO i dont know how to do this better
MODULE_PACKAGE_MAPPING = {
    'sklearn': 'scikit-learn',
    'skimage': 'scikit-image'
}
PACKAGE_MODULE_MAPPING = {v: k for k, v in MODULE_PACKAGE_MAPPING.items()}


def read(path):
    with open(path, 'r') as f:
        return f.read()


@type_field('type')
class Requirement(EboniteParams):
    """
    Base class for python requirement
    """
    type = None


@make_string(include_name=True)
class InstallableRequirement(Requirement):
    """
    This class represents pip-installable python library

    :param module: name of python module
    :param version: version of python package
    :param package_name: Optional. pip package name for this module, if it is different from module name
    """
    type = 'installable'

    def __init__(self, module: str, version: str = None, package_name: str = None):
        self.module = module
        self.version = version
        self.package_name = package_name

    @property
    def package(self):
        """
        Pip package name
        """
        return self.package_name or MODULE_PACKAGE_MAPPING.get(self.module, self.module)

    def to_str(self):
        """
        pip installable representation of this module
        """
        if self.version is not None:
            return '{}=={}'.format(self.package, self.version)
        return self.package

    @classmethod
    def from_module(cls, mod: ModuleType, package_name: str = None) -> 'InstallableRequirement':
        """
        Factory method to create :class:`InstallableRequirement` from module object

        :param mod: module object
        :param package_name: PIP package name if it is not equal to module name
        :return: :class:`InstallableRequirement`
        """
        from ebonite.utils.module import get_module_version
        return InstallableRequirement(mod.__name__, get_module_version(mod), package_name)

    @classmethod
    def from_str(cls, name):
        """
        Factory method for creating :class:`InstallableRequirement` from string

        :param name: string representation
        :return: :class:`InstallableRequirement`
        """
        for rel in ['==', '>=', '<=']:  # TODO for now we interpret everything as exact version
            if rel in name:
                package, version = name.split(rel)
                return InstallableRequirement(package, version)

        return InstallableRequirement(name)  # FIXME for other relations like > < !=


@make_string(include_name=True)
class CustomRequirement(Requirement):
    """
    This class represents local python code that you need as a requirement for your code

    :param name: filename of this code
    :param source64zip: zipped and base64-encoded source
    :param is_package: whether this code should be in %name%/__init__.py
    """
    type = 'custom'

    def __init__(self, name: str, source64zip: str, is_package: bool):
        self.source64zip = source64zip
        self.name = name
        self.is_package = is_package

    @staticmethod
    def from_module(mod: ModuleType) -> 'CustomRequirement':
        """
        Factory method to create :class:`CustomRequirement` from module object

        :param mod: module object
        :return: :class:`CustomRequirement`
        """
        is_package = mod.__file__.endswith('__init__.py')
        if is_package:
            pkg_dir = os.path.dirname(mod.__file__)
            par = os.path.dirname(pkg_dir)
            sources = {os.path.relpath(p, par): read(p) for p in glob.glob(os.path.join(pkg_dir, '**', '*.py'),
                                                                           recursive=True)}
            src = CustomRequirement.compress(json.dumps(sources))
        else:
            src = CustomRequirement.compress(read(mod.__file__))
        return CustomRequirement(mod.__name__, src, is_package)

    @staticmethod
    def compress(s: str) -> str:
        """
        Helper method to compress source code

        :param s: source code
        :return: base64 encoded string of zipped source
        """
        zp = zlib.compress(s.encode('utf8'))
        b64 = base64.standard_b64encode(zp)
        return b64.decode('utf8')

    @staticmethod
    def decompress(s: str) -> str:
        """
        Helper method to decompress source code

        :param s: compressed source code
        :return: decompressed source code
        """
        zp = base64.standard_b64decode(s.encode('utf8'))
        src = zlib.decompress(zp)
        return src.decode('utf8')

    @property
    def source(self) -> str:
        """
        Source code of this requirement
        """
        if not self.is_package:
            return CustomRequirement.decompress(self.source64zip)
        raise AttributeError("package requirement does not have source attribute")

    @property
    def sources(self) -> Dict[str, str]:
        if self.is_package:
            return json.loads(CustomRequirement.decompress(self.source64zip))
        raise AttributeError("non package requirement does not have sources attribute")

    def to_sources_dict(self):
        """
        Mapping path -> source code for this requirement

        :return: dict path -> source
        """
        if self.is_package:
            return self.sources
        else:
            return {self.name.replace('.', '/') + '.py': self.source}


class Requirements(EboniteParams):
    """
    A collection of requirements

    :param requirements: list of :class:`Requirement` instances
    """

    def __init__(self, requirements: List[Requirement] = None):
        self.requirements = requirements or []

    @property
    def installable(self) -> List[InstallableRequirement]:
        """
        List of installable requirements
        """
        return [r for r in self.requirements if isinstance(r, InstallableRequirement)]

    @property
    def custom(self) -> List[CustomRequirement]:
        """
        List of custom requirements
        """
        return [r for r in self.requirements if isinstance(r, CustomRequirement)]

    @property
    def modules(self) -> List[str]:
        """
        List of module names
        """
        return [r.module for r in self.requirements]

    def add(self, requirement: Requirement):
        """
        Adds requirement to this collection

        :param requirement: :class:`Requirement` instance to add
        """
        if isinstance(requirement, InstallableRequirement):
            for r in self.installable:
                if r.package == requirement.package:
                    if r.version == requirement.version:
                        break
                    if r.version is not None and r.version != requirement.version:
                        raise ValueError('Conflicting versions for package {}: {} and {}'.format(r.package, r.version,
                                                                                                 requirement.version))
            else:
                self.requirements.append(requirement)
        elif isinstance(requirement, CustomRequirement):
            if requirement.is_package:
                for r in self.custom:
                    if r.name.startswith(requirement.name + '.') or r.name == requirement.name:
                        # existing req is subpackage or equals to new req
                        self.requirements.remove(r)
                    if requirement.name.startswith(r.name + '.'):
                        # new req is subpackage of existing
                        break
                else:
                    self.requirements.append(requirement)
            else:
                for r in self.custom:
                    if r.is_package and requirement.name.startswith(r.name + '.'):
                        # new req is from existing package
                        break
                    if not r.is_package and r.name == requirement.name:
                        # new req equals to existing
                        break
                else:
                    self.requirements.append(requirement)

    def to_pip(self) -> List[str]:
        """
        :return: list of pip installable packages
        """
        return [r.to_str() for r in self.installable]

    def __add__(self, other: 'AnyRequirements'):
        other = resolve_requirements(other)
        res = Requirements([])
        for r in itertools.chain(self.requirements, other.requirements):
            res.add(r)
        return res

    def __iadd__(self, other: 'AnyRequirements'):
        return self + other


def resolve_requirements(other: 'AnyRequirements') -> Requirements:
    """
    Helper method to create :class:`Requirements` from any supported source.
    Supported formats: :class:`Requirements`, :class:`Requirement`, list of :class:`Requirement`,
    string representation or list of string representations

    :param other: requirement in supported format
    :return: :class:`Requirements` instance
    """
    if not isinstance(other, Requirements):
        if isinstance(other, list):
            if isinstance(other[0], str):
                other = Requirements([InstallableRequirement.from_str(r) for r in other])
            elif isinstance(other[0], Requirement):
                other = Requirements([r for r in other])
        elif isinstance(other, Requirement):
            other = Requirements([other])
        elif isinstance(other, str):
            other = Requirements([InstallableRequirement.from_str(other)])
        else:
            raise TypeError('only other Requirements, Requirement, list of Requirement objects, string '
                            '(or list of strings) can be added')
    return other


AnyRequirements = Union[Requirements, Requirement, List[Requirement], str, List[str]]
