import io

import numpy as np
import pytest
from imageio import imsave

from ebonite.ext.imageio.helpers import filelike_image_input, filelike_image_output


@pytest.fixture
def numpy_image():
    return np.zeros((5, 5, 3))


@pytest.fixture
def filelike_image(numpy_image):
    buffer = io.BytesIO()
    imsave(buffer, numpy_image, format='PNG')
    buffer.seek(0)
    return buffer


def test_filelike_image_input(numpy_image, filelike_image):
    @filelike_image_input
    def inner(img):
        assert isinstance(img, np.ndarray)
        assert np.all(img == numpy_image)

    inner(filelike_image)


def test_filelike_image_output(numpy_image, filelike_image):
    @filelike_image_output
    def inner():
        return numpy_image

    assert inner().getvalue() == filelike_image.getvalue()
