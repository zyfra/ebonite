from ebonite import Ebonite, create_model
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
    image = ebnt.create_image(p, 'ebnt_pipeline_test', server=FlaskServer(), builder_args={'force_overwrite': True})
    instance = ebnt.create_instance(image, 'ebnt_pipeline_test', port_mapping={9000: 9000}).run(detach=True)

    print(f'Instance is running - {instance.is_running()}')

    ebnt.delete_instance(instance)

    print('Instance successfuly stopped and deleted')


if __name__ == '__main__':
    main()
