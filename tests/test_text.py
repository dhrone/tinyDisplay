# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of Text Widget for the tinyDisplay system.

.. versionadded:: 0.0.1
"""
from pathlib import Path

from PIL import Image, ImageChops

from tinydisplay.render.widget import text
from tinydisplay.utility import dataset


def test_text_widget():
    """Test text widget render including render after variable change."""
    path = (
        Path(__file__).parent / "reference/images/text_artist_sting_60x8.png"
    )
    img = Image.open(path).convert("1")

    db = {"artist": "Sting"}
    ds = dataset({"db": db})
    w = text(
        dvalue="f\"Artist {db['artist']}\"", dataset=ds, size=(60, 8), mode="1"
    )
    renderImage = w.render()[0]
    bbox = ImageChops.difference(img, renderImage).getbbox()
    assert not bbox, "Sting image did not match"

    path = (
        Path(__file__).parent
        / "reference/images/text_artist_new_republic_60x8.png"
    )
    img = Image.open(path).convert("1")

    db["artist"] = "New Republic"
    ds.update("db", db)
    renderImage = w.render()[0]
    bbox = ImageChops.difference(img, renderImage).getbbox()
    assert not bbox, "New Republic image did not match"
