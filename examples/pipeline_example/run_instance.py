from ebonite import Ebonite, create_model
from ebonite.build.builder.base import use_local_installation
from ebonite.ext.flask import FlaskServer


def step1(data: str):
    return data * 2


def step2(data: str):
    return len(data)


def main():
    s1 = create_model(step1, 'a', 'step1')
    s2 = create_model(step2, 'a', 'step2')

    p = s1.as_pipeline().append(s2)

    ebnt = Ebonite.local(clear=True)
    task = ebnt.get_or_create_task('a', 'b')
    task.push_model(s1)
    task.push_model(s2)
    task.add_pipeline(p)
    with use_local_installation():
        image = ebnt.build_image('ebnt_pipeline_test', p, task, FlaskServer(), force_overwrite=True)
        instance = ebnt.run_instance('ebnt_pipeline_test', image, server=FlaskServer())

        print(instance.is_running())

        ebnt.stop_instance(instance)


if __name__ == '__main__':
    main()
