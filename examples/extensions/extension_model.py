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
    model = ebnt.create_model('my_extended_model', 'model', 1)

    # your extension code will be inside docker image in form of files if you have local files
    # or requirement if you installed it from pip
    image = ebnt.create_image(model, 'local_ext_model', builder_args={'force_overwrite': True})

    ebnt.create_instance(image, 'local_ext_model').run(detach=False)


if __name__ == '__main__':
    main()
