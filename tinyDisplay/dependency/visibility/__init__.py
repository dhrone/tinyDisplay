"""
Visibility management for the dependency system.

This package provides components for tracking and managing visibility states
of objects in a hierarchical display system. It's designed to work with
the dependency management system to optimize rendering and event propagation.

Key components:
- VisibilityContext: Tracks visibility state and notifies listeners of changes
- VisibilityTracker: Handles spatial queries and visibility computation
- Protocols: Defines interfaces for visibility-aware objects
"""

from .context import VisibilityContext
from .tracker import VisibilityTracker
from .protocols import VisibilityAware, VisibilityProvider

__all__ = [
    'VisibilityContext',
    'VisibilityTracker',
    'VisibilityAware',
    'VisibilityProvider',
]
