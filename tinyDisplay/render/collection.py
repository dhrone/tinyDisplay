# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Collection widgets to present, and animate the display canvases.

.. versionadded:: 0.0.1
"""
import bisect
from inspect import currentframe, getargvalues, getfullargspec, isclass

from PIL import Image

from tinyDisplay.render import collection
from tinyDisplay.render.widget import image, widget
from tinyDisplay.utility import getArgDecendents, getNotDynamicDecendents


class canvas(widget):
    """
    The Canvas class allows a group of widgets to be displayed together.

    Canvas is a subclass of widget and is a parent for all of the other
    container classes.  It is used to assemble a set of widgets together
    in relation to each other.  A canvas can contain any subclass of widget
    including other canvases.

    :param *args: Additional arguments to pass to parent `widget`
    :param **kwargs: Additional keyword arguments to pass to parent `widget`
    """

    # Standard Z levels
    ZSTD = 100
    ZHIGH = 1000
    ZVHIGH = 10000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._widgets_dict = {}
        self._placements = []
        self._activeList = []
        self._priorities = []
        self._reprVal = "no widgets"
        self._tick = 0  # Add tick counter

        if not hasattr(self, "size"):
            print(f"CANVAS {self.name} has no size")

    @staticmethod
    def _convertPlacement(p):
        # Convert placement into offset and justification values

        if type(p) is str:
            p = p.split(",")
            p = [i.strip() for i in p]

        if type(p) in [tuple, list]:
            if len(p) == 1:
                return ((0, 0), p[0])
            elif len(p) == 2:
                return ((int(p[0]), int(p[1])), "lt")
            elif len(p) == 3:
                return ((int(p[0]), int(p[1])), p[2])
        return ((0, 0), "lt")

    def append(self, item=None, placement=None, z=ZSTD):
        """
        Append new widget to canvas.

        :param item: The item (widget or canvas) to add to this canvas
        :type item: `tinyDisplay.render.widget`
        :param placement: Instruction on where to place the widget on the canvas
        :param z: The z order for the item.  Higher z order items get placed
            above lower ones.
        :type z: int

        ..Note:
            placements can be either a single justification value (e.g. 'lt'),
            an (x,y) tuple that places the item at that position on the canvas
            using the upper left corner as the origin, or an (x,y,just) tuple
            that places the widget using the requested justification and then
            offsets it by the provided x and y values.

            Possible justification values can be found in the `widget` documentation.

        ..Example:
            To place at the upper left: 'lt' (default)
            To place at the bottom right: 'rb'
            To place 20 pixels in from the left, and 10 pixels down from the top: (20, 10)
            To place 10 pixels above the center, middle: (0, -10, 'mm')
        """
        assert (
            item
        ), "Attempted to append to canvas but did not provide an item to add"
        self._newWidget = True

        offset, just = self._convertPlacement(placement)
        item._parent = self

        # Place widget according to its z value
        pos = bisect.bisect_left(self._priorities, z)
        self._priorities.insert(pos, z)
        self._placements.insert(pos, (item, offset, just))
        self._activeList.insert(pos, True)

        self._reprVal = f'{len(self._placements) or "no"} widgets'

        self.render(reset=True)

    def _renderWidgets(self, force=False, *args, **kwargs):
        # Increment tick counter
        self._tick += 1

        notReady = {}
        # Check wait status for any widgets that have wait settings
        for i in self._placements:
            wid, off, anc = i
            if hasattr(wid, "_wait") and wid._wait is not None:
                waiting = {
                    "atStart": wid.atStart,
                    "atPause": wid.atPause,
                    "atPauseEnd": wid.atPauseEnd,
                }.get(wid._wait)
                notReady[wid._wait] = not waiting or notReady.get(
                    wid._wait, False
                )

        changed = (
            False if not force and not self._newWidget and self.image else True
        )
        results = []

        for i, p in enumerate(self._placements):
            wid, off, anc = p

            if not force:
                # If widget has wait setting
                if hasattr(wid, "_wait"):
                    # Check to see if any widgets of this widgets wait type are not ready
                    if notReady[wid._wait]:
                        # If there are widgets waiting, see if this widget should still be
                        # rendered because it has not reached the point it should wait
                        if not {
                            "atStart": wid.atStart,
                            "atPause": wid.atPause,
                            "atPauseEnd": wid.atPauseEnd,
                        }.get(wid._wait):
                            img, updated = wid.render(
                                force=force, *args, **kwargs
                            )
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

            # Only display active widgets
            if wid.active:
                if not self._activeList[i]:
                    changed = True
                    self._activeList[i] = True
                results.append((img, off, anc))
            else:
                if self._activeList[i]:
                    changed = True
                    self._activeList[i] = False

        return (results, changed)

    def _render(self, force=False, newData=None, *args, **kwargs):
        results, changed = self._renderWidgets(force, *args, **kwargs)

        # If any have changed, render a fresh canvas
        if changed or newData:
            self._newWidget = False
            self.clear()
            for img, off, just in results:
                self._place(wImage=img, offset=off, just=just)

        return (self.image, changed)


class stack(canvas):
    """
    Container that expands to contain a set of widgets.

    Stack is a subclass of canvas.  As widgets are added to the stack,
    the stack expands in size to accomodate the new widgets.  This expansion
    can occur horizontally or vertically.

    :param orientation: Direction that stack grows.  Possible values are 'horizonal' and 'vertical'
    :type orientation: str
    :param gap: the number of pixels that separate each widget in the stack
    :type gap: int
    :param *args: Additional arguments to pass to parent `widget`
    :param **kwargs: Additional keyword arguments to pass to parent `widget`
    """

    def __init__(self, orientation="horizontal", gap=0, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self._orientation = orientation

        self._widgets = []
        self._gap = gap
        self._cached_size = None
        self._newWidget = False  # Keep tracking widget changes
        self.render(reset=True)

    def append(self, item=None, gap=None):
        """
        Add a new widget (or widgets) to the stack.

        Widgets are added left to right for horizontal orientation or top to
        bottom for vertical orientation.

        :param item: A widget to add to the stack
        :type item: `tinyDisplay.render.widget`
        :param gap: The number of pixels to place between this widget and the
            next widget in the stack.  This value can also be set at the
            stack level if you want the same gap between every widget
        :type gap: int
        """
        if item is not None:
            self._widgets.append((item, gap))
            self._reprVal = f'{len(self._widgets) or "no"} widgets'
            self._newWidget = True  # Set flag when widget is added
            self._cached_size = None  # Invalidate size cache
            self._render(force=True)

    def _computeSize(self):
        # Only recompute if widgets have changed or cache is None
        if self._cached_size is not None and not self._newWidget:
            return self._cached_size

        x = 0
        y = 0
        gap = 0
        if self._orientation == "horizontal":
            for w, g in self._widgets:
                if w.active:
                    gap = g if g is not None else self._gap
                    x += w.size[0] + gap
                    y = max(y, w.size[1])
            x -= gap
        else:
            for w, g in self._widgets:
                if w.active:
                    gap = g if g is not None else self._gap
                    x = max(x, w.size[0])
                    y += w.size[1] + gap
            y -= gap

        self._cached_size = (x, y)
        self._newWidget = False  # Reset flag after computing new size
        return self._cached_size

    def _render(self, force=False, newData=None, *args, **kwargs):
        changed = False or force
        for w, g in self._widgets:
            if w.render(force=force)[1]:
                changed = True

        if changed or newData:
            x, y = self._computeSize()
            img = Image.new(self._mode, (x, y), self._background)
            if self._orientation == "horizontal":
                o = 0
                for w, g in self._widgets:
                    if w.active:
                        gap = g if g is not None else self._gap
                        img.paste(w.image, (o, 0))
                        o += w.image.size[0] + gap
            else:
                o = 0
                for w, g in self._widgets:
                    if w.active:
                        gap = g if g is not None else self._gap
                        img.paste(w.image, (0, o))
                        o += w.image.size[1] + gap

            self.clear(img.size)
            self._place(wImage=img, just=self.just)

        return (self.image, changed)


class index(canvas):
    """
    Display one from a set of widgets.

    Index is a subclass of canvas and is used to display one of a set of
    widgets based on the index's current value.  This is useful when
    there are several variants of an image that need to be rendered based upon
    the current state of a system.  As example: a volume icon that goes from
    muted up to full volume in a set of five images (muted, off, low, med, high)

    :param value: A `dynamic` value used to determine which image to display
    :param *args: Additional arguments to pass to parent `widget`
    :param **kwargs: Additional keyword arguments to pass to parent `widget`
    """

    def __init__(self, value=0, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self._initArguments(
            getfullargspec(index.__init__), getargvalues(currentframe())
        )
        self._evalAll()

        self._widgets = []
        self._max = (0, 0)

        self.render(reset=True)

    def append(self, item=None):
        """
        Add a new widget to the index.

        :param item:  Item to add to widget
        :type item: `tinyDisplay.render.widget`
        """

        if item is None:
            return

        self._widgets.append(item)
        self._reprVal = f'{len(self._widgets) or "no"} widgets'
        self.render(force=True)

    def _calculateSize(self):
        if self._size is None:
            x, y = 0, 0
            for w in self._widgets:
                x = max(x, w.size[0])
                y = max(y, w.size[1])
            return (x, y)
        else:
            return self._size

    def _render(self, force=False, newData=None, *args, **kwargs):
        img = None
        changed = None
        value = self._value
        try:
            img, changed = self._widgets[value].render(force=force)
        except IndexError:
            if hasattr(self, "image"):
                img = self.image

        if changed or newData:
            self.clear(self._calculateSize())
            self._place(wImage=img, just=self.just)
        changed = changed or newData

        return (self.image, changed)


class sequence(canvas):  # noqa: D101
    """
    Display a sequence of widgets.

    Sequence is a subclass of canvas and is used to display a sequence
    of widgets in the order they are added to the sequence.  When a widget's
    turn arrives, it is displayed if active.

    See the documentation for `tinyDisplay.render.widget` to see how the
    active state of widgets are managed.

    :param defaultCanvas: a canvas to display when there are no active canvases
    :type defaultCanvas: tinyDisplay.render.widget
    :param *args: Additional arguments passed to parent `widget`

    # noqa: DAR101
    """

    def __init__(
        self,
        defaultCanvas=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        size = self._size or (0, 0)
        self._defaultCanvas = defaultCanvas or image(
            image=Image.new(self._mode, size, self._background)
        )  # Set an empty image if no defaultCanvas provided

        self._canvases = []
        self._currentCanvas = None
        self.render(reset=True)

    def __repr__(self):
        n = self.name if self.name else "unnamed"

        return f"<sequence {n} at 0x{id(self):x}>"

    def append(self, item=None):
        """
        Add an item (either canvas or widget) to the sequence.

        :param item: the canvas or widget to be added to the sequence
        :type item: tinyDisplay.render.canvas or tinyDisplay.render.widget
        """
        assert (
            item
        ), "Attempted to append to sequence but did not provide an item to add"
        self._canvases.append(item)
        item.render(force=True)

        # Resize sequence's canvas as needed to fit any appended canvas
        rs = self._size or (0, 0)
        mx = max(item.size[0], rs[0])
        my = max(item.size[1], rs[1])
        self._size = (mx, my)
        self._currentCanvas = 0
        self.render(force=True)

    def _computeSize(self):
        mx, my = self._size or (0, 0)
        if len(self._canvases) == 0:
            dcs = self._defaultCanvas.size
            mx, my = max(dcs[0], mx), max(dcs[1], my)
        else:
            for item in self._canvases:
                mx, my = max(item.size[0], mx), max(item.size[1], my)
        return (mx, my)

    def _render(self, force=False, newData=None, *args, **kwargs):
        if force:
            self.resetMovement()
            self._currentCanvas = 0 if len(self._canvases) > 0 else None

        img, new = self.activeCanvas(force)
        if not img:
            img, new = self._defaultCanvas.render()
        if new or newData:
            self.clear(self._computeSize())
            self._place(wImage=img, just=self.just)
        return (self.image, new or force)

    def activeCanvas(self, force=False):
        """
        Determine and return the current canvas.

        :param force: Set force True to force the canvas to re-render itself
        :type force: bool
        :returns: the currently active Canvas or None if no canvas is active
            and whether the activeCanvas is newly activated
        :rtype: (tinyDisplay.render.widget, bool)
        """
        if self._currentCanvas is None:
            return (None, False)

        img, changed = self._canvases[self._currentCanvas].render(force=force)
        if self._canvases[self._currentCanvas].active:
            return img, changed

        # Iterate through list of canvases to see which one should be active.
        for i in range(len(self._canvases) - 1):
            self._currentCanvas = (
                self._currentCanvas + 1
                if self._currentCanvas < len(self._canvases) - 1
                else 0
            )
            img, changed = self._canvases[self._currentCanvas].render(
                force=True
            )
            if self._canvases[self._currentCanvas].active:
                # New canvas selected
                return (img, True)

        self._currentCanvas = (
            self._currentCanvas + 1
            if self._currentCanvas < len(self._canvases) - 1
            else 0
        )
        # Didn't find any new canvases to display so see if the old canvas is now active
        img, changed = self._canvases[self._currentCanvas].render(force=force)
        if self._canvases[self._currentCanvas].active:
            return img, changed

        # No active canvas found
        return (None, False)


PARAMS = {
    k: getArgDecendents(v)
    for k, v in collection.__dict__.items()
    if isclass(v) and issubclass(v, canvas)
}

for k, v in PARAMS.items():
    nv = list(v)
    NDD = getNotDynamicDecendents(collection.__dict__[k])
    for arg in v:
        if arg not in NDD:
            nv.append(f"d{arg}")
    PARAMS[k] = nv
