# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of tinyDisplay sequence class

.. versionadded:: 0.0.1
"""
import pytest

from tinyDisplay.render.collection import canvas, sequence
from tinyDisplay.render.widget import text
from tinyDisplay.utility import dataset, image2Text


@pytest.fixture
def makeSetup():
    db = {"artist": "Sting", "title": "Desert Rose"}
    system = {"state": "play", "temp": 40}
    ds = dataset({"db": db, "sys": system})
    artist = text(value="f\"Artist {db['artist']}\"", dataset=ds)
    title = text(value="f\"Title {db['title']}\"", dataset=ds)
    alert = text(value="'ALERT -- HOT'")
    time = text("'12:32p'")
    cArt = canvas(
        size=(80, 16),
        duration=2,
        activeWhen="sys['state'] == 'play'",
        dataset=ds,
        name="Artist",
    )
    cArt.append(artist)
    cTitle = canvas(
        size=(80, 16),
        duration=2,
        activeWhen="sys['state'] == 'play'",
        dataset=ds,
        name="Title",
    )
    cTitle.append(title)
    cAlert = canvas(
        size=(80, 16),
        duration=5,
        minDuration=2,
        activeWhen="sys['temp'] >= 100",
        dataset=ds,
        name="Alert",
    )
    cAlert.append(alert)
    cTime = canvas(
        size=(80, 16),
        duration=10,
        activeWhen="sys['state'] == 'stop'",
        dataset=ds,
        name="Time",
    )
    cTime.append(time, placement="mm")

    seq = sequence(dataset=ds)
    seq.append(cArt)
    seq.append(cTitle)
    seq.append(cAlert)
    seq.append(cTime)

    return (ds, seq)


def test_sequence_timing(makeSetup):

    ds, seq = makeSetup

    sImg = seq.render(force=True)[0]
    sSame = seq.render()[0]
    sNew = seq.render()[0]
    seq.render()[0]
    sOld = seq.render()[0]

    assert (
        sImg == sSame
    ), f"Images should have been identical but instead were\n{image2Text(sImg)}\nand\n{image2Text(sSame)}"

    assert (
        sImg != sNew
    ), f"Images should have been different but instead were\n{image2Text(sImg)}\nand\n{image2Text(sNew)}"

    assert (
        sImg == sOld
    ), f"Images should have been back to identical but instead were\n{image2Text(sImg)}\nand\n{image2Text(sOld)}"


def test_sequence_conditions(makeSetup):
    ds, seq = makeSetup

    # Should be Artist Play canvas
    sOrig = seq.render(force=True)[0]

    # Skip to end of sequence (assuming state stays the same)
    for i in range(3):
        seq.render()

    sTst = seq.render()[0]
    assert (
        sOrig == sTst
    ), f"Images should have been identical but instead were\n{image2Text(sOrig)}\nand\n{image2Text(sTst)}"

    ds.update("sys", {"state": "stop"})
    sTst = seq.render()[0]
    assert (
        sOrig != sTst
    ), f"Images should have been different but instead were\n{image2Text(sOrig)}\nand\n{image2Text(sTst)}"


def test_min_duration(makeSetup):
    ds, seq = makeSetup

    ds.update("sys", {"temp": 100, "state": "stop"})

    sOrig = seq.render(force=True)[0]
    ds.update("sys", {"temp": 40})
    sTst = seq.render()[0]
    sTst2 = seq.render()[0]

    # sTst should == sOrig (because of the minDuration of 2 for cAlert)
    assert (
        sOrig == sTst
    ), f"Images should have been identical but instead were\n{image2Text(sOrig)}\nand\n{image2Text(sTst)}"

    assert (
        sOrig != sTst2
    ), f"Images should have been different but instead were\n{image2Text(sOrig)}\nand\n{image2Text(sTst2)}"
