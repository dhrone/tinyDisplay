# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Load tinyDisplay system from yaml file

.. versionadded:: 0.0.1
"""

import yaml
import re
import os
import pathlib
from PIL import ImageFont
from inspect import isclass, getfullargspec, getmro

from tinyDisplay.utility import dataset as Dataset
from tinyDisplay.render.collection import sequence, windows, canvas
from tinyDisplay.render import widget, collection
from tinyDisplay.font import bmImageFont


class _yamlLoader(yaml.SafeLoader):
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super(_yamlLoader, self).__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        with open(filename, 'r') as f:
            return yaml.load(f, _yamlLoader)


_yamlLoader.add_constructor('!include', _yamlLoader.include)


class tdLoader():

    def __init__(self, pageFile=None, dataset=None, displaySize=None, defaultCanvas=None):
        assert pageFile, 'You must supply a yaml pageFile to load'
        self.size = displaySize if displaySize else (0, 0)
        self._defaultCanvas = defaultCanvas
        self._dataset = Dataset(dataset) if dataset and type(dataset) is dict else dataset if dataset else Dataset()

        self._fonts = {}
        self._widgets = {}
        self._canvases = {}
        self._sequences = {}

        # Load valid parameters for each widget type
        self._wParams = {k: self.getArgDecendents(v) for k, v in widget.__dict__.items() if isclass(v) and issubclass(v, widget.widget) and k != 'widget'}

        # Load valid parameters for each collection type
        self._cParams = {k: self.getArgDecendents(v) for k, v in collection.__dict__.items() if isclass(v) and issubclass(v, collection.canvas) }

        self._loadPageFile(pageFile)

    @staticmethod
    def getArgDecendents(c):
        args = []
        for i in getmro(c):
            for arg in getfullargspec(i)[0][1:]:
                if arg not in args:
                    args.append(arg)
        return args

    def _loadPageFile(self, filename):
        """
        Loads the pageFile configuring the WIDGETS, CANVASES, and SEQUENCES that will be animated within this Renderer
        """
        if pathlib.Path(filename).exists():
            path = pathlib.Path(filename)
        else:
            path = pathlib.Path.home() / filename
        if not path.exists():
            raise FileNotFoundError(f'Page File \'{filename}\' not found')

        f = open(path)
        self._pf = yaml.load(f, _yamlLoader)
        self._transform()


    @staticmethod
    def _adjustPlacement(placement=(0, 0, 'lt')):
        offset = (int(placement[0]), int(placement[1])) if len(placement) >= 2 else (0, 0)
        just = placement[2] if len(placement) == 3 else placement[0] if len(placement) == 1 else 'lt'
        return (offset, just.strip())

    def _createWindows(self):
        self._windows = windows(name='MAIN', size=self.size, dataset=self._dataset, defaultCanvas=self._defaultCanvas)

        for name, config in self._pf['WINDOWS'].items():
            window = self._createSequence(name) if name in self._pf['SEQUENCES'] else \
                self._createCanvas(name) if name in self._pf['CANVASES'] else \
                self._createWidget(name, self._pf['WIDGETS'][name]) if name in self._pf['WIDGETS'] else \
                None
            if not window:
                raise ValueError(f'Cannot locate a sequence, canvas or widget named {name}')
            offset, just = self._adjustPlacement(config.get('placement', (0, 0, 'lt')))
            self._windows.append(window=window, offset=offset, just=just, z=config.get('z', windows.ZSTD), duration=config.get('duration', 0), minDuration=config.get('minDuration', 0), coolingPeriod=config.get('coolingPeriod', 0), condition=config.get('condition'))


    def _createSequence(self, name):
        if name in self._sequences:
            return self._sequences[name]

        if not name in self._pf['SEQUENCES']:
            raise ValueError(f'Cannot locate a sequence named {name}')

        cfg = self._pf['SEQUENCES'][name]
        items = []
        for si in cfg.get('items') or []:
            if si['name'] in self._pf['CANVASES']:
                w = self._createCanvas(si['name'])
            elif si['name'] in self._pf['WIDGETS']:
                w = self._createWidget(si['name'], self._pf['WIDGETS'][si['name']])
            else:
                raise ValueError(f"Cannot locate a canvas (or widget) named {si['name']}")

            duration = si.get('duration', 30)
            minDuration = si.get('minDuration', 0)
            condition = si.get('condition', 'True')
            items.append((w, duration, minDuration, condition))

        # name=None, size=None, placements=None
        s = sequence(name=name, size=cfg.get('size'), dataset=self._dataset)
        for se in items:
            s.append(item=se[0], duration=se[1], minDuration=se[2], condition=se[3])
        if 'effect' in cfg:
            s = self._addEffect(s, name, cfg)

        self._sequences[name] = s
        return s



    def _createCanvas(self, name):
        if name in self._canvases:
            return self._canvases[name]

        if not name in self._pf['CANVASES']:
            raise ValueError(f'Cannot locate a canvas named {name}')

        cfg = self._pf['CANVASES'][name]
        widgets = []
        for wi in cfg.get('items') or []:
            if wi['name'] in self._pf['CANVASES']:
                w = _createCanvas(wi['name'])
            elif wi['name'] in self._pf['WIDGETS']:
                w = self._createWidget(wi['name'], self._pf['WIDGETS'][wi['name']])
            else:
                raise ValueError(f"Cannot locate a canvas (or widget) named {wi['name']}")

            zorder = wi.get('z', canvas.ZSTD)
            # Placement is (x, y, just)
            # If placement includes all three values then use it
            # If placement only contains two then these are the offset values, use (x, y, 'lt')
            # If placement only has one value then this is the just, use (0, 0, just)
            offset, just = self._adjustPlacement(wi.get('placement', (0, 0, 'lt')))
            widgets.append((w, offset, just, zorder))

        # name=None, size=None, placements=None
        c = canvas(name=name, size=cfg['size'], dataset=self._dataset)
        for we in widgets:
            c.append(item=we[0], offset=we[1], just=we[2], z=we[3])
        if 'effect' in cfg:
            c = self._addEffect(c, name, cfg)

        self._canvases[name] = c
        return c

    def _createWidget(self, name, cfg):

        if name in self._widgets:
            return self._widgets[name]

        # Create any needed resources
        if 'font' in cfg:
            cfg['font'] = self._createFont(cfg['font'])
        if 'mask' in cfg:
            cfg['mask'] = self._findFile(cfg['mask'], 'images')
        if 'file' in cfg:
            cfg['file'] = self._findFile(cfg['file'], 'images')
        if 'widget' in cfg:
            if type(cfg['widget']) is str:
                cfg['widget'] = self._createWidget(None, self._pf['WIDGETS'][cfg['widget']])

        if 'type' not in cfg:
            raise KeyError(f'A widget type was not provided for {name}')
        if cfg['type'] not in self._wParams:
            raise TypeError(f"{cfg['type']} is not a valid widget.  Valid values are {self._wParams.keys()}")

        cfg['name'] = name
        cfg['dataset'] = self._dataset

        # Translate format/variable into value
        if cfg['type'] == 'text':
            if 'format' in cfg:
                if 'variables' in cfg:
                    cfg['value'] = "f\"{0}\"".format(cfg['format'].format(*[f'{{{i}}}' for i in cfg['variables']]))
                    del cfg['variables']
                else:
                    cfg['value'] = cfg['format']
                del cfg['format']
        elif cfg['type'] == 'progressBar':
            if 'variables' in cfg:
                cfg['value'] = cfg['variables'][0]
                del cfg['variables']

        kwargs = {k: v for k, v in cfg.items() if k in self._wParams[cfg['type']]}
        w = widget.__dict__[cfg['type']](**kwargs)

        if 'effect' in cfg:
            w = self._addEffect(w, name, cfg)

        if name:
            self._widgets[name] = w
        return w

    def _addEffect(self, w, name, cfg):
        if 'type' not in cfg['effect']:
            raise TypeError('Cannot add an effect to a widget without a containing type.  Options are (slide, scroll, or popUp)')
        if cfg['effect']['type'] not in ['scroll', 'slide', 'popUp']:
            raise TypeError(f"Cannot add a widget to an effect of type '{cfg['effect']['type']}'")
        cfg['effect']['widget'] = w
        w = self._createWidget(name, cfg['effect'])

        return w

    def _findFile(self, name, type):

        # If DEFAULTS/paths/type exists, add to search path
        try:
            search = [
                pathlib.Path(self._pf['DEFAULTS']['paths'][type]) / name,
                pathlib.Path(__file__).parent / self._pf['DEFAULTS']['paths'][type] / name
            ]
        except KeyError:
            search = []

        search = search + \
        [
            pathlib.Path(name),
            pathlib.Path(__file__).parent / f'../{type}' / name,
        ]

        for s in search:
            if s.exists():
                return s
        raise FileNotFoundError(f'FileNotFoundError: File {name} of type \'{type}\' not found')

    def _createFont(self, name):

        if name in self._fonts:
            return self._fonts[name]

        fnt = None
        if name in self._pf['FONTS']:
            cfg = self._pf['FONTS'][name]
            if cfg['type'] == 'BMFONT':
                p = self._findFile(cfg['file'], 'fonts')
                fnt = bmImageFont(p)
            elif cfg['type'].lower() == 'truetype':
                fnt = ImageFont.truetype(cfg['file'], int(cfg['size']))
        else:
            # Assume that name is a filename instead of a reference to a font description in FONTS
            fnt = bmImageFont(self._findFile(name, 'fonts'))
        if fnt:
            self._fonts[name] = fnt
        return fnt

    @staticmethod
    def _find(key, dictionary):
        for k, v in dictionary.items():
            if k == key:
                yield (k, v, dictionary)
            elif isinstance(v, dict):
                for result in tdLoader._find(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    if isinstance(d, dict):
                        for result in tdLoader._find(key, d):
                            yield result


    def _transform(self):
        # Convert Single line fonts in the format "{ 'name': 'filename' }" into standard format (e.g. { 'name': { 'file': 'filename', 'type':'BMFONT'}})
        self._pf['FONTS'] = {k: {'file': v, 'type': 'BMFONT'} if type(v) is str else v for k, v in self._pf['FONTS'].items()}

        # Convert sizes into tuples
        for k, v, d in self._find('size', self._pf):
            if type(v) is str and len(v.split(',')) > 1:
                d[k] = tuple([int(v.strip()) for v in v.split(',')])

        # Convert actions into tuples
        for k, v, d in self._find('actions', self._pf):
            if type(v) is list:
                d[k] = [(i.split(',')[0], int(i.split(',')[1])) if type(i) is str and len(i.split(',')) == 2 else
                i for i in v]

        # Convert placements into tuples
        for k, v, d in self._find('placements', self._pf):
            if type(v) is list:
                d[k] = [(i.split(',')[0], tuple([int(i) for i in i.split(',')[1:3]])) if type(i) is str and len(i.split(',')) == 3 else
                (i.split(',')[0], tuple([int(i) for i in i.split(',')[1:3]]), i.split(',')[3].strip("' \n")) if type(i) is str and len(i.split(',')) == 4 else
                i for i in v]

        # Convert placement into tuples
        for k, v, d in self._find('placement', self._pf):
            if type(v) is str and len(v.split(',')) >= 1:
                d[k] = tuple([v for v in v.split(',')])

        # Convert gap into tuples
        for k, v, d in self._find('gap', self._pf):
            if type(v) is str and len(v.split(',')) > 1:
                d[k] = tuple([v for v in v.split(',')])

        # Convert delay into tuples
        for k, v, d in self._find('delay', self._pf):
            if type(v) is str and len(v.split(',')) > 1:
                d[k] = tuple([int(v) for v in v.split(',')])

        # Convert singleton variables into lists
        for k, v, d in self._find('variables', self._pf):
            if type(v) is str:
                d[k] = [v]

        # Convert range string into tuple
        for k, v, d in self._find('range', self._pf):
            if type(v) is str:
                d[k] = tuple([i.strip() for i in v.split(',')])

        # Convert xy into four integer tuple
        for k, v, d in self._find('xy', self._pf):
            if type(v) is str:
                d[k] = tuple([int(i) for i in v.split(',')])

        # Convert canvas Z values into numeric values
        for k, v, d in self._find('z', self._pf):
            if type(v) is str:
                d[k] = { 'ZVHIGH': canvas.ZVHIGH, 'ZHIGH': canvas.ZHIGH, 'ZSTD': canvas.ZSTD }.get(v, v)


def load(file, dataset=None, displaySize=None, defaultCanvas=None):
    '''
    Initialize and return a tinyDisplay windows object from a tinyDisplay yaml file

    :param file: The filename of the tinyDisplay yaml file
    :type file: str
    :param dataset: A dataset to provide variables to any widgets which require them
    :type dataset: tinyDisplay.utility.dataset
    :param displaySize: A tuple containing the size of the display
    :type displaySize: (int, int)
    :param defaultWindow: A window (canvas) to display if there are no active windows
    :type defaultWindow: tinyDisplay.widget.canvas
    '''
    tdl = tdLoader(pageFile = file, dataset = dataset, displaySize = displaySize, defaultCanvas = defaultCanvas)
    tdl._createWindows()

    return tdl._windows
