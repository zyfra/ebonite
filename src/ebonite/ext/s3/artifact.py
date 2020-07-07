import contextlib
import io
import os
import typing

import boto3
from botocore.exceptions import ClientError
from pyjackson.decorators import cached_property

from ebonite.config import Config, Core, Param
from ebonite.core.errors import ArtifactExistsError, NoSuchArtifactError
from ebonite.core.objects.artifacts import ArtifactCollection, Blob, Blobs, StreamContextManager
from ebonite.repository.artifact import ArtifactRepository
from ebonite.utils.log import logger


class S3Config(Config):
    namespace = 's3'
    ACCESS_KEY = Param('access_key')
    SECRET_KEY = Param('secret_key')


if Core.DEBUG:
    S3Config.log_params()


class _WithS3Client:
    def __init__(self, bucket_name: str, endpoint: str = None, region: str = None):
        self.bucket_name = bucket_name
        self.endpoint = endpoint
        self.region = region

    @cached_property
    def _s3(self):
        logger.debug('Creating s3 client with endpoint %s', self.endpoint)
        return boto3.client('s3',
                            endpoint_url=self.endpoint,
                            aws_access_key_id=S3Config.ACCESS_KEY,
                            aws_secret_access_key=S3Config.SECRET_KEY,
                            region_name=self.region)

    @cached_property
    def _s3_res(self):
        logger.debug('Creating s3 resource with endpoint %s', self.endpoint)
        return boto3.resource('s3',
                              endpoint_url=self.endpoint,
                              aws_access_key_id=S3Config.ACCESS_KEY,
                              aws_secret_access_key=S3Config.SECRET_KEY,
                              region_name=self.region)


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
        os.makedirs(os.path.dirname(path), exist_ok=True)
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
        if not self._bucket_exists():
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

    def get_artifact(self, artifact_type, artifact_id: str) -> ArtifactCollection:
        artifact_id = f'{artifact_type}/{artifact_id}'
        if not self._bucket_exists():
            raise NoSuchArtifactError(artifact_id, self)

        keys = list(self._list_blobs(artifact_id).keys())
        if len(keys) == 0:
            raise NoSuchArtifactError(artifact_id, self)
        elif len(keys) == 1 and keys[0] == '.':
            return Blobs({})
        else:
            return Blobs({
                os.path.relpath(key, artifact_id): S3Blob(key, self.bucket_name, self.endpoint)
                for key in keys
            })

    def push_artifact(self, artifact_type, artifact_id: str, blobs: typing.Dict[str, Blob]) -> ArtifactCollection:
        artifact_id = f'{artifact_type}/{artifact_id}'
        self._ensure_bucket()

        if len(self._list_blobs(artifact_id)) > 0:
            raise ArtifactExistsError(artifact_id, self)

        if len(blobs) == 0:
            self._s3.upload_fileobj(io.BytesIO(b''), self.bucket_name, artifact_id)
            return Blobs({})

        result = {}
        for filepath, blob in blobs.items():
            join = os.path.join(artifact_id, filepath)
            with blob.bytestream() as b:
                logger.debug('Uploading %s to s3 %s/%s', blob, self.endpoint, self.bucket_name)
                self._s3.upload_fileobj(b, self.bucket_name, join)
            result[filepath] = S3Blob(join, self.bucket_name, self.endpoint)
        return Blobs(result)

    def delete_artifact(self, artifact_type, artifact_id: str):
        artifact_id = f'{artifact_type}/{artifact_id}'
        if not self._bucket_exists():
            raise NoSuchArtifactError(artifact_id, self)
        keys = list(self._list_blobs(artifact_id).keys())
        if len(keys) == 0:
            raise NoSuchArtifactError(artifact_id, self)
        else:
            logger.debug('Deleting %s from %s/%s', artifact_id, self.endpoint, self.bucket_name)
            self._s3.delete_objects(Bucket=self.bucket_name, Delete={'Objects': [{'Key': k} for k in keys]})
