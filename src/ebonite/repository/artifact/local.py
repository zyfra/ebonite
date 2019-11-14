import glob
import os
import shutil
import typing

from ebonite.core.objects.artifacts import ArtifactCollection, Blob, Blobs, LocalFileBlob
from ebonite.repository.artifact import ArtifactExistsError, ArtifactRepository, NoSuchArtifactError
from ebonite.utils.fs import get_lib_path
from ebonite.utils.log import logger


class LocalArtifactRepository(ArtifactRepository):
    """
    :class:`.ArtifactRepository` implementation which stores artifacts in a local file system as directory

    :param: path: path to directory where artifacts are to be stored,
    if `None` "local_storage" directory in Ebonite distribution is used
    """
    type = 'local'

    def __init__(self, path: str = None):
        self.path = os.path.abspath(path or get_lib_path('local_storage'))

    def _get_artifact(self, model_id: str) -> ArtifactCollection:
        path = os.path.join(self.path, model_id)
        if not os.path.exists(path):
            raise NoSuchArtifactError(model_id, self)
        return Blobs({
            os.path.relpath(file, path): LocalFileBlob(os.path.join(self.path, file)) for file in
            glob.glob(os.path.join(path, '**'), recursive=True) if os.path.isfile(file)
        })

    def _push_artifact(self, model_id: str, blobs: typing.Dict[str, Blob]) -> ArtifactCollection:
        path = os.path.join(self.path, model_id)
        if os.path.exists(path):
            raise ArtifactExistsError(model_id, self)

        os.makedirs(path, exist_ok=True)
        result = {}
        for filepath, blob in blobs.items():
            join = os.path.join(path, filepath)
            os.makedirs(os.path.dirname(join), exist_ok=True)
            logger.debug('Writing artifact %s to %s', blob, join)
            blob.materialize(join)
            result[filepath] = LocalFileBlob(join)
        return Blobs(result)

    def _delete_artifact(self, model_id: str):
        path = os.path.join(self.path, model_id)
        if not os.path.exists(path):
            raise NoSuchArtifactError(model_id, self)
        logger.debug('Removing artifact %s', path)
        shutil.rmtree(path)
