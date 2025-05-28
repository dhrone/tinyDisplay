"""tinyDisplay - High-performance display framework for embedded devices.

A specialized display framework for Single Board Computers (SBCs) with small displays
(under 256x256 resolution). Built for 60fps performance on Raspberry Pi Zero 2W.

Architecture:
- Ring buffers for high-performance data flow
- SQLite for reactive state management  
- asteval for safe expression evaluation
- Reactive patterns for automatic dependency tracking

Example:
    >>> from tinydisplay import Canvas, Text
    >>> canvas = Canvas(width=128, height=64)
    >>> text = Text("Hello World").position(10, 10)
    >>> canvas.add(text)
"""

__version__ = "2.0.0"
__author__ = "tinyDisplay Team"
__license__ = "MIT"

# Core framework components will be imported here as they're implemented
# from .widgets import Text, Image, ProgressBar, Canvas
# from .animation import sync, wait_for, barrier, sequence
# from .data import ReactiveValue, DataSource

# For now, expose version info
__all__ = ["__version__", "__author__", "__license__"]
