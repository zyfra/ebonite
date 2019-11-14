import typing

from ebonite.core.objects.artifacts import ArtifactCollection, Blob, Blobs
from ebonite.repository.artifact import ArtifactRepository
from ebonite.repository.artifact.base import ArtifactExistsError, NoSuchArtifactError


class InMemoryArtifactRepository(ArtifactRepository):
    """
    :class:`.ArtifactRepository` implementation which stores artifacts in-memory
    """

    type = 'inmemory'

    def __init__(self):
        self._cache: typing.Dict[str, ArtifactCollection] = {}

    def _get_artifact(self, model_id: str) -> ArtifactCollection:
        if model_id not in self._cache:
            raise NoSuchArtifactError(model_id, self)

        return self._cache[model_id]

    def _push_artifact(self, model_id: str, blobs: typing.Dict[str, Blob]) -> ArtifactCollection:
        if model_id in self._cache:
            raise ArtifactExistsError(model_id, self)
        self._cache[model_id] = Blobs(blobs)
        return self._cache[model_id]

    def _delete_artifact(self, model_id: str):
        if model_id not in self._cache:
            raise NoSuchArtifactError(model_id, self)
        del self._cache[model_id]
