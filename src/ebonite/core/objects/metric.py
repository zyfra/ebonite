from abc import abstractmethod
from typing import Any, Dict

from pyjackson.decorators import cached_property, type_field

from ebonite.core.objects.base import EboniteParams
from ebonite.utils.importing import import_string


@type_field('type')
class Metric(EboniteParams):
    @abstractmethod
    def evaluate(self, truth, prediction):
        pass  # pragma: no cover


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
