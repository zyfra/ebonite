import os
from typing import Dict

import pytest

from ebonite.core.objects.artifacts import ArtifactCollection, InMemoryBlob
from ebonite.core.objects.core import Model
from ebonite.repository.artifact import ArtifactExistsError, ArtifactRepository, NoSuchArtifactError
from tests.repository.artifact.test_local.conftest import local_artifact as repo_fixture

# from tests.ext.s3.conftest import s3_artifact as repo_fixture
art_repo = repo_fixture


def test_push_artifact(art_repo: ArtifactRepository, model: Model, blobs: Dict[str, InMemoryBlob], tmpdir):
    artifact: ArtifactCollection = art_repo.push_artifact(model, blobs)

    assert artifact is not None
    with artifact.blob_dict() as bd:
        assert len(bd) == len(blobs)

    assert artifact.bytes_dict() == {n: b.payload for n, b in blobs.items()}

    artifact.materialize(tmpdir)
    assert set(os.listdir(tmpdir)) == set(list(blobs.keys()))

    for name, blob in blobs.items():
        with open(os.path.join(tmpdir, name), 'rb') as f:
            payload = f.read()
        assert payload == blob.payload

        with blob.bytestream() as p:
            assert p.read() == blob.payload


def test_get_artifact(art_repo: ArtifactRepository, model: Model, blobs: Dict[str, InMemoryBlob]):
    artifact: ArtifactCollection = art_repo.push_artifact(model, blobs)

    new_artifact = art_repo.get_artifact(model)

    assert new_artifact == artifact


def test_push_non_existing_artifact(art_repo: ArtifactRepository, model: Model):
    with pytest.raises(NoSuchArtifactError):
        art_repo.get_artifact(model)


def test_push_duplicate_artifact(art_repo: ArtifactRepository, model: Model):
    art_repo.push_artifact(model, {})
    with pytest.raises(ArtifactExistsError):
        art_repo.push_artifact(model, {})


def test_delete_artifact(art_repo: ArtifactRepository, model: Model):
    art_repo.push_artifact(model, {})
    art_repo.get_artifact(model)
    art_repo.delete_artifact(model)
    with pytest.raises(NoSuchArtifactError):
        art_repo.get_artifact(model)
    art_repo.push_artifact(model, {})


def test_delete_non_existing_artifact(art_repo: ArtifactRepository, model: Model):
    with pytest.raises(NoSuchArtifactError):
        art_repo.delete_artifact(model)
