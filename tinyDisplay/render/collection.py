# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
window enables a series of canvases to be displayed

.. versionadded:: 0.0.1
"""
import time
import bisect
import logging
from PIL import Image
from tinyDisplay.utility import dataset as Dataset
from tinyDisplay.render.widget import widget, image


class canvas(widget):

    # Standard Z levels
    ZSTD = 100
    ZHIGH = 1000
    ZVHIGH = 10000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._newWidget = True
        self._placements = []
        self._priorities = []
        self._reprVal = 'no widgets'


    def append(self, item=None, offset=None, just='lt', z=ZSTD):
        assert item, 'Attempted to append to canvas but did not provide an item to add'
        self._newWidget = True
        offset = offset or (0, 0)

        item.reset()

        # Place widget according to its z value
        pos = bisect.bisect_left(self._priorities, z)
        self._priorities.insert(pos, z)
        self._placements.insert(pos, (item, offset, just))

        self._reprVal = f'{len(self._placements) or "no"} widgets'


    def _renderWidgets(self, force=False, *args, **kwargs):
        notReady = {}

        # Check wait status for any widgets that have wait settings
        for i in self._placements:
            wid, off, anc = i
            if hasattr(wid, '_wait'):
                notReady[wid._wait] = not { 'atStart': wid.atStart, 'atPause': wid.atPause, 'atPauseEnd': wid.atPauseEnd }.get(wid._wait) or notReady.get(wid._wait, False)

        changed = False if not force and not self._newWidget and self.image else True
        results = []
        for i in self._placements:
            wid, off, anc = i

            if not force:
                # If widget has wait setting
                if hasattr(wid, '_wait'):
                    # Check to see if any widgets of this widgets wait type are not ready
                    if notReady[wid._wait]:
                        # If there are widgets waiting, see if this widget should still be
                        # rendered because it has not reached the point it should wait
                        if not { 'atStart': wid.atStart, 'atPause': wid.atPause, 'atPauseEnd': wid.atPauseEnd }.get(wid._wait):
                            img, updated = wid.render(force=force, *args, **kwargs)
                        else:
                            img = wid.image
                            updated = False
                    else:
                        # If everyone is ready, then it's ok to render all of the waiting widgets
                        img, updated = wid.render(force=force, *args, **kwargs)
                else:
                    # If this widget isn't part of a wait type, then it always gets rendered
                    img, updated = wid.render(force=force, *args, **kwargs)
            else:
                # If force then all widgets get rendered
                img, updated = wid.render(force=force, *args, **kwargs)

            if updated:
                changed = True
            results.append((img, off, anc))

        return (results, changed)


    def _render(self, force=False, *args, **kwargs):


        results, changed = self._renderWidgets(force, *args, **kwargs)

        # If any have changed, render a fresh canvas
        if changed:
            self._newWidget = False
            self.image = Image.new('1', self.size)
            for img, off, just in results:
                self._place(retainImage=True, wImage=img, offset=off, just=just)

        return (self.image, changed)


class windows(canvas):
    '''
    Create a collection of windows (e.g. canvases)

    :param name: The name to use for the collection
    :type name: str
    :param size: The size of the canvas that will contain the collection
    :type size: tuple(int, int)
    :param defaultCanvas: A canvas to display if no other windows are active
    :type defaultCanvas: tinyDisplay.render.widget.canvas
    '''

    def __init__(self, name=None, size=(0, 0), dataset = None, defaultCanvas=None, *args, **kwargs):

        self._defaultCanvas = defaultCanvas or image(image=Image.new('1', size)) # Set an empty image if no defaultCanvas provided

        super().__init__(name = name,
            size=(max(size[0], self._defaultCanvas.size[0]), max(size[1], self._defaultCanvas.size[1])), dataset = dataset, *args, **kwargs)

        self._windows = []
        self._reset()

    def _reset(self):
        self._tick = 0
        self._minTimer = {}
        self._inUse = set()
        self._cooling = {}
        self._duration = {}

    def append(self, window=None, offset=None, just=None, z=canvas.ZSTD, duration = 0, minDuration=0, coolingPeriod=0, condition='True'):
        '''
        Add a new window to the collection

        :param window: The canvas to add as a new window to the collection
        :type window: tinyDisplay.render.widget.canvas
        :param offset: The coordinates to place the canvas within the collections window
            relative to its just setting
        :type offset: str
        :param just: The justification to use when placing the canvas.  It is a two letter
            combination the determines the horizontal and vertical justification.  For horizontal
            the allowed values are l for left, m for middle, and r for right.  For vertical the allowed
            values are t for top, m for middle, and b for bottom.  Default is 'lt' for left and top.
        :type just: str
        :param z: The z value for this window.  Windows with higher values will be placed above
            windows with lower values.  Windows with equal z values with be placed in the order
            they were added with more recent windows being placed lower than windows added earlier
        :type z: int
        :param duration: Number of ticks to render a window after it is activated before deactivating it
        :type duration: int
        :param minDuration: the minimum amount time (in ticks) this canvas should remain active
            (even if its condition becomes False)
        :type minDuration: int
        :param coolingPeriod: Time (in ticks) required between activation of this window.  Even if
            condition is True this window will not be displayed again until the cooling period has expired
        :type coolingPeriod: int
        :param condition: boolean function to determine if the sequence is active.  Can either be a function or a
            string that 'evals' to a boolean.
        :type condition: function or str
        '''
        offset = offset if offset else (0, 0)
        just = just if just else 'lt'
        z = z or canvas.ZSTD

        # Compile condition
        condition = self._dataset.compile(condition) if type(condition) is str else condition

        # Add window to collection
        self._windows.append((window, offset, just, z, duration, minDuration, coolingPeriod, condition))

    def _render(self, force=False, *args, **kwargs):
        if force:
            self._reset()

        ct = self._tick

        # minDuration and cooling values are (startTime, duration)
        # a window that is cooling cannot be activated

        # Remove any window that's cooling period has ended
        self._cooling = {k: v for k, v in self._cooling.items() if v[0] + v[1] >= ct}

        # Remove any window that's minDuration period has ended
        self._minTimer = {k: v for k, v in self._minTimer.items() if v[0] + v[1] >= ct}

        # Remove any window that's Duration period has ended
        self._duration = {k: v for k, v in self._duration.items() if v[0] + v[1] >= ct}

        renderList = []
        # Look for active windows
        for w, o, j, z, dur, min, cool, cond in self._windows:
            # Reminder: w-window, o-offset, j-justification, z-z order, dur-max duration, min-min duration, cool-cooling period, cond-condition

            ''' If window is active and not in a cooling period (or still has time left
            from its minimum display timer) add it to the render list '''
            winActive = self._dataset.eval(cond)
            if (winActive and w not in self._cooling and w not in self._inUse) or \
                (winActive and w in self._inUse and (dur == 0 or w in self._duration)) or \
                w in self._minTimer:
                # When a window is newly activated, force render it and place it in the inUse record.
                # Also record start time in _active and _cooling
                inUse = False
                if w not in self._inUse:
                    self._inUse.add(w)
                    self._minTimer[w] = (ct-1, min)
                    self._cooling[w] = (ct-1, cool)
                    self._duration[w] = (ct-1, dur)
                    inUse = True
                renderList.append((w, w.render(force=inUse or force)[0], o, j, z))
            else:
                if w in self._inUse:
                    self._inUse.remove(w)

        if not self._inUse:
            renderList.append((self._defaultCanvas, self._defaultCanvas.render(force=True)[0], (0, 0), 'lt', canvas.ZSTD))

        c = canvas(size=self.size)
        for w, img, o, j, z in renderList:
            c.append(item=image(img), offset=o, just=j, z=z)

        self.image, result = c.render()
        self._tick += 1

        return self.image, result



class sequence(canvas):
    def __init__(self, name=None, size=(0, 0), dataset=None, defaultCanvas=None, *args, **kwargs):
        """
        Create a sequence of canvases

        :param name: the name of the new sequence
        :type name: str
        :param size: the requested size for the sequence
        :type size: tuple (int, int)
        :param dataset: shared dataset for all widgets, canvases, and sequences
        :type dataset: dict
        :param defaultCanvas: a canvas to return by render method when there are no active canvases
        :type defaultCanvas: tinyDisplay.render.widget
        """

        self._defaultCanvas = defaultCanvas or image(image=Image.new('1', (0, 0)))  # Set an empty image if no defaultCanvas provided

        size = size or (0, 0)
        super().__init__(name = name,
            size=(max(size[0], self._defaultCanvas.size[0]), max(size[1], self._defaultCanvas.size[1])), dataset=dataset, *args, **kwargs)

        self._place()
        self._canvases = []
        self._currentCanvas = None
        self._tick = 0
        self._minTimer = 0

        self.reset()  # Initialize starting time to now

    def __repr__(self):
        n = self.name if self.name else 'unnamed'

        return f'<sequence {n} at 0x{id(self):x}>'

    def append(self, item=None, duration=30, minDuration=0, condition='True'):
        """
        Add an item (either canvas or widget) to the sequence

        :param item: the canvas or widget to be added to the sequence
        :type item: tinyDisplay.render.canvas or tinyDisplay.render.widget
        :param duration: number of ticks this canvas will be rendered until it expires
        :type duration: int
        :param minDuration: the minimum amount of ticks this canvas should remain active (even if condition becomes False)
        :type minDuration: int
        :param condition: boolean function to determine if the canvas is active based the information contained within the dataset.  Can either be a function or a string that 'evals' to a boolean
        :type condition: function or str
        """
        assert item, 'Attempted to append to sequence but did not provide an item to add'
        condition = self._dataset.compile(condition) if type(condition) is str else condition
        self._canvases.append((item, duration, minDuration, condition))
        item.render(True)

        # Resize sequence's canvas as needed to fit any appended canvas
        mx = max(item.size[0], self._requestedSize[0])
        my = max(item.size[1], self._requestedSize[1])
        self._requestedSize = (mx, my)


    def _render(self, force=False, *args, **kwargs):
        if force:
            self.reset()

        c, new = self.activeCanvas()
        self._tick += 1
        self.image = c.image
        if not c:
            self.image = self._defaultCanvas.image
            return self._defaultCanvas.render()
        return c.render(new)


    def activeCanvas(self):
        """
        Determine and return the current canvas.

        :return: the currently active Canvas or None if no canvas is active and whether the activeCanvas is newly activated
        :rtype: (tinyDisplay.render.widget, bool)

        """
        flag = False
        cc = self._currentCanvas

        # Iterate through list of canvases to see which one should be active
        # list iterates one past the length of canvas list in case the current canvas has expired but should remain active
        # because it is the only active canvas
        for i in range(len(self._canvases) + 1):

            # If the canvas remains active and has not expired OR
            # the canvas still has some minimum time remaining
            if self._activeCanvas() and not self._expiredCurrentCanvas():

                # If canvas expired but winds up as the next active canvas anyway
                # then do not indicate that it is new
                flag = False if cc == self._currentCanvas else flag

                # If canvas is new set minTimer
                if flag:
                    self._minTimer = self._canvases[self._currentCanvas][2]

                return (self._canvases[self._currentCanvas][0], flag)

            flag = True
            self._reset()
            self._currentCanvas += 1
            if self._currentCanvas == len(self._canvases):
                self._currentCanvas = 0

        return (None, False)

    def reset(self):
        """
        Reset sequence to the beginning
        """
        self._currentCanvas = 0
        self._reset()

    def _activeCanvas(self):
        return (self._dataset.eval(self._canvases[self._currentCanvas][3]) or self._ticksRemainingCurrentCanvas())

    def _reset(self):
        """
        Reset canvas timer
        """
        self._tick = 0

    def _expiredCurrentCanvas(self):
        """
        Determine whether the current Canvas's time is expired

        :return: True if time has expired otherwise False
        :rtype: bool
        """
        if self._tick >= self._canvases[self._currentCanvas][1]:
            return True
        return False

    def _ticksRemainingCurrentCanvas(self):
        """
        Determine whether the current Canvas has ticks remaining (minimum time has not expired)

        :return: True if minimum time has not expired else False
        :rtype: bool
        """
        if self._tick >= self._minTimer:
            return False
        return True
