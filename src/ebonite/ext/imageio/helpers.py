import io
from functools import wraps

from imageio import imread, imsave


def filelike_image_input(f):
    """
    Decorator which marks that function consumes images stored as file-like objects.

    :param f: function to decorate
    :return: decorated function
    """
    @wraps(f)
    def inner(filelike):
        im = imread(filelike)
        return f(im)

    return inner


def filelike_image_output(f):
    """
    Decorator which marks that function returns images stored as file-like objects.

    :param f: function to decorate
    :return: decorated function
    """

    @wraps(f)
    def inner(*args, **kwargs):
        im = f(*args, **kwargs)
        buffer = io.BytesIO()
        imsave(buffer, im, format='PNG')
        buffer.seek(0)
        buffer.name = 'response.png'
        return buffer

    return inner
