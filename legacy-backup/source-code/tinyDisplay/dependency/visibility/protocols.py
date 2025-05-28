"""
Protocols for visibility management.

This module defines the interfaces for objects that participate in the
visibility system.
"""

from typing import Protocol, runtime_checkable, Any, Optional, Callable, Tuple, List


@runtime_checkable
class VisibilityAware(Protocol):
    """Protocol for objects that can be visible or invisible.
    
    Objects implementing this protocol can have their visibility state tracked
    by the visibility system.
    """
    
    def set_visible(self, visible: bool) -> None:
        """Set the visibility state of the object.
        
        Args:
            visible: Whether the object should be visible.
        """
        ...
    
    def is_visible(self) -> bool:
        """Check if the object is currently visible.
        
        Returns:
            bool: True if the object is visible, False otherwise.
        """
        ...


@runtime_checkable
class VisibilityProvider(Protocol):
    """Protocol for objects that manage visibility of other objects.
    
    Typically implemented by container objects that can determine the
    visibility of their children based on layout, z-order, etc.
    """
    
    def compute_visibility(self) -> None:
        """Compute visibility states for all managed objects."""
        ...
    
    def get_visible_objects(self) -> set[Any]:
        """Get all objects that are currently visible.
        
        Returns:
            set: Set of visible objects.
        """
        ...
    
    def add_visibility_listener(
        self, 
        obj: Any, 
        callback: Callable[[Any, bool], None]
    ) -> None:
        """Register a callback for visibility changes.
        
        Args:
            obj: The object whose visibility changes we're interested in.
            callback: Function to call when visibility changes.
                     Called as callback(obj, is_visible).
        """
        ...


@runtime_checkable
class BoundsProvider(Protocol):
    """Protocol for objects that have bounds that affect visibility."""
    
    def get_bounds(self) -> tuple[int, int, int, int]:
        """Get the bounding box of the object.
        
        Returns:
            tuple: (x1, y1, x2, y2) coordinates of the bounding box.
        """
        ...
    
    def get_z_index(self) -> int:
        """Get the z-index of the object for depth ordering.
        
        Higher values are rendered on top of lower values.
        """
        ...
