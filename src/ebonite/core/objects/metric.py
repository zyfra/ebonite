import base64
import os
import tempfile
import zlib
from abc import abstractmethod
from typing import Any, Dict

from pyjackson.decorators import cached_property, type_field

from ebonite.core.objects.base import EboniteParams
from ebonite.core.objects.requirements import Requirements
from ebonite.core.objects.wrapper import PickleModelIO
from ebonite.utils.importing import import_string
from ebonite.utils.module import get_object_requirements


@type_field('type')
class Metric(EboniteParams):
    @abstractmethod
    def evaluate(self, truth, prediction):
        raise NotImplementedError()


class LibFunctionMetric(Metric):
    def __init__(self, function: str, args: Dict[str, Any] = None, invert_input: bool = False):
        self.invert_input = invert_input
        self.args = args or {}
        self.function = function

    @cached_property
    def _function(self):
        return import_string(self.function)

    def evaluate(self, truth, prediction):
        if self.invert_input:
            return self._function(prediction, truth, **self.args)
        else:
            return self._function(truth, prediction, **self.args)


class CallableMetricWrapper:
    def __init__(self, artifacts: Dict[str, str], requirements: Requirements):
        self.artifacts = artifacts
        self.requirements = requirements
        self.callable = None

    def bind(self, callable):
        self.callable = callable
        return self

    @staticmethod
    def compress(s: bytes) -> str:
        """
        Helper method to compress source code

        :param s: source code
        :return: base64 encoded string of zipped source
        """
        zp = zlib.compress(s)
        b64 = base64.standard_b64encode(zp)
        return b64.decode('utf8')

    @staticmethod
    def decompress(s: str) -> bytes:
        """
        Helper method to decompress source code

        :param s: compressed source code
        :return: decompressed source code
        """
        zp = base64.standard_b64decode(s.encode('utf8'))
        src = zlib.decompress(zp)
        return src

    @classmethod
    def from_callable(cls, callable):
        reqs = get_object_requirements(callable)
        with PickleModelIO().dump(callable) as artifacts:
            payload = {path: cls.compress(bts) for path, bts in artifacts.bytes_dict().items()}
        return CallableMetricWrapper(payload, reqs).bind(callable)

    def load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for path, art in self.artifacts.items():
                with open(os.path.join(tmpdir, path), 'wb') as f:
                    f.write(self.decompress(art))
            self.callable = PickleModelIO().load(tmpdir)


class CallableMetric(Metric):
    def __init__(self, wrapper: CallableMetricWrapper):
        self.wrapper = wrapper

    def evaluate(self, truth, prediction):
        if self.wrapper.callable is None:
            self.wrapper.load()
        return self.wrapper.callable(truth, prediction)
