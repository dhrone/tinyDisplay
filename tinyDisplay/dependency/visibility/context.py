"""
Visibility context implementation.

This module provides the VisibilityContext class which tracks visibility states
and notifies listeners of changes.
"""

from __future__ import annotations

import weakref
from collections import defaultdict
from typing import Any, Callable, Dict, Set, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .protocols import VisibilityAware


class VisibilityContext:
    """Tracks visibility states and notifies listeners of changes.
    
    This class maintains the visibility state of objects and provides methods
    to update and query these states. It uses weak references to avoid
    preventing garbage collection of tracked objects.
    """
    
    def __init__(self):
        """Initialize a new VisibilityContext."""
        # Maps objects to their visibility state
        self._visibility_states: Dict[int, bool] = {}
        
        # Maps objects to sets of callbacks to call when their visibility changes
        self._listeners: Dict[int, Set[Callable[[Any, bool], None]]] = defaultdict(set)
        
        # Keep weak refs to objects to avoid memory leaks
        self._weak_refs: Dict[int, weakref.ref] = {}
    
    def set_visible(self, obj: Any, visible: bool) -> None:
        """Update the visibility state of an object.
        
        If the visibility has changed, notifies all registered listeners.
        
        Args:
            obj: The object whose visibility is changing.
            visible: The new visibility state.
        """
        obj_id = id(obj)
        current = self._visibility_states.get(obj_id)
        
        if current != visible:
            self._visibility_states[obj_id] = visible
            self._weak_refs[obj_id] = weakref.ref(obj)
            self._notify_listeners(obj, visible)
    
    def is_visible(self, obj: Any) -> bool:
        """Check if an object is currently visible.
        
        Args:
            obj: The object to check.
            
        Returns:
            bool: True if the object is visible, False otherwise.
                  Returns True if the object's visibility hasn't been set.
        """
        return self._visibility_states.get(id(obj), True)
    
    def add_listener(
        self, 
        obj: Any, 
        callback: Callable[[Any, bool], None]
    ) -> None:
        """Register a callback for visibility changes of an object.
        
        Args:
            obj: The object to monitor for visibility changes.
            callback: Function to call when visibility changes.
                     Called as callback(obj, is_visible).
        """
        obj_id = id(obj)
        self._listeners[obj_id].add(callback)
        self._weak_refs[obj_id] = weakref.ref(obj)
    
    def remove_listener(
        self, 
        obj: Any, 
        callback: Callable[[Any, bool], None]
    ) -> None:
        """Unregister a visibility change callback.
        
        Args:
            obj: The object being monitored.
            callback: The callback function to remove.
        """
        obj_id = id(obj)
        if obj_id in self._listeners:
            self._listeners[obj_id].discard(callback)
    
    def _notify_listeners(self, obj: Any, visible: bool) -> None:
        """Notify all listeners of a visibility change.
        
        Args:
            obj: The object whose visibility changed.
            visible: The new visibility state.
        """
        obj_id = id(obj)
        listeners = self._listeners.get(obj_id, set()).copy()
        
        # Clean up dead weak refs while we're here
        dead_refs = []
        
        for ref_id, ref in list(self._weak_refs.items()):
            if ref() is None:
                dead_refs.append(ref_id)
        
        for ref_id in dead_refs:
            self._weak_refs.pop(ref_id, None)
            self._visibility_states.pop(ref_id, None)
            self._listeners.pop(ref_id, None)
        
        # Notify listeners
        for callback in listeners:
            try:
                callback(obj, visible)
            except Exception as e:
                import logging
                logging.getLogger(__name__).exception(
                    f"Error in visibility change callback: {e}"
                )
    
    def get_visible_objects(self) -> Set[Any]:
        """Get all objects that are currently marked as visible.
        
        Returns:
            Set of objects that are currently visible.
        """
        visible = set()
        for obj_id, is_visible in self._visibility_states.items():
            if is_visible:
                obj = self._weak_refs.get(obj_id, lambda: None)()
                if obj is not None:
                    visible.add(obj)
        return visible
    
    def __contains__(self, obj: Any) -> bool:
        """Check if an object is being tracked by this context."""
        return id(obj) in self._visibility_states
    
    def __len__(self) -> int:
        """Get the number of objects being tracked."""
        return len(self._visibility_states)
