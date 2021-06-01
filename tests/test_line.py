# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of Line Widget for the tinyDisplay system

.. versionadded:: 0.0.1
"""
import pytest
from PIL import Image, ImageChops, ImageDraw

from tinydisplay.render.widget import line
from tinydisplay.utility import compareImage


def test_line_widget():

    img = Image.new("1", (50, 50), "black")
    d = ImageDraw.Draw(img)
    d.line([(0, 0), (49, 49)], fill="white")
    w = line(xy=[(0, 0), (49, 49)], fill="white", mode="1")
    assert compareImage(
        img, w.render()[0]
    ), f"Lines did not match (two tuple test)"

    w = line(xy=(0, 0, 49, 49), fill="white", mode="1")
    assert compareImage(
        img, w.render()[0]
    ), f"Lines did not match (one tuple test)"

    img = Image.new("1", (10, 8), "black")
    d = ImageDraw.Draw(img)
    d.line([(0, 0), (49, 49)], fill="white")
    w = line(xy=(0, 0, 49, 49), fill="white", mode="1", size=(10, 8))
    assert compareImage(
        img, w.render()[0]
    ), f"Lines did not match (small image test)"
