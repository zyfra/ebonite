from typing import Union

import ebonite
from ebonite.build.docker import DockerContainer, DockerHost, DockerImage
from ebonite.build.provider.ml_model import MLModelProvider
from ebonite.build.runner.docker import DockerRunner
from ebonite.core.objects import Image, Model
from ebonite.runtime.server import Server
from ebonite.utils.importing import module_importable


def build_model_docker(image_params: Union[str, DockerImage], model: Model, server: Server = None,
                       force_overwrite=False, debug=False, **kwargs) -> Image:
    """
    Builds docker image from Model instance

    :param image_params: params (or simply name) for docker image to be built
    :param model: model to create image
    :param server: server instance to wrap model
    :param force_overwrite: force overwrite image if it exists
    :param debug: run server in debug mode
    :param kwargs: same as in :meth:`~ebonite.build.builder.docker.DockerBuilder.__init__`
    :return built image
    """
    if isinstance(image_params, str):
        image_params = DockerImage(image_params)

    if server is None:
        from ebonite.ext.flask import FlaskServer
        server = FlaskServer()

    if not module_importable('docker'):
        raise RuntimeError("Can't build docker container: docker module is not installed. Install it "
                           "with 'pip install docker'")

    from ebonite.build.builder.docker import DockerBuilder
    from ebonite.build.docker import is_docker_running

    if not is_docker_running():
        raise RuntimeError("Docker is unavailable")

    provider = MLModelProvider(model, server, debug)
    builder = DockerBuilder(provider, image_params, force_overwrite, **kwargs)
    image = builder.build()
    image.model = model
    return image


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


def create_service_from_model(model_name: str, model_object, model_input, *,
                              project_name: str = 'default_project', task_name: str = 'default_project',
                              service_name: str = None, run_service: bool = False, detach=True):
    """
    This function does full default Ebonite's pipeline.
    Creates model, pushes it, wraps with a server, builds the docker image and runs it locally (if needed).

    :param model_name: model name to create.
    :param model_object: object containing model.
    :param model_input: model input.
    :param project_name: project name.
    :param task_name: task name.
    :param service_name: service name. Use model_name if not provided.
    :param run_service: run wrapped model with docker container if provided.
    :param detach: if `False` block execution until service exits
    """
    service_name = service_name or model_name
    ebnt = ebonite.Ebonite.inmemory()

    t = ebnt.get_or_create_task(project_name, task_name)
    model = t.create_and_push_model(model_object, model_input, model_name)

    image = ebnt.build_image(service_name, model)

    if run_service:
        ebnt.run_instance(service_name, image, detach=detach)
