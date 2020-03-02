from ebonite.build.docker_objects import DefaultDockerRegistry, DockerImage
from ebonite.build.runner import DockerRunner, DockerServiceInstance
from ebonite.build.runner.base import LocalTargetHost


def run_detached_and_remove():
    container_name = 'test'

    img_registry = DefaultDockerRegistry()
    img = DockerImage('test_broken_image', registry=img_registry)
    host = LocalTargetHost()
    instance = DockerServiceInstance(container_name, img, host, {80: 8080})

    runner = DockerRunner()
    runner.run(instance, detach=True, rm=True)


def run_detached():
    container_name = 'test'

    img_registry = DefaultDockerRegistry()
    img = DockerImage('test_broken_image', registry=img_registry)
    host = LocalTargetHost()
    instance = DockerServiceInstance(container_name, img, host, {80: 8080})

    runner = DockerRunner()
    runner.run(instance, detach=True, rm=False)


def run_attached_and_remove():
    container_name = 'test'

    img_registry = DefaultDockerRegistry()
    img = DockerImage('test_broken_image', registry=img_registry)
    host = LocalTargetHost()
    instance = DockerServiceInstance(container_name, img, host, {80: 8080})

    runner = DockerRunner()
    runner.run(instance, detach=False, rm=True)


def run_attached():
    container_name = 'test'

    img_registry = DefaultDockerRegistry()
    img = DockerImage('test_broken_image', registry=img_registry)
    host = LocalTargetHost()
    instance = DockerServiceInstance(container_name, img, host, {80: 8080})

    runner = DockerRunner()
    runner.run(instance, detach=False, rm=False)


def run_good():
    container_name = 'test'

    img_registry = DefaultDockerRegistry()
    img = DockerImage('mike0sv/ebaklya', registry=img_registry)
    host = LocalTargetHost()
    instance = DockerServiceInstance(container_name, img, host, {80: 8080})

    runner = DockerRunner()
    service = runner.run(instance, detach=True, rm=True)

    for a in runner.logs(service):
        print(a)


def run_good_attached():
    container_name = 'test'

    img_registry = DefaultDockerRegistry()
    img = DockerImage('mike0sv/ebaklya', registry=img_registry)
    host = LocalTargetHost()
    instance = DockerServiceInstance(container_name, img, host, {80: 8080})

    runner = DockerRunner()
    runner.run(instance, detach=False, rm=True)


if __name__ == '__main__':
    run_good_attached()
