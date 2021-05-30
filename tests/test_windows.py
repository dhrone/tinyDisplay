# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of tinyDisplay windows class

.. versionadded:: 0.0.1
"""
import pytest

from tinyDisplay.render.collection import canvas, sequence
from tinyDisplay.render.widget import rectangle, text
from tinyDisplay.utility import dataset, image2Text


@pytest.fixture
def makeSetup():
    db = {
        "artist": "Sting",
        "title": "Desert Rose",
        "album": "Ten Summoner's Tales",
    }
    system = {"state": "play", "temp": 40}
    ds = dataset({"db": db, "sys": system})

    # Widgets
    artist = text(value="f\"Artist {db['artist']}\"", dataset=ds)
    title = text(value="f\"Title {db['title']}\"", dataset=ds)
    album = text(value="f\"Album {db['album']}\"", dataset=ds)
    alert = text(value="'ALERT -- HOT'")
    rectAlert = rectangle(
        (0, 0, alert.size[0] + 3, alert.size[1] + 3),
        outline="'white'",
        fill="'black'",
    )

    time = text("'12:32p'")

    # Canvases
    cAT = canvas(size=(80, 16), duration=2)
    cAT.append(artist)
    cAT.append(title, placement=(0, 8))

    cAA = canvas(
        size=(80, 16),
        duration=2,
        activeWhen="len(db['album']) > 0",
        dataset=ds,
    )
    cAA.append(artist)
    cAA.append(album, placement=(0, 8))

    seqPlay = sequence(
        size=(80, 16), activeWhen="sys['state'] == 'play'", dataset=ds
    )
    seqPlay.append(cAT)
    seqPlay.append(cAA)

    cStop = canvas(
        size=(80, 16), activeWhen="sys['state'] == 'stop'", dataset=ds
    )
    cStop.append(time, placement="mm")

    cAlert = canvas(
        size=(64, 12),
        duration=5,
        minDuration=2,
        coolingPeriod=10,
        activeWhen="sys['temp'] >= 100",
        dataset=ds,
    )
    cAlert.append(alert, placement="mm")
    cAlert.append(rectAlert, placement="mm")

    wins = canvas(size=(80, 16), dataset=ds)
    wins.append(seqPlay)
    wins.append(cStop)
    wins.append(cAlert, placement="mm", z=canvas.ZVHIGH)

    return (ds, wins, seqPlay, cStop, cAlert, cAT, cAA)


def test_sequence_timing(makeSetup):

    ds, wins, seqPlay, cStop, cAlert, cAT, cAA = makeSetup

    for i in range(10):
        # Render two times for sequence entry cAT
        sImg = wins.render(force=True)[0]
        assert (
            sImg == wins.render()[0]
        ), f"Images should have been identical but instead were \n{image2Text(sImg)}\nand\n{str(wins)}"

        # Render two times for sequence entry cAA (and album has data)
        assert (
            wins.render()[0] == cAA.image
        ), f"Images should have been identical but instead were \n{str(wins)}\nand\n{str(cAA)}"
        assert (
            sImg != wins.render()[0]
        ), f"Images should have been different but instead were \n{image2Text(sImg)}\nand\n{str(wins)}"

    # Deactiveate sequence element CAA
    ds.update("db", {"album": ""})

    # Render two times for sequence entry cAT
    sImg = wins.render()[0]
    assert (
        sImg == wins.render()[0]
    ), f"Images should have been identical but instead were \n{image2Text(sImg)}\nand\n{str(wins)}"

    # Render two more times.  Should only be cAT as cAA should be deactivated
    assert (
        wins.render()[0] == cAT.image
    ), f"Images should have been identical but instead were \n{str(wins)}\nand\n{str(cAT)}"
    assert (
        sImg == wins.render()[0]
    ), f"Images should have been identical but instead were \n{image2Text(sImg)}\nand\n{str(wins)}"


def test_alert_timing(makeSetup):

    ds, wins, seqPlay, cStop, cAlert, cAT, cAA = makeSetup

    sImg = wins.render()[0]
    ds.update("sys", {"temp": 100})

    canvasWAlert = canvas(size=(80, 16))
    canvasWAlert.append(cAlert, placement="mm")
    canvasWAlert.append(cAT)

    sAlert = wins.render(force=True)[0]
    assert (
        sAlert == canvasWAlert.render()[0]
    ), f"Images should have been identical but instead were \n{image2Text(sAlert)}\nand\n{str(canvasWAlert)}"


"""
def test_sequence_conditions(makeSetup):
    ds, wins, seqPlay, cStop, cAlert, cAT, cAA = makeSetup

    # Should be Artist Play canvas
    sOrig = wins.render()[0]

    # Skip to end of sequence (assuming state stays the same)
    for i in range(3):
        wins.render()

    sTst = seq.render()[0]
    assert sOrig == sTst, f'Images should have been identical but instead were\n{image2Text(sOrig)}\nand\n{image2Text(sTst)}'

    ds.update('sys', {'state': 'stop'})
    sTst = seq.render()[0]
    assert sOrig != sTst, f'Images should have been different but instead were\n{image2Text(sOrig)}\nand\n{image2Text(sTst)}'


def test_min_duration(makeSetup):
    ds, seq = makeSetup

    ds.update('sys', {'temp': 100, 'state': 'stop'} )

    sOrig = seq.render()[0]
    ds.update('sys', {'temp': 40} )
    sTst = seq.render()[0]
    sTst2 = seq.render()[0]

    # STst should == sOrig (because of the minDuration of 2 for cAlert)
    assert sOrig == sTst, f'Images should have been identical but instead were\n{image2Text(sOrig)}\nand\n{image2Text(sTst)}'

    assert sOrig != sTst2, f'Images should have been different but instead were\n{image2Text(sOrig)}\nand\n{image2Text(sTst2)}'
"""
