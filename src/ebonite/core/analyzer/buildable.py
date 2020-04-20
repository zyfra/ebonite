from abc import ABC

from ebonite.core.analyzer import analyzer_class, Hook
from ebonite.core.objects.core import Buildable


class BuildableHook(Hook, ABC):
    pass


BuildableAnalyzer = analyzer_class(BuildableHook, Buildable)
