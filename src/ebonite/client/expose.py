import inspect
import re
from abc import abstractmethod
from typing import Optional

from pyjackson.utils import get_function_signature

EXPOSED_FIELD = '_client_exposed'


class ExposedMethod:
    def __init__(self, name: str = None):
        self.name = name
        self.method = None

    def __call__(self, method):
        setattr(method, EXPOSED_FIELD, self)
        self.method = method
        if self.name is None:
            self.name = self.original_name
        return method

    def __repr__(self):
        return f'{self.name}_method'

    @property
    def original_name(self):
        return self.method.__name__

    @abstractmethod
    def generate_code(self):
        """Generate method code"""
        raise NotImplementedError()

    def get_declaration(self):
        dec = ''
        for line in inspect.getsourcelines(self.method)[0]:
            strip = line.strip()
            if not strip or (dec == '' and not strip.startswith('def')):
                continue
            dec += line
            if re.sub(re.compile("#.*?\n"), "", line).strip().endswith(':'):
                break
        return dec.strip().replace(self.original_name, self.name)

    def get_signature(self):
        return get_function_signature(self.method)


def get_exposed_method(f) -> Optional[ExposedMethod]:
    return getattr(f, EXPOSED_FIELD, None)
