import io
from functools import wraps

from imageio import imread, imsave


def bytes_image_input(f):
    """
    Decorator which marks that function consumes images stored as bytes objects.

    :param f: function to decorate
    :return: decorated function
    """
    @wraps(f)
    def inner(b):
        im = imread(b)
        return f(im)

    return inner


def bytes_image_output(f):
    """
    Decorator which marks that function returns images stored as bytes objects.

    :param f: function to decorate
    :return: decorated function
    """

    @wraps(f)
    def inner(*args, **kwargs):
        im = f(*args, **kwargs)
        buffer = io.BytesIO()
        imsave(buffer, im, format='PNG')
        return buffer.getvalue()

    return inner
