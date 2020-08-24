import subprocess

from ebonite.ext.docker.base import DockerContainer, DockerEnv, DockerImage
from ebonite.ext.docker.runner import DockerRunner


class CvDockerRunner(DockerRunner):

    def run(self, instance: DockerContainer, image: DockerImage, env: DockerEnv, rm=True, detach=True, **kwargs):
        if not (isinstance(instance, DockerContainer) and isinstance(image, DockerImage) and
                isinstance(env, DockerEnv)):
            raise TypeError('DockerRunner works with DockerContainer, DockerImage and DockerHost only')

        gpus = kwargs.get('gpus')
        if gpus is None:
            gpus = 'all '

        ports = ''
        for exp, pub in instance.port_mapping.items():
            ports += f'-p {exp}:{pub} '

        if rm:
            rm = '--rm '
        else:
            rm = ''

        command = f"docker run --gpus {gpus} {rm} {ports} --name {instance.name} -d {image.uri}"
        subprocess.run(command.split())
