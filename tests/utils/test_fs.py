from os import path

from ebonite.utils import fs


def test_module_path():
    assert fs.get_lib_path(path.join('utils', 'fs.py')) == fs.__file__


def test_module_dir_path():
    assert fs.current_module_path('test_fs.py') == __file__
