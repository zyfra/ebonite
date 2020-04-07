"""This module shows how to load extensions from local code"""

import ebonite
from ebonite.build.builder.base import use_local_installation


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
        image = ebnt.build_image('local_ext_model', model, force_overwrite=True)

    ebnt.run_instance('local_ext_model', image, detach=False)


if __name__ == '__main__':
    main()
