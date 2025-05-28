Marquee Classes in tinyDisplay
==========================

This document provides a comprehensive overview of the marquee class and its subclasses (scroll, slide, popUp) within the tinyDisplay library.

Base Class: marquee
------------------

The marquee class serves as the base class for animated widgets in tinyDisplay. It provides core functionality for moving widgets across a display with various animation behaviors.

Purpose
~~~~~~~

The marquee class enables animated movement of widgets. It serves as the foundation for more specialized animation classes like scroll, slide, and popUp, providing the common infrastructure for:

- Defining movement patterns through action sequences
- Managing animation timelines
- Controlling animation speed and distance
- Handling pauses and animation state

Key Properties
~~~~~~~~~~~~~

- **widget**: The widget to be animated
- **resetOnChange**: Boolean determining whether to reset animation when the widget changes
- **actions**: List of movement instructions, each a tuple of (command, optional parameter)
- **speed**: Number of ticks between moves (higher = slower)
- **distance**: Pixels to move per move event (higher = faster)
- **moveWhen**: Function or statement to determine if animation should continue
- **timeline**: Internal array storing the animation sequence

Animation Controls
~~~~~~~~~~~~~~~~

The marquee class provides several properties to check animation state:

- **atPause**: Returns True when animation reaches the start of a pause
- **atPauseEnd**: Returns True when animation reaches the end of a pause
- **atStart**: Returns True when animation returns to its starting position

Movement Commands
~~~~~~~~~~~~~~~

The marquee class understands these basic movement commands:

- **"rtl"** - Right to left movement
- **"ltr"** - Left to right movement  
- **"ttb"** - Top to bottom movement
- **"btt"** - Bottom to top movement
- **"pause"** - Pause for a specified duration

Understanding Actions
~~~~~~~~~~~~~~~~~~~

The ``actions`` parameter is a crucial part of configuring marquee animations. It defines the sequence of movements that the widget will follow.

Format
^^^^^^

Actions are specified as a list of tuples, where each tuple contains:
1. A command string (required)
2. An optional numerical parameter (optional)

For example:

.. code-block:: python

    actions=[
        ("rtl", 100),    # Move right to left for 100 pixels
        ("pause", 20),   # Pause for 20 ticks
        ("ltr", 50),     # Move left to right for 50 pixels
    ]

Default parameter behavior:
- For movement commands (rtl, ltr, ttb, btt): If no parameter is provided, the widget moves until it reaches the boundary of the display
- For pause: The parameter specifies the number of ticks to pause
- For rts (return to start): The parameter specifies the axis of movement ("h" for horizontal, "v" for vertical, or omitted for both)

The Return to Start Command
^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``"rts"`` command is a special action that returns the widget to its starting position. This command is particularly useful for creating cycling animations without having to compute the exact distance back to the starting point.

Syntax:
  
.. code-block:: python

    ("rts",)          # Return to start position on both axes
    ("rts", "h")      # Return to start position on horizontal axis only
    ("rts", "v")      # Return to start position on vertical axis only

When processed, the ``"rts"`` command:

1. Calculates the current position relative to the starting position
2. Determines the appropriate direction (rtl/ltr for horizontal, ttb/btt for vertical)
3. Adds movement actions to the timeline to return to the start coordinates
4. Uses the same speed and distance settings as other movements

Example usage:

.. code-block:: python

    # Move widget down, then return to top
    actions=[
        ("ttb", 100),    # Move top to bottom
        ("rts", "v")     # Return to starting vertical position
    ]
    
    # Create a rectangular motion pattern
    actions=[
        ("rtl", 50),     # Move right to left
        ("ttb", 30),     # Move top to bottom
        ("ltr", 50),     # Move left to right
        ("rts", "v")     # Return to starting vertical position only
    ]

This command is primarily implemented in the ``slide`` class and may not be available or may behave differently in other marquee subclasses.

Processing of Actions
^^^^^^^^^^^^^^^^^^^^^

When a marquee widget is initialized, it processes the actions list:

1. Each action is converted to a series of positions in the ``_timeline`` array
2. For movement actions, positions are calculated based on the ``speed`` and ``distance`` parameters
3. For pause actions, the same position is repeated for the specified number of ticks
4. The timeline becomes a complete set of coordinates that the widget will follow

The marquee class then cycles through this timeline during rendering, moving the widget to each position in sequence.

Complex Action Sequences
^^^^^^^^^^^^^^^^^^^^^^^

By combining different action types, you can create complex animation patterns:

.. code-block:: python

    # Slide in from right, pause, slide out to left
    actions=[
        ("ltr", 80),     # Slide in from right
        ("pause", 30),   # Hold still for 30 ticks
        ("rtl", 120)     # Slide out to left (and beyond)
    ]

    # Popup-style vertical animation
    actions=[
        ("pause", 10),   # Pause at top position
        ("btt", 40),     # Move up to show lower content
        ("pause", 10),   # Pause at bottom position
        ("ttb", 40)      # Move down to original position
    ]
    
    # Loop horizontally with a return-to-start action
    actions=[
        ("rtl", 100),    # Move right to left
        ("rts", "h")     # Return to start horizontally
    ]

