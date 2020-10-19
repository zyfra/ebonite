import os
import re
import subprocess
import sys
import json

import numpy as np
import psutil
import pytest
import platform

from ebonite.build.builder.base import PythonBuildContext, use_local_installation
from ebonite.build.provider import LOADER_ENV, PythonProvider, SERVER_ENV
from ebonite.build.provider.ml_model import ModelBuildable
from ebonite.build.provider.ml_model_multi import MultiModelBuildable
from ebonite.core.objects.artifacts import Blobs, InMemoryBlob
from ebonite.core.objects.core import Buildable
from ebonite.core.objects.requirements import Requirements
from ebonite.ext.aiohttp import AIOHTTPServer
from ebonite.ext.flask import FlaskServer
from ebonite.ext.flask.client import HTTPClient
from ebonite.runtime.interface.ml_model import ModelLoader, MultiModelLoader
from tests.build.conftest import check_ebonite_port_free
from ebonite.core.objects.core import Model, Task, Project
from ebonite.build.provider.pipeline import PipelineProvider, PipelineBuildable

# in Python < 3.7 type of patterns is private, from Python 3.7 it becomes `re.Pattern`
Pattern = type(re.compile(''))

SECRET = 'henlo fren!'
SERVER_CODE = '''from ebonite.runtime.server import Server
class TestServer(Server):
    def start(self, loader_module_path=None):
        print('{}')
'''.format(SECRET)


class ProviderMock(PythonProvider):
    def __init__(self):
        super().__init__(None, None)

    def get_env(self):
        return {
            SERVER_ENV: 'server.TestServer',
            LOADER_ENV: ModelLoader.classpath,
            'EBONITE_LOG_LEVEL': 'ERROR',
            'EBONITE_WATCH': 'False'
        }

    def get_requirements(self):
        return Requirements([])

    def get_sources(self):
        return {
            'server.py': SERVER_CODE
        }

    def get_artifacts(self):
        return Blobs({'test.bin': InMemoryBlob(b'test_bytes')})

    def get_options(self):
        return {}


class BuildableMock(Buildable):
    def get_provider(self):
        return ProviderMock()


def test_pipeline_provider(pipeline):
    provider = PipelineProvider(pipeline, FlaskServer)
    assert provider.get_python_version() == platform.python_version()
    assert provider.get_env() == {'EBONITE_LOADER': 'ebonite.runtime.interface.pipeline.PipelineLoader',
                                  'EBONITE_SERVER': 'ebonite.ext.flask.server.FlaskServer',
                                  'EBONITE_RUNTIME': 'true'}
    assert provider.get_requirements().requirements == []
    reqs_json = json.loads(provider.get_sources()['pipeline.json'])['pipeline']
    assert reqs_json['name'] == 'Test Pipeline'
    assert reqs_json['steps'] == [{"model_name": "a", "method_name": "b"}, {"model_name": "c", "method_name": "d"}]
    assert 'docker' in provider.get_options()


@pytest.fixture
def python_build_context_mock() -> PythonBuildContext:
    return PythonBuildContext(ProviderMock())


@pytest.fixture
def python_build_context_sync(created_model) -> PythonBuildContext:
    buildable = ModelBuildable(created_model, server_type=FlaskServer.type)
    return PythonBuildContext(buildable.get_provider())


@pytest.fixture
def python_build_context_async(created_model) -> PythonBuildContext:
    buildable = ModelBuildable(created_model, server_type=AIOHTTPServer.type)
    return PythonBuildContext(buildable.get_provider())


@pytest.fixture
def python_multi_build_context(created_model) -> PythonBuildContext:
    buildable = MultiModelBuildable([created_model], server_type=FlaskServer.type)
    return PythonBuildContext(buildable.get_provider())


def test_python_build_context__distr_contents(tmpdir, python_build_context_mock):
    python_build_context_mock._write_distribution(tmpdir)

    _check_basic_distr_contents(tmpdir)
    _check_requirements(tmpdir, set(_get_builder_requirements(python_build_context_mock)))


def test_python_build_context__distr_contents_local(tmpdir, python_build_context_mock):
    with use_local_installation():
        python_build_context_mock._write_distribution(tmpdir)

    _check_basic_distr_contents(tmpdir)
    assert os.path.isdir(os.path.join(tmpdir, 'ebonite'))
    from setup import setup_args
    _check_requirements(tmpdir,
                        {*setup_args['install_requires'], *_get_builder_requirements(python_build_context_mock)})


def _get_builder_requirements(python_build_context: PythonBuildContext):
    return python_build_context.provider.get_requirements().to_pip()


def _check_basic_distr_contents(base_dir):
    _check_contents(base_dir, 'server.py', SERVER_CODE)
    _check_contents(base_dir, 'test.bin', b'test_bytes')
    _check_contents(base_dir, 'run.sh', re.compile('ebonite'))


def _check_requirements(base_dir, expected_modules):
    from setup import get_requirements
    actual_modules = set(get_requirements(os.path.join(base_dir, 'requirements.txt')))
    expected_modules = set(expected_modules)
    missed_modules = expected_modules.difference(actual_modules)
    extra_modules = actual_modules.difference(expected_modules)
    assert missed_modules == set() and extra_modules == set(), f'missing {missed_modules}, extra {extra_modules}'


def _check_contents(base_dir, name, contents):
    path = os.path.join(base_dir, name)
    assert os.path.isfile(path)

    if contents is None:
        return

    mode = 'rb' if isinstance(contents, bytes) else 'r'
    with open(path, mode) as f:
        file_contents = f.read()
        if isinstance(contents, Pattern):
            assert re.findall(contents, file_contents)
        else:
            assert file_contents == contents


