from ebonite import Ebonite, create_model


def model_function(data):
    """Dummy function is our model"""
    return data


def main():
    ebnt = Ebonite.local(clear=True)
    task = ebnt.get_or_create_task('local_deployment', 'local_deployment')

    model = create_model(model_function, 0, model_name='dummy_function')
    task.add_model(model)

    image = ebnt.build_image('dummy_image', model, force_overwrite=True)

    service = ebnt.run_instance('dummy_service', image)

    for log in service.logs(stream=True):
        try:
            print(log, end='')
        except KeyboardInterrupt:  # FIXME does not work since we stuck in generator
            break

    ebnt.stop_instance(service)


if __name__ == '__main__':
    main()
