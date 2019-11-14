from ebonite.core.objects.requirements import InstallableRequirement, Requirements, resolve_requirements


def test_resolve_requirements_arg():
    requirements = Requirements([InstallableRequirement('dumb', '0.4.1'), InstallableRequirement('art', '4.0')])
    actual_reqs = resolve_requirements(requirements)
    assert actual_reqs == requirements


def test_resolve_requirement_arg():
    req = InstallableRequirement('dumb', '0.4.1')
    actual_reqs = resolve_requirements(req)
    assert actual_reqs.installable[0] == req


def test_resolve_requirement_list_arg():
    req = [InstallableRequirement('dumb', '0.4.1'), InstallableRequirement('art', '4.0')]
    actual_reqs = resolve_requirements(req)
    assert len(actual_reqs.installable) == 2
    assert actual_reqs.installable == req


def test_resolve_str_arg():
    req = "dumb==0.4.1"
    actual_reqs = resolve_requirements(req)
    assert actual_reqs.installable[0].to_str() == req


def test_resolve_str_list_arg():
    req = ["dumb==0.4.1", "art==4.0"]
    actual_reqs = resolve_requirements(req)
    assert len(actual_reqs.installable) == 2
    assert req == [r.to_str() for r in actual_reqs.installable]
