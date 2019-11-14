import typing
from abc import abstractmethod

from pyjackson.decorators import type_field

from ebonite.core.objects import core
from ebonite.core.objects.artifacts import ArtifactCollection, Blob


class ArtifactError(Exception):
    """
    Base class for exceptions in :class:`ArtifactRepository`
    """
    pass


class NoSuchArtifactError(ArtifactError):
    """
    Exception which is thrown if artifact is not found in the repository
    """
    def __init__(self, artifact_id, repo: 'ArtifactRepository'):
        super(NoSuchArtifactError, self).__init__('No artifact with id {} found in {}'.format(artifact_id, repo))


class ArtifactExistsError(ArtifactError):
    """
    Exception which is thrown if artifact already exists in the repository
    """
    def __init__(self, artifact_id, repo: 'ArtifactRepository'):
        super(ArtifactExistsError, self).__init__('Artifact with id {} already in {}'.format(artifact_id, repo))


@type_field('type')
class ArtifactRepository:
    """
    Base abstract class for persistent repositories of artifacts
    """

    type = None

    def get_model_id(self, model: 'core.Model') -> str:
        return model.id

    def push_artifacts(self, model: 'core.Model'):
        """
        Helper method which handles the most common model artifacts workflow.
        Based on :meth:`ArtifactRepository.push_artifact` and :meth:`core.Model.persist_artifacts` methods.

        :param model: model to store artifacts in the repository for
        :return: nothing
        """
        def _persister(artifact):
            with artifact.blob_dict() as files:
                return self.push_artifact(model, files)
        model.persist_artifacts(_persister)

    def push_artifact(self, model: 'core.Model', blobs: typing.Dict[str, Blob]) -> ArtifactCollection:
        """
        Stores given :class:`.Blob` artifacts in the repository and associates them with given model

        :param model: model to associate artifacts with
        :param blobs: artifacts to store in the repository
        :return: :class:`.ArtifactCollection` object containing stored artifacts
        :exception: :exc:`ArtifactExistsError` if there are already artifacts stored for this model
        """
        return self._push_artifact(self.get_model_id(model), blobs)

    def get_artifact(self, model: 'core.Model') -> ArtifactCollection:
        """
        Gets artifacts for given model

        :param model: model to get artifacts for
        :return: :class:`.ArtifactCollection` object containing stored artifacts
        :exception: :exc:`NoSuchArtifactError` if no artifacts were associated with given model
        """
        return self._get_artifact(self.get_model_id(model))

    def delete_artifact(self, model: 'core.Model'):
        """
        Deletes artifacts for given model

        :param model: model to delete artifacts for
        :return: nothing
        :exception: :exc:`NoSuchArtifactError` if no artifacts were associated with given model
        """
        self._delete_artifact(self.get_model_id(model))

    @abstractmethod
    def _push_artifact(self, model_id: str, blobs: typing.Dict[str, Blob]) -> ArtifactCollection:
        raise NotImplementedError

    @abstractmethod
    def _get_artifact(self, model_id: str) -> ArtifactCollection:
        raise NotImplementedError

    @abstractmethod
    def _delete_artifact(self, model_id: str):
        raise NotImplementedError


# noinspection PyAbstractClass
class RepoArtifactBlob(Blob):
    def __init__(self, repository: ArtifactRepository):
        self.repository = repository
