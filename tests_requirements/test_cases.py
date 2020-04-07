import os
import shutil
import subprocess

import dill

from ebonite.utils import fs
from ebonite.utils.module import get_object_requirements


def test_requirements_analyzer__custom_modules():
    import catboost  # noqa
    import unused_code  # noqa
    from proxy_model import model
    reqs = get_object_requirements(model)

    custom_reqs = {req.name for req in reqs.custom}
    # "test_cases" appears here as this code is imported by pytest
    # __main__ modules won't appear here
    assert {'model_trainer', 'proxy_pkg_import', 'pkg_import', 'pkg'} == custom_reqs

    inst_reqs = {req.package for req in reqs.installable}
    assert {'scikit-learn', 'six', 'isort'} == inst_reqs


def test_requirements_analyzer__model_works(tmpdir):
    from proxy_model import model
    reqs = get_object_requirements(model)

    for r in reqs.custom:
        for p, src in r.to_sources_dict().items():
            join = os.path.join(tmpdir, p)
            os.makedirs(os.path.dirname(join), exist_ok=True)
            with open(join, 'w') as f:
                f.write(src)

    with open(os.path.join(tmpdir, 'model.pkl'), 'wb') as f:
        dill.dump(model, f)

    shutil.copy(fs.current_module_path('use_model.py'), tmpdir)

    cp = subprocess.run('python use_model.py', shell=True, cwd=tmpdir)
    assert cp.returncode == 0
