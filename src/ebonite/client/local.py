import os
import shutil

from ebonite.client import Ebonite
from ebonite.client.base import ebonite_client
from ebonite.repository.artifact.local import LocalArtifactRepository
from ebonite.repository.metadata.local import LocalMetadataRepository

DEFAULT_LOCAL_STORE = '.ebonite'


@ebonite_client('local')
class LocalClient(Ebonite):
    """
    Ebonite client that stores metadata and artifacts on local filesystem

    :param path: path to storage dir. If None, store everything inmemory
    :param clear: if True, erase previous data from storage
    """
    def __init__(self, path=None, clear=False):
        self.path = path or DEFAULT_LOCAL_STORE
        if clear:
            self._clear()
        meta_repo = LocalMetadataRepository(os.path.join(self.path, 'metadata.json'))
        artifact_repo = LocalArtifactRepository(os.path.join(self.path, 'artifacts'))
        super().__init__(meta_repo, artifact_repo)

    def _clear(self):
        if os.path.exists(self.path):
            shutil.rmtree(self.path)
