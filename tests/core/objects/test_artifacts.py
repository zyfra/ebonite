import os

import pytest

from ebonite.core.objects.artifacts import Blobs, InMemoryBlob, _RelativePathWrapper


@pytest.fixture
def artifact_collection():
    blobs = Blobs({'1': InMemoryBlob(bytes(123)), '2': InMemoryBlob(bytes(321))})

    ac = blobs + _RelativePathWrapper(blobs, 'first') + _RelativePathWrapper(blobs, 'second')
    ac += _RelativePathWrapper(blobs, 'third')

    ret = ac + _RelativePathWrapper(ac, 'go')
    ret += _RelativePathWrapper(ac, 'be')
    return ret


def _check(condition, tmpdir):
    for pre_path in [[], ['go'], ['be']]:
        for post_path in [[], ['first'], ['second'], ['third']]:
            for name, value in [('1', bytes(123)), ('2', bytes(321))]:
                condition(os.path.join(*tmpdir, *pre_path, *post_path, name), value)


def test_artifact_collection__materialize(artifact_collection, tmpdir):
    artifact_collection.materialize(tmpdir)

    def condition(path, value):
        with open(path, 'rb') as f:
            assert f.read() == value

    _check(condition, [tmpdir])


def test_artifact_collection__bytes_dict(artifact_collection):
    bytes_dict = artifact_collection.bytes_dict()

    assert len(bytes_dict) == 3 * 4 * 2

    def condition(path, value):
        assert bytes_dict[path] == value

    _check(condition, [])


def test_artifact_collection__blob_dict(artifact_collection):
    with artifact_collection.blob_dict() as blob_dict:
        assert len(blob_dict) == 3 * 4 * 2

        def condition(path, value):
            assert blob_dict[path] == InMemoryBlob(value)

        _check(condition, [])