def test_multimodel_buildable(metadata_repo):
    # Dunno why, but it only worked w/o fixtures
    proj = Project('proj')
    task = Task('Test Task')
    mdl = Model.create(lambda data: data, 'input', 'test_model')

    proj = metadata_repo.create_project(proj)
    task.project = proj
    task = metadata_repo.create_task(task)
    mdl.task = task
    mdl = metadata_repo.create_model(mdl)

    with pytest.raises(ValueError):
        MultiModelBuildable([], server_type=FlaskServer.type)
    assert mdl.has_meta_repo
    mm_buildable = MultiModelBuildable([mdl], server_type=FlaskServer.type)
    assert mm_buildable.task.name == 'Test Task'
    assert mm_buildable.get_provider().get_python_version() == platform.python_version()
    assert len(mm_buildable.models) == 1


def test_pipeline_buildable(metadata_repo, pipeline):
    proj = Project('proj')
    task = Task('Test Task')
    proj = metadata_repo.create_project(proj)
    task.project = proj
    task = metadata_repo.create_task(task)

    pipeline.task = task
    pipeline = metadata_repo.create_pipeline(pipeline)
    buildable = PipelineBuildable(pipeline, server_type=FlaskServer.type)
    assert buildable.get_provider().get_python_version() == platform.python_version()
    assert buildable.task.name == 'Test Task'
    assert buildable.pipeline == pipeline


@pytest.mark.parametrize("python_build_context", ["python_build_context_sync", "python_build_context_async"])
def test_python_build_context__distr_loadable(tmpdir, python_build_context, created_model, pandas_data, request):
    python_build_context: PythonBuildContext = request.getfixturevalue(python_build_context)
    prediction = created_model.wrapper.call_method('predict', pandas_data)

    with use_local_installation():
        python_build_context._write_distribution(tmpdir)

    assert python_build_context.provider.get_python_version() == platform.python_version()

    iface = _load(ModelLoader(), tmpdir)
    prediction2 = iface.execute('predict', {'vector': pandas_data})

    np.testing.assert_almost_equal(prediction, prediction2)


def test_python_multi_builder__distr_loadable(tmpdir, python_multi_build_context, created_model, pandas_data):
    prediction = created_model.wrapper.call_method('predict', pandas_data)

    with use_local_installation():
        python_multi_build_context._write_distribution(tmpdir)

    assert python_multi_build_context.provider.get_python_version() == platform.python_version()

    iface = _load(MultiModelLoader(), tmpdir)
    prediction2 = iface.execute(f'{created_model.name}_predict', {'vector': pandas_data})

    np.testing.assert_almost_equal(prediction, prediction2)


def _load(loader, tmpdir):
    cwd = os.getcwd()
    os.chdir(tmpdir)
    iface = loader.load()
    os.chdir(cwd)
    return iface


def test_python_build_context__distr_runnable(tmpdir, python_build_context_mock):
    args, env = _prepare_distribution(tmpdir, python_build_context_mock)
    server_output = subprocess.run(args, env=env, check=True, stdout=subprocess.PIPE).stdout
    assert server_output.decode('utf8').strip() == SECRET


@pytest.mark.parametrize(("python_build_context", "server_reqs"), [
    ("python_build_context_sync", {}),
    ("python_build_context_async", {'aiohttp_swagger'})
])
def test_python_build_context_flask_distr_runnable(tmpdir, python_build_context, pandas_data, server_reqs, request):
    python_build_context: PythonBuildContext = request.getfixturevalue(python_build_context)
    args, env = _prepare_distribution(tmpdir, python_build_context)

    from setup import setup_args
    _check_requirements(tmpdir, {*setup_args['install_requires'], *server_reqs,
                                 'pandas==1.0.3', 'scikit-learn==0.22.2', 'numpy==1.18.2'})  # model reqs

    check_ebonite_port_free()

    # TODO make ModelLoader.load cwd-independent
    server = subprocess.Popen(args, env=env, cwd=tmpdir)
    with pytest.raises(subprocess.TimeoutExpired):
        # we hope that 5 seconds is enough to determine that server didn't crash
        server.wait(5)

    try:
        client = HTTPClient()
        predictions = client.predict(pandas_data)
        np.testing.assert_array_almost_equal(predictions, [1, 0])

        probas = client.predict_proba(pandas_data)
        np.testing.assert_array_almost_equal(np.argmax(probas, axis=1), [1, 0])
    finally:
        # our server runs for eternity, thus we should kill it to clean up
        # `server.kill` kills just shell script, Python subprocess still alive
        parent = psutil.Process(server.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()


def _prepare_distribution(target_dir, python_build_context):
    with use_local_installation():
        python_build_context._write_distribution(target_dir)

    # prevent escaping from interpreter installation used for running tests
    run_sh = os.path.join(target_dir, 'run.sh')
    with open(run_sh, 'r') as f:
        contents = f.read()
    # windows paths are deadly for shell scripts under Cygwin
    python_exe = sys.executable.replace('\\', '/')
    contents = contents.replace('python', python_exe)
    with open(run_sh, 'w') as f:
        f.write(contents)

    args = ['sh', run_sh]

    # prevent leak of PYTHONPATH used for running tests
    env = os.environ.copy()
    env['PYTHONPATH'] = str(target_dir)
    env.update(python_build_context.provider.get_env())

    return args, env
