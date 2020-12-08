# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of tinyDisplay windows class

.. versionadded:: 0.0.1
"""
import pytest

from tinyDisplay.render.widget import text, staticText, rectangle
from tinyDisplay.render.collection import canvas, sequence, windows
from tinyDisplay.utility import dataset, image2Text

@pytest.fixture
def makeSetup():
    db = {'artist': 'Sting', 'title': 'Desert Rose', 'album': 'Ten Summoner\'s Tales' }
    system = { 'state': 'play', 'temp': 40 }
    ds = dataset({'db': db, 'sys': system} )

    # Widgets
    artist = text(value = 'f"Artist {db[\'artist\']}"', dataset = ds)
    title = text(value = 'f"Title {db[\'title\']}"', dataset = ds)
    album = text(value = 'f"Album {db[\'album\']}"', dataset = ds)
    alert = staticText(value = 'ALERT -- HOT')
    rectAlert = rectangle((0, 0, alert.size[0]+3, alert.size[1]+3), outline='white', fill='black')

    time = staticText('12:32p')

    # Canvases
    cAT = canvas(size = (80,16))
    cAT.append(artist)
    cAT.append(title, offset=(0, 8))

    cAA = canvas(size = (80, 16))
    cAA.append(artist)
    cAA.append(album, offset=(0, 8))

    seqPlay = sequence(dataset = ds, size = (80, 16))
    seqPlay.append(cAT, duration = 2)
    seqPlay.append(cAA, duration = 2, condition = "len(db['album']) > 0")

    cStop = canvas(size = (80, 16))
    cStop.append(time, just = 'mm')

    cAlert = canvas(size = (64, 12))
    cAlert.append(alert, just='mm')
    cAlert.append(rectAlert, just='mm')

    wins = windows(size = (80, 16), dataset=ds)
    wins.append(seqPlay, condition = 'sys[\'state\'] == \'play\'' )
    wins.append(cStop, condition = "sys['state'] == 'stop'" )
    wins.append(cAlert, just='mm', duration=5, minDuration = 2, coolingPeriod=10, z=canvas.ZVHIGH, condition = 'sys[\'temp\'] >= 100')

    return (ds, wins, seqPlay, cStop, cAlert, cAT, cAA)


def test_sequence_timing(makeSetup):

    ds, wins, seqPlay, cStop, cAlert, cAT, cAA = makeSetup

    for i in range(10):
        # Render two times for sequence entry cAT
        sImg = wins.render()[0]
        assert sImg == wins.render()[0], f'Images should have been identical but instead were \n{image2Text(sImg)}\nand\n{str(wins)}'

        # Render two times for sequence entry cAA (and album has data)
        assert wins.render()[0] == cAA.image, f'Images should have been identical but instead were \n{str(wins)}\nand\n{str(cAA)}'
        assert sImg != wins.render()[0], f'Images should have been different but instead were \n{image2Text(sImg)}\nand\n{str(wins)}'

    # Deactiveate sequence element CAA
    ds.update('db', {'album': ''})

    # Render two times for sequence entry cAT
    sImg = wins.render()[0]
    assert sImg == wins.render()[0], f'Images should have been identical but instead were \n{image2Text(sImg)}\nand\n{str(wins)}'

    # Render two more times.  Should only be cAT as cAA should be deactivated
    assert wins.render()[0] == cAT.image, f'Images should have been identical but instead were \n{str(wins)}\nand\n{str(cAT)}'
    assert sImg == wins.render()[0], f'Images should have been identical but instead were \n{image2Text(sImg)}\nand\n{str(wins)}'

def test_alert_timing(makeSetup):

    ds, wins, seqPlay, cStop, cAlert, cAT, cAA = makeSetup

    sImg = wins.render()[0]
    ds.update('sys', {'temp': 100})

    canvasWAlert = canvas(size = (80, 16))
    canvasWAlert.append(cAlert, just='mm')
    canvasWAlert.append(cAT)

    sAlert = wins.render()[0]
    assert sAlert == canvasWAlert.render()[0], f'Images should have been identical but instead were \n{image2Text(sAlert)}\nand\n{str(canvasWAlert)}'





'''
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
'''
