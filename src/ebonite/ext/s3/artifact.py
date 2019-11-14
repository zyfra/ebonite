import contextlib
import io
import os
import typing

import boto3
from botocore.exceptions import ClientError
from pyjackson.decorators import cached_property

from ebonite.config import Config, Param
from ebonite.core.objects.artifacts import ArtifactCollection, Blob, Blobs, StreamContextManager
from ebonite.repository.artifact import ArtifactExistsError, ArtifactRepository, NoSuchArtifactError
from ebonite.utils.log import logger


class S3Config(Config):
    ACCESS_KEY = Param('access_key', namespace='s3')
    SECRET_KEY = Param('secret_key', namespace='s3')


class _WithS3Client:
    def __init__(self, bucket_name: str, endpoint: str = None):
        self.bucket_name = bucket_name
        self.endpoint = endpoint

    @cached_property
    def _s3(self):
        logger.debug('Creating s3 client with endpoint %s', self.endpoint)
        return boto3.client('s3',
                            endpoint_url=self.endpoint,
                            aws_access_key_id=S3Config.ACCESS_KEY,
                            aws_secret_access_key=S3Config.SECRET_KEY)

    @cached_property
    def _s3_res(self):
        logger.debug('Creating s3 resource with endpoint %s', self.endpoint)
        return boto3.resource('s3',
                              endpoint_url=self.endpoint,
                              aws_access_key_id=S3Config.ACCESS_KEY,
                              aws_secret_access_key=S3Config.SECRET_KEY)


class S3Blob(Blob, _WithS3Client):
    """
    :class:`.Blob` implementation which stores artifacts in Amazon S3-compatible file system

    S3 credentials are to be specified through `S3_ACCESS_KEY` and `S3_SECRET_KEY` environment variables.

    :param: s3path: S3 path to the artifact represented by this object
    :param: bucket_name: name of S3 bucket to use for storage
    :param: endpoint: HTTP URL of S3 server to connect to
    """
    type = 's3'

    def __init__(self, s3path: str, bucket_name: str, endpoint: str = None):
        _WithS3Client.__init__(self, bucket_name, endpoint)
        self.s3path = s3path

    def materialize(self, path):
        logger.debug('Downloading file from %s to %s', self.s3path, path)
        self._s3.download_file(self.bucket_name, self.s3path, path)

    @contextlib.contextmanager
    def bytestream(self) -> StreamContextManager:
        logger.debug('Streaming file from %s', self.s3path)
        yield self._s3.get_object(Bucket=self.bucket_name, Key=self.s3path)['Body']


class S3ArtifactRepository(ArtifactRepository, _WithS3Client):
    """
    :class:`.ArtifactRepository` implementation which stores artifacts in Amazon S3-compatible file system

    S3 credentials are to be specified through `S3_ACCESS_KEY` and `S3_SECRET_KEY` environment variables.

    :param: bucket_name: name of S3 bucket to use for storage
    :param: endpoint: HTTP URL of S3 server to connect to
    """

    type = 's3'

    def _ensure_bucket(self):
        self._s3.create_bucket(Bucket=self.bucket_name)

    def _bucket_exists(self):
        try:
            self._s3.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError:
            return False

    def _list_blobs(self, prefix):
        bs = self._s3.list_objects(Bucket=self.bucket_name, Prefix=prefix)
        if 'Contents' not in bs:
            return {}
        return {o['Key']: o for o in bs['Contents']}

    def _get_artifact(self, model_id: str) -> ArtifactCollection:
        if not self._bucket_exists():
            raise NoSuchArtifactError(model_id, self)

        keys = list(self._list_blobs(model_id).keys())
        if len(keys) == 0:
            raise NoSuchArtifactError(model_id, self)
        elif len(keys) == 1 and keys[0] == '.':
            return Blobs({})
        else:
            return Blobs({
                os.path.relpath(key, model_id): S3Blob(key, self.bucket_name, self.endpoint)
                for key in keys
            })

    def _push_artifact(self, model_id: str, blobs: typing.Dict[str, Blob]) -> ArtifactCollection:
        self._ensure_bucket()

        if len(self._list_blobs(model_id)) > 0:
            raise ArtifactExistsError(model_id, self)

        if len(blobs) == 0:
            self._s3.upload_fileobj(io.BytesIO(b''), self.bucket_name, model_id)
            return Blobs({})

        result = {}
        for filepath, blob in blobs.items():
            join = os.path.join(model_id, filepath)
            with blob.bytestream() as b:
                logger.debug('Uploading %s to s3 %s/%s', blob, self.endpoint, self.bucket_name)
                self._s3.upload_fileobj(b, self.bucket_name, join)
            result[filepath] = S3Blob(join, self.bucket_name, self.endpoint)
        return Blobs(result)

    def _delete_artifact(self, model_id: str):
        if not self._bucket_exists():
            raise NoSuchArtifactError(model_id, self)
        keys = list(self._list_blobs(model_id).keys())
        if len(keys) == 0:
            raise NoSuchArtifactError(model_id, self)
        else:
            logger.debug('Deleting %s from %s/%s', model_id, self.endpoint, self.bucket_name)
            self._s3.delete_objects(Bucket=self.bucket_name, Delete={'Objects': [{'Key': k} for k in keys]})
