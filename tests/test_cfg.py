# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of CFG class for the tinyDisplay system

.. versionadded:: 0.0.1
"""
import time
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from tinyDisplay.cfg import _tdLoader, load
from tinyDisplay.font import bmImageFont
from tinyDisplay.render.widget import rectangle, scroll, text
from tinyDisplay.utility import dataset, image2Text


@pytest.fixture(scope="function")
def make_dataset():
    ds = dataset()
    ds.add(
        "db",
        {
            "artist": "David Bowie",
            "album": "Blackstar",
            "title": "Sue (Or in a Season of Crime)",
            "elapsed": 2.34,
            "length": 93.2,
            "plPos": 2,
            "plLen": 7,
            "state": "play",
        },
    )
    ds.add("sys", {"temp": 53.5, "time": time.time()})

    return ds


@pytest.mark.parametrize(
    "yaml, ref, ticks, db, update, utick",
    [
        ("basicMedia.yaml", "basicMediaArtist.png", 1, "", {}, 0),
        ("basicMedia.yaml", "basicMediaArtist.png", 15, "", {}, 0),
        ("basicMedia.yaml", "basicMediaAlbum.png", 16, "", {}, 0),
        ("basicMedia.yaml", "basicMediaTitle.png", 31, "", {}, 0),
        ("basicMedia.yaml", "basicMediaTitleScroll1.png", 36, "", {}, 0),
        (
            "basicMedia.yaml",
            "basicMediaArtistAlert.png",
            5,
            "sys",
            {"temp": 102},
            4,
        ),
        (
            "basicMedia.yaml",
            "basicMediaArtist.png",
            6,
            "sys",
            {"temp": 102},
            0,
        ),
        (
            "basicMedia.yaml",
            "basicMediaArtist.png",
            10,
            "sys",
            {"temp": 102},
            0,
        ),
        (
            "basicMedia.yaml",
            "basicMediaArtistAlert.png",
            15,
            "sys",
            {"temp": 102},
            0,
        ),
        ("basicMedia.yaml", "pydPiper_splash.png", 46, "", {}, 0),
    ],
)
def test_load(make_dataset, yaml, ref, ticks, db, update, utick):

    ds = make_dataset

    path = Path(__file__).parent / "reference/pageFiles" / yaml
    refImg = Image.open(
        Path(__file__).parent / "reference/images/" / ref
    ).convert("1")
    main = load(path, dataset=ds)

    first = True
    for i in range(ticks):
        if i == utick:
            if db:
                ds.update(db, update)
        main.render(force=first)
        first = False

    assert image2Text(main.image) == image2Text(
        refImg
    ), f"tick {ticks}: Images should have matched\n{print(main)}\n{print(image2Text(refImg))}"


def test_yaml_include(make_dataset):
    ds = make_dataset
    path = Path(__file__).parent / "reference/pageFiles" / "basicMedia.yaml"
    tdl = _tdLoader(pageFile=path, dataset=ds)

    assert (
        tdl._pf["DEFAULTS"]["display"]["type"] == "weh001602a"
    ), "Yaml failed to retrieve contents from !include reference"


def test_file_open(make_dataset):
    ds = make_dataset
    path = Path(__file__).parent / "reference/pageFiles" / "bad.yaml"
    try:
        tdl = _tdLoader(pageFile=path)
    except FileNotFoundError as ex:
        assert str(ex) == f"Page File '{path}' not found"
