from typing import Union

import ebonite
from ebonite.build.provider.ml_model import MLModelProvider
from ebonite.build.runner.docker import DockerImage, DockerRunner, DockerRuntimeInstance
from ebonite.core.objects import core
from ebonite.runtime.server import Server
from ebonite.utils.importing import module_importable


def build_model_docker(image_params: Union[str, DockerImage], model: 'core.Model', server: Server = None,
                       force_overwrite=False, debug=False, **kwargs) -> 'core.Image':
    """
    Builds docker image from Model instance

    :param image_params: params (or simply name) for docker image to be built
    :param model: model to create image
    :param server: server instance to wrap model
    :param force_overwrite: force overwrite image if it exists
    :param debug: run server in debug mode
    :param kwargs: same as in :meth:`~ebonite.build.builder.docker_builder.DockerBuilder.__init__`
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

    from ebonite.build.builder.docker_builder import DockerBuilder, is_docker_running

    if not is_docker_running():
        raise RuntimeError("Docker is unavailable")

    provider = MLModelProvider(model, server, debug)
    builder = DockerBuilder(provider, image_params, force_overwrite, **kwargs)
    image = builder.build()
    image.model = model
    return image


def run_docker_img(container_name: str, image_params: Union[str, DockerImage],
                   target_uri='', ports_mapping=None, detach=True):
    """
    Runs Docker image as container

    :param container_name: expected name of container to be run
    :param image_params: params (or simply name) for docker image to be run
    :param target_uri: host URI to connect to Docker daemon on, if no given "localhost" is used
    :param ports_mapping: mapping of exposed ports in container
    :param detach: if `False` block execution until container exits
    :return: nothing
    """
    if isinstance(image_params, str):
        image_params = DockerImage(image_params)

    if ports_mapping is None:
        ports_mapping = {9000: 9000}

    runner = DockerRunner()
    service = DockerRuntimeInstance(container_name, image_params,
                                    target_uri=target_uri, ports_mapping=ports_mapping)
    runner.run(service, detach=detach)


def is_docker_container_running(container_name: str, target_uri='') -> bool:
    """
    Checks whether Docker container is running

    :param container_name: name of container to be stopped
    :param target_uri: host URI to connect to Docker daemon on, if no given "localhost" is used
    :return: "is running" flag
    """
    runner = DockerRunner()
    service = DockerRuntimeInstance(container_name, None, target_uri=target_uri)
    return runner.is_running(service)


def stop_docker_container(container_name: str, target_uri=''):
    """
    Stops Docker container

    :param container_name: name of container to be stopped
    :param target_uri: host URI to connect to Docker daemon on, if no given "localhost" is used
    :return: nothing
    """
    runner = DockerRunner()
    service = DockerRuntimeInstance(container_name, None, target_uri=target_uri)
    runner.stop(service)


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

    image = ebnt.build_service(service_name, model)

    if run_service:
        ebnt.run_service(service_name, image, detach=detach)
