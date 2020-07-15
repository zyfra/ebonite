import contextlib
import os
import shutil

import pandas as pd
import pytest
from dvc.repo import Repo

from ebonite.core.analyzer.dataset import DatasetAnalyzer
from ebonite.ext.pandas import DataFrameType
from ebonite.ext.pandas.dataset_source import PandasFormatCsv, PandasReader
from ebonite.ext.s3 import S3ArtifactRepository
from ebonite.utils import fs
from tests.conftest import docker_test
from tests.ext.test_s3.conftest import ACCESS_KEY, SECRET_KEY  # noqa


@pytest.fixture
def dvc_repo_factory(tmpdir):
    def dvc_repo(remote, remote_kwargs=None):
        repo_path = tmpdir
        repo = Repo.init(repo_path, no_scm=True)

        with repo.config.edit() as conf:
            remote_config = {'url': remote}
            if remote_kwargs is not None:
                remote_config.update(remote_kwargs)
            conf['remote']['storage'] = remote_config
            conf['core']['remote'] = 'storage'

        shutil.copy(fs.current_module_path('data1.csv'), repo_path)
        data1_path = os.path.join(repo_path, 'data1.csv')
        assert os.path.exists(data1_path)
        repo.add([data1_path])
        assert os.path.exists(data1_path + '.dvc')
        repo.push()
        os.remove(data1_path)
        shutil.rmtree(os.path.join(repo_path, '.dvc', 'cache'), ignore_errors=True)

        return repo_path

    return dvc_repo


@pytest.fixture
def local_dvc_repo(tmpdir_factory, dvc_repo_factory):
    storage_path = str(tmpdir_factory.mktemp('storage'))
    return dvc_repo_factory(storage_path)


@contextlib.contextmanager
def override_env(**envs):
    prev = {e: os.environ.get(e, None) for e in envs.keys()}
    try:
        for e, val in envs.items():
            os.environ[e] = val
        yield
    finally:
        for e, val in prev.items():
            if val is not None:
                os.environ[e] = val


@pytest.fixture
def s3_dvc_repo(s3server, dvc_repo_factory):
    url = f'http://localhost:{s3server}'

    with override_env(AWS_ACCESS_KEY_ID=ACCESS_KEY, AWS_SECRET_ACCESS_KEY=SECRET_KEY,
                      S3_ACCESS_KEY=ACCESS_KEY, S3_SECRET_KEY=SECRET_KEY):
        S3ArtifactRepository('dvc-bucket', url)._ensure_bucket()  # noqa
        return dvc_repo_factory('s3://dvc-bucket',
                                {'endpointurl': url})


def _test_create_dvc_source__local(local_dvc_repo):
    create_dvc_source = None
    dt = DataFrameType(['col1', 'col2'], ['int64', 'string'], [])
    ds = create_dvc_source(path='data1.csv',
                           reader=PandasReader(PandasFormatCsv(), dt, 'data1.csv'),
                           repo=local_dvc_repo)
    dataset = ds.read()
    assert isinstance(dataset.data, pd.DataFrame)
    assert DatasetAnalyzer.analyze(dataset.data) == dt


@docker_test
def _test_create_dvc_source_s3(s3_dvc_repo):
    create_dvc_source = None
    dt = DataFrameType(['col1', 'col2'], ['int64', 'string'], [])
    ds = create_dvc_source(path='data1.csv',
                           reader=PandasReader(PandasFormatCsv(), dt, 'data1.csv'),
                           repo=s3_dvc_repo)
    dataset = ds.read()
    assert isinstance(dataset.data, pd.DataFrame)
    assert DatasetAnalyzer.analyze(dataset.data) == dt
