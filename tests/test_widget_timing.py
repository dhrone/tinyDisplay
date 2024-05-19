# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of Widget class for the tinyDisplay system

.. versionadded:: 0.0.1
"""
import pytest
from PIL import Image, ImageChops, ImageDraw

from tinyDisplay.render.widget import text
from tinyDisplay.utility import dataset


def test_duration():
    """Test duration

    Three tests:
      Does active go False when duration expires
      Does active return to True when render after active went to False
      Does active remain True when duration not specified
    """
    w = text(value="'abc'", duration=3)
    for i in range(3):
        w.render()
    assert (
        not w.active
    ), "With three renders and a duration of three, widget should have not been active"

    w.render()
    assert (
        w.active
    ), "After going inactive, the next render should have made it active again"

    w = text(value="'abc'")
    active = True
    for i in range(100):
        w.render()
        active = w.active
        if not active:
            break
    assert active, "Widget should not have gone inactive"


def test_minDuration():
    """Test Min Duration

    Tests:
        Widget is active for minDuration even when activeWhen evaluates False
        Widget remains active when activeWhen goes false if minDuration not expired
        Widget restores minDuration when activeWhen returns to True value
    """
    ds = {"db": {"f": True}}
    w = text(
        value="'abc'",
        duration=5,
        minDuration=2,
        activeWhen='db["f"]',
        dataset=ds,
    )
    w._dataset.update("db", {"f": False})
    w.render()
    assert w.active, "Widget should still be active"

    ds = {"db": {"f": True}}
    w = text(
        value="'abc'",
        duration=5,
        minDuration=2,
        activeWhen='db["f"]',
        dataset=ds,
    )
    w.render()
    w._dataset.update("db", {"f": False})
    assert (
        w.active
    ), "Even when activeWhen goes False, widget should be active if minDuration has not expired"

    w = text(value="'abc'", minDuration=3, activeWhen='db["f"]', dataset=ds)
    for _ in range(5):
        w.render()

    assert w.active, "activeWhen is still True so should still be active"
    w._dataset.update("db", {"f": False})
    w.render()
    assert (
        not w.active
    ), "with minDuration expired and activeWhen false, should be inactive"
    w._dataset.update("db", {"f": True})
    w.render()
    w._dataset.update("db", {"f": False})
    w.render()
    assert (
        w.active
    ), f"minDuration should have been reset so widget should still be active.  Current minDuration is {w._currentMinDuration}"


def test_coolingPeriod():
    """Test that widget does not become active during coolingPeriod

    Test:
        Widget does not enter coolingPeriod prematurely
        Widget with coolingPeriod does not become active until it expires
    """
    ds = {"db": {"f": False}}
    w = text(
        value="abc",
        duration=5,
        coolingPeriod=10,
        activeWhen='db["f"]',
        dataset=ds,
    )
    assert (
        not w.active
    ), "Widget should be inactive because activeWhen is False"

    w._dataset.update("db", {"f": True})  # Trigger widget
    for _ in range(5):
        w.render()
    assert not w.active, "Widget should stop being active after 5 renders"

    w.render()
    assert not w.active, "In cooling period.  Widget should not be active"

    for _ in range(8):
        w.render()
    assert (
        not w.active
    ), "Still in cooling period.  Widget should not be active"

    w.render()
    assert (
        w.active
    ), "Widget should be back in active state having exited cooling Period"
