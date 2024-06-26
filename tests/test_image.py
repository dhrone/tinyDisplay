# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of Image Widget for the tinyDisplay system.

.. versionadded:: 0.0.1
"""
from pathlib import Path

from PIL import Image, ImageChops

from tinyDisplay.render.widget import image
from tinyDisplay.utility import compareImage, image2Text


def test_image_widget():
    """Create image widget and compare to reference image."""
    path = Path(__file__).parent / "reference/images/pydPiper_splash.png"
    img = Image.open(path)

    w = image(size=img.size, image=img, mode=img.mode)
    assert compareImage(
        img, w.render()[0]
    ), f"{path} did not match image within widget"

    w = image(file=path, mode=img.mode)
    assert compareImage(
        img, w.render()[0], debug=True
    ), f"{path} did not match image within widget. {image2Text(img)}\n{w}"
