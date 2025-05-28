# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Load tinyDisplay system from yaml file.

.. versionadded:: 0.0.1
"""

import logging
import os
import pathlib
from copy import deepcopy
from inspect import getfullargspec

import yaml
from PIL import ImageFont

from tinyDisplay.font import bmImageFont
from tinyDisplay.render import collection, widget
from tinyDisplay.utility import dataset as Dataset


class _yamlLoader(yaml.SafeLoader):
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super(_yamlLoader, self).__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        with open(filename, "r") as f:
            return yaml.load(f, _yamlLoader)


_yamlLoader.add_constructor("!include", _yamlLoader.include)


class _tdLoader:
    def __init__(self, pageFile=None, defaultCanvas=None):
        assert pageFile, "You must supply a yaml pageFile to load"
        self._defaultCanvas = defaultCanvas
        self._dataset = Dataset()

        self._fonts = {}
        self._display = None

        # Load valid parameters for each widget type
        self._wParams = widget.PARAMS

        # Load valid parameters for each collection type
        self._cParams = collection.PARAMS

        self._loadPageFile(pageFile)

    def _loadPageFile(self, filename):
        """
        Load YAML pageFile.

        Loads the pageFile configuring the WIDGETS, CANVASES, and SEQUENCES that will be animated within this Renderer

        :param filename: The filename of the pageFile
        :type filename: str

        :raises FileNotFoundError: Throws exception if provided file does not exist
        """
        if pathlib.Path(filename).exists():
            path = pathlib.Path(filename)
        else:
            path = pathlib.Path.home() / filename
        if not path.exists():
            raise FileNotFoundError(f"Page File '{filename}' not found")

        with open(path) as f:
            self._pf = yaml.load(f, _yamlLoader)
        self._transform()

    @staticmethod
    def _adjustPlacement(placement=(0, 0, "lt")):
        offset = (
            (int(placement[0]), int(placement[1]))
            if len(placement) >= 2
            else (0, 0)
        )
        just = (
            placement[2]
            if len(placement) == 3
            else placement[0] if len(placement) == 1 else "lt"
        )
        return (offset, just.strip())

    def _createDataValidations(self):
        if "DATASET" not in self._pf:
            return

        cfg = self._pf["DATASET"]

        # for each database in the dataset
        for db, data in cfg.items():

            # for each value element in the database
            if "values" in data:
                for k, v in data["values"].items():
                    v = v if v is not None else {}
                    # Register its data element settings
                    self._dataset.registerValidation(dbName=db, key=k, **v)

            dbcfg = {
                k: v for k, v in data.items() if k in ["onUpdate", "validate"]
            }
            if len(dbcfg) > 0:
                self._dataset.registerValidation(dbName=db, **dbcfg)

    def _createDisplay(self):

        try:
            cfg = None
            size = None
            cfg = deepcopy(self._pf["DISPLAY"])
            size = cfg.get("size")
            dsize = cfg.get("dsize")
        except KeyError:
            if cfg is None:
                raise RuntimeError(
                    "No Display configuration found in page file"
                )
            raise RuntimeError("No items provided for Display in page file")
        if not (size or dsize):
            raise RuntimeError("No size provided for Display in page file")

        if "type" not in cfg:
            cfg["type"] = "canvas"
        if "name" not in cfg:
            cfg["name"] = "MAIN"

        return self._createWidget(cfg)

    def _createWidget(self, cfg, parent="", itemNr=0):
        name = (
            parent + ":" + cfg.get("name", f"item {itemNr + 1}")
            if parent != ""
            else cfg.get("name", itemNr)
        )

        if "type" not in cfg:
            raise RuntimeError(f'Type not provided for {cfg["name"]}')

        # If effect, move widget config to 'widget' key and
        # make effect the containing widget
        if "effect" in cfg:
            wHold = dict(cfg)
            cfg = dict(cfg["effect"])
            del wHold["effect"]
            cfg["widget"] = wHold

        # Make font for widget if it is needed
        if "font" in cfg:
            cfg["font"] = self._createFont(cfg["font"])

        # Resolve location of files if needed
        # TODO:  Determine whether this functionality should be removed #
        if "mask" in cfg:
            cfg["mask"] = self._findFile(cfg["mask"], "images")
        if "file" in cfg:
            cfg["file"] = self._findFile(cfg["file"], "images")

        # If widget is inside an effect, create widget that will be effected
        if "widget" in cfg:
            cfg["widget"] = self._createWidget(cfg["widget"], name, 0)

        # If this is a widget
        if cfg["type"] in self._wParams.keys():
            kwargs = {
                k: v
                for k, v in cfg.items()
                if k in self._wParams[cfg["type"]]
                and k not in ("dataset", "name")
            }
            return widget.__dict__[cfg["type"]](
                dataset=self._dataset, name=name, **kwargs
            )

        # Else a collection
        elif cfg["type"] in self._cParams.keys():
            kwargs = {
                k: v
                for k, v in cfg.items()
                if k in self._cParams[cfg["type"]]
                and k not in ("dataset", "name")
            }
            col = collection.__dict__[cfg["type"]](
                dataset=self._dataset, name=name, **kwargs
            )
            items = cfg.get("items", [])
            for nr, i in enumerate(items):
                appendArgSpec = getfullargspec(col.append)[0][1:]
                # contained item
                appendArgs = {
                    k: v
                    for k, v in i.items()
                    if k in appendArgSpec and k not in ["item", "dataset"]
                }
                ci = self._createWidget(i, name, nr)
                col.append(item=ci, **appendArgs)
            return col

    def _findFile(self, name, type):

        # If DEFAULTS/paths/type exists, add to search path
        try:
            fp = pathlib.Path(self._pf["PATHS"][type]) / name
            search = [
                fp,
            ]
        except KeyError:
            search = []

        search = search + [
            pathlib.Path(name),
        ]

        for s in search:
            if s.exists():
                return s
        raise FileNotFoundError(
            f"FileNotFoundError: File {name} not found at {os.path.realpath(search[0])}"
        )

    def _createFont(self, name):

        if name in self._fonts:
            return self._fonts[name]

        fnt = None
        if name in self._pf["FONTS"]:
            cfg = self._pf["FONTS"][name]
            cType = cfg.get("type", "BMFONT")
            if cType == "BMFONT":
                p = self._findFile(cfg["file"], "fonts")
                fnt = bmImageFont(p)
            elif cfg["type"].lower() == "truetype":
                fnt = ImageFont.truetype(cfg["file"], int(cfg["size"]))
        else:
            # Assume that name is a filename instead of a reference to a font description in FONTS
            fnt = bmImageFont(self._findFile(name, "fonts"))
        if fnt:
            self._fonts[name] = fnt
        return fnt

    @staticmethod
    def _find(key, dictionary):
        for k, v in dictionary.items():
            if k == key:
                yield (k, v, dictionary)
            elif isinstance(v, dict):
                for result in _tdLoader._find(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    if isinstance(d, dict):
                        for result in _tdLoader._find(key, d):
                            yield result

    def _transform(self):
        # Convert Single line fonts in the format "{ 'name': 'filename' }" into standard format (e.g. { 'name': { 'file': 'filename', 'type':'BMFONT'}})
        self._pf["FONTS"] = {
            k: {"file": v, "type": "BMFONT"} if type(v) is str else v
            for k, v in self._pf["FONTS"].items()
        }

        # Convert actions into tuples
        for k, v, d in self._find("actions", self._pf):
            if type(v) is list:
                d[k] = [
                    (
                        (i.split(",")[0], int(i.split(",")[1]))
                        if type(i) is str and len(i.split(",")) == 2
                        else i
                    )
                    for i in v
                ]

        # Convert delay into tuples
        for k, v, d in self._find("delay", self._pf):
            if type(v) is str and len(v.split(",")) > 1:
                d[k] = tuple([int(v) for v in v.split(",")])


def load(file, dataset=None, defaultCanvas=None, debug=False, demo=False):
    """
    Initialize and return a tinyDisplay windows object from a tinyDisplay yaml file.

    :param file: The filename of the tinyDisplay yaml file
    :type file: str
    :param dataset: A dataset to provide variables to any widgets which require them
    :type dataset: tinyDisplay.utility.dataset
    :param defaultCanvas: A window (canvas) to display if there are no active windows
    :type defaultCanvas: tinyDisplay.widget.canvas
    :param debug: Set resulting display into debug mode
    :type debug: bool
    :param demo: Set resulting database into demo mode
    :type demo: bool

    :returns: windows collection
    :rtype: `tinyDisplay.collection.windows`

    ..Note:
        Debug mode causes exceptions to be thrown when dynamic variable
        evaluation fails or any other issues occur during rendering.  Otherwise
        these failures will be logged but otherwise ignored.

        Demo mode causes the dataset to be populated with sample data to
        enable simplified testing of display configurations.
    """
    if debug:
        from tinyDisplay import globalVars

        globalVars.__DEBUG__ = True
        logging.getLogger("tinyDisplay").setLevel(logging.DEBUG)

    tdl = _tdLoader(
        pageFile=file,
        defaultCanvas=defaultCanvas,
    )

    tdl._createDataValidations()
    if demo:
        tdl._dataset.setDemo()
    elif type(dataset) in [Dataset, dict]:
        tdl._dataset.setDefaults()
        for db in dataset:
            if db != "prev":
                tdl._dataset.update(db, dataset[db])
    else:
        tdl._dataset.setDefaults()

    return tdl._createDisplay()
