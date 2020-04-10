from typing import Union

from ebonite.build.docker import DockerContainer, DockerHost, DockerImage
from ebonite.build.runner.docker import DockerRunner


def run_docker_img(container_params: Union[str, DockerContainer], image_params: Union[str, DockerImage],
                   host_params: Union[str, DockerHost] = '', ports_mapping=None, detach=True):
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

    DockerRunner().run(_as_container(container_params, ports_mapping),
                       image_params, _as_host(host_params), detach=detach)


def is_docker_container_running(container_params: Union[str, DockerContainer],
                                host_params: Union[str, DockerHost] = '') -> bool:
    """
    Checks whether Docker container is running

    :param container_params: params (or simply name) of container to check running
    :param host_params: host params (or simply URI) to connect to Docker daemon on, if no given "localhost" is used
    :return: "is running" flag
    """
    return DockerRunner().is_running(_as_container(container_params), _as_host(host_params))


def stop_docker_container(container_params: Union[str, DockerContainer], host_params: Union[str, DockerHost] = ''):
    """
    Stops Docker container

    :param container_params: params (or simply name) of container to be stopped
    :param host_params: host params (or simply URI) to connect to Docker daemon on, if no given "localhost" is used
    :return: nothing
    """
    DockerRunner().stop(_as_container(container_params), _as_host(host_params))


def _as_container(container_params: Union[str, DockerContainer], ports_mapping=None):
    if isinstance(container_params, str):
        container_params = DockerContainer(container_params, ports_mapping)
    return container_params


def _as_host(host_params: Union[str, DockerHost]):
    if isinstance(host_params, str):
        host_params = DockerHost(host_params)
    return host_params
