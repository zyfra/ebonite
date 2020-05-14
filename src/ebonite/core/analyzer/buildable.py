from abc import ABC

from ebonite.core.analyzer import Hook, analyzer_class
from ebonite.core.objects.core import Buildable


class BuildableHook(Hook, ABC):
    pass


BuildableAnalyzer = analyzer_class(BuildableHook, Buildable)
