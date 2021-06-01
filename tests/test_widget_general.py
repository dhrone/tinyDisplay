# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of Widget class for the tinyDisplay system

.. versionadded:: 0.0.1
"""
import pytest
from PIL import Image, ImageChops, ImageDraw

from tinydisplay import globalVars
from tinydisplay.render.widget import rectangle, text
from tinydisplay.utility import compareImage as ci, dataset


def test_image_placement():

    # Make H
    hImg = Image.new("1", (5, 8))
    d = ImageDraw.Draw(hImg)
    d.line([(0, 1), (0, 7)], fill="white")
    d.line([(4, 1), (4, 7)], fill="white")
    d.line([(0, 4), (4, 4)], fill="white")

    w = text(value="H", size=(100, 16), just="rt", mode="1")
    renderImage = w.render()[0]

    for size in [(100, 16), (99, 15), (20, 8), (19, 8)]:
        for j in ["lt", "lm", "lb", "mt", "mm", "mb", "rt", "rm", "rb"]:
            offsetH = {"r": size[0] - 5, "l": 0, "m": round((size[0] - 5) / 2)}
            offsetV = {"b": size[1] - 8, "t": 0, "m": round((size[1] - 8) / 2)}

            w = text(value="H", size=size, just=j, mode="1")
            renderImage = w.render()[0]

            img = Image.new("1", size)
            img.paste(hImg, (offsetH[j[0]], offsetV[j[1]]))
            bbox = ImageChops.difference(img, renderImage).getbbox()
            assert not bbox, f"Place {j[0]}{j[1]} failed at size {size}"


def test_clear():
    w = rectangle((0, 0, 10, 10), size=(11, 11))
    img = Image.new(w.image.mode, (11, 11), w._background)
    drw = ImageDraw.Draw(img)
    drw.rectangle((0, 0, 10, 10), fill="white")
    assert ci(w.render()[0], img)

    w.clear()
    img = Image.new(w.image.mode, (11, 11), w._background)
    assert ci(w.render()[0], img)


def test_repr():
    w = text(name="STATIC12345", value="12345")
    v = "<STATIC12345.text value('12345') size(25, 8)"
    assert repr(w)[0 : len(v)] == v, f"Unexpected repr value given: {w}"


def test_text_image_print():
    w = text(name="STATIC12345", value="12345")
    v = "---------------------------\n"
    v += "|                         |\n"
    v += "|  *   *** *****   * *****|\n"
    v += "| **  *   *   *   ** *    |\n"
    v += "|  *      *  *   * * **** |\n"
    v += "|  *     *    * *  *     *|\n"
    v += "|  *    *      ******    *|\n"
    v += "|  *   *   *   *   * *   *|\n"
    v += "| *** ***** ***    *  *** |\n"
    v += "---------------------------"

    assert (
        str(w)[0 : len(v)] == v
    ), f"Unexpected image produced:\n{w}\n\nShould have been\n{v}"


def test_string_eval():
    s = "abc"
    w = text(value=f"{s}")
    drw = ImageDraw.Draw(Image.new("1", (0, 0), 0))
    img = Image.new(w.image.mode, drw.textsize(s, font=w.font), w._background)
    drw = ImageDraw.Draw(img)
    drw.text((0, 0), s, font=w.font, fill=w._foreground)

    assert ci(w.image, img), f"Images do not match for value {w.current}"


def test_request_size():
    s = "abc"
    w = text(f"{s}", size=(10, 8))
    img = Image.new(w.image.mode, (10, 8), w._background)
    drw = ImageDraw.Draw(img)
    drw.text((0, 0), s, font=w.font, fill=w._foreground)

    assert ci(w.image, img), f"Image should only contain 'ab'"

    db = {"value": s}
    ds = dataset()
    ds.add("db", db)
    w = text(dvalue="db['value']", dataset=ds, size=(10, 8))
    db["value"] = s[0]
    ds.update("db", db)
    w.render()
    img = Image.new(w.image.mode, (10, 8), w._background)
    drw = ImageDraw.Draw(img)
    drw.text((0, 0), s[0], font=w.font, fill=w._foreground)

    assert ci(w.image, img), f"Image should only contain 'a'"


def test_bad_four_tuple():
    globalVars.__DEBUG__ = True
    with pytest.raises(ValueError) as ex:
        w = rectangle((0, 1, 2, 3, 4), fill="'black'", outline="'white'")
    try:
        assert (
            str(ex.value)
            == "xy must be an array of two tuples or four integers.  Instead received (0, 1, 2, 3, 4)"
        )
    finally:
        globalVars.__DEBUG__ = False
