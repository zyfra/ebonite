"""This example shows how to create a model, that consumes binary object (image file).
This is useful for DL models."""

import numpy as np
import scipy.stats
from imageio import imread

import ebonite
from ebonite.ext.imageio import filelike_image_input, filelike_image_output
from ebonite.runtime import run_model_server


def add_alpha(img):
    """Adds alpha channel to image"""
    if img.shape[2] == 4:
        return img
    gray = img.mean(2).astype(np.int8)
    mode = scipy.stats.mode(gray).mode[0][0]
    mask = np.ones(img.shape[:2])
    #  set mode pixel to transparent (in our case, it's blue background)
    mask[np.abs(gray - mode) < 15] = 0
    return np.dstack([img, mask])


#  This is the overlay we will put on top of provided image
OVERLAY = imread('ebaklya.png')
OVERLAY = add_alpha(OVERLAY)


# use this decorator to mark that function consumes file-like objects
@filelike_image_input
def shape_model(im):
    """Returns image shape"""
    return np.array(im.shape)


# use this decorators to mark that function consumes and returns file-like objects
@filelike_image_input
@filelike_image_output
def overlay_model(im):
    """Puts OVERLAY on top of image """
    if im.shape[2] == 4:
        orig_mask = im[:, :, 3]
        im = im[:, :, :3]
    else:
        orig_mask = None
    x, y = (np.array(im.shape[:2]) - np.array(OVERLAY.shape[:2])) // 2
    x, y = max(0, x), max(0, y)
    ox, oy = im.shape[:2]
    sx, sy = OVERLAY.shape[:2]
    sx, sy = min(sx, ox), min(sy, oy)

    mask1d = OVERLAY[:sx, :sy, 3]
    mask = np.stack([mask1d for _ in range(3)], axis=2)
    inv_mask = 1. - mask
    im[x:x + sx, y:y + sy, :] = im[x:x + sx, y:y + sy, :] * inv_mask + OVERLAY[:sx, :sy, :-1] * mask
    if orig_mask is not None:
        im = np.dstack([im, orig_mask])
    return im


def main():
    # create model from function and file-like object as sample data
    with open('ebaklya.png', 'rb') as f:
        model = ebonite.create_model(overlay_model, f)

    # run flask service with this model
    run_model_server(model)
    # now you can use client.py to call this service or go to http://localhost:9000/apidocs to view swagger ui


if __name__ == '__main__':
    main()
