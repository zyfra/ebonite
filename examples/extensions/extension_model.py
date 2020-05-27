"""This module shows how to load extensions from local code"""

import ebonite


def main():
    # load extension
    # you just use plain module name, if it's installed from pip
    # or, you can just directly import your classes
    # to automatically load extension on startup, set EBONITE_EXTENSIONS env variable
    ebonite.load_extensions('myext.extension_source')

    # set up client
    ebnt = ebonite.Ebonite.local(clear=True)

    # create a model using myext extension
    model = ebnt.create_model('ahaha', 1, 'model')

    # your extension code will be inside docker image in form of files if you have local files
    # or requirement if you installed it from pip
    image = ebnt.create_image('local_ext_model', model, force_overwrite=True)

    ebnt.create_instance('local_ext_model', image).run(detach=False)


if __name__ == '__main__':
    main()
