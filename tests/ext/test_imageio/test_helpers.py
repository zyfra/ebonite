import io

import numpy as np
import pytest
from imageio import imsave

from ebonite.ext.imageio.helpers import bytes_image_input, bytes_image_output


@pytest.fixture
def numpy_image():
    return np.zeros((5, 5, 3))


@pytest.fixture
def bytes_image(numpy_image):
    buffer = io.BytesIO()
    imsave(buffer, numpy_image, format='PNG')
    return buffer.getvalue()


def test_bytes_image_input(numpy_image, bytes_image):
    @bytes_image_input
    def inner(img):
        assert isinstance(img, np.ndarray)
        assert np.all(img == numpy_image)
        return img

    assert np.all(inner(bytes_image) == inner(bytes_image))


def test_bytes_image_output(numpy_image, bytes_image):
    @bytes_image_output
    def inner():
        return numpy_image

    assert inner() == bytes_image
