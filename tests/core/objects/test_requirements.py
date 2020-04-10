import pytest

from ebonite.core.objects.requirements import (CustomRequirement, InstallableRequirement, Requirements,
                                               resolve_requirements)


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


def test_installable_requirement__from_module():
    import pandas as pd
    assert InstallableRequirement.from_module(pd).to_str() == f'pandas=={pd.__version__}'

    import numpy as np
    assert InstallableRequirement.from_module(np).to_str() == f'numpy=={np.__version__}'

    import sklearn as sk
    assert InstallableRequirement.from_module(sk).to_str() == f'scikit-learn=={sk.__version__}'
    assert InstallableRequirement.from_module(sk, 'xyz').to_str() == f'xyz=={sk.__version__}'


def test_custom_requirement__source():
    from ebonite.core import objects
    package = CustomRequirement.from_module(objects)
    assert package.is_package
    assert package.sources is not None
    with pytest.raises(AttributeError):
        package.source  # noqa

    module = CustomRequirement.from_module(objects.requirements)
    assert not module.is_package
    assert module.source is not None
    with pytest.raises(AttributeError):
        module.sources  # noqa
