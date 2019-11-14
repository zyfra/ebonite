from ebonite.utils.module import get_object_requirements


def test_requirements_analyzer__custom_modules():
    import tensorflow  # noqa
    from custom_module import MODEL
    reqs = get_object_requirements(MODEL)

    custom_reqs = {req.name for req in reqs.custom}
    # "test_cases" appears here as this code is imported by pytest
    # __main__ modules won't appear here
    assert {'model_trainer', 'custom_module', 'test_cases'} == custom_reqs

    inst_reqs = {req.package for req in reqs.installable}
    assert {'scikit-learn', 'pandas', 'six'} == inst_reqs
