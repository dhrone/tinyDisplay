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
import queue
import threading
from inspect import currentframe, getargvalues, getfullargspec, isclass
from time import monotonic
from urllib.request import urlopen

from PIL import Image, ImageChops, ImageColor, ImageDraw

from tinyDisplay import globalVars
from tinyDisplay.exceptions import DataError, RenderError
from tinyDisplay.font import bmImageFont
from tinyDisplay.render import widget as Widgets
from tinyDisplay.utility import (
    dataset as Dataset,
    evaluator,
    getArgDecendents,
    getNotDynamicDecendents,
    image2Text,
    okPath,
)


# from IPython.core.debugger import set_trace


class widget(metaclass=abc.ABCMeta):
    """
    Base class for all widgets.

    :param name: The name of the widget (optional)
    :type name: str
    :param size: the max size of the widget (x,y) in pixels
    :type size: (int, int)
    :param activeWhen: Widget active when activeWhen is True
    :type activeWhen: bool
    :param duration: Number of ticks to remain active
    :type duration: int
    :param minDuration: Minimum number of ticks to stay active
    :type minDuration: int
    :param coolingPeriod: Number of ticks before widget can return to active state
    :type coolingPeriod: int
    :param overRun: Should widget remain active past its active state.  If yes,
        widget will reset minDuration when active goes False
    :type overRun: bool
    :param dataset: dataset to be used for any arguments that are evaluated during run-time
    :type dataset: `tinyDisplay.utility.dataset`
    :param foreground: The color to use for any foreground parts of the widget
    :type foreground: str, int, or tuple
    :param foreground: The color to use for any background parts of the widget
    :type foreground: str, int, or tuple
    :param just: The justification to use when placing the widget on its image.
    :type just: str
    :param trim: Determine whether to trim image after render and what part of the
        image to trim if yes.
    :type time: str
    """

    NOTDYNAMIC = ["name", "dataset"]

    def __init__(
        self,
        name=None,
        size=None,
        activeWhen=True,
        duration=None,
        minDuration=None,
        coolingPeriod=None,
        overRun=False,
        dataset=None,
        mode="RGBA",
        foreground="white",
        background=None,
        just="lt",
        trim=None,
        **kwargs,
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

        # Image Cache
        self._cache = {}  # Currently only used by image widget

        # Active State variables
        self._tick = 0
        self._normalDuration = duration
        self._currentDuration = duration
        self._minDuration = minDuration
        self._currentMinDuration = 0
        self._coolingPeriod = coolingPeriod
        self._currentCoolingPeriod = 0
        self._currentActiveState = False
        self._overRunning = False

        # Perf problem alerting
        self._slowRender = 0.1

        assert mode in (
            "1",
            "L",
            "LA",
            "RGB",
            "RGBA",
        ), "TinyDisplay only supports PIL modes 1, L, LA, RGB, and RGBA"

        self._initArguments(
            getfullargspec(widget.__init__),
            getargvalues(currentframe()),
            widget.NOTDYNAMIC,
        )
        self._evalAll()

        # Override dynamicValue for background if it is not dynamic
        if not self._dV._statements["_background"].dynamic:
            bgDefault = (0, 0, 0, 0) if self._mode == "RGBA" else "black"
            self._background = background or bgDefault

        if not self._dV._statements["_activeWhen"].dynamic:
            self._compile(
                activeWhen, "_activeWhen", default=True, dynamic=True
            )
        self._fixColors()
        self.clear()  # Create initial canvas

        # Establish initial values for local DB
        self._computeLocalDB()

    def _initArguments(self, argSpec, argValues, exclude=None):
        kwargs = argValues[3]["kwargs"]
        args = (
            [item for item in argSpec[0][1:] if item not in exclude]
            if exclude is not None
            else argSpec[0][1:]
        )
        defaults = argSpec[3]
        for a in args:
            kname = f"d{a}"
            aname = f"_{a}"
            if kname in kwargs:
                i = args.index(a)
                self._compile(
                    kwargs[kname],
                    name=aname,
                    default=defaults[i],
                    dynamic=True,
                )
            else:
                self._compile(argValues[3][a], name=aname, dynamic=False)

    def _compile(
        self, source, name, default=None, validator=None, dynamic=True
    ):
        """
        Compile dynamicValue for Widget.

        :param source: The source for the dynamicValue
        :param name: The name to assign the dynamicValue
        :type name: str
        :param default: The devault value used for the dynamicValue if
            the evaluation fails
        :param validator: function used to validate answer during eval (optional)
        :type validator: callable
        :param dynamic: True if dynamicVariable should compute value during eval
        :type dynamic: bool

        ..note:
            If dynamic is False, eval returns the value provided in source every
            time eval is called.  If dynamic is True, a new value is computed
            based upon the function or evaluatable statement that was provided
            in source.

        ..note:
            If provided, the validator function must accept a value to be tested
            and return True if it is ok, or False if it is bad

        :raises: `tinyDisplay.exception.CompileError`
        """
        self._dV.compile(
            source=source,
            name=name,
            default=default,
            validator=validator,
            dynamic=dynamic,
        )
        setattr(self, name, default)

    def _eval(self, name):
        """
        Evaluate dynamicValue.

        :param name: The name of the dynamicValue to evaluate
        :type name: str
        :returns: The resulting value
        :raises: `tinyDisplay.exceptions.EvaluationError`
        :raises: `tinyDisplay.exceptions.ValidationError`
        :raises: AttributeError
        """
        try:
            value = self._dV.eval(name)
            if self._dV._statements[name].changed:
                setattr(self, name, value)
            return value
        except KeyError as ex:
            # It's a KeyError from the perspective of the evaluator but from the
            # widget's perspective it's a member variable so throw AttributeError
            raise AttributeError(ex)

    def _evalAll(self):
        """
        Evaluate all dynamicValues that are contained in the widget.

        :returns: True if any of the values have changed
        :rtype: bool
        :raises: `tinyDisplay.exceptions.EvaluationError`
        :raises: `tinyDisplay.exceptions.ValidationError`
        """
        changed = False
        for name in self._dV:
            self._eval(name)
            if self._dV._statements[name].changed:
                changed = True
        return changed

    def _fixColors(self):
        # When reaching from Yaml need to accept lists because tuples are not
        # possible.  Colors require tuples (if numeric) so thie function
        # converts list entries into tuples.
        colorArgs = ["_background", "_foreground", "_fill", "_outline"]
        for c in colorArgs:
            if c in dir(self):
                a = getattr(self, c)
                if type(a) is list:
                    setattr(self, c, tuple(a))

    def __getattr__(self, name):
        msg = f"{self.__class__.__name__} object {self.name} has no attribute {name}.  image is type({type(self.image)})"
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
        if "size" in dir(self) or (
            "image" in dir(self) and "size" in dir(self.image)
        ):
            return (
                f"<{n}.{self.type} {v}size{self.size} {cw}at 0x{id(self):x}>"
            )
        else:
            return f"<{n}.{self.type} {v}size(unknown) {cw}at 0x{id(self):x}>"

    def __str__(self):
        if self.image:
            return image2Text(self.image, self._background)
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
        size = (
            self._size
            if self._size is not None
            else size if type(size) is tuple and len(size) == 2 else (0, 0)
        )
        self.image = Image.new(self._mode, size, self._background)
        if self.image is None:
            raise RuntimeError(f"Clear resulted in `None` for {self.name}")

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
        # isActive = self._dV["activeWhen"]
        isActive = self._activeWhen

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
            # If overRun is set, then reset currentMinDuration and remain active
            if (
                self._overRun is True
                and self._minDuration is not None
                and not self._overRunning
            ):
                self._currentMinDuration = self._minDuration
                self._overRunning = True
                result = True
            else:
                # else reset cooling timer and go inactive
                self._resetCoolingTimer()
        self._currentActiveState = result
        return result

    def _resetDurationTimers(self):
        """Reset Timers when widget newly becomes active."""
        if self._normalDuration is not None:
            self._currentDuration = self._normalDuration

        if self._minDuration is not None:
            self._currentMinDuration = (
                self._minDuration if not self._overRun else 0
            )

        if self._overRun is not None:
            self._overRunning = False

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
            self._currentMinDuration = (
                self._minDuration if isActive and not self._overRun else 0
            )
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

    def trim(self, region=None):
        """Trim image of any extra (non-content e.g. background) pixels.

        :param region: Detemines what parts of the image to trip.  Possible Values
            are 'top', 'bottom', 'left', 'right', 'horizontal', or 'vertical'
        :type region: str
        :returns: trimmed image
        :rtype: `PIL.Image.Image`

        ..note:
            region values that relate to a side, trim that side
            (e.g. top, bottom, left, right)
            horizontal trims both the top and bottom of the image
            vertical trims the left and right sides of the image
            default is to trim all sides
        """
        # Strip Alpha channel from Mode (because ImageChops dif doesn't like alpha)
        compMode = self._mode if self._mode[-1] != "A" else self._mode[0:-1]
        empty = Image.new(compMode, self.size, self._background)

        size = self.size
        bbox = ImageChops.difference(
            self.image.convert(compMode), empty
        ).getbbox()
        if bbox:
            cropd = {
                "left": (bbox[0], 0, size[0], size[1]),
                "right": (0, 0, bbox[2], size[1]),
                "top": (0, bbox[1], size[0], size[1]),
                "bottom": (0, 0, size[0], bbox[3]),
                "horizontal": (0, bbox[1], size[0], bbox[3]),
                "vertical": (bbox[0], 0, bbox[2], size[1]),
            }.get(region, (bbox[0], bbox[1], bbox[2], bbox[3]))
            self.image = self.image.crop(cropd)
        return self.image

    def _place(self, wImage=None, offset=(0, 0), just="lt"):
        just = just or "lt"
        offset = offset or (0, 0)
        assert (
            just[0] in "lmr" and just[1] in "tmb"
        ), f"Requested justification \"{just}\" is invalid.  Valid values are left top ('lt'), left middle ('lm'), left bottom ('lb'), middle top ('mt'), middle middle ('mm'), middle bottom ('mb'), right top ('rt'), right middle ('rm'), and right bottom ('rb')"

        if self.image is None:
            print(f"WIDGET._PLACE 'image' is None in {self.name}")
            raise RuntimeError(f"WIDGET._PLACE 'image' is None in {self.name}")
        # if there is an image to place
        if wImage:
            mh = round((self.image.size[0] - wImage.size[0]) / 2)
            r = self.image.size[0] - wImage.size[0]

            mv = round((self.image.size[1] - wImage.size[1]) / 2)
            b = self.image.size[1] - wImage.size[1]

            a = (
                0
                if just[0] == "l"
                else mh if just[0] == "m" else r if just[0] == "r" else 0
            )
            b = (
                0
                if just[1] == "t"
                else mv if just[1] == "m" else b if just[1] == "b" else 0
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
        self._renderTime = monotonic()
        if self.image is None:
            raise RuntimeError(
                f"Starting Render for {repr(self)}:{self.name}.  Image is None"
            )
        self._computeLocalDB()

        if reset:
            force = True

        try:
            nd = self._evalAll()
            self._fixColors()  # Refix colors if they have changed because of eval
        except DataError as ex:
            if self._debug:
                raise
            else:
                self._logger.warning(
                    f"Unable to evaluate widget variables: {ex}"
                )
                return (self.image, False)

        if monotonic() - self._renderTime > self._slowRender:
            print(
                f"=== slow data render {self.name} {monotonic() - self._renderTime:0.3f} ==="
            )
        if force:
            self.resetMovement()

        img = self.image
        changed = False

        try:
            img, changed = self._render(
                force=force, tick=tick, move=move, newData=nd or newData
            )
            # If any trim is selected, perform trim if image has changed
            if self._trim is not None and changed:
                img = self.trim(self._trim)
        except Exception as ex:
            if self._debug:
                raise
            else:
                self._logger.warning(f"Render for {self.name} failed: {ex}")
                return (img, False)

        self._updateTimers(force)

        if monotonic() - self._renderTime > self._slowRender:
            print(
                f"=== slow render {self.name} {monotonic() - self._renderTime:0.3f} ==="
            )

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
    :param wrap: Wrap text if true
    :type wrap: bool

    ..note:
        If wrap is True, you must provide a size.  Otherwise wrap is ignored.
    """

    NOTDYNAMIC = ["font", "antiAlias", "lineSpacing", "wrap"]

    def __init__(
        self,
        value=None,
        font=None,
        antiAlias=False,
        lineSpacing=0,
        wrap=False,
        width=None,
        height=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self._initArguments(
            getfullargspec(text.__init__),
            getargvalues(currentframe()),
            text.NOTDYNAMIC,
        )
        self._evalAll()

        self._font = font or _textDefaultFont
        self._lineSpacing = lineSpacing
        self._antiAlias = antiAlias
        self._wrap = wrap

        self._tsDraw = ImageDraw.Draw(Image.new(self._mode, (0, 0), 0))
        self._tsDraw.fontmode = self._fontMode

        self.render(reset=True)

    @property
    def font(self):
        """
        Return current font.

        :returns: The current font used in the text widget
        """
        if "_font" in dir(self):
            return self._font
        return None

    @property
    def _fontMode(self):
        if "_antiAlias" in dir(self):
            return "L" if self._antiAlias else "1"
        return "1"

    def _makeWrapped(self, value, width):
        vl = value.split(" ")
        lines = []
        line = ""
        for w in vl:
            tl = line + " " + w if len(line) > 0 else w
            if self._sizeLine(tl)[0] <= width:
                line = tl
            else:
                if len(line) == 0:
                    lines.append(tl)
                else:
                    lines.append(line)
                    line = w
        if len(line) > 0:
            lines.append(line)

        return "\n".join(lines)

    def _sizeLine(self, value):
        if value == "" or value is None:
            return (0, 0)

        if "getmetrics" in dir(self._font):
            # Bitmap font path
            ascent, descent = self._font.getmetrics()
            h = 0
            w = 0
            for v in value.split("\n"):
                try:
                    # Use getbbox() instead of getmask().getbbox() for more accurate sizing
                    bbox = self._tsDraw.textbbox((0, 0), v, font=self._font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1] + descent
                    w = max(w, tw)
                    h += th
                except TypeError:
                    pass
            tSize = (w, h)
        else:
            # TrueType font path
            bbox = self._tsDraw.textbbox(
                (0, 0), value, font=self._font, spacing=self._lineSpacing
            )
            tSize = (bbox[2] - bbox[0], bbox[3] - bbox[1])

        tSize = (0, 0) if tSize[0] == 0 else tSize
        return tSize

    def _render(self, force=False, newData=False, *args, **kwargs):
        # If the string to render has not changed then return current image
        if not newData and not force:
            return (self.image, False)

        value = str(self._value)
        self._reprVal = f"'{value}'"

        tBB = self._tsDraw.textbbox(
            (0, 0), value, font=self.font, spacing=self._lineSpacing
        )
        tSize = (tBB[2], tBB[3])
        tSize = (0, 0) if tSize[0] == 0 else tSize
        if self._wrap and self._width is not None:
            # Wrap only if a width was requested, otherwise ignore
            value = self._makeWrapped(value, self._width)

        tSize = self._sizeLine(value)

        img = Image.new(self._mode, tSize, self._background)
        if img.size[0] != 0:
            d = ImageDraw.Draw(img)
            d.fontmode = self._fontMode
            just = {"l": "left", "r": "right", "m": "center"}.get(self.just[0])
            d.text(
                (0, 0),
                value,
                font=self.font,
                # fill=self._dV["foreground"],
                fill=self._foreground,
                spacing=self._lineSpacing,
                align=just,
            )

        size = (
            self._width if self._width is not None else img.size[0],
            self._height if self._height is not None else img.size[1],
        )
        self.clear(size)
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

    NOTDYNAMIC = ["mask"]

    def __init__(
        self,
        value=None,
        range=(0, 100),
        mask=None,
        fill="white",
        opacity=0,
        direction="ltr",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self._initArguments(
            getfullargspec(progressBar.__init__),
            getargvalues(currentframe()),
            progressBar.NOTDYNAMIC,
        )
        self._evalAll()

        self._mask = (
            mask
            if mask
            else self._defaultMask(
                self._size,
                self._mode,
                self._foreground,
                self._background,
                self._opacity,
            )
        )
        if type(mask) in [str, pathlib.PosixPath]:
            self._mask = Image.open(pathlib.PosixPath(mask))

        self.render(reset=True)

    @staticmethod
    def _defaultMask(size, mode, foreground, background, opacity):
        mode = (
            "L"
            if mode in ("1", "L", "LA")
            else "RGBA" if mode in ("RGB", "RGBA") else "RGBA"
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
        if rangeSize == 0:
            return 0
        else:
            return (scale - r0) / rangeSize

    def _render(self, force=False, newData=False, *args, **kwargs):
        if not newData and not force:
            return (self.image, False)

        value = self._value
        range = self._range
        scale = self._getScaler(value, range)

        self._reprVal = f"{scale * 100:.1f}%"

        size = self._mask.size
        dir = self._direction

        (w, h) = (
            (size[0], round(size[1] * scale))
            if dir in ["ttb", "btt"]
            else (round(size[0] * scale), size[1])
        )
        (px, py) = (
            (0, 0)
            if dir in ["ltr", "ttb"]
            else (size[0] - w, 0) if dir == "rtl" else (0, size[1] - h)
        )

        # Build Fill

        fill = Image.new(self._mode, size, self._background)
        fill.paste(
            Image.new(self._mode, (w, h), self._fill or self._foreground),
            (px, py),
        )
        fill.paste(self._mask, (0, 0), self._mask)

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

    NOTDYNAMIC = ["widget", "actions"]

    def __init__(
        self,
        widget=None,
        resetOnChange=True,
        actions=[("rtl",)],
        speed=1,
        distance=1,
        moveWhen=None,
        wait=None,
        gap=(0, 0),
        *args,
        **kwargs,
    ):
        assert widget, "No widget supplied to initialize scroll"
        super().__init__(*args, **kwargs)

        self._initArguments(
            getfullargspec(marquee.__init__),
            getargvalues(currentframe()),
            marquee.NOTDYNAMIC,
        )
        self._evalAll()

        self._widget = widget
        self._actions = []
        for a in actions:
            a = a if type(a) in [tuple, list] else (a,)
            self._actions.append(a)

        self._timeline = []
        self._tick = 0

        if not self._dV._statements["_moveWhen"].dynamic:
            self._compile(
                moveWhen or self._shouldIMove,
                "_moveWhen",
                default=False,
                dynamic=True,
            )

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
                else (
                    (-self._distance, 0)
                    if direction == "rtl"
                    else (
                        (0, self._distance)
                        if direction == "ttb"
                        else (0, -self._distance)
                    )
                )
            )
            curPos = (curPos[0] + dir[0], curPos[1] + dir[1])

            for _ in range(self._speed):
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
            else (
                self.size[0] - (pos[0] + self._widget.size[0])
                if direction == "ltr"
                else (
                    pos[1]
                    if direction == "btt"
                    else self.size[1] - (pos[1] + self._widget.size[1])
                )
            )
        )

    def _returnToStart(self, direction, curPos, tickCount):
        sp = self._timeline[0]

        dem = 0 if direction[0] == "h" else 1
        for i in range(2):
            dir = (
                "rtl"
                if dem == 0 and curPos[dem] > sp[dem]
                else (
                    "ltr"
                    if dem == 0 and curPos[dem] < sp[dem]
                    else "btt" if dem == 1 and curPos[dem] > sp[dem] else "ttb"
                )
            )
            curPos, tickCount = self._addMovement(
                abs(curPos[dem] - sp[dem]), dir, curPos, tickCount
            )
            dem = 0 if dem == 1 else 1

        return (curPos, tickCount)

    def _computeTimeline(self):
        if self._moveWhen:
            self._reprVal = "sliding"
            tickCount = 0
            curPos = self._curPos

            for a in self._actions:
                a = a if type(a) in [tuple, list] else (a,)
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

        delay = delay if type(delay) in [tuple, list] else (delay, delay)
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

    def __init__(self, actions=[("rtl",)], *args, **kwargs):

        # Figure out which directions the scroll will move so that we can inform the _computeShadowPlacements method
        dirs = [
            v[0]
            for v in actions
            if (
                type(v) in [tuple, list]
                and v[0] in ["rtl", "ltr", "ttb", "btt"]
            )
        ] + [v for v in actions if v in ["rtl", "ltr", "ttb", "btt"]]

        h = True if ("ltr" in dirs or "rtl" in dirs) else False
        v = True if ("ttb" in dirs or "btt" in dirs) else False
        self._movement = (h, v)

        super().__init__(actions=actions, *args, **kwargs)

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
        gap = self._gap
        gap = gap if type(gap) is tuple else (gap, gap)

        gapX = round(float(gap[0]))
        gapY = round(float(gap[1]))
        sizeX = self._widget.size[0] + gapX
        sizeY = self._widget.size[1] + gapY
        self._aWI = self._widget.image.crop((0, 0, sizeX, sizeY))

    def _computeTimeline(self):
        if self._moveWhen:
            self._reprVal = "scrolling"
            tickCount = 0
            curPos = self._curPos
            for a in self._actions:
                a = a if type(a) in [tuple, list] else (a,)
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

    NOTDYNAMIC = ["allowedDirs"]

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
        self._initArguments(
            getfullargspec(Widgets.image.__init__),
            getargvalues(currentframe()),
            Widgets.image.NOTDYNAMIC,
        )
        self._evalAll()

        self._allowedDirs = (
            allowedDirs if allowedDirs is not None else os.getcwd()
        )

        self._response = queue.Queue()
        self._fetchSet = set()

        self.render(reset=True)

    def fetchURL(self, url):
        """Fetch Image from url and place into image cache.

        :param url: The url to retrieve the image from
        """
        threading.Thread(target=self._fetchURL, args=(url,)).start()
        self._fetchSet.add(url)

    def _fetchURL(self, url):
        try:
            img = Image.open(urlopen(url))
            print(f"=== Fetch succeeded for {url} ===")
            self._response.put((url, img))
        except Exception as ex:
            print(f"=== Fetch failed for {url} ===")
            self._response.put((url, ex))

    def _gatherURLResponses(self):
        # Determine if there are responses waiting
        while True:
            try:
                url, img = self._response.get_nowait()
                self._response.task_done()
                if isinstance(img, Exception):
                    msg = f"Retrieval of image {url} failed: {img}"
                    if self._debug:
                        raise RenderError(msg)
                    else:
                        self._logger.warning(msg)
                else:
                    self._cache[url] = img
                    self._fetchSet.remove(url)
            except queue.Empty:
                break

    def _render(self, force=False, newData=False, *args, **kwargs):

        typeImage = (
            "url"
            if self._url
            else "file" if self._file else "image" if self._image else None
        )
        source = self._url or self._file or self._image

        if (
            not force
            and not newData
            and (typeImage == "image" or source in self._cache)
        ):
            return (self.image, False)

        # Put any received responses in the cache
        self._gatherURLResponses()

        if typeImage in ["url", "file"] and source in self._cache:
            print(f"=== Cache Hit: {source}: {self._cache[source]}")
            img = self._cache[source]
        else:
            # Retrieve image
            img = None
            if typeImage == "url":
                url = source.replace(" ", "%20")
                if url not in self._fetchSet:
                    self.fetchURL(url)
            elif typeImage == "file":
                if okPath(self._allowedDirs, source):
                    img = Image.open(pathlib.Path(source))
                else:
                    raise ValueError(f"{source} is not an authorized path")
            elif typeImage == "image":
                if isinstance(source, Image.Image):
                    img = source.copy()
                    img = img.convert(self._mode)
                else:
                    raise ValueError(
                        f"{source} is {type(source)} which is not a valid Image"
                    )
        if (
            typeImage != "image"
            and source not in self._cache
            and img is not None
        ):
            self._cache[source] = img  # Store image in cache

        if (
            self._size is not None
            and img is not None
            and img.size != self._size
        ):
            img = img.resize(self._size)

        if img is not None and img.mode != self._mode:
            img = img.convert(self._mode)

        self.clear((0, 0) if img is None else img.size)
        if img is not None:
            self._place(wImage=img, just=self.just)
            self._reprVal = f"{source}"
        else:
            self._reprVal = f"no image: {source}"

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

    NOTDYNAMIC = ["shape"]

    def __init__(
        self,
        xy=[],
        shape=None,
        fill="white",
        outline="white",
        width=1,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._initArguments(
            getfullargspec(Widgets.shape.__init__),
            getargvalues(currentframe()),
            Widgets.shape.NOTDYNAMIC,
        )
        self._evalAll()

        self._shape = shape

    def _render(self, force=False, newData=False, *args, **kwargs):
        if not force and not newData:
            return (self.image, False)

        img = None
        img, d = _makeShape(
            self._shape,
            self._xy,
            self._fill,
            self._outline,
            self._width,
            self._mode,
            self._background,
        )
        self._reprVal = f"{self._xy}"

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, shape="line")
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, shape="rectangle")
        self.render(reset=True)


PARAMS = {
    k: getArgDecendents(v)
    for k, v in Widgets.__dict__.items()
    if isclass(v) and issubclass(v, widget) and k != "widget"
}

for k, v in PARAMS.items():
    nv = list(v)
    NDD = getNotDynamicDecendents(Widgets.__dict__[k])
    for arg in v:
        if arg not in NDD:
            nv.append(f"d{arg}")
    PARAMS[k] = nv
