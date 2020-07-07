import typing

from ebonite.core.errors import ArtifactExistsError, NoSuchArtifactError
from ebonite.core.objects.artifacts import ArtifactCollection, Blob, Blobs, InMemoryBlob
from ebonite.repository.artifact import ArtifactRepository


class InMemoryArtifactRepository(ArtifactRepository):
    """
    :class:`.ArtifactRepository` implementation which stores artifacts in-memory
    """

    type = 'inmemory'

    def __init__(self):
        self._cache: typing.Dict[str, ArtifactCollection] = {}

    def get_artifact(self, artifact_type, artifact_id: str) -> ArtifactCollection:
        artifact_id = f'{artifact_type}/{artifact_id}'
        if artifact_id not in self._cache:
            raise NoSuchArtifactError(artifact_id, self)

        return self._cache[artifact_id]

    def push_artifact(self, artifact_type, artifact_id: str, blobs: typing.Dict[str, Blob]) -> ArtifactCollection:
        artifact_id = f'{artifact_type}/{artifact_id}'
        if artifact_id in self._cache:
            raise ArtifactExistsError(artifact_id, self)
        self._cache[artifact_id] = Blobs({
            k: InMemoryBlob(v.bytes()) for k, v in blobs.items()
        })
        return self._cache[artifact_id]

    def delete_artifact(self, artifact_type, artifact_id: str):
        artifact_id = f'{artifact_type}/{artifact_id}'
        if artifact_id not in self._cache:
            raise NoSuchArtifactError(artifact_id, self)
        del self._cache[artifact_id]
