# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of Marquee Widget for the tinyDisplay system.

.. versionadded:: 0.0.1
"""
import time

import pytest
from PIL import Image, ImageChops

from tinyDisplay.render.collection import canvas
from tinyDisplay.render.widget import popUp, scroll, slide, text
from tinyDisplay.utility import animate, image2Text


@pytest.fixture(scope="function")
def animator(request):
    """Make animator object to use for testing."""
    cleanup = []

    def _animate(cps=60, function=None, queueSize=10):
        a = animate(cps=cps, function=function, queueSize=queueSize)
        cleanup.append(a)
        return a

    yield _animate

    for c in cleanup:
        c.stop()


@pytest.fixture(scope="function")
def makeScroll(request):
    """Make scroll object for testing."""

    def _make_scroll(val, size, distance=1, speed=1):
        w = text(value=val)
        sw = scroll(
            size=size,
            widget=w,
            actions=[("rtl")],
            distance=distance,
            speed=speed,
        )
        return sw

    yield _make_scroll


def test_scroll_widget_performance(animator, makeScroll):
    """Test whether scroll animation is smoothly rendered at the requested speed."""
    # Run renders for 2 seconds at 60hz and a scroll speed of 1.
    # Poll for results at 120hz
    # Should produce around 120 renders

    scrollHigh = makeScroll("High", (19, 8))
    a = animator(function=scrollHigh.render, cps=60)
    a.start()
    t = time.time()
    s = 60
    d = 2
    p = 0
    while t + d >= time.time():
        retval = a.get()
        p = p + 1 if retval and retval[1] else p
        time.sleep(1 / 120)

    expected = s * d
    received = p

    assert (
        abs(received - expected) < 0.05 * expected
    ), f"Received {received} renders.  Expected {expected}"


def test_scroll_wrap_move(makeScroll):
    """Test the shouldIMove detected change in variable value."""
    sw = makeScroll("High", (19, 8))
    startImg = sw.render()[0]
    img = sw.render()[0]
    assert (
        img != startImg
    ), f"scroll should have moved but didn't\n{image2Text(img)}\nand\n{image2Text(startImg)}"

    sw = makeScroll("Hig", (19, 8))
    startImg = sw.render()[0]
    assert sw.render()[0] == startImg, "scroll shouldn't have moved but did"


def test_scroll_wrap_return_to_start(makeScroll):
    """Test that scroll loops back to starting position."""
    sw = makeScroll("High", (19, 8))
    startImg = sw.render()[0]

    images = []
    for i in range(19):
        img, res = sw.render()
        if res:
            images.append(img)

    flag = False
    for img in images:
        if img == startImg:
            flag = True
            break
    assert not flag, "scroll didn't return to start"


@pytest.mark.parametrize(
    "value, size, distance",
    [
        ("Five!", (20, 8), 1),
        ("Five!", (20, 8), 2),
        ("Five!", (20, 8), 3),
        ("Five!", (20, 8), 4),
        ("Five!", (20, 8), 5),
        ("Five!", (20, 8), 6),
        ("Five!", (19, 8), 1),
        ("Five!", (19, 8), 2),
        ("Five!", (19, 8), 3),
        ("Five!", (19, 8), 4),
        ("Five!", (19, 8), 5),
        ("Five!", (19, 8), 6),
        ("Hello World", (25, 7), 1),
        ("Hello World", (25, 7), 2),
    ],
)
def test_scroll_distance(value, size, distance, makeScroll):
    """Test distance moved functionality."""
    sw = makeScroll(value, size, distance)
    w = sw._widget

    startImg = sw.render()[0]
    for i in range(
        (w.size[0] // distance) + (1 if w.size[0] % distance else 0)
    ):
        img, res = sw.render()
    bbox = ImageChops.difference(img, startImg).getbbox()
    assert not bbox, "scroll didn't return to start"


def test_wait(makeScroll):
    """Test that pause action is working correctly."""
    pause = 5
    w1 = text("Five!")
    swL = scroll(
        size=(19, 8),
        widget=w1,
        actions=[("pause", pause), ("rtl")],
        wait="atStart",
    )
    w2 = text("Four")
    swS = scroll(
        size=(19, 8),
        widget=w2,
        actions=[("pause", pause), ("rtl")],
        wait="atStart",
    )

    c = canvas(size=(19, 16))
    c.append(swL)
    c.append(swS, (0, 8))

    imgOrig, update = c.render(force=True)
    for _ in range(pause - 1):
        img, update = c.render()

    assert (
        imgOrig == img
    ), f"This image should have matched the first one as we are still in the pause period \n{image2Text(imgOrig)}\nand\n{str(img)}"

    for _ in range(w2.size[0]):
        img, update = c.render()

    imgCrop = img.crop((0, 8, 19, 16))
    w2Crop = w2.image.crop((0, 0, 19, 8))
    assert (
        w2Crop == imgCrop
    ), f"The cropped area should have matched the original 'Four' text widget\n{image2Text(w2Crop)}\nand\n{image2Text(imgCrop)}"

    for _ in range(w1.size[0] - w2.size[0]):
        img, update = c.render()

    assert (
        imgOrig == img
    ), f"Images should have matched again as they should have become aligned due to the wait condition \n{image2Text(imgOrig)}\nand\n{image2Text(img)}"


def test_should_scroll_move(makeScroll):
    """Basic scroll move test."""
    sMoved = "scroll moved when it shouldn't have"
    sNotMoved = "scroll didn't move when it should have"

    sw = makeScroll("High", (20, 8), 1)
    w = sw._widget

    startImg = sw.render()[0]
    img = sw.render()[0]
    assert img == startImg, sMoved

    sw = makeScroll("High", (19, 8), 1)
    w = sw._widget

    startImg = sw.render()[0]
    img = sw.render()[0]
    assert img != startImg, sNotMoved

    sw = scroll(widget=w, size=(20, 4), actions=[("pause", 10), ("ttb")])
    startImg = sw.render()[0]
    img = sw.render()[0]
    assert img == startImg, sMoved

    while not sw.atPauseEnd:
        sw.render()
    img = sw.render()[0]
    assert img != startImg, sNotMoved


@pytest.mark.parametrize("gap", [("25"), ("4.6"), ("4")])
def test_scroll_gap(gap):
    """Test that gaps are being computed correctly."""
    w = text("Hello")
    sw = scroll(widget=w, size=(20, 8), gap=gap)
    img = sw.render()[0]
    img2 = Image.new("RGBA", (0, 0), "black")
    while not sw.atStart:
        img2 = sw.render()[0]

    bbox = ImageChops.difference(img, img2).getbbox()
    assert (
        not bbox
    ), f"scroll didn't return to start\n{image2Text(img)}\nand\n{image2Text(img2)}"


def test_slide1():
    """Test sliding from left to right to left and test if back to starting position."""
    w = text(value="This is a test!")
    sw = slide(
        size=(100, 16),
        widget=w,
        actions=[("pause", 60), ("ltr"), ("pause", 2), ("rtl")],
        speed=1,
    )
    startImg = sw.render()[0]

    # Move past initial pause
    while not sw.atPauseEnd:
        img, res = sw.render()

    bbox = ImageChops.difference(sw.render()[0], startImg).getbbox()
    assert not bbox, "slide should have moved but didn't"

    while not sw.atStart:
        img, res = sw.render()

    bbox = ImageChops.difference(img, startImg).getbbox()
    assert not bbox, "slide didn't return to start"


@pytest.mark.parametrize(
    "value, size, moved",
    [
        (
            "High",
            (20, 8),
            False,
        ),
        ("High", (25, 8), True),
        ("12345", (20, 8), False),
        ("12345", (26, 8), True),
    ],
)
def test_should_slide_move(value, size, moved):
    """Test that default shouldIMove function is working correctly."""
    msg = (
        "slide moved when it shouldn't have"
        if not moved
        else "slide didn't move when it should have"
    )
    w = text(value=value)
    sw = slide(size=size, widget=w, actions=[("ltr")])
    startImg = sw.render()[0]
    img = sw.render()[0]
    bbox = ImageChops.difference(img, startImg).getbbox()
    assert moved != (img == startImg), msg


@pytest.fixture(scope="function")
def _slide23(request):
    def _slide(actions):
        w = text(value="This is a test!")
        sw = slide(
            size=(100, 16), widget=w, just="mm", actions=actions, speed=1
        )
        return sw

    yield _slide


def test_slider_return_to_start(_slide23):
    """Test whether slider returns to starting position as expected from provided actions."""
    # Return to start without using RTS
    sw = _slide23(
        [("pause", 1), ("ltr"), ("pause", 2), ("ttb"), ("rtl"), ("btt")]
    )
    startPos = sw._curPos
    sw.render()
    while not sw.atStart:
        img, res = sw.render()

    assert (
        sw._curPos == startPos
    ), f"Slide didn't return to origin.  Instead it is at {sw._curPos}"

    # Return to start using RTS
    sw = _slide23(
        [
            ("pause", 1),
            ("ltr"),
            ("pause", 2),
            ("ttb"),
            ("rtl"),
            ("btt"),
            ("rts"),
        ]
    )
    startPos = sw._curPos
    while not sw.atStart:
        img, res = sw.render()

    assert (
        sw._curPos == startPos
    ), f"Slide didn't return to origin ({startPos}).  Instead it is at {sw._curPos}"


def test_popup():
    """Test animation of a window popUp widget."""
    w = text(value="1\n2")
    pu = popUp(size=(5, 8), widget=w, delay=(6, 6))
    top = w.image.crop((0, 0, 5, 8))
    btm = w.image.crop((0, 8, 5, 16))

    # Start at top
    assert pu.render()[0] == top

    # Move to bottom
    while not pu.atPauseEnd:
        pu.render()
    while not pu.atPause:
        pu.render()
    assert pu.render()[0] == btm

    # Move back to top
    while not pu.atPauseEnd:
        pu.render()
    while not pu.atPause:
        pu.render()
    assert pu.render()[0] == top
