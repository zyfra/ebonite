import contextlib
import io
import os
import shutil
import sys
import tempfile
import typing
from abc import abstractmethod
from copy import copy

from pyjackson.core import Unserializable
from pyjackson.decorators import make_string, type_field

from ebonite.core.objects.base import EboniteParams

StreamContextManager = typing.Iterable[typing.BinaryIO]


@type_field('type')
class Blob(EboniteParams):
    """
    This class is a base class for blobs.
    Blob is a binary payload, which can be accessed either through
    :meth:`~Blob.bytestream` context manager, which returns file-like object, or through
    :meth:`~Blob.materialize` method, which places a file in local fs

    Must be pyjackson-able or marked Unserializable
    """
    type = None

    @abstractmethod
    def materialize(self, path):
        """
        Implementation must write blob's payload as a file to local fs

        :param path: path to write file
        """
        pass

    @abstractmethod
    @contextlib.contextmanager
    def bytestream(self) -> StreamContextManager:
        """
        Implementation must be a context manager (using @contextlib.contextmanager decorator)
        that returns file-like object with blob's payload

        :yields: file-like object
        """
        pass

    def bytes(self) -> bytes:
        """
        Returns blob's bytes

        :return: bytes
        """
        with self.bytestream() as bs:
            return bs.read()


class LocalFileBlob(Blob):
    """
    Blob implementation for local file

    :param path: path to local file
    """
    type = 'local_file'

    def __init__(self, path: str):
        self.path = path

    def materialize(self, path):
        """
        Copies local file to another path

        :param path: target path
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        shutil.copy(self.path, path)

    @contextlib.contextmanager
    def bytestream(self) -> StreamContextManager:
        """
        Opens file for reading

        :return: file handler
        """
        with open(self.path, 'rb') as f:
            yield f


# noinspection PyAbstractClass
class MaterializeOnlyBlobMixin(Blob):
    """
    Mixin for blobs which always have to be materialized first
    """

    def _get_file_name(self):
        return 'blob'

    @contextlib.contextmanager
    def bytestream(self) -> StreamContextManager:
        """
        Materializes blob to temporary dir and returns it's file handler

        :return: file handler
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, self._get_file_name())
            self.materialize(path)
            with open(path, 'rb') as f:
                yield f


class InMemoryBlob(Blob, Unserializable):
    """
    Blob implementation for in-memory bytes

    :param payload: bytes
    """
    type = 'inmemory'

    def __init__(self, payload: bytes):
        self.payload = payload

    def materialize(self, path):
        """
        Writes payload to path

        :param path: target path
        """
        with open(path, 'wb') as f:
            f.write(self.payload)

    @contextlib.contextmanager
    def bytestream(self) -> StreamContextManager:
        """
        Creates BytesIO object from bytes

        :yields: file-like object
        """
        yield io.BytesIO(self.payload)


@type_field('type')
class ArtifactCollection(EboniteParams):
    """
    Base class for artifact collection.
    Artifact collection is a number of named artifacts, represented by Blob's

    Must be pyjackson-able
    """
    type = None

    @abstractmethod
    def materialize(self, path):
        """
        Implementation must write artifacts payload to local fs

        :param path: dir to write blobs
        """
        pass

    @abstractmethod
    def bytes_dict(self) -> typing.Dict[str, bytes]:
        """
        Implementation must return a dict of artifact name -> artifact payload

        :returns: dict of artifact names -> artifact payloads
        """
        pass

    @abstractmethod
    def blob_dict(self) -> typing.ContextManager[typing.Dict[str, Blob]]:
        """
        Implementation must be a context manager (using `@contextlib.contexmanager` decorator) that yields a dict of
        artifact name -> blob

        :yields: dict of artifact name -> blob
        """
        pass

    def __add__(self, other):
        """
        Creates a :py:class:`CompositeArtifactCollection` with union of artifacts from self and other ArtifactCollection

        :param other:
        :return:
        """
        if not isinstance(other, ArtifactCollection):
            raise ValueError('Cant and {} to ArtifactCollection'.format(other))
        return CompositeArtifactCollection([self, other])


