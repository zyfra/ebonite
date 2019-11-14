"""This module shows how to load extensions from local code"""

import ebonite
from ebonite.build import build_model_docker, run_docker_img
from ebonite.build.builder.base import use_local_installation


def run_model(name):
    """This function creates a model using myext extension"""

    ebnt = ebonite.Ebonite.local(clear=True)

    t = ebnt.get_or_create_task('project', 'task')
    model = t.create_and_push_model('ahaha', 1, 'model')

    with use_local_installation():
        build_model_docker(name, model)

    run_docker_img(name, name)


def main():
    # load extension
    # you just use plain module name, if it's installed from pip
    # or, you can just directly import your classes
    # to automatically load extension on startup, set EBONITE_EXTENSIONS env variable
    ebonite.load_extensions('myext.extension_source')

    # set up client and task
    ebnt = ebonite.Ebonite.local(clear=True)
    task = ebnt.get_or_create_task('project', 'task')

    # create a model using myext extension
    model = task.create_and_push_model('ahaha', 1, 'model')

    with use_local_installation():
        # your extension code will be inside docker image in form of files
        # if you have local files, or requirement if you installed it from pip
        build_model_docker('local_ext_model', model, force_overwrite=True)

    run_docker_img('local_ext_model', 'local_ext_model')


if __name__ == '__main__':
    main()
