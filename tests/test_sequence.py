# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of tinyDisplay sequence class

.. versionadded:: 0.0.1
"""
import pytest
from PIL import Image, ImageChops, ImageDraw

from tinyDisplay.render.widget import text
from tinyDisplay.render.collection import canvas, sequence
from tinyDisplay.utility import dataset, image2Text


def test_sequence_timing():
    db = {'artist': 'Sting', 'title': 'Desert Rose'}
    ds = dataset({'db': db})
    artist = text(value = 'f"Artist {db[\'artist\']}"', dataset = ds)
    title = text(value = 'f"Title {db[\'title\']}"', dataset = ds)
    cArt = canvas(size = (80,16))
    cArt.append(artist)
    cTitle = canvas(size = (80, 16))
    cTitle.append(title)

    seq = sequence(dataset = ds)
    seq.append(cArt, duration=2)
    seq.append(cTitle, duration=2)

    sImg = seq.render()[0]
    sSame = seq.render()[0]
    sNew = seq.render()[0]
    seq.render()[0]
    sOld = seq.render()[0]

    assert sImg == sSame, f'Images should have been identical but instead were\n{image2Text(sImg)}\nand\n{image2Text(sSame)}'

    assert sImg != sNew, f'Images should have been different but instead were\n{image2Text(sImg)}\nand\n{image2Text(sNew)}'

    assert sImg == sOld, f'Images should have been back to identical but instead were\n{image2Text(sImg)}\nand\n{image2Text(sOld)}'
