from abc import abstractmethod
from typing import List

from ebonite.core.analyzer import Hook
from ebonite.core.objects.requirements import AnyRequirements, Requirement, Requirements, resolve_requirements


class RequirementAnalyzer:
    """
    Analyzer for RequirementHook hooks
    """
    hooks: List['RequirementHook'] = []

    @classmethod
    def analyze(cls, obj: AnyRequirements) -> Requirements:
        """
        Run RequirementHook hooks to analyze obj

        :param obj: objects to analyze
        :return: Instance of Requirements
        """
        obj = resolve_requirements(obj)
        to_process = list(obj.requirements)
        result = []
        for hook in cls.hooks:
            while len(to_process) > 0:
                req = to_process.pop()
                if hook.can_process(req):
                    result += hook.process(req).requirements
                else:
                    result.append(req)
            to_process = result
            result = []

        return Requirements(to_process)


class RequirementHook(Hook):
    _analyzer = RequirementAnalyzer

    def must_process(self, obj: Requirement) -> bool:
        return self.can_process(obj)

    @abstractmethod
    def can_process(self, obj: Requirement) -> bool:
        pass

    @abstractmethod
    def process(self, obj: Requirement, **kwargs) -> Requirements:
        pass
