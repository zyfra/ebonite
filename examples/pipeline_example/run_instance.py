from ebonite.build import DockerBuilder, DockerImage, DockerRunner, DockerContainer, DockerHost

from ebonite import create_model
from ebonite.build.builder.base import use_local_installation
from ebonite.build.provider.pipeline import PipelineProvider
from ebonite.ext.flask import FlaskServer


def step1(data: str):
    return data * 2


def step2(data: str):
    return len(data)


def main():
    s1 = create_model(step1, 'a', 'step1')
    s2 = create_model(step2, 'a', 'step2')

    p = s1.as_pipeline().append(s2)
    with use_local_installation():
        pp = PipelineProvider(p, FlaskServer())
        builder = DockerBuilder(pp, DockerImage('ebnt_pipeline_test'), True)

        image = builder.build()

        runner = DockerRunner()
        instance = DockerContainer('ebnt_pipeline_test', {9000: 9000})
        runner.run(instance, image.params, DockerHost(), detach=False)


if __name__ == '__main__':
    main()
