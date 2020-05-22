import os
import time
from contextlib import contextmanager
from threading import Lock

import docker
import requests
from docker.errors import DockerException


def _is_docker_running(client: docker.DockerClient) -> bool:
    """
    Check if docker binary and docker daemon are available

    :param client: DockerClient instance
    :return: true or false
    """
    try:
        client.info()
        return True
    except (ImportError, IOError, DockerException):
        return False


def is_docker_running() -> bool:
    """
    Check if docker binary and docker daemon are available

    :return: true or false
    """
    with create_docker_client(check=False) as c:
        return _is_docker_running(c)


_docker_host_lock = Lock()


@contextmanager
def create_docker_client(docker_host: str = '', check=True) -> docker.DockerClient:
    """
    Context manager for DockerClient creation

    :param docker_host: DOCKER_HOST arg for DockerClient
    :param check: check if docker is available
    :return: DockerClient instance
    """
    with _docker_host_lock:
        os.environ["DOCKER_HOST"] = docker_host  # The env var DOCKER_HOST is used to configure docker.from_env()
        client = docker.from_env()
    if check and not _is_docker_running(client):
        raise RuntimeError("Docker daemon is unavailable")
    try:
        yield client
    finally:
        client.close()


def image_exists_at_dockerhub(tag):
    repo, tag = tag.split(':')
    resp = requests.get(f'https://registry.hub.docker.com/v1/repositories/{repo}/tags/{tag}')
    time.sleep(1)  # rate limiting
    return resp.status_code == 200


def repository_tags_at_dockerhub(repo):
    resp = requests.get(f'https://registry.hub.docker.com/v1/repositories/{repo}/tags')
    time.sleep(1)  # rate limiting
    if resp.status_code != 200:
        return {}
    else:
        return {tag['name'] for tag in resp.json()}
