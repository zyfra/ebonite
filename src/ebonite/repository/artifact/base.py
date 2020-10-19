import typing
from abc import abstractmethod

from pyjackson.decorators import type_field

from ebonite.core.objects import core
from ebonite.core.objects.artifacts import ArtifactCollection, Blob


@type_field('type')
class ArtifactRepository:
    """
    Base abstract class for persistent repositories of artifacts
    """

    type = None
    MODEL_TYPE = 'model'

    def get_model_id(self, model: 'core.Model') -> str:
        model_id = model.id
        if model_id is None:
            raise ValueError('model_id cannot be "None"')
        return str(model_id)

    def push_model_artifacts(self, model: 'core.Model'):
        """
        Helper method which handles the most common model artifacts workflow.
        Based on :meth:`.ArtifactRepository.push_artifact` and :meth:`.core.Model.persist_artifacts` methods.

        :param model: model to store artifacts in the repository for
        :return: nothing
        """

        def _persister(artifact):
            with artifact.blob_dict() as files:
                return self.push_model_artifact(model, files)

        model.persist_artifacts(_persister)
        model.bind_artifact_repo(self)

    def push_model_artifact(self, model: 'core.Model', blobs: typing.Dict[str, Blob]) -> ArtifactCollection:
        """
        Stores given :class:`.Blob` artifacts in the repository and associates them with given model

        :param model: model to associate artifacts with
        :param blobs: artifacts to store in the repository
        :return: :class:`.ArtifactCollection` object containing stored artifacts
        :exception: :exc:`.ArtifactExistsError` if there are already artifacts stored for this model
        """
        model.bind_artifact_repo(self)
        return self.push_artifact(self.MODEL_TYPE, self.get_model_id(model), blobs)

    def get_model_artifact(self, model: 'core.Model') -> ArtifactCollection:
        """
        Gets artifacts for given model

        :param model: model to get artifacts for
        :return: :class:`.ArtifactCollection` object containing stored artifacts
        :exception: :exc:`.NoSuchArtifactError` if no artifacts were associated with given model
        """
        return self.get_artifact(self.MODEL_TYPE, self.get_model_id(model))

    def delete_model_artifact(self, model: 'core.Model'):
        """
        Deletes artifacts for given model

        :param model: model to delete artifacts for
        :return: nothing
        :exception: :exc:`.NoSuchArtifactError` if no artifacts were associated with given model
        """
        self.delete_artifact(self.MODEL_TYPE, self.get_model_id(model))
        model.unbind_artifact_repo()

    @abstractmethod
    def push_artifact(self, artifact_type: str, artifact_id: str, blobs: typing.Dict[str, Blob]) -> ArtifactCollection:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def get_artifact(self, artifact_type: str, artifact_id: str) -> ArtifactCollection:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def delete_artifact(self, artifact_type: str, artifact_id: str):
        raise NotImplementedError  # pragma: no cover


# noinspection PyAbstractClass
class RepoArtifactBlob(Blob):
    def __init__(self, repository: ArtifactRepository):
        self.repository = repository
