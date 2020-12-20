# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of CFG class for the tinyDisplay system

.. versionadded:: 0.0.1
"""
import pytest
import time
from pathlib import Path

from PIL import Image, ImageChops

from tinyDisplay.cfg import load, tdLoader
from tinyDisplay.font import bmImageFont
from tinyDisplay.utility import dataset, image2Text
from tinyDisplay.render.widget import text, rectangle, scroll


@pytest.fixture(scope='function')
def make_dataset(request):
    ds = dataset()
    ds.add('db', { 'artist': 'David Bowie', 'album': 'Blackstar', 'title': 'Sue (Or in a Season of Crime)', 'elapsed': 2.34, 'length': 93.2, 'plPos': 2, 'plLen': 7, 'state': 'play'})
    ds.add('sys', {'temp': 53.5, 'time': time.time()})

    return ds

@pytest.mark.parametrize("yaml, ref, ticks, db, update, utick", [\
        ("basicMedia.yaml", "basicMediaArtist.png", 1, '', {}, 0), \
        ("basicMedia.yaml", "basicMediaArtist.png", 15, '', {}, 0), \
        ("basicMedia.yaml", "basicMediaAlbum.png", 16, '', {}, 0), \
        ("basicMedia.yaml", "basicMediaTitle.png", 31, '', {}, 0), \
        ("basicMedia.yaml", "basicMediaTitleScroll1.png", 36, '', {}, 0), \
        ("basicMedia.yaml", "basicMediaArtistAlert.png", 5, 'sys', {'temp' : 102}, 4), \
        ("basicMedia.yaml", "basicMediaArtist.png", 6, 'sys', {'temp' : 102}, 0), \
        ("basicMedia.yaml", "basicMediaArtist.png", 10, 'sys', {'temp' : 102}, 0), \
        ("basicMedia.yaml", "basicMediaArtistAlert.png", 11, 'sys', {'temp' : 102}, 0), \
        ("basicMedia.yaml", "pydPiper_splash.png", 46, '', {}, 0), \
    ])
def test_load(make_dataset, yaml, ref, ticks, db, update, utick):

    ds = make_dataset

    path = Path(__file__).parent / "reference/pageFiles" / yaml
    refImg = Image.open(Path(__file__).parent / "reference/images/" / ref).convert('1')
    main = load(path, dataset = ds, displaySize=(100, 16))

    for i in range(ticks):
        if i == utick:
            if db:
                ds.update(db, update)
        main.render()

    assert image2Text(main.image) == image2Text(refImg), f"Images should have matched\n{print(main)}\n{print(image2Text(refImg))}"

def test_yaml_include(make_dataset):
    ds = make_dataset
    path = Path(__file__).parent / "reference/pageFiles" / 'basicMedia.yaml'
    tdl = tdLoader(pageFile = path, dataset = ds, displaySize = (100,16))

    assert tdl._pf['DEFAULTS']['display']['type'] == 'weh001602a', 'Yaml failed to retrieve contents from !include reference'

def test_file_open(make_dataset):
    ds = make_dataset
    path = Path(__file__).parent / "reference/pageFiles" / 'bad.yaml'
    try:
        tdl = tdLoader(pageFile = path, dataset = ds, displaySize = (100,16))
    except FileNotFoundError as ex:
        assert str(ex) == f'Page File \'{path}\' not found'
