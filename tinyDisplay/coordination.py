"""
DEPRECATED: Timeline Coordination Manager for tinyDisplay.

This module has been moved to tinyDisplay.render.coordination.
This file is kept for backward compatibility and will be removed in a future version.

Please update your imports to use:
from tinyDisplay.render.coordination import timeline_manager
"""

import logging
import warnings

# Issue deprecation warning
warnings.warn(
    "The 'tinyDisplay.coordination' module is deprecated and will be removed in a future version. "
    "Please use 'tinyDisplay.render.coordination' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from the new location
from tinyDisplay.render.coordination import TimelineCoordinationManager, timeline_manager

# Maintain backward compatibility
__all__ = ['TimelineCoordinationManager', 'timeline_manager'] 