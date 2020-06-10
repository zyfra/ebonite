import os
import re
import shutil
import sys
import tempfile

from jinja2 import Environment, FileSystemLoader

from ebonite.ext.docker import DockerIORegistry
from ebonite.ext.docker.utils import create_docker_client, image_exists_at_dockerhub, repository_tags_at_dockerhub
from ebonite.utils.log import logger


def prebuild_image(prebuild_path, name_template, python_version, *, push=False):
    tag = name_template.format(python_version)
    if image_exists_at_dockerhub(tag):
        logger.info('Skipped building image %s: already exists', tag)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        context_dir = os.path.join(tmpdir, 'context')
        logger.info('Building image %s on %s ...', tag, context_dir)

        shutil.copytree(prebuild_path, context_dir)
        _generate_dockerfile(context_dir, python_version)

        try:
            with create_docker_client() as client:
                client.images.build(path=context_dir, tag=tag, rm=True)

            logger.info('Successfully built image %s', tag)
        except Exception as e:
            logger.error('Failed to build image %s: %s', tag, e)
            return

    if push:
        with create_docker_client() as client:
            DockerIORegistry().login(client)
            client.images.push(tag)


def _generate_dockerfile(context_dir, python_version):
    j2 = Environment(loader=FileSystemLoader([context_dir]))
    docker_tmpl = j2.get_template('Dockerfile.j2')
    with open(os.path.join(context_dir, 'Dockerfile'), 'w') as df:
        df.write(docker_tmpl.render({'python_version': python_version}))


PY_BLACK_LIST = {'^2\\.', '^3\\.[0-5]\\.', '^3\\.6\\.[0-4]'}


def prebuild_missing_images(prebuild_path, name_template):
    if len(sys.argv) < 2:
        python_tags = repository_tags_at_dockerhub('python')
        python_versions = [tag for tag in python_tags if re.match('^[0-9]+\\.[0-9]+\\.[0-9]+$', tag)]
        python_versions = [tag for tag in python_versions if not any(re.match(pre, tag) for pre in PY_BLACK_LIST)]
        python_versions.sort()
    else:
        python_versions = sys.argv[1:]

    for python_version in python_versions:
        prebuild_image(prebuild_path, name_template, python_version, push=True)
