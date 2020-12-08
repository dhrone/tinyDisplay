# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of tinyDisplay canvas class

.. versionadded:: 0.0.1
"""
import pytest
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

from tinyDisplay.render.widget import text, staticText
from tinyDisplay.render.collection import canvas

def compute_placement(size, wsize, offset, anchor):
    anchor = anchor or 'lt'
    offset = offset or (0, 0)

    mh = round((size[0] - wsize[0]) / 2)
    r = size[0] - wsize[0]

    mv = round((size[1] - wsize[1]) / 2)
    b = size[1] - wsize[1]

    a = \
        0 if anchor[0] == 'l' else \
        mh if anchor[0] == 'm' else \
        r if anchor[0] == 'r' else \
        0
    b = \
        0 if anchor[1] == 't' else \
        mv if anchor[1] == 'm' else \
        b if anchor[1] == 'b' else \
        0
    return (offset[0] + a, offset[1] + b)

@pytest.mark.parametrize("size, offset, anchor", [\
        ((100, 100), (0, 0), None), \
        ((100, 100), (0, 0), 'lt'), \
        ((100, 100), (0, 0), 'rt'), \
        ((100, 100), (0, 0), 'mt'), \
        ((100, 100), (0, 0), 'lm'), \
        ((100, 100), (0, 0), 'mm'), \
        ((100, 100), (0, 0), 'rm'), \
        ((100, 100), (0, 0), 'lb'), \
        ((100, 100), (0, 0), 'mb'), \
        ((100, 100), (0, 0), 'rb'), \
        ((99, 99), None, None), \
        ((99, 99), (0, 0), 'lt'), \
        ((99, 99), (0, 0), 'rt'), \
        ((99, 99), (0, 0), 'mt'), \
        ((99, 99), (0, 0), 'lm'), \
        ((99, 99), (0, 0), 'mm'), \
        ((99, 99), (0, 0), 'rm'), \
        ((99, 99), (0, 0), 'lb'), \
        ((99, 99), (0, 0), 'mb'), \
        ((99, 99), (0, 0), 'rb'), \
        ((80, 16), (-4, -8), 'rb'), \
        ((80, 16), (1, 1), 'rb'), \
        ((80, 16), (-1, -1), None), \
    ])
def test_canvas_widget(size, offset, anchor):
    '''
    Place widgets and verify position
    '''
    w = text('X')
    ri = w.render()[0]

    img = Image.new('1', size, 0)
    drw = ImageDraw.Draw(img)
    fnt = w.font

    if anchor and offset:
        c = canvas(size=size)
        c.append(w, offset, anchor)
    elif offset:
        c = canvas(size=size)
        c.append(w, offset, anchor)
    else:
        c = canvas(size=size)
        c.append(w)
    pos = compute_placement(size, fnt.getsize('X'), offset, anchor)
    drw.text( pos, 'X', font=fnt, fill='white')
    assert c.render()[0] == img, f'Placing \'X\' on {size} canvas at {offset} anchored {anchor} failed'

    img = Image.new('1', size, 0)
    drw = ImageDraw.Draw(img)

    c = canvas(size=size)
    c.append(w, offset, anchor)
    drw.text( pos, 'X', font=fnt, fill='white')
    assert c.render()[0] == img, f'Placing \'X\' by append on {size} canvas at {offset} anchored {anchor} failed'


def test_z_order():
    w1 = staticText('ABC', size=(20,8))
    w2 = staticText('123', size=(20,8))

    # Place second append at a higher z
    c1 = canvas(size=(20,8))
    c1.append(w1)
    c1.append(w2, z=canvas.ZHIGH)
    assert w2.render()[0] == c1.render()[0], f"123 should have been on top but got {c1}"

    # Place both appends at the same z level.  Should make first append higher than the second
    c2 = canvas(size=(20,8))
    c2.append(w1)
    c2.append(w2)
    assert w1.render()[0] == c2.render()[0], f"ABC should have been on top but got {c1}"


def test_canvas_widget_change():

    db = {'artist': 'Sting'}
    w = text(value='f"Artist {db[\'artist\']}"', dataset = { 'db': db }, size=(60,8))
    c = canvas(size=(80,16))
    c.append(w)
    img, m1 = c.render()
    img, m2 = c.render()
    db['artist'] = 'Moby'
    w._dataset.update('db', db)
    img, m3 = c.render()

    assert m1 and m3 and not m2