Each subclass may interpret these actions differently or add specialized behavior:

- ``scroll`` typically uses actions to create continuous looping motion
- ``slide`` often uses actions for entrance/exit effects
- ``popUp`` has a predefined action sequence to alternate between content sections

Subclass: scroll
---------------

The scroll class provides functionality to scroll a widget's content continuously, often used for text that exceeds the display width.

Purpose
~~~~~~~

The scroll class is designed to:
- Allow content wider/taller than the display area to be shown through scrolling motion
- Create looping animations where content moves continuously in one direction
- Provide options for gaps between repetitions of content

Key Properties
~~~~~~~~~~~~~

- **gap**: Space to add between beginning and end of widget (x, y)
- **size**: Size of the scrolling container

Behavior
~~~~~~~~

1. When a scroll widget is rendered, it moves the contained widget according to the defined actions
2. The content loops seamlessly when it reaches boundaries
3. The default scrolling behavior is right-to-left ("rtl")
4. A gap can be defined to provide visual separation between the end of content and its repeating beginning

Example Usage
~~~~~~~~~~~~

A simple text scroll moving right to left:

.. code-block:: python

    text_widget = text(value="This text is too long to fit on the display")
    scrolling_text = scroll(
        widget=text_widget,
        actions=[("rtl",)],
        speed=1,
        distance=1
    )

Subclass: slide
--------------

The slide class provides functionality to slide a widget within a display area, often moving from offscreen to onscreen and back.

Purpose
~~~~~~~

The slide class is designed to:
- Move widgets into and out of view
- Create transition effects between display states
- Provide more complex movement patterns than simple scrolling

Key Properties
~~~~~~~~~~~~~

Inherits all properties from marquee, with specialized behavior for boundary detection and positional movement.

Movement Commands
~~~~~~~~~~~~~~~

In addition to the basic movement commands, slide supports:

- **"rts"** - Return to start position
- Direction parameter can specify movement axis ("h" for horizontal, "v" for vertical)

Behavior
~~~~~~~~

1. The slide widget moves its contained widget according to defined actions
2. Can calculate boundaries to determine when to stop or reverse movement
3. Can return to starting position using "rts" command
4. Movement stops when content goes outside the display area

Example Usage
~~~~~~~~~~~~

A widget that slides in from the right, pauses, then slides back out:

.. code-block:: python

    info_widget = text(value="Breaking News!")
    sliding_info = slide(
        widget=info_widget,
        actions=[("ltr", 100), ("pause", 20), ("rtl", 100)],
        speed=2,
        distance=1
    )

Subclass: popUp
--------------

The popUp class provides specialized behavior to show alternating portions of a tall widget, such as toggling between two screens of information.

Purpose
~~~~~~~

The popUp class is designed to:
- Display tall content in a smaller viewing area
- Automatically shift between top and bottom portions of content
- Provide timed pauses at each position

Key Properties
~~~~~~~~~~~~~

- **size**: Maximum size of the viewing area
- **delay**: Tuple with delay times for top and bottom positions (top_delay, bottom_delay)

Behavior
~~~~~~~~

1. The popUp widget starts by showing the top portion of the contained widget
2. After the top delay period, it slides up to show the bottom portion
3. After the bottom delay period, it slides back down to show the top portion
4. This cycle repeats continuously

Example Usage
~~~~~~~~~~~~

Creating a popup that alternates between two lines of information:

.. code-block:: python

    info_widget = text(value="Weather: Sunny\nTemp: 72°F")
    popup_info = popUp(
        widget=info_widget,
        size=(100, 8),  # Only show 8 pixels height at once
        delay=(10, 10)  # Wait 10 ticks at top and bottom
    )

Integration with Canvas and Sequences
-----------------------------------

The marquee widgets can be integrated into the tinyDisplay canvas and sequence system:

.. code-block:: yaml

    myCanvas:
      items:
        - name: scrollingText
          type: text
          value: "This is a very long message that needs to scroll"
          effect:
            type: scroll
            speed: 1
            distance: 1
        
        - name: popupInfo
          type: text
          value: "First line info\nSecond line info"
          effect:
            type: popUp
            size: 100, 8
            delay: 5, 5

Internal Implementation
---------------------

The marquee class and its subclasses use these key implementation patterns:

1. A timeline array that stores all positions in the animation sequence
2. Abstract methods that subclasses must implement:
   - _shouldIMove: Determines if movement should continue
   - _computeTimeline: Generates the sequence of positions
   - _adjustWidgetSize: Handles widget sizing during animation
3. The _render method that calculates current position and moves the widget
4. Special position tracking for pause points in the animation

This architecture allows for complex animations while maintaining a consistent interface for all marquee widget types. 