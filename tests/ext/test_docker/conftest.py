import time

import docker.errors
import pytest
from testcontainers.core.container import DockerContainer as TestContainer

from ebonite.build.builder.base import use_local_installation
from ebonite.ext.docker import DockerEnv, RemoteRegistry
from ebonite.ext.docker.base import DockerDaemon

EXTERNAL_REGISTRY_PORT = 2374
INTERNAL_REGISTRY_PORT = 5000
DAEMON_PORT = 2375


@pytest.fixture(scope='session')
def dockerenv_local():
    with use_local_installation():
        yield DockerEnv()


@pytest.fixture(scope='session')
def dind():
    with (TestContainer('docker:dind')
            .with_env('DOCKER_TLS_CERTDIR', '')
            .with_kargs(privileged=True)
            .with_exposed_ports(DAEMON_PORT)
            .with_bind_ports(EXTERNAL_REGISTRY_PORT, EXTERNAL_REGISTRY_PORT)) as daemon:
        time.sleep(1)
        yield daemon


@pytest.fixture(scope='session')
def docker_daemon(dind):
    return DockerDaemon(f'localhost:{dind.get_exposed_port(DAEMON_PORT)}')


@pytest.fixture(scope='session')
def docker_registry(dind, docker_daemon):
    with docker_daemon.client() as c:
        c: docker.DockerClient
        c.containers.run('registry:latest', ports={INTERNAL_REGISTRY_PORT: EXTERNAL_REGISTRY_PORT},
                         detach=True, remove=True,
                         environment={'REGISTRY_STORAGE_DELETE_ENABLED': 'true'})
        yield RemoteRegistry(f'localhost:{EXTERNAL_REGISTRY_PORT}')


@pytest.fixture(scope='session')
def dockerenv_remote(docker_registry, docker_daemon):
    with use_local_installation():
        yield DockerEnv(registry=docker_registry, daemon=docker_daemon)
