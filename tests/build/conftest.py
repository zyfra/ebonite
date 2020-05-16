import os
import socket

import docker.errors
import pytest

from ebonite.build.docker import create_docker_client, is_docker_running
from ebonite.core.objects.core import Model
from ebonite.runtime.server import HTTPServerConfig
from tests.client.test_func import func


def has_docker():
    if os.environ.get('SKIP_DOCKER_TESTS', None) == 'true':
        return False
    return is_docker_running()


def has_local_image(img_name: str) -> bool:
    if not has_docker():
        return False
    with create_docker_client() as client:
        try:
            client.images.get(img_name)
        except docker.errors.ImageNotFound:
            return False
    return True


def rm_container(container_name: str, host: str = ''):
    with create_docker_client(host) as client:
        containers = client.containers.list()
        if any(container_name == c.name for c in containers):
            client.containers.get(container_name).remove(force=True)


def rm_image(image_tag: str, host: str = ''):
    with create_docker_client(host) as client:
        tags = [t for i in client.images.list() for t in i.tags]
        if any(image_tag == t for t in tags):
            client.images.remove(image_tag, force=True)


@pytest.fixture
def model():
    model = Model.create(func, "kek", "Test Model")
    return model


def check_ebonite_port_free():
    host, port = HTTPServerConfig.host, HTTPServerConfig.port
    s = socket.socket()
    # With this option `bind` will fail only if other process actively listens on port
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((host, port))
    except OSError:
        raise OSError(f'Ebonite services start at port {port} but it\'s used by other process') from None
    finally:
        s.close()
