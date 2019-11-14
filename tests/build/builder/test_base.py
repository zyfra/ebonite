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
from ebonite.build.provider.ml_model import MLModelProvider
from ebonite.core.objects.artifacts import Blobs, InMemoryBlob
from ebonite.core.objects.requirements import InstallableRequirement, Requirements
from ebonite.ext.flask import FlaskServer
from ebonite.ext.flask.client import HTTPClient
from ebonite.runtime.interface.ml_model import ModelLoader
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


@pytest.fixture
def python_builder_mock() -> PythonBuilder:
    return PythonBuilder(ProviderMock())


@pytest.fixture
def python_builder(created_model) -> PythonBuilder:
    return PythonBuilder(MLModelProvider(created_model, FlaskServer()))


def test_python_builder__distr_contents(tmpdir, python_builder_mock: PythonBuilder):
    python_builder_mock._write_distribution(tmpdir)

    _check_basic_distr_contents(tmpdir)


def test_python_builder__distr_contents_local(tmpdir, python_builder_mock: PythonBuilder):
    with use_local_installation():
        python_builder_mock._write_distribution(tmpdir)

    _check_basic_distr_contents(tmpdir)
    assert os.path.isdir(os.path.join(tmpdir, 'ebonite'))
    _check_requirements(tmpdir, 'pyjackson')


def _check_basic_distr_contents(base_dir):
    _check_contents(base_dir, 'server.py', SERVER_CODE)
    _check_requirements(base_dir, 'dill')
    _check_contents(base_dir, 'test.bin', b'test_bytes')
    _check_contents(base_dir, 'run.sh', re.compile('ebonite'))


def _check_requirements(base_dir, mod_name):
    version = get_module_version(__import__(mod_name))
    _check_contents(base_dir, 'requirements.txt', re.compile(f'^{mod_name}=={re.escape(version)}$', re.MULTILINE))


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


def test_python_builder__distr_runnable(tmpdir, python_builder_mock: PythonBuilder):
    args, env = _prepare_distribution(tmpdir, python_builder_mock)
    server_output = subprocess.run(args, env=env, check=True, stdout=subprocess.PIPE).stdout
    assert server_output.decode('utf8').strip() == SECRET


def test_python_builder_flask_distr_runnable(tmpdir, python_builder: PythonBuilder, pandas_data):
    args, env = _prepare_distribution(tmpdir, python_builder)

    # TODO make ModelLoader.load cwd-independent
    server = subprocess.Popen(args, env=env, cwd=tmpdir)
    with pytest.raises(subprocess.TimeoutExpired):
        # we hope that 5 seconds is enough to determine that server didn't crash
        server.wait(5)

    try:
        client = HTTPClient()
        predictions = client.predict(pandas_data)
        np.testing.assert_array_almost_equal(predictions, [1, 0])
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
    contents = contents.replace(' python ', f' {python_exe} ')
    with open(run_sh, 'w') as f:
        f.write(contents)

    args = ['sh', run_sh]

    # prevent leak of PYTHONPATH used for running tests
    env = os.environ.copy()
    env['PYTHONPATH'] = str(target_dir)

    return args, env
