# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of CFG class for the tinyDisplay system

.. versionadded:: 0.0.1
"""
import time
from pathlib import Path
import logging
import sys

import pytest
from PIL import Image, ImageChops

from tinyDisplay.cfg import _tdLoader, load
from tinyDisplay.font import bmImageFont
from tinyDisplay.render.widget import rectangle, scroll, text
from tinyDisplay.utility import dataset, image2Text

# Configure the tinyDisplay logger for tests
logger = logging.getLogger("tinyDisplay")
logger.setLevel(logging.DEBUG)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


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
    ds = main._dataset

    # Get the alert widget to monitor its timers
    alert_widget = main._placements[2][0]

    first = True
    for i in range(ticks):
        if i == utick:
            if db:
                logger.debug(f"\n--- Updating {db} with {update} at tick {i} ---")
                ds.update(db, update)
        
        # Log timer values before rendering
        if alert_widget:
            logger.debug(f"\n--- Tick {i} ---")
            logger.debug(f"Active: {alert_widget.active}")
            logger.debug(f"activeWhen: {alert_widget._activeWhen}")
            logger.debug(f"_currentDuration: {getattr(alert_widget, '_currentDuration', 'N/A')}")
            logger.debug(f"_currentMinDuration: {getattr(alert_widget, '_currentMinDuration', 'N/A')}")
            logger.debug(f"_currentCoolingPeriod: {getattr(alert_widget, '_currentCoolingPeriod', 'N/A')}")
            logger.debug(f"_overRunning: {getattr(alert_widget, '_overRunning', 'N/A')}")
            logger.debug(f"_currentActiveState: {getattr(alert_widget, '_currentActiveState', 'N/A')}")
        
        main.render(force=first)
        first = False
        
        # Log timer values after rendering
        if alert_widget:
            logger.debug(f"After render - Active: {alert_widget.active}")
            logger.debug(f"After render - _currentDuration: {getattr(alert_widget, '_currentDuration', 'N/A')}")
            logger.debug(f"After render - _currentMinDuration: {getattr(alert_widget, '_currentMinDuration', 'N/A')}")
            logger.debug(f"After render - _currentCoolingPeriod: {getattr(alert_widget, '_currentCoolingPeriod', 'N/A')}")
            logger.debug(f"After render \n{main}") 

    assert image2Text(main.image) == image2Text(
        refImg
    ), f"tick {ticks}: Images should have matched\n{print(main)}\n{print(image2Text(refImg))}"


def test_yaml_include():
    path = Path(__file__).parent / "reference/pageFiles" / "basicMedia.yaml"
    tdl = _tdLoader(pageFile=path)

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
