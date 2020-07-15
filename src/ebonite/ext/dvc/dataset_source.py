import contextlib

import dvc.api
from dvc.repo import Repo

from ebonite.core.objects.artifacts import Blob, Blobs, StreamContextManager
from ebonite.core.objects.dataset_source import DatasetSource
from ebonite.repository.dataset.artifact import ArtifactDatasetSource, DatasetReader


class DvcBlob(Blob):
    def __init__(self, path: str, repo: str = None, rev: str = None, remote: str = None, mode: str = 'r',
                 encoding: str = None):
        self.path = path
        self.repo = repo
        self.rev = rev
        self.remote = remote
        self.mode = mode
        self.encoding = encoding

    def materialize(self, path):
        Repo.get(self.remote, self.path, out=path, rev=self.rev)  # TODO tests

    @contextlib.contextmanager
    def bytestream(self) -> StreamContextManager:
        with dvc.api.open(self.path, self.repo, self.rev, self.remote, self.mode, self.encoding) as f:
            yield f


def create_dvc_source(path: str, reader: DatasetReader, repo, rev: str = None, remote: str = None, mode: str = 'r',
                      encoding: str = None) -> DatasetSource:
    artifacts = Blobs.from_blobs({path: DvcBlob(path, repo, rev, remote, mode, encoding)})
    return ArtifactDatasetSource(reader, artifacts)
