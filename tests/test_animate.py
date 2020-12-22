# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of animation class for the tinyDisplay system

.. versionadded:: 0.0.1
"""
import time

import pytest

from tinyDisplay.utility import animate


@pytest.fixture(scope="function")
def animator(request):
    cleanup = []

    def _animate(cps=60, function=None, queueSize=10):
        a = animate(cps=cps, function=function, queueSize=queueSize)
        cleanup.append(a)
        return a

    yield _animate

    for c in cleanup:
        c.stop()


@pytest.fixture(scope="function")
def test_func(request):
    def _func(*args, **kwargs):
        retval = [time.time()]
        if args:
            retval.append(args)
        if kwargs:
            retval.append(kwargs)
        return retval

    yield _func


def test_queue(animator, test_func):

    a = animator(function=test_func, queueSize=10, cps=10)
    t = time.time()
    assert (
        a.empty
    ), f"Animation hasn't started so queue should be empty. Queue size currently {a.qsize}"

    a.start()
    time.sleep(0.25)
    assert (
        not a.empty
    ), f"Animation has started, queue should be filling.  Queue size currently {a.qsize}"

    time.sleep(0.9)
    assert (
        a.full
    ), f"Queue has been running long enough to fill up completely. Queue size currently {a.qsize}"

    a.pause()
    a.clear()
    assert (
        a.empty
    ), f"Animation has been paused and cleared.  Queue should be empty. Queue size currently {a.qsize}"

    a.restart()
    time.sleep(0.5)
    a.pause()
    assert (
        not a.full and a.qsize > 0
    ), f"Animation run for a 1/2 second.  It should contain some values but not be full. Queue size currently {a.qsize}"

    cSize = a.qsize
    time.sleep(0.8)
    assert (
        not a.full
    ), f"Animation not running.  Queue size shouldn't have become full. Queue size currently {a.qsize}"

    a.toggle()
    time.sleep(0.8)
    assert (
        a.full
    ), f"Animation should have run until full when it got toggled back into operation. Queue size currently {a.qsize}"

    a.toggle()
    time.sleep(0.2)
    a.clear()
    assert (
        a.empty
    ), f"Animation should be paused and queue has been cleared so it should be empty. Queue size currently {a.qsize}"


def test_force(animator, test_func):

    a = animator(function=test_func, queueSize=10, cps=20)
    a.start()
    time.sleep(0.1)

    v = a.get()
    assert (
        len(v) == 1
    ), f"Function without arguments should be returning a list with only one value (time).  Value was {v}"

    a.force(1)
    v = a.get()
    assert len(v) == 2 and v[1] == (
        1,
    ), f"Function should return list with (1,) as its second value.  Value was {v}"

    a.force(a=1)
    v = a.get()
    assert len(v) == 2 and v[1] == {
        "a": 1
    }, f"Function should return list with a dictionary as its second value.  Value was {v}"

    a.force(1, a=1)
    v = a.get()
    assert (
        len(v) == 3 and v[1] == (1,) and v[2] == {"a": 1}
    ), f"Function should return list with the value '1' as its second value and a dictionary as its third value.  Value was {v}"


def test_fps(animator, test_func):
    a = animator(function=test_func, queueSize=200, cps=20)
    a.start()

    assert (
        a.fps == 0
    ), f"FPS value gets calculated every five seconds.  At start should be 0.  Current value is {a.fps}"
    time.sleep(6)

    assert (
        a.fps > 0
    ), f"It's been six seconds.  FPS value should be around 20.  Current value is {a.fps}"
