# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of Dataset class for the tinyDisplay system

.. versionadded:: 0.0.1
"""
import time

import pytest

from tinyDisplay.utility import dataset


updates = [
    ("db", {"state": "play"}),
    (
        "db",
        {"artist": "Abba", "title": "Dancing Queen", "album": "Dancing Queen"},
    ),
    ("sys", {"temp": 54.3}),
    (
        "db",
        {
            "artist": "Eurythmics",
            "title": "Thorn in My Side",
            "album": "Revenge",
        },
    ),
    (
        "db",
        {
            "artist": "Talking Heads",
            "title": "Psycho Killer",
            "album": "Talking Heads",
        },
    ),
    ("sys", {"temp": 62.8}),
    (
        "db",
        {
            "artist": "Billy Joel",
            "title": "Uptown Girl",
            "album": "An Innocent Man",
        },
    ),
    (
        "db",
        {"artist": "Billy Eilish", "title": "bad guy", "album": "Toggo Music"},
    ),
    ("sys", {"temp": 92.6}),
    ("db", {"state": "stop"}),
    ("db", {"time": time.gmtime(1593626862)}),
]

conditions = [
    "db['state']=='play'",
    "db['artist']=='Abba'",
    "sys['temp']==54.3",
    "db['album'].lower()=='revenge'",
    "db['title'][0:5]=='Psych'",
    "sys['temp']<100",
    "db['title'].find('Girl')>=0",
    "prev.db['artist']=='Billy Joel'",
    "history('sys', -1)['temp']==62.8",
    "history('sys', -4)['temp']==54.3",
    "history('sys', 0)['temp']==92.6",
    "db['state']!=prev.db['state']",
    "time.strftime('%H:%M',db['time']) == '18:07'",
    "select(db['state'], 'play', True, 'stop', False) == False",
]


@pytest.mark.parametrize(
    "updates, condition",
    [
        (updates[0:1], conditions[0]),
        (updates[0:2], conditions[1]),
        (updates[0:3], conditions[2]),
        (updates[0:4], conditions[3]),
        (updates[0:5], conditions[4]),
        (updates[0:6], conditions[5]),
        (updates[0:7], conditions[6]),
        (updates[0:8], conditions[7]),
        (updates[0:9], conditions[8]),
        (updates[0:9], conditions[9]),
        (updates[0:9], conditions[10]),
        (updates[0:10], conditions[11]),
        (updates[0:11], conditions[12]),
        (updates[0:11], conditions[13]),
    ],
)
def test_dsEval(updates, condition):
    ds = dataset(historySize=5)
    for u in updates:
        ds.update(u[0], u[1])

    code = ds.compile(condition)
    ans = ds.eval(code)

    assert ans, f"{condition} failed for {updates}"


def test_badinput():
    dsT = dataset()
    try:
        ds = dataset(data={"db": {"a": 1}}, dataset=dsT)
    except RuntimeError as ex:
        assert str(ex) == "You must provide data or a dataset but not both"

    try:
        ds = dataset(historySize=0)
    except ValueError as ex:
        assert (
            str(ex)
            == 'Requested history size "0" is too small.  It must be at least one.'
        )

    try:
        ds = dataset(data={1: 2})
    except ValueError as ex:
        assert (
            str(ex)
            == "All datasets within a database must use strings as names.  This dataset has a database named 1"
        )

    try:
        ds = dataset(data={"eval": {"a": 1}})
    except NameError as ex:
        assert (
            str(ex)
            == "eval is a reserved name and cannot be used witin a dataset"
        )

    ds = dataset(data={"db": {"a": 1}})
    try:
        ds.add("db", {"b": 2})
    except NameError as ex:
        assert str(ex) == "db already exists in dataset"


def test_len_interface():
    ds = dataset()
    ds.add("db", {"title": "Synchronicity"})
    ds.add("sys", {"temp": 90})

    assert (
        len(ds) == 2
    ), f"Dataset should contain two values but instead contained {len(ds)}"


def test_ischanged():
    ds = dataset()
    ds.add("db", {"title": "a"})
    code = ds.compile("changed(db['title'])")

    assert not ds.eval(code), "Nothing has changed yet"
    ds.update("db", {"title": "b"})
    assert ds.eval(code), "Title has changed but change was not detected"


def test_eval_errors():
    ds = dataset()
    ds.add("db", {"val": "a"})

    # Type Error
    c = ds.compile("db['val']+1 == 2")
    try:
        ds.eval(c)
    except TypeError as ex:
        # Need variant of error message because 3.6 not the same as >=3.7
        assert (
            str(ex)
            == "Type Error: can only concatenate str (not \"int\") to str while trying to evalute db['val']+1 == 2"
            or str(ex)
            == "Type Error: must be str, not int while trying to evalute db['val']+1 == 2"
        )

    # KeyError
    c = ds.compile("db['value'] == 2")
    try:
        ds.eval(c)
    except KeyError as ex:
        assert (
            str(ex).strip('"')
            == "KeyError: 'value' while trying to evaluate db['value'] == 2"
        )

    # suppress error
    c = ds.compile("db['value'] == 2")
    try:
        v = ds.eval(c, suppressErrors=True)
    except KeyError as ex:
        assert False, "Suppression Failed"
    assert v == "", f"Suppressed value should have been '' but was {v} instead"


def test_get():
    ds = dataset()
    ds.add("db", {"val": "a"})

    assert ds.get("db")["val"] == "a", "Get returned unexpected value"
    assert ds.get("bad", {"val": "a"}) == {
        "val": "a"
    }, "Get returned unexpected default value"
