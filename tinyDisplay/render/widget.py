# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Widgets for the tinyDisplay system.

.. versionadded:: 0.0.1
"""
import abc
import logging
import os
import pathlib
from inspect import isclass
from urllib.request import urlopen

from PIL import Image, ImageColor, ImageDraw

from tinyDisplay import globalVars
from tinyDisplay.exceptions import DataError
from tinyDisplay.font import bmImageFont
from tinyDisplay.render import widget as Widgets
from tinyDisplay.utility import (
    dataset as Dataset,
    evaluator,
    getArgDecendents,
    image2Text,
    okPath,
)


class widget(metaclass=abc.ABCMeta):
    """
    Base class for all widgets.

    :param name: The name of the widget (optional)
    :type name: str
    :param size: the max size of the widget (x,y) in pixels
    :type size: (int, int)
    :param dataset: dataset to be used for any arguments that are evaluated during run-time
    :type dataset: `tinyDisplay.utility.dataset`
    :param foreground: The color to use for any foreground parts of the widget
    :type foreground: str, int, or tuple
    :param foreground: The color to use for any background parts of the widget
    :type foreground: str, int, or tuple
    :param just: The justification to use when placing the widget on its image.
    :type just: str
    """

    def __init__(
        self,
        name=None,
        size=None,
        activeWhen=True,
        duration=None,
        minDuration=None,
        coolingPeriod=None,
        dataset=None,
        mode="RGBA",
        foreground="'white'",
        background=None,
        just="lt",
    ):

        self._debug = globalVars.__DEBUG__
        self._localDB = {"__self__": {}, "__parent__": {}}
        self._dataset = (
            dataset if isinstance(dataset, Dataset) else Dataset(dataset)
        )
        self._dV = evaluator(
            self._dataset, localDataset=self._localDB, debug=self._debug
        )

        self.name = name
        self.just = just.lower()
        self.type = self.__class__.__name__
        self.current = None
        self._reprVal = None

        # Initialize logging system
        self._logger = logging.getLogger("tinyDisplay")

        # Active State variables
        self._tick = 0
        self._normalDuration = duration
        self._currentDuration = duration
        self._minDuration = minDuration
        self._currentMinDuration = 0
        self._coolingPeriod = coolingPeriod
        self._currentCoolingPeriod = 0
        self._currentActiveState = False

        assert mode in (
            "1",
            "L",
            "LA",
            "RGB",
            "RGBA",
        ), "TinyDisplay only supports PIL modes 1, L, LA, RGB, and RGBA"
        self._mode = mode

        bgDefault = (0, 0, 0, 0) if self._mode == "RGBA" else "'black'"

        self._dV.compile(size, name="requestedSize", default=None)
        self._dV.compile(activeWhen, name="activeWhen", default=True)
        self._dV.compile(foreground, name="foreground", default="white")
        self._dV.compile(
            background or bgDefault, name="background", default=bgDefault
        )
        self._dV.evalAll()
        self.clear()  # Create initial canvas

        # Establish initial values for local DB
        self._computeLocalDB()

    def __getattr__(self, name):
        msg = f"{self.__class__.__name__} object has no attribute {name}"
        if "image" not in self.__dict__:
            raise AttributeError(msg)
        if name in dir(self.image):
            return getattr(self.image, name)
        else:
            raise AttributeError(msg)

    def __repr__(self):
        cw = ""
        n = self.name if self.name else "unnamed"
        v = f"value({self._reprVal}) " if self._reprVal else ""
        return f"<{n}.{self.type} {v}size{self.size} {cw}at 0x{id(self):x}>"

    def __str__(self):
        if self.image:
            return image2Text(self.image, self._dV["background"])
        return "image empty"

    def _computeLocalDB(self):
        wdb = {
            "size": self.size,
            "name": self.name,
            "just": self.just,
        }
        pdb = (
            {
                "size": self._parent.size,
                "name": self._parent.name,
                "just": self._parent.just,
            }
            if hasattr(self, "_parent")
            else {}
        )

        self._localDB["__self__"] = wdb
        self._localDB["__parent__"] = pdb

    def clear(self, size=(0, 0)):
        """
        Clear the image.

        Reset the existing image to a blank image.  The blank image will be
        set to the size provided when the widget was created.  If no size
        was provided when the widget was instantiated, then it will use the size
        provided as input to the clear method.

        :param size: Sets the size of the cleared image
        :type size: tuple(int, int)

        ..Note:
            If size is not provided, clear will use the size requested when
            the widget was originally created.  If no size was originally
            provided, clear will produce a blank image that has size (0, 0).
        """
        self.image = None
        size = self._dV["requestedSize"] or size
        self.image = Image.new(self._mode, size, self._dV["background"])

    @property
    def active(self):
        """
        Return active state of widget.

        Widgets default to being active but if an active test was provided
        during instantiation it will be evaluated to determine if the widget
        is currently active

        :returns: True when the widget is active
        :rtype: bool

        ..note:
            This property is not guaranteed to be accurate unless used right
            after a render is completed
        """

        result = False
        isActive = self._dV["activeWhen"]

        # If currentCoolingPeriod has time left return False
        if self._coolingPeriod is not None and self._currentCoolingPeriod > 0:
            result = False
        # If min duration timer has time left return True
        elif self._minDuration is not None and self._currentMinDuration > 0:
            result = True
        # If duration timer has time left and activeWhen is True
        elif self._normalDuration is not None:
            result = self._currentDuration > 0 and isActive
        else:
            # Else return activeWhen
            result = isActive

        if self._currentActiveState is False and result is True:
            self._resetDurationTimers()
        if self._currentActiveState is True and result is False:
            self._resetCoolingTimer()
        self._currentActiveState = result
        return result

    def _resetDurationTimers(self):
        """Reset Timers when widget newly becomes active."""
        if self._normalDuration is not None:
            self._currentDuration = self._normalDuration

        if self._minDuration is not None:
            self._currentMinDuration = self._minDuration

    def _resetCoolingTimer(self):
        if self._coolingPeriod is not None:
            self._currentCoolingPeriod = self._coolingPeriod

    def _updateTimers(self, reset=False):
        """
        Maintain the current state of the duration, minDuration and coolingPeriod timers.

        :param reset: Resets all of the widget timers
        :type reset: bool
        """

        isActive = self.active
        if reset:
            self._currentDuration = self._normalDuration
            self._currentMinDuration = self._minDuration if isActive else 0
            self._currentCoolingPeriod = 0
        else:
            if self._normalDuration is not None:
                """If duration has expired, reset it to its starting value else
                decrement it by one.  This allows active to go false after the
                render that exhausts duration then return to True at the next
                call to render"""
                self._currentDuration = (
                    self._normalDuration
                    if self._currentDuration < 1
                    else self._currentDuration - 1
                )
            if self._minDuration is not None:
                self._currentMinDuration = self._currentMinDuration - 1
            if (
                self._coolingPeriod is not None
                and self._currentCoolingPeriod > 0
            ):
                self._currentCoolingPeriod = self._coolingPeriod = (
                    self._currentCoolingPeriod - 1
                )

    def resetMovement(self):
        """Reset widget back to starting position."""
        if hasattr(self, "_resetMovement"):
            self._resetMovement()
        self._tick = 0

    def _place(self, wImage=None, offset=(0, 0), just="lt"):
        just = just or "lt"
        offset = offset or (0, 0)
        assert (
            just[0] in "lmr" and just[1] in "tmb"
        ), f"Requested justification \"{just}\" is invalid.  Valid values are left top ('lt'), left middle ('lm'), left bottom ('lb'), middle top ('mt'), middle middle ('mm'), middle bottom ('mb'), right top ('rt'), right middle ('rm'), and right bottom ('rb')"

        # if there is an image to place
        if wImage:
            mh = round((self.image.size[0] - wImage.size[0]) / 2)
            r = self.image.size[0] - wImage.size[0]

            mv = round((self.image.size[1] - wImage.size[1]) / 2)
            b = self.image.size[1] - wImage.size[1]

            a = (
                0
                if just[0] == "l"
                else mh
                if just[0] == "m"
                else r
                if just[0] == "r"
                else 0
            )
            b = (
                0
                if just[1] == "t"
                else mv
                if just[1] == "m"
                else b
                if just[1] == "b"
                else 0
            )

            pos = (offset[0] + a, offset[1] + b)
            mask = wImage if wImage.mode in ["RGBA", "L"] else None
            self.image.paste(wImage, pos, mask=mask)
            return (pos[0], pos[1])
        else:
            # If not return position 0, 0
            return (0, 0)

    def render(
        self, force=False, tick=None, move=True, reset=False, newData=False
    ):
        """
        Compute image for widget.

        Compute current image based upon widgets configuration and the current
        dataset values.

        :param force: Set force True to force the widget to re-render itself
        :type force: bool
        :param tick: Change the current tick (e.g. time) for animated widgets
        :type tick: int
        :param move: Determine whether time moves forward during the render.
            Default is True.
        :type move: bool
        :param reset: Return animated widgets to their starting position
        :type reset: bool
        :param newData: Render widget regardless of change in data
        :type newData: bool
        :returns: a 2-tuple with the widget's current image and a flag to
            indicate whether the image has just changed.  If force was set, it
            will always return changed
        :rtype: (PIL.Image, bool)
        :raises DataError: When the dynamic values of the widget cannot
            be successfully evaluated (debug mode only)
        :raises Exception: When any other exception occurs during render (debug
            mode only)
        """
        self._computeLocalDB()

        if reset:
            force = True

        try:
            nd = self._dV.evalAll()
        except DataError as ex:
            if self._debug:
                raise
            else:
                self._logger.warning(
                    f"Unable to evaluate widget variables: {ex}"
                )
                return (self.image, False)

        if force:
            self.resetMovement()

        img = self.image
        changed = False

        try:
            img, changed = self._render(
                force=force, tick=tick, move=move, newData=nd or newData
            )
        except Exception as ex:
            if self._debug:
                raise
            else:
                self._logger.warning(f"Render for {self.name} failed: {ex}")
                return (img, False)

        self._updateTimers(force)

        return (img, changed)

    @abc.abstractmethod
    def _render(self, *args, **kwargs):
        pass  # pragma: no cover


_textDefaultFont = bmImageFont(
    pathlib.Path(__file__).parent / "fonts/hd44780.fnt"
)


class text(widget):
    """
    text widget.

    Displays a line of text based upon the provided evaluation value

    :param value: The value to evaluate
    :type value: str
    :param font: the font that should be used to render the value.  If not supplied
        a default font will be used which is similar to fonts used on HD44780 style devices
    :type font: `PIL.ImageFont`
    :param lineSpacing: The number of pixels to add between lines of text (default 0)
    :type lineSpacing: int
    """

    def __init__(
        self,
        value=None,
        font=None,
        antiAlias=False,
        lineSpacing=0,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        font = font or _textDefaultFont
        self.font = font
        self._fontMode = "L" if antiAlias else "1"
        self.lineSpacing = lineSpacing
        self._tsDraw = ImageDraw.Draw(Image.new("1", (0, 0), 0))
        self._tsDraw.fontmode = self._fontMode
        self._dV.compile(value, name="value", default="")
        self.render(reset=True)

    def _render(self, force=False, newData=False, *args, **kwargs):

        # If the string to render has not changed then return current image
        if not newData and not force:
            return (self.image, False)

        value = str(self._dV["value"])
        self._reprVal = f"'{value}'"

        tSize = self._tsDraw.textsize(
            value, font=self.font, spacing=self.lineSpacing
        )
        tSize = (0, 0) if tSize[0] == 0 else tSize

        img = Image.new(self._mode, tSize, self._dV["background"])
        if img.size[0] != 0:
            d = ImageDraw.Draw(img)
            d.fontmode = self._fontMode
            just = {"l": "left", "r": "right", "m": "center"}.get(self.just[0])
            d.text(
                (0, 0),
                value,
                font=self.font,
                fill=self._dV["foreground"],
                spacing=self.lineSpacing,
                align=just,
            )

        self.clear(img.size)
        self._place(wImage=img, just=self.just)
        return (self.image, True)


class progressBar(widget):
    """
    progressBar widget.  Shows percent completion graphically.

    :param value: Current value to display (EVAL)
    :type value: str
    :param range: Pair of values that form the range of possible values.  The progressBar
        will show how far the current value is between the low and high ends of the range. Both the start and end of the range are evaluated values. (EVAL)
    :type range: (str, str)
    :param mask: A `PIL.Image` or filename for a image to use as a mask
    :type mask: `PIL.Image` or str
    :param direction: The direction to fill from when filling in the progressBar.  Values are
        'ltr' for left to right, 'rtl' for right to left, 'ttb' for top to bottom and 'btt'
        for bottom to top.
    :type direction: str

    ..note:
        You can supply a mask or a barSize but not both.

        If using a mask, your PIL.Image must contain a region within
        the image that is transparent.
    """

    def __init__(
        self,
        value=None,
        range=None,
        mask=None,
        fill=None,
        opacity=0,
        direction="ltr",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._dV.compile(fill, "fill", "white")
        self._opacity = opacity
        self.direction = direction.lower()

        size = self._dV["requestedSize"]
        self.mask = (
            mask
            if mask
            else self._defaultMask(
                size,
                self._mode,
                self._dV["foreground"],
                self._dV["background"],
                self._opacity,
            )
        )
        if type(mask) in [str, pathlib.PosixPath]:
            self.mask = Image.open(pathlib.PosixPath(mask))

        self._dV.compile(range or (0, 100), name="range", default=(0, 100))
        self._dV.compile(value, name="value", default="")
        self.render(reset=True)

    @staticmethod
    def _defaultMask(size, mode, foreground, background, opacity):
        mode = (
            "L"
            if mode in ("1", "L", "LA")
            else "RGBA"
            if mode in ("RGB", "RGBA")
            else "RGBA"
        )

        # Convert color name into color value if needed
        if type(background) is str:
            background = ImageColor.getcolor(background, mode)

        # Add opacity to background color value
        # Note: Removes any existing opacity (e.g. alpha value)
        if mode == "RGBA":
            if type(background) is int:
                background = (background, opacity)
            else:
                background = (
                    background[0:-1] + (opacity,)
                    if len(background) in (2, 4)
                    else background + (opacity,)
                )
        else:
            background = opacity

        img = Image.new(mode, size, background)
        d = ImageDraw.Draw(img)
        if size[0] - 1 < 3 or size[1] - 1 < 3:
            d.rectangle(
                (0, 0, size[0] - 1, size[1] - 1),
                fill=background,
                outline=background,
            )
        else:
            d.rectangle(
                (0, 0, size[0] - 1, size[1] - 1),
                fill=background,
                outline=foreground,
            )
        return img

    @staticmethod
    def _getScaler(scale, range):
        # Convert scale and range if needed
        scale = float(scale) if type(scale) in [str, int] else scale
        r0 = float(range[0]) if type(range[0]) in [str, int] else range[0]
        r1 = float(range[1]) if type(range[1]) in [str, int] else range[1]

        if scale < r0 or scale > r1:
            scale = r0 if scale < r0 else r1

        rangeSize = r1 - r0
        return (scale - r0) / rangeSize

    def _render(self, force=False, newData=False, *args, **kwargs):
        if not newData and not force:
            return (self.image, False)

        value = self._dV["value"]
        range = self._dV["range"]
        scale = self._getScaler(value, range)

        self._reprVal = f"{scale*100:.1f}%"

        size = self.mask.size
        dir = self.direction

        (w, h) = (
            (size[0], round(size[1] * scale))
            if dir in ["ttb", "btt"]
            else (round(size[0] * scale), size[1])
        )
        (px, py) = (
            (0, 0)
            if dir in ["ltr", "ttb"]
            else (size[0] - w, 0)
            if dir == "rtl"
            else (0, size[1] - h)
        )

        # Build Fill

        fill = Image.new(self._mode, size, self._dV["background"])
        fill.paste(
            Image.new(
                self._mode, (w, h), self._dV["fill"] or self._dV["foreground"]
            ),
            (px, py),
        )
        fill.paste(self.mask, (0, 0), self.mask)

        self.clear(fill.size)
        self._place(wImage=fill, just=self.just)
        return (self.image, True)


class marquee(widget):
    """
    Base class for the animated scroll, slide and popup classes.

    :param: widget: The widget that will be animated
    :type widget: `tinyDisplay.render.widget`
    :param resetOnChange: Determines whether to reset the contained widget to its starting
        position if the widget changes value
    :type resetOnChange: bool
    :param actions: A list of instructions for how the widget should move.  Each
        value in the list is a tuple containing a command/direction and an optional
        integer parameter
    :type actions: [(str, int)]
    :param speed: Determines the number of ticks between moves of the object.  A speed of
        of 1 will move the widget every tick.  A speed of 2, every two ticks, etc.  This combined with distance determines how fast the widget moves.  Larger speed values
        will decrease the speed at which the widget appears to move.
    :type speed: int
    :param distance: Determines how many pixels to move per tick.  Larger values will
        make the widget appear to move faster.
    :type distance: int
    :param moveWhen: A function or evaluatable statement to determine whether the
        widget should be moved.  If the statement returns True, the animation will
        continue, or False, the animation will be paused. If not provided, a default
        will be used that is appropriate to the subclass.
    :type moveWhen: `function` or str
    """

    def __init__(
        self,
        widget=None,
        resetOnChange=True,
        actions=[("rtl",)],
        speed=1,
        distance=1,
        moveWhen=None,
        wait=None,
        gap=None,
        *args,
        **kwargs,
    ):
        assert widget, "No widget supplied to initialize scroll"
        super().__init__(*args, **kwargs)

        self._timeRatio = int(speed)
        self._widget = widget
        self._resetOnChange = resetOnChange
        self._actions = []
        for a in actions:
            a = a if type(a) == tuple else (a,)
            self._actions.append(a)
        self._distance = int(distance)
        self._timeline = []
        self._tick = 0

        assert wait in [
            "atStart",
            "atPause",
            "atPauseEnd",
            None,
        ], f"{0} is an invalid wait type.  Supported values are 'atStart', 'atPause' or 'atPauseEnd'"
        if wait:
            self._wait = wait

        self._dV.compile(
            moveWhen or self._shouldIMove, name="moveWhen", default=""
        )
        if gap is not None:
            self._dV.compile(gap, name="gap", default=(0, 0))

        self.render(reset=True, move=False)

    @abc.abstractmethod
    def _shouldIMove(self, *args, **kwargs):
        pass  # pragma: no cover

    @abc.abstractmethod
    def _computeTimeline(self):
        pass  # pragma: no cover

    @abc.abstractmethod
    def _adjustWidgetSize(self):
        pass  # pragma: no cover

    # The at properties can be used by a controlling system to coordinate pauses between multiple marquee objects
    @property
    def atPause(self):
        """
        Has animation reached the start of a pause action.

        :returns: True if yes, False if No
        :rtype: bool
        """
        if (self._tick - 1) % len(self._timeline) in self._pauses:
            return True
        return False

    @property
    def atPauseEnd(self):
        """
        Has animation reached the end of a pause action.

        :returns: True if yes, False if No
        :rtype: bool
        """
        if (self._tick - 1) % len(self._timeline) in self._pauseEnds:
            return True
        return False

    @property
    def atStart(self):
        """
        Has an animation return to it's starting position.

        :returns: True if yes, False if No
        :rtype: bool
        """
        if not (self._tick - 1) % len(self._timeline):
            return True
        return False

    def _addPause(self, length, startingPos, tickCount):
        self._pauses.append(tickCount)
        tickCount += int(length)
        for i in range(int(length)):
            self._timeline.append(startingPos)
        return tickCount

    def _addMovement(self, length, direction, startingPos, tickCount):
        curPos = startingPos
        self._pauseEnds.append(tickCount)

        # If this is the first timeline entry, add a starting position
        if not tickCount:
            self._timeline.append(curPos)
            tickCount = 1

        for _ in range(length // self._distance):
            dir = (
                (self._distance, 0)
                if direction == "ltr"
                else (-self._distance, 0)
                if direction == "rtl"
                else (0, self._distance)
                if direction == "ttb"
                else (0, -self._distance)
            )
            curPos = (curPos[0] + dir[0], curPos[1] + dir[1])

            for _ in range(self._timeRatio):
                self._timeline.append(curPos)
                tickCount += 1
        return (curPos, tickCount)

    def _resetMovement(self):
        self.clear()
        self._tick = 0
        self._pauses = []
        self._pauseEnds = []
        self._adjustWidgetSize()
        tx, ty = self._place(wImage=self._aWI, just=self.just)
        self._curPos = self._lastPos = (tx, ty)
        self._timeline = []
        self._computeTimeline()

    @staticmethod
    def _withinDisplayArea(pos, d):
        if (
            (pos[0] >= 0 and pos[0] < d[0])
            or (pos[2] >= 0 and pos[2] < d[0])
            or (pos[0] < 0 and pos[2] >= d[0])
        ) and (
            (pos[1] >= 0 and pos[1] < d[1])
            or (pos[3] >= 0 and pos[3] < d[1])
            or (pos[1] < 0 and pos[3] >= d[1])
        ):
            return True
        return False

    @staticmethod
    def _enclosedWithinDisplayArea(pos, d):
        if (
            (pos[0] >= 0 and pos[0] <= d[0])
            and (pos[2] >= 0 and pos[2] <= d[0])
        ) and (
            (pos[1] >= 0 and pos[1] <= d[1])
            and (pos[3] >= 0 and pos[3] <= d[1])
        ):
            return True
        return False

    @abc.abstractmethod
    def _paintScrolledWidget(self):
        pass  # pragma: no cover

    def _render(self, force=False, tick=None, move=True, newData=False):
        self._tick = tick or self._tick
        img, updated = self._widget.render(
            force=force, tick=tick, move=move, newData=newData
        )
        if updated:
            self._adjustWidgetSize()
        if (updated and self._resetOnChange) or force:
            self._resetMovement()
            self._tick = self._tick + 1 if move else self._tick
            return (self.image, True)

        moved = False
        self._curPos = self._timeline[self._tick % len(self._timeline)]

        if self._curPos != self._lastPos or updated:
            self.image = self._paintScrolledWidget()
            moved = True
            self._lastPos = self._curPos

        self._tick = (
            (self._tick + 1) % len(self._timeline) if move else self._tick
        )
        return (self.image, moved)


class slide(marquee):
    """Slides a widget from side to side or top to bottom."""

    def _shouldIMove(self, *args, **kwargs):
        return self._enclosedWithinDisplayArea(
            (
                self._curPos[0],
                self._curPos[1],
                self._curPos[0] + self._widget.image.size[0],
                self._curPos[1] + self._widget.image.size[1],
            ),
            (self.size),
        )

    def _adjustWidgetSize(self):
        self._aWI = self._widget.image

    def _boundaryDistance(self, direction, pos):
        return (
            pos[0]
            if direction == "rtl"
            else self.size[0] - (pos[0] + self._widget.size[0])
            if direction == "ltr"
            else pos[1]
            if direction == "btt"
            else self.size[1] - (pos[1] + self._widget.size[1])
        )

    def _returnToStart(self, direction, curPos, tickCount):
        sp = self._timeline[0]

        dem = 0 if direction[0] == "h" else 1
        for i in range(2):
            dir = (
                "rtl"
                if dem == 0 and curPos[dem] > sp[dem]
                else "ltr"
                if dem == 0 and curPos[dem] < sp[dem]
                else "btt"
                if dem == 1 and curPos[dem] > sp[dem]
                else "ttb"
            )
            curPos, tickCount = self._addMovement(
                abs(curPos[dem] - sp[dem]), dir, curPos, tickCount
            )
            dem = 0 if dem == 1 else 1

        return (curPos, tickCount)

    def _computeTimeline(self):
        if self._dV["moveWhen"]:
            self._reprVal = "sliding"
            tickCount = 0
            curPos = self._curPos

            for a in self._actions:
                a = a if type(a) == tuple else (a,)
                if a[0] == "pause":
                    tickCount = self._addPause(a[1], curPos, tickCount)
                elif a[0] == "rts":
                    dir = "h" if len(a) == 1 else a[1]
                    curPos, tickCount = self._returnToStart(
                        dir, curPos, tickCount
                    )
                else:
                    distance = (
                        self._boundaryDistance(a[0], curPos)
                        if len(a) == 1
                        else a[1]
                    )
                    curPos, tickCount = self._addMovement(
                        distance, a[0], curPos, tickCount
                    )
        else:
            self.reprVal = "not sliding"
            self._timeline.append(self._curPos)

    def _paintScrolledWidget(self):
        self.clear()
        self.image.paste(self._aWI, self._curPos, self._aWI)
        return self.image


class popUp(slide):
    """
    popUp widget.

    Implements a type that starts by displaying the top portion of a widget
    and then moves the widget up to show the bottom portion, pausing each time
    it reaches one direction of the other.

    :param: widget: The widget that will be animated
    :type widget: `tinyDisplay.render.widget`
    :param size: the max size of the widget (x,y) in pixels
    :type size: (int, int)
    :param delay: The amount of time to delay at the top and then the bottom of
        the slide motion.
    :type delay: (int, int)
    """

    def __init__(
        self, widget=widget, size=(0, 0), delay=(10, 10), *args, **kwargs
    ):

        delay = delay if type(delay) == tuple else (delay, delay)
        range = widget.size[1] - size[1]
        actions = [
            ("pause", delay[0]),
            ("btt", range),
            ("pause", delay[1]),
            ("ttb", range),
        ]

        super().__init__(
            widget=widget, size=size, actions=actions, *args, **kwargs
        )

    def _shouldIMove(self, *args, **kwargs):
        return self._withinDisplayArea(
            (
                self._curPos[0],
                self._curPos[1],
                self._curPos[0] + self._widget.image.size[0],
                self._curPos[1] + self._widget.image.size[1],
            ),
            (self.size),
        )


class scroll(marquee):
    """
    Scroll widget.

    Scrolls contained widget within its image, looping it when it reaches the boundary

    :param gap: The amount of space to add in the x and y axis to the widget in
        order to create space between the beginning and the end of the widget.
    :type gap: (int, int) or (str, str)
    """

    def __init__(self, gap=(0, 0), actions=[("rtl",)], *args, **kwargs):

        # Figure out which directions the scroll will move so that we can inform the _computeShadowPlacements method
        dirs = [
            v[0]
            for v in actions
            if (type(v) == tuple and v[0] in ["rtl", "ltr", "ttb", "btt"])
        ] + [v for v in actions if v in ["rtl", "ltr", "ttb", "btt"]]

        h = True if ("ltr" in dirs or "rtl" in dirs) else False
        v = True if ("ttb" in dirs or "btt" in dirs) else False
        self._movement = (h, v)

        super().__init__(actions=actions, gap=gap, *args, **kwargs)

    def _shouldIMove(self, *args, **kwargs):
        if (
            ("rtl",) in self._actions or ("ltr",) in self._actions
        ) and self._widget.image.size[0] > self.size[0]:
            return True
        if (
            ("btt",) in self._actions or ("ttb",) in self._actions
        ) and self._widget.image.size[1] > self.size[1]:
            return True
        return False

    def _adjustWidgetSize(self):
        gap = self._dV["gap"]
        gap = gap if type(gap) is tuple else (gap, gap)

        gapX = round(gap[0])
        gapY = round(gap[1])
        sizeX = self._widget.size[0] + gapX
        sizeY = self._widget.size[1] + gapY
        self._aWI = self._widget.image.crop((0, 0, sizeX, sizeY))

    def _computeTimeline(self):
        if self._dV["moveWhen"]:
            self._reprVal = "scrolling"
            tickCount = 0
            curPos = self._curPos
            for a in self._actions:
                a = a if type(a) == tuple else (a,)
                if a[0] == "pause":
                    tickCount = self._addPause(a[1], curPos, tickCount)
                else:
                    aws = (
                        self._aWI.size[0]
                        if a[0] in ["ltr", "rtl"]
                        else self._aWI.size[1]
                    )
                    curPos, tickCount = self._addMovement(
                        aws, a[0], curPos, tickCount
                    )

            # If position has looped back to start remove last position to prevent stutter
            if (
                (
                    a[0] == "ltr"
                    and self._timeline[-1][0] - aws == self._timeline[0][0]
                )
                or (
                    a[0] == "rtl"
                    and self._timeline[-1][0] + aws == self._timeline[0][0]
                )
                or (
                    a[0] == "ttb"
                    and self._timeline[-1][1] - aws == self._timeline[0][1]
                )
                or (
                    a[0] == "btt"
                    and self._timeline[-1][1] + aws == self._timeline[0][1]
                )
            ):
                self._timeline.pop()
        else:
            self._reprVal = "not scrolling"
            self._timeline.append(self._curPos)

    def _computeShadowPlacements(self):
        lShadows = []
        x = (
            self._curPos[0] - self._aWI.size[0],
            self._curPos[0],
            self._curPos[0] + self._aWI.size[0],
        )
        y = (
            self._curPos[1] - self._aWI.size[1],
            self._curPos[1],
            self._curPos[1] + self._aWI.size[1],
        )
        a = (
            x[0] + self._widget.size[0] - 1,
            x[1] + self._widget.size[0] - 1,
            x[2] + self._widget.size[0] - 1,
        )
        b = (
            y[0] + self._widget.size[1] - 1,
            y[1] + self._widget.size[1] - 1,
            y[2] + self._widget.size[1] - 1,
        )

        # Determine which dimensions need to be shadowed
        xr = range(3) if self._movement[0] else range(1, 2)
        yr = range(3) if self._movement[1] else range(1, 2)

        for i in xr:
            for j in yr:
                if self._withinDisplayArea(
                    (x[i], y[j], a[i], b[j]), (self.size[0], self.size[1])
                ):
                    lShadows.append((x[i], y[j]))
        return lShadows

    def _paintScrolledWidget(self):
        self.clear()
        pasteList = self._computeShadowPlacements()
        for p in pasteList:
            self.image.paste(self._aWI, p, self._aWI)
        return self.image


class image(widget):
    """
    image widget.

    Contains an image sourced from either a PIL.Image object or
    from a file that contains an Image that PIL can read.

    :param image: The image object (if initializating from an PIL.Image)
    :type image: PIL.Image
    :param file: The filename of the image (if initializing from a file)
    :type file: str
    """

    def __init__(
        self,
        image=None,
        url=None,
        file=None,
        allowedDirs=None,
        *args,
        **kwargs,
    ):

        super().__init__(*args, **kwargs)
        self._type = (
            "image"
            if image is not None
            else "url"
            if url is not None
            else "file"
        )
        self._allowedDirs = (
            allowedDirs if allowedDirs is not None else os.getcwd()
        )

        self._dV.compile(image or url or file, "source")
        self.render(reset=True)

    def _render(self, force=False, newData=False, *args, **kwargs):
        if not force and not newData:
            return (self.image, False)

        source = self._dV["source"]

        img = None
        if self._type == "url":
            url = source.replace(" ", "%20")
            img = Image.open(urlopen(url))
        elif self._type == "file":
            if okPath(self._allowedDirs, source):
                img = Image.open(pathlib.Path(source))
            else:
                raise ValueError(f"{source} is not an authorized path")
        elif self._type == "image":
            if isinstance(source, Image.Image):
                img = source.copy()
            else:
                raise ValueError(
                    f"{source} is {type(source)} which is not a valid Image"
                )

        if self._dV["requestedSize"] is not None:
            img = img.resize(self._dV["requestedSize"])

        self.clear((0, 0) if img is None else img.size)
        self.image = img
        if img is not None:
            self._place(wImage=img, just=self.just)
            self._reprVal = f"{source}"
        else:
            self._reprVal = f"no image found: {source}"

        return (self.image, True if self.image is not None else False)


def _makeShape(
    shape=None,
    xy=None,
    fill=None,
    outline=None,
    width=None,
    mode=None,
    background=None,
):
    if len(xy) == 4:
        x0, y0, x1, y1 = xy[0], xy[1], xy[2], xy[3]
    elif len(xy) == 2:
        x0, y0, x1, y1 = xy[0][0], xy[0][1], xy[1][0], xy[1][1]
    else:
        raise ValueError(
            f"xy must be an array of two tuples or four integers.  Instead received {xy}"
        )

    img = Image.new(mode, (max(x0, x1) + 1, max(y0, y1) + 1), background)
    drw = ImageDraw.Draw(img)
    if shape == "line":
        drw.line(xy, fill=fill, width=width)
    elif shape == "rectangle":
        drw.rectangle(xy, fill=fill, outline=outline, width=width)

    return (img, drw)


class shape(widget):
    """
    shape widget.

    :param shape: The type of shape.  Allowed values are 'rectangle' or 'line'
    :type shape: str
    :param xy: coordinates to place line
    :type xy: [x1, y1, x2, y2] or [(x1, y1), (x2, y2)]
    :param fill: the color to fill the interior of the line
    :type fill: str
    :param width: thickness of the line in pixels
    :type width: int
    """

    def __init__(
        self,
        shape=None,
        xy=[],
        fill="'white'",
        outline="'white'",
        width=1,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._dV.compile(xy, "xy")
        self._shape = shape
        self._dV.compile(fill, "fill", "white")
        self._dV.compile(outline, "outline", "white")
        self._dV.compile(width, "width", 1)

    def _render(self, force=False, newData=False, *args, **kwargs):
        if not force and not newData:
            return (self.image, False)

        xy = self._dV["xy"]
        img = None
        img, d = _makeShape(
            self._shape,
            xy,
            self._dV["fill"],
            self._dV["outline"],
            self._dV["width"],
            self._mode,
            self._dV["background"],
        )
        self._reprVal = f"{xy}"

        self.clear((0, 0) if img is None else img.size)
        self._place(wImage=img, just=self.just)
        return (self.image, True)


class line(shape):
    """
    line widget.

    :param xy: coordinates to place line
    :type xy: [x1, y1, x2, y2] or [(x1, y1), (x2, y2)]
    :param fill: the color to fill the interior of the line
    :type fill: str
    :param width: thickness of the line in pixels
    :type width: int
    """

    def __init__(self, xy=[], *args, **kwargs):
        super().__init__(shape="line", xy=xy, *args, **kwargs)
        self.render(reset=True)


class rectangle(shape):
    """
    rectangle widget.

    :param xy: coordinates to place rectangle
    :type xy: [x1, y1, x2, y2] or [(x1, y1), (x2, y2)]
    :param fill: the color to fill the interior of the rectangle
    :type fill: str
    :param outline: the color to draw the outline of the rectangle
    :type outline: str
    """

    def __init__(self, xy=[], *args, **kwargs):
        super().__init__(shape="rectangle", xy=xy, *args, **kwargs)
        self.render(reset=True)


PARAMS = {
    k: getArgDecendents(v)
    for k, v in Widgets.__dict__.items()
    if isclass(v) and issubclass(v, widget) and k != "widget"
}
