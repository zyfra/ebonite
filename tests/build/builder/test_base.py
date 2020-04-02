import re
import os
import subprocess
import sys

import dill
import numpy as np
import psutil
import pytest

from ebonite.build.builder.base import PythonBuilder, use_local_installation
from ebonite.build.provider import LOADER_ENV, PythonProvider, SERVER_ENV
from ebonite.build.provider.ml_model_multi import MLModelMultiProvider
from ebonite.build.provider.ml_model import MLModelProvider
from ebonite.core.objects.artifacts import Blobs, InMemoryBlob
from ebonite.core.objects.requirements import InstallableRequirement, Requirements
from ebonite.ext.aiohttp import AIOHTTPServer
from ebonite.ext.flask import FlaskServer
from ebonite.ext.flask.client import HTTPClient
from ebonite.runtime.interface.ml_model import ModelLoader, MultiModelLoader
from ebonite.utils.module import get_module_version

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
        return Requirements([InstallableRequirement.from_str(f'dill=={get_module_version(dill)}')])  # for example

    def get_sources(self):
        return {
            'server.py': SERVER_CODE
        }

    def get_artifacts(self):
        return Blobs({'test.bin': InMemoryBlob(b'test_bytes')})

    def get_options(self):
        return {}


@pytest.fixture
def python_builder_mock() -> PythonBuilder:
    return PythonBuilder(ProviderMock())


@pytest.fixture
def python_builder_sync(created_model) -> PythonBuilder:
    return PythonBuilder(MLModelProvider(created_model, FlaskServer()))


@pytest.fixture
def python_builder_async(created_model) -> PythonBuilder:
    return PythonBuilder(MLModelProvider(created_model, AIOHTTPServer()))


@pytest.fixture
def python_multi_builder(created_model) -> PythonBuilder:
    return PythonBuilder(MLModelMultiProvider([created_model], FlaskServer()))


def test_python_builder__distr_contents(tmpdir, python_builder_mock: PythonBuilder):
    python_builder_mock._write_distribution(tmpdir)

    _check_basic_distr_contents(tmpdir)
    _check_requirements(tmpdir, set(_get_builder_requirements(python_builder_mock)))


def test_python_builder__distr_contents_local(tmpdir, python_builder_mock: PythonBuilder):
    with use_local_installation():
        python_builder_mock._write_distribution(tmpdir)

    _check_basic_distr_contents(tmpdir)
    assert os.path.isdir(os.path.join(tmpdir, 'ebonite'))
    from setup import setup_args
    _check_requirements(tmpdir, {*setup_args['install_requires'], *_get_builder_requirements(python_builder_mock)})


def _get_builder_requirements(python_builder: PythonBuilder):
    return python_builder.provider.get_requirements().to_pip()


def _check_basic_distr_contents(base_dir):
    _check_contents(base_dir, 'server.py', SERVER_CODE)
    _check_contents(base_dir, 'test.bin', b'test_bytes')
    _check_contents(base_dir, 'run.sh', re.compile('ebonite'))


def _check_requirements(base_dir, expected_modules):
    from setup import get_requirements
    actual_modules = set(get_requirements(os.path.join(base_dir, 'requirements.txt')))

    assert actual_modules == expected_modules


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


@pytest.mark.parametrize("python_builder", ["python_builder_sync", "python_builder_async"])
def test_python_builder__distr_loadable(tmpdir, python_builder, created_model, pandas_data, request):
    python_builder: PythonBuilder = request.getfixturevalue(python_builder)
    prediction = created_model.wrapper.call_method('predict', pandas_data)

    with use_local_installation():
        python_builder._write_distribution(tmpdir)

    iface = _load(ModelLoader(), tmpdir)
    prediction2 = iface.execute('predict', {'vector': pandas_data})

    np.testing.assert_almost_equal(prediction, prediction2)


def test_python_multi_builder__distr_loadable(tmpdir, python_multi_builder: PythonBuilder, created_model, pandas_data):
    prediction = created_model.wrapper.call_method('predict', pandas_data)

    with use_local_installation():
        python_multi_builder._write_distribution(tmpdir)

    iface = _load(MultiModelLoader(), tmpdir)
    prediction2 = iface.execute(f'{created_model.name}-predict', {'vector': pandas_data})

    np.testing.assert_almost_equal(prediction, prediction2)


def _load(loader, tmpdir):
    cwd = os.getcwd()
    os.chdir(tmpdir)
    iface = loader.load()
    os.chdir(cwd)
    return iface


def test_python_builder__distr_runnable(tmpdir, python_builder_mock: PythonBuilder):
    args, env = _prepare_distribution(tmpdir, python_builder_mock)
    server_output = subprocess.run(args, env=env, check=True, stdout=subprocess.PIPE).stdout
    assert server_output.decode('utf8').strip() == SECRET


@pytest.mark.parametrize(("python_builder", "server_reqs"), [
    ("python_builder_sync", {'flasgger==0.9.3'}),
    ("python_builder_async", {'aiohttp_swagger'})
])
def test_python_builder_flask_distr_runnable(tmpdir, python_builder, pandas_data, server_reqs, request):
    python_builder: PythonBuilder = request.getfixturevalue(python_builder)
    args, env = _prepare_distribution(tmpdir, python_builder)

    from setup import setup_args
    _check_requirements(tmpdir, {*setup_args['install_requires'], *server_reqs,
                                 'pandas==0.25.1', 'scikit-learn==0.22', 'numpy==1.17.3'})  # model reqs

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


def _prepare_distribution(target_dir, python_builder):
    with use_local_installation():
        python_builder._write_distribution(target_dir)

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
    env.update(python_builder.provider.get_env())

    return args, env
