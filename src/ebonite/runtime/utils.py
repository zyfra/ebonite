import logging
from typing import Dict, Type

from ebonite.utils.classproperty import classproperty
from ebonite.utils.importing import import_string

logger = logging.getLogger(__name__)


def registering_type(type_name):
    """
    Helper for base classes which maintains registry of all their subclasses

    :param type_name: name for base class to use
    :return: class with subclasses registry built in
    """

    class RegType:
        impls: Dict[str, Type] = {}

        def __init_subclass__(cls, **kwargs):
            RegType.impls[cls.classpath] = cls
            super(RegType, cls).__init_subclass__(**kwargs)

        @staticmethod
        def get(name):
            import_string(name)
            impl = RegType.impls.get(name)
            if impl is None:
                raise ValueError('{} class {} not found'.format(type_name, name))
            return impl

        @classproperty
        def classpath(cls):
            return '{}.{}'.format(cls.__module__, cls.__name__)

    return RegType
