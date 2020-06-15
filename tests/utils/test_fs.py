import os

from ebonite.utils import fs
from ebonite.utils.fs import switch_curdir


def test_module_path():
    assert fs.get_lib_path(os.path.join('utils', 'fs.py')) == fs.__file__


def test_module_dir_path():
    assert fs.current_module_path('test_fs.py') == __file__


def test_switch_curdir(tmp_path):
    with open(os.path.join(tmp_path, 'a'), 'w'):
        pass
    assert not os.path.exists('a')
    with switch_curdir(tmp_path):
        assert os.path.exists('a')
    assert not os.path.exists('a')
