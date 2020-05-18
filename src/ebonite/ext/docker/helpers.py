import os
import time
from contextlib import contextmanager
from threading import Lock
from typing import Generator, Union

import docker
import requests
from docker.errors import DockerException

from ebonite.utils.log import logger

from .base import DockerContainer, DockerDaemon, DockerEnv, DockerImage, DockerRegistry, RemoteDockerRegistry


def login_to_registry(client: docker.DockerClient, registry: DockerRegistry):
    """
    Logs in to Docker registry (if it is remote).

    Corresponding credentials should be specified as environment variables per registry:
    e.g., if registry host is "168.32.25.1:5000" then
    "168_32_25_1_5000_USERNAME" and "168_32_25_1_5000_PASSWORD" variables should be specified

    :param client: Docker client instance
    :param registry: Docker registry descriptor
    :return: nothing
    """
    if isinstance(registry, RemoteDockerRegistry):
        host_for_env = registry.host.replace('.', '_').replace(':', '_')
        username_var = f'{host_for_env}_username'.upper()
        username = os.getenv(username_var)
        password_var = f'{host_for_env}_password'.upper()
        password = os.getenv(password_var)

        if username and password:
            client.login(registry=registry.host, username=username, password=password)
            logger.info('Logged in to remote registry at host %s', registry.host)
        else:
            logger.warning('Skipped logging in to remote registry at host %s because no credentials given. ' +
                           'You could specify credentials as %s and %s environment variables.',
                           registry.host, username_var, password_var)


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
def create_docker_client(docker_host: str = '', check=True) -> Generator[docker.DockerClient, None, None]:
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


def run_docker_img(container_params: Union[str, DockerContainer], image_params: Union[str, DockerImage],
                   host_params: Union[str, (DockerEnv)] = '', ports_mapping=None, detach=True):
    """
    Runs Docker image as container

    :param container_params: expected params (or simply name) of container to be run
    :param image_params: params (or simply name) for docker image to be run
    :param host_params: host params (or simply URI) to connect to Docker daemon on, if no given "localhost" is used
    :param ports_mapping: mapping of exposed ports in container
    :param detach: if `False` block execution until container exits
    :return: nothing
    """
    if isinstance(image_params, str):
        image_params = DockerImage(image_params)

    from .runner import DockerRunner
    DockerRunner().run(_as_container(container_params, ports_mapping),
                       image_params, _as_host(host_params), detach=detach)


def is_docker_container_running(container_params: Union[str, DockerContainer],
                                host_params: Union[str, DockerEnv] = '') -> bool:
    """
    Checks whether Docker container is running

    :param container_params: params (or simply name) of container to check running
    :param host_params: host params (or simply URI) to connect to Docker daemon on, if no given "localhost" is used
    :return: "is running" flag
    """
    from .runner import DockerRunner
    return DockerRunner().is_running(_as_container(container_params), _as_host(host_params))


def stop_docker_container(container_params: Union[str, DockerContainer], host_params: Union[str, DockerEnv] = ''):
    """
    Stops Docker container

    :param container_params: params (or simply name) of container to be stopped
    :param host_params: host params (or simply URI) to connect to Docker daemon on, if no given "localhost" is used
    :return: nothing
    """
    from .runner import DockerRunner
    DockerRunner().stop(_as_container(container_params), _as_host(host_params))


def _as_container(container_params: Union[str, DockerContainer], ports_mapping=None):
    if isinstance(container_params, str):
        container_params = DockerContainer(container_params, ports_mapping)
    return container_params


def _as_host(host_params: Union[str, DockerEnv]):
    if isinstance(host_params, str):
        host_params = DockerEnv(DockerRegistry(host_params), DockerDaemon(host_params))
    return host_params