@make_string
class Blobs(ArtifactCollection):
    """
    Artifact collection represented by a dictionary of blobs

    :param blobs: dict of name -> blob
    """
    type = 'blobs'

    def __init__(self, blobs: typing.Dict[str, Blob]):
        self.blobs = blobs

    def materialize(self, path):
        """
        Materializes artifacts to path

        :param path: target dir
        """
        os.makedirs(path, exist_ok=True)
        for name, blob in self.blobs.items():
            blob.materialize(os.path.join(path, name))

    def bytes_dict(self) -> typing.Dict[str, bytes]:
        return {name: b.bytes() for name, b in self.blobs.items()}

    @contextlib.contextmanager
    def blob_dict(self) -> typing.ContextManager[typing.Dict[str, Blob]]:
        """
        :yields: self.blobs
        """
        yield self.blobs


def _enter_all_cm(managers):
    entered = []
    dicts = []
    try:
        for m in managers:
            dicts.append(m.__enter__())
            entered.append(m)
    except Exception as e:
        for m in reversed(entered):
            try:
                m.__exit__(type(e), e, sys.exc_traceback)
            except Exception as e2:
                e = e2
        raise e
    return dicts


class _ExitAllCm:
    def __init__(self, managers):
        self.managers = managers

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        for m in reversed(self.managers):
            try:
                m.__exit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                exc_type, exc_val, exc_tb = type(e), e, sys.exc_traceback


class CompositeArtifactCollection(ArtifactCollection):
    """
    Represents a merger of two or more ArtifactCollections

    :param artifacts: ArtifactCollections to merge
    """
    type = 'composite'

    def __init__(self, artifacts: typing.List[ArtifactCollection]):
        self.artifacts = artifacts

    def materialize(self, path):
        """
        Materializes every ArtifactCollection to path

        :param path: taget dir
        """
        for a in self.artifacts:
            a.materialize(path)

    def bytes_dict(self) -> typing.Dict[str, bytes]:
        return {k: v for a in self.artifacts for k, v in a.bytes_dict().items()}

    @contextlib.contextmanager
    def blob_dict(self) -> typing.ContextManager[typing.Dict[str, Blob]]:
        """
        Enters all ArtifactCollections blob_dict context managers and returns their union

        :yields: name -> blob mapping
        """
        managers: typing.List[typing.ContextManager] = [a.blob_dict() for a in self.artifacts]
        dicts = _enter_all_cm(managers)
        with _ExitAllCm(managers):
            yield {name: blob for d in dicts for name, blob in d.items()}

    def __add__(self, other):
        if not isinstance(other, ArtifactCollection):
            raise ValueError('Cant and {} to ArtifactCollection'.format(other))
        arts = copy(self.artifacts)
        if isinstance(other, CompositeArtifactCollection):
            arts += other.artifacts
        else:
            arts.append(other)
        return CompositeArtifactCollection(arts)

    def __iadd__(self, other):
        if not isinstance(other, ArtifactCollection):
            raise ValueError('Cant and {} to ArtifactCollection')
        if isinstance(other, CompositeArtifactCollection):
            self.artifacts += other.artifacts
        else:
            self.artifacts.append(other)


class _RelativePathWrapper(ArtifactCollection):
    """
    ArtifactCollection that adds path as a parent dir to every artifact

    :param path: parent dir
    """
    type = 'relative'

    def __init__(self, artifact: ArtifactCollection, path: str):
        self.artifact = artifact
        self.path = path

    def materialize(self, path):
        return self.artifact.materialize(os.path.join(path, self.path))

    def bytes_dict(self) -> typing.Dict[str, bytes]:
        return {os.path.join(p, self.path): b for p, b in self.artifact.bytes_dict().items()}

    @contextlib.contextmanager
    def blob_dict(self) -> typing.Iterable[typing.Dict[str, Blob]]:
        with self.artifact.blob_dict() as blobs:
            yield {os.path.join(p, self.path): b for p, b in blobs.items()}
