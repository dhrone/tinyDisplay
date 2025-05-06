"""
New Marquee widget using the tinyDisplay Marquee DSL.

This module provides a new marquee widget that uses the Marquee DSL to describe
animations rather than the traditional action-based approach.
"""

import logging
import abc
from inspect import currentframe, getargvalues, getfullargspec
from PIL import Image

from tinyDisplay.render.widget import widget
from tinyDisplay.dsl.marquee import parse_and_validate_marquee_dsl
from tinyDisplay.dsl.marquee_executor import MarqueeExecutor, Position


class new_marquee(widget):
    """
    A widget that animates another widget using a Marquee DSL program.
    
    This widget uses the tinyDisplay Marquee Animation DSL to describe complex
    animations in a declarative way.
    
    :param widget: The widget that will be animated
    :type widget: `tinyDisplay.render.widget`
    :param program: A string containing a Marquee DSL program
    :type program: str
    :param resetOnChange: Determines whether to reset the contained widget to its starting
        position if the widget changes value
    :type resetOnChange: bool
    :param variables: Initial variables to make available to the DSL program
    :type variables: dict
    :param moveWhen: A function or evaluatable statement to determine whether the
        widget should be moved. If the statement returns True, the animation will
        continue, or False, the animation will be paused.
    :type moveWhen: `function` or str
    """

    NOTDYNAMIC = ["widget", "program"]

    def __init__(
        self,
        widget=None,
        program="",
        resetOnChange=True,
        variables=None,
        moveWhen=True,
        *args,
        **kwargs,
    ):
        assert widget, "No widget supplied to initialize new_marquee"
        super().__init__(*args, **kwargs)

        self._initArguments(
            getfullargspec(new_marquee.__init__),
            getargvalues(currentframe()),
            new_marquee.NOTDYNAMIC,
        )
        self._evalAll()

        self._widget = widget
        self._program = program
        self._variables = variables or {}
        
        # Parse and validate the DSL program
        self.ast, self.errors = parse_and_validate_marquee_dsl(self._program)
        
        # Set up executor
        self._executor = MarqueeExecutor(self.ast, self._variables)
        
        # Initialize state
        self._timeline = []
        self._tick = 0
        self._last_tick = 0
        self._curPos = (0, 0)
        self._lastPos = (0, 0)
        self._pauses = []
        self._pauseEnds = []
        
        # Logger setup
        self._logger = logging.getLogger("tinyDisplay.render.new_marquee")
        
        # Log any validation errors
        if self.errors:
            for error in self.errors:
                self._logger.warning(f"Marquee program validation error: {error}")
        
        # Compile moveWhen if not dynamic
        if not self._dV._statements["_moveWhen"].dynamic:
            self._compile(
                moveWhen,
                "_moveWhen",
                default=True,
                dynamic=True,
            )
        
        # Initial render with move=False
        self.render(reset=True, move=False)

    def _adjustWidgetSize(self):
        """Adjust the widget image for animation."""
        # This is a simple wrapper to hold the widget's image
        self._aWI = self._widget.image

    def _computeTimeline(self):
        """Compute the animation timeline using the DSL executor."""
        # Execute the program to generate the timeline
        widget_size = self._widget.image.size
        container_size = self._size or widget_size
        
        # Execute the program
        positions = self._executor.execute(widget_size, container_size)
        
        # Convert positions to timeline format
        self._timeline = [(pos.x, pos.y) for pos in positions]
        
        # Extract pause points for properties
        self._pauses = self._executor.context.pauses
        self._pauseEnds = self._executor.context.pause_ends
        
        # Make sure we have at least one position in the timeline
        if not self._timeline:
            self._timeline = [(0, 0)]

    # The at properties can be used by a controlling system to coordinate pauses between multiple marquee objects
    @property
    def atPause(self):
        """
        Has animation reached the start of a pause action.

        :returns: True if yes, False if No
        :rtype: bool
        """
        if len(self._timeline) == 0:
            return False
            
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
        if len(self._timeline) == 0:
            return False
            
        if (self._tick - 1) % len(self._timeline) in self._pauseEnds:
            return True
        return False

    @property
    def atStart(self):
        """
        Has an animation returned to its starting position.

        :returns: True if yes, False if No
        :rtype: bool
        """
        if len(self._timeline) == 0:
            return True
            
        if self._tick > 0 and not (self._tick - 1) % len(self._timeline):
            return True
        return False

    def _resetMovement(self):
        """Reset the animation to its starting position."""
        self.clear()
        self._tick = 0
        self._pauses = []
        self._pauseEnds = []
        self._adjustWidgetSize()
        tx, ty = self._place(wImage=self._aWI, just=self.just)
        self._curPos = self._lastPos = (tx, ty)
        self._timeline = []
        self._computeTimeline()

    def _paintMarqueeWidget(self):
        """Paint the widget at its current position."""
        self.clear()
        self.image.paste(self._aWI, self._curPos, self._aWI)
        return self.image

    def _render(self, force=False, tick=None, move=True, newData=False):
        """
        Render the marquee animation.
        
        :param force: Force a complete re-render
        :param tick: Set the current tick
        :param move: Whether to move to the next position
        :param newData: Whether data has changed
        :returns: Tuple of (image, changed)
        """
        # Update tick if provided
        self._tick = tick if tick is not None else self._tick
        
        # Render the contained widget
        img, updated = self._widget.render(
            force=force, tick=tick, move=move, newData=newData
        )
        
        # Re-adjust widget size if it changed
        if updated:
            self._adjustWidgetSize()
            
        # Reset animation if forced or widget changed and resetOnChange is True
        if (updated and self._resetOnChange) or force:
            self._resetMovement()
            # Increment tick if move is True
            self._tick = self._tick + 1 if move else self._tick
            return (self.image, True)

        # Handle case where timeline is empty (no animation)
        if not self._timeline:
            self._computeTimeline()
            if not self._timeline:  # Still empty after compute
                return (self.image, False)
        
        # Get current position from timeline
        moved = False
        if len(self._timeline) > 0:
            self._curPos = self._timeline[self._tick % len(self._timeline)]
            
            # Update widget if position changed or widget updated
            if self._curPos != self._lastPos or updated:
                self.image = self._paintMarqueeWidget()
                moved = True
                self._lastPos = self._curPos
        
        # Only increment tick if movement is enabled and moveWhen evaluates to True
        if move and self._moveWhen:
            self._tick = (self._tick + 1) % (len(self._timeline) or 1)
        
        return (self.image, moved) 