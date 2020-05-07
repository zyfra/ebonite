from ebonite.core.analyzer.requirement import RequirementHook
from ebonite.core.objects.requirements import InstallableRequirement, Requirement, Requirements, UnixPackageRequirement


class LightGBMRequirementHook(RequirementHook):
    def can_process(self, obj: Requirement) -> bool:
        return isinstance(obj, InstallableRequirement) and obj.package.lower() == 'lightgbm'

    def process(self, obj: Requirement, **kwargs) -> Requirements:
        return Requirements([obj, UnixPackageRequirement('libgomp1')])
