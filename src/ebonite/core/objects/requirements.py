import base64
import itertools
import os
import zlib
from types import ModuleType
from typing import List, Union

from pyjackson.decorators import make_string, type_field

from ebonite.core.objects.base import EboniteParams

# TODO i dont know how to do this better
MODULE_PACKAGE_MAPPING = {
    'sklearn': 'scikit-learn',
    'skimage': 'scikit-image'
}
PACKAGE_MODULE_MAPPING = {v: k for k, v in MODULE_PACKAGE_MAPPING.items()}


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
    """
    type = 'custom'

    def __init__(self, name: str, source64zip: str):
        self.source64zip = source64zip
        self.name = name

    @staticmethod
    def from_module(mod: ModuleType) -> 'CustomRequirement':
        """
        Factory method to create :class:`CustomRequirement` from module object

        :param mod: module object
        :return: :class:`CustomRequirement`
        """
        with open(mod.__file__, 'r', encoding='utf-8') as f:
            src = CustomRequirement.compress(f.read())
            return CustomRequirement(mod.__name__, src)

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
        return CustomRequirement.decompress(self.source64zip)

    @property
    def module(self):
        """
        Module name for this requirement
        """
        return self.name.split('.')[0]

    def to_sources_dict(self):
        """
        Mapping path -> source code for this requirement

        :return: dict path -> source
        """
        res = {
            self.name.replace('.', '/') + '.py': self.source
        }
        paths = self.name.split('.')
        res.update({
            os.path.join(*paths[:i + 1], '__init__.py'): '' for i in range(len(paths) - 1)
        })
        return res


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
            for r in self.custom:
                if r.name == requirement.name:
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
