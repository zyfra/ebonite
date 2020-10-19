import contextlib
import inspect
import os


def get_lib_path(*filename):
    path = __file__
    for _ in range(len(__name__.split('.')) - 1):
        path = os.path.dirname(path)
    return os.path.join(path, *filename)


def current_module_path(*path):
    stack = inspect.stack()
    caller_path = stack[1][1]
    return os.path.join(os.path.dirname(caller_path), *path)


@contextlib.contextmanager
def switch_curdir(path):
    """Context manager to temproary switch current dir"""
    prev_path = os.path.abspath('.')
    try:
        try:
            os.chdir(path)
        except FileNotFoundError:
            pass
        yield
    finally:
        os.chdir(prev_path)
