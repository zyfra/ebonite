from ebonite.core.analyzer.requirement import RequirementAnalyzer
from ebonite.core.objects.requirements import UnixPackageRequirement
from ebonite.utils.module import get_object_requirements


def test_libgomp(wrapper):
    req = get_object_requirements(wrapper)
    assert RequirementAnalyzer.analyze(req).of_type(UnixPackageRequirement) == [UnixPackageRequirement('libgomp1')]
