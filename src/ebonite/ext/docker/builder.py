from ebonite.build.builder.base import BuilderBase
from ebonite.build.helpers import validate_kwargs
from ebonite.core.objects.core import Buildable
from ebonite.ext.docker.build_context import DockerBuildArgs, DockerBuildContext

from .base import DockerEnv, DockerImage


class DockerBuilder(BuilderBase):
    """Builder implementation to build docker images"""
    @validate_kwargs
    def create_image(self, name: str, environment: DockerEnv, tag: str = 'latest', repository: str = None,
                     **kwargs) -> DockerImage:
        return DockerImage(name, tag, repository, environment.registry)

    @validate_kwargs(allowed_funcs=[DockerBuildArgs.__init__])
    def build_image(self, buildable: Buildable, image: DockerImage, environment: DockerEnv,
                    force_overwrite=False, **kwargs):
        context = DockerBuildContext(buildable.get_provider(), image, force_overwrite=force_overwrite, **kwargs)
        docker_image = context.build(environment)
        image.image_id = docker_image.id

    @validate_kwargs
    def delete_image(self, image: DockerImage, environment: DockerEnv, force=False, **kwargs):
        with environment.daemon.client() as client:
            image.delete(client, force, **kwargs)

    @validate_kwargs
    def image_exists(self, image: DockerImage, environment: DockerEnv, **kwargs) -> bool:
        with environment.daemon.client() as client:
            return image.exists(client)
