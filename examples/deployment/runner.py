from ebonite.ext.docker import DockerContainer, DockerEnv, DockerRegistry
from ebonite.ext.docker.builder import DockerImage
from ebonite.ext.docker.runner import DockerRunner


def run_detached_and_remove():
    container_name = 'test'

    img_registry = DockerRegistry()
    img = DockerImage('test_broken_image', registry=img_registry)
    instance = DockerContainer(container_name)
    host = DockerEnv()

    runner = DockerRunner()
    runner.run(instance, img, host, detach=True, rm=True)


def run_detached():
    container_name = 'test'

    img_registry = DockerRegistry()
    img = DockerImage('test_broken_image', registry=img_registry)
    instance = DockerContainer(container_name, port_mapping={80: 8080})
    host = DockerEnv()

    runner = DockerRunner()
    runner.run(instance, img, host, detach=True, rm=False)


def run_attached_and_remove():
    container_name = 'test'

    img_registry = DockerRegistry()
    img = DockerImage('test_broken_image', registry=img_registry)
    instance = DockerContainer(container_name, port_mapping={80: 8080})
    host = DockerEnv()

    runner = DockerRunner()
    runner.run(instance, img, host, detach=False, rm=True)


def run_attached():
    container_name = 'test'

    img_registry = DockerRegistry()
    img = DockerImage('test_broken_image', registry=img_registry)
    instance = DockerContainer(container_name, port_mapping={80: 8080})
    host = DockerEnv()

    runner = DockerRunner()
    runner.run(instance, img, host, detach=False, rm=False)


def run_good():
    container_name = 'test'

    img_registry = DockerRegistry()
    img = DockerImage('mike0sv/ebaklya', registry=img_registry)
    instance = DockerContainer(container_name, port_mapping={80: 8080})
    host = DockerEnv()

    runner = DockerRunner()
    runner.run(instance, img, host, detach=True, rm=True)

    for a in runner.logs(instance, host):
        print(a)


def run_good_attached():
    container_name = 'test'

    img_registry = DockerRegistry()
    img = DockerImage('mike0sv/ebaklya', registry=img_registry)
    instance = DockerContainer(container_name, port_mapping={80: 8080})
    host = DockerEnv()

    runner = DockerRunner()
    runner.run(instance, img, host, detach=False, rm=True)


if __name__ == '__main__':
    run_good_attached()
