import pytest

from ebonite.core.objects.core import Model


@pytest.fixture
def unpersisted_model(sklearn_model_obj, pandas_data):
    model = Model.create(sklearn_model_obj, pandas_data)
    model._id = 'test_model'
    assert model._persisted_artifacts is None
    assert model._unpersisted_artifacts is not None
    return model


def test_push_artifacts__new(artifact_repository, unpersisted_model):
    bytes_dict = unpersisted_model._unpersisted_artifacts.bytes_dict()
    artifact_repository.push_artifacts(unpersisted_model)

    assert unpersisted_model._persisted_artifacts.bytes_dict() == bytes_dict
    assert unpersisted_model._unpersisted_artifacts is None


def test_push_artifacts__repush(artifact_repository, unpersisted_model):
    artifact_repository.push_artifacts(unpersisted_model)
    unpersisted_model._id = 'test_model2'

    bytes_dict = unpersisted_model._persisted_artifacts.bytes_dict()
    artifact_repository.push_artifacts(unpersisted_model)
    assert unpersisted_model._persisted_artifacts.bytes_dict() == bytes_dict
    assert unpersisted_model._unpersisted_artifacts is None


def test_push_artifacts__repush_with_add(artifact_repository, unpersisted_model, artifact):
    artifact_repository.push_artifacts(unpersisted_model)
    unpersisted_model._id = 'test_model2'
    unpersisted_model.attach_artifact(artifact)

    bytes_dict = unpersisted_model._persisted_artifacts.bytes_dict()
    bytes_dict.update(artifact.bytes_dict())

    artifact_repository.push_artifacts(unpersisted_model)
    assert unpersisted_model._persisted_artifacts.bytes_dict() == bytes_dict
    assert unpersisted_model._unpersisted_artifacts is None
