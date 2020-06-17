from ebonite import Ebonite, create_model


def model_function(data):
    """Dummy function is our model"""
    return data


def main():
    ebnt = Ebonite.local(clear=True)
    task = ebnt.get_or_create_task('local_deployment', 'local_deployment')

    model = create_model(model_function, 0, model_name='dummy_function')
    task.add_model(model)

    image = ebnt.create_image(model, 'dummy_image', force_overwrite=True)

    instance = ebnt.create_instance(image, 'dummy_service')
    instance.run()
    for log in instance.logs(stream=True):
        try:
            print(log, end='')
        except KeyboardInterrupt:  # FIXME does not work since we stuck in generator
            break

    ebnt.delete_instance(instance)


if __name__ == '__main__':
    main()
