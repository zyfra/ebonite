from ebonite.core.analyzer.requirement import RequirementAnalyzer, RequirementHook
from ebonite.core.objects.requirements import InstallableRequirement, Requirement, Requirements


class TestReqHook1(RequirementHook):
    def can_process(self, obj: Requirement) -> bool:
        return obj == InstallableRequirement('aaaa')

    def process(self, obj: Requirement, **kwargs) -> Requirements:
        return Requirements([obj, InstallableRequirement('bbbb')])


class TestReqHook2(RequirementHook):
    def can_process(self, obj: Requirement) -> bool:
        return obj == InstallableRequirement('aaaa')

    def process(self, obj: Requirement, **kwargs) -> Requirements:
        return Requirements([obj, InstallableRequirement('cccc')])


def test_requirement_analyzer():
    req = InstallableRequirement('aaaa')
    result = RequirementAnalyzer.analyze(req)
    assert isinstance(result, Requirements)
    assert len(result.requirements) == 3
    assert sorted(r.module for r in result.requirements) == ['aaaa', 'bbbb', 'cccc']
