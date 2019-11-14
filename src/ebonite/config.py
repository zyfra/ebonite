import argparse
from typing import Callable, Type

from everett import NO_VALUE
from everett.manager import ConfigManager, ConfigOSEnv, ListOf, generate_uppercase_key

_config = ConfigManager([])


class ConfigEnv:
    register = True
    on_top = True

    def get(self, key, namespace=None):
        raise NotImplementedError

    def __init_subclass__(cls: Type['ConfigEnv']):
        if cls.register:
            inst = cls()
            if cls.on_top:
                _config.envs.insert(0, inst)
            else:
                _config.envs.append(inst)


class _ConfigArgParseEnv(ConfigEnv):
    on_top = False

    def __init__(self):
        self.cache = dict()

    def get(self, key, namespace=None):
        name = generate_uppercase_key(key, namespace).lower()
        if name in self.cache:
            return self.cache[name]
        parser = argparse.ArgumentParser()
        parser.add_argument(f'--{name}')
        args = parser.parse_known_args([name])
        res = getattr(args, name, NO_VALUE)
        self.cache[name] = res
        return res


class _NamespacedOSEnv(ConfigOSEnv, ConfigEnv):
    namespace = 'EBONITE'

    def get(self, key, namespace=None):
        return super(_NamespacedOSEnv, self).get(key, namespace or self.namespace)


class Param:
    def __init__(self, key, namespace=None, default=NO_VALUE,
                 alternate_keys=NO_VALUE, doc='', parser: Callable = str, raise_error=True,
                 raw_value=False):
        self.key = key
        self.namespace = namespace
        self.default = default
        self.alternate_keys = alternate_keys
        self.doc = doc
        self.parser = parser
        self.raise_error = raise_error
        self.raw_value = raw_value

    def __get__(self, instance: 'Config', owner: Type['Config']):
        if instance is None:
            return self
        return _config(key=self.key, namespace=self.namespace,
                       default=self.default, alternate_keys=self.alternate_keys,
                       doc=self.doc, parser=self.parser,
                       raise_error=self.raise_error, raw_value=self.raw_value)


class _ConfigMeta(type):
    def __new__(cls, name, bases, namespace):
        meta = super().__new__(cls, name + 'Meta', (cls,) + bases, namespace)
        res = super().__new__(meta, name, bases, {})
        return res


class Config(metaclass=_ConfigMeta):
    pass


class Core(Config):
    DEBUG = Param('debug', default='false', doc='turn debug on', parser=bool)
    ADDITIONAL_EXTENSIONS = Param('extensions', default='',
                                  doc='comma-separated list of additional ebonite extensions to load',
                                  parser=ListOf(str),
                                  raise_error=False)
    AUTO_IMPORT_EXTENSIONS = Param('auto_import_extensions', default='true',
                                   doc='Set to true to automatically load available extensions on ebonite import',
                                   parser=bool)
    RUNTIME = Param('runtime', default='false', doc='is this instance a runtime', parser=bool)


class Runtime(Config):
    SERVER = Param('server', doc='server for runtime')
    LOADER = Param('loader', doc='interface loader for runtime')
