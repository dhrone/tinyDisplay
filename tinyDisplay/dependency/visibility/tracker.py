"""
Visibility tracker for spatial queries and visibility computation.

This module provides the VisibilityTracker class which determines visibility
based on spatial relationships and z-ordering of objects.
"""

from __future__ import annotations

import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .protocols import BoundsProvider, VisibilityAware
    from .context import VisibilityContext


@dataclass(order=True)
class _ZIndexEntry:
    """Internal class for tracking objects with z-indices."""
    z_index: int
    obj: Any = field(compare=False)


def _get_bounds(obj: Any) -> Optional[Tuple[int, int, int, int]]:
    """Safely get bounds from an object that may implement BoundsProvider."""
    if hasattr(obj, 'get_bounds'):
        try:
            return obj.get_bounds()
        except Exception:
            pass
    return None


class VisibilityTracker:
    """Tracks visibility of objects based on spatial relationships.
    
    This class determines which objects are visible based on their bounds,
    z-indices, and the bounds of other objects that might occlude them.
    It works with a VisibilityContext to maintain visibility states.
    """
    
    def __init__(self, context: Optional[VisibilityContext] = None):
        """Initialize a new VisibilityTracker.
        
        Args:
            context: Optional VisibilityContext to use. If not provided,
                   a new one will be created.
        """
        from .context import VisibilityContext
        self.context = context or VisibilityContext()
        
        # Track objects by their bounds for spatial queries
        self._objects: List[Any] = []
        self._bounds_cache: Dict[int, Optional[Tuple[int, int, int, int]]] = {}
        
        # Spatial index (simple implementation - could be enhanced with R-tree)
        self._spatial_index: Dict[Tuple[int, int, int, int], List[Any]] = {}
        
        # Track z-indices for proper depth ordering
        self._z_indices: Dict[int, int] = {}
    
    def add_object(self, obj: Any) -> None:
        """Add an object to be tracked for visibility.
        
        Args:
            obj: The object to track. Should implement BoundsProvider.
        """
        obj_id = id(obj)
        if obj_id not in self._bounds_cache:
            self._objects.append(weakref.ref(obj, self._object_finalized))
            self._update_object_cache(obj)
    
    def remove_object(self, obj: Any) -> None:
        """Stop tracking an object's visibility.
        
        Args:
            obj: The object to stop tracking.
        """
        obj_id = id(obj)
        self._bounds_cache.pop(obj_id, None)
        self._z_indices.pop(obj_id, None)
        
        # Remove from spatial index
        for bounds, objects in list(self._spatial_index.items()):
            try:
                objects.remove(obj)
                if not objects:
                    self._spatial_index.pop(bounds, None)
            except ValueError:
                pass
    
    def _object_finalized(self, ref: weakref.ref) -> None:
        """Clean up when a tracked object is garbage collected."""
        # Find and remove the dead reference
        dead_refs = [i for i, r in enumerate(self._objects) if r == ref or r() is None]
        for i in reversed(dead_refs):
            self._objects.pop(i)
    
    def _update_object_cache(self, obj: Any) -> None:
        """Update cached bounds and z-index for an object."""
        obj_id = id(obj)
        
        # Get bounds
        bounds = _get_bounds(obj)
        old_bounds = self._bounds_cache.get(obj_id)
        
        # Update bounds cache
        self._bounds_cache[obj_id] = bounds
        
        # Update spatial index if bounds changed
        if bounds != old_bounds:
            # Remove from old bounds in spatial index
            if old_bounds in self._spatial_index:
                try:
                    self._spatial_index[old_bounds].remove(obj)
                    if not self._spatial_index[old_bounds]:
                        self._spatial_index.pop(old_bounds)
                except ValueError:
                    pass
            
            # Add to new bounds in spatial index
            if bounds is not None:
                if bounds not in self._spatial_index:
                    self._spatial_index[bounds] = []
                self._spatial_index[bounds].append(obj)
        
        # Update z-index if available
        if hasattr(obj, 'get_z_index'):
            try:
                self._z_indices[obj_id] = obj.get_z_index()
            except Exception:
                self._z_indices.pop(obj_id, None)
    
    def compute_visibility(self) -> None:
        """Compute visibility for all tracked objects.
        
        This is a simple implementation that marks objects as visible if they
        have bounds and aren't completely occluded by other objects with
        higher z-indices.
        """
        # Update all object caches
        for obj_ref in self._objects[:]:  # Make a copy to avoid modification during iteration
            obj = obj_ref()
            if obj is not None:
                self._update_object_cache(obj)
        
        # For each object, check if it's occluded by any other object
        for obj_ref in self._objects:
            obj = obj_ref()
            if obj is None:
                continue
                
            obj_id = id(obj)
            bounds = self._bounds_cache.get(obj_id)
            
            if bounds is None:
                # Objects without bounds are considered visible
                self.context.set_visible(obj, True)
                continue
                
            # Default to visible unless we find an occluding object
            is_visible = True
            obj_z = self._z_indices.get(obj_id, 0)
            
            # Check for occluding objects
            for other_bounds, other_objects in self._spatial_index.items():
                if not self._bounds_intersect(bounds, other_bounds):
                    continue
                    
                for other in other_objects:
                    if other is obj:
                        continue
                        
                    other_id = id(other)
                    other_z = self._z_indices.get(other_id, 0)
                    
                    # Only consider objects with higher z-index as potential occluders
                    if other_z > obj_z and self._bounds_contain(other_bounds, bounds):
                        is_visible = False
                        break
                
                if not is_visible:
                    break
            
            self.context.set_visible(obj, is_visible)
    
    @staticmethod
    def _bounds_intersect(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
        """Check if two bounding boxes intersect."""
        return not (a[2] <= b[0] or  # a is left of b
                   a[0] >= b[2] or   # a is right of b
                   a[3] <= b[1] or    # a is above b
                   a[1] >= b[3])      # a is below b
    
    @staticmethod
    def _bounds_contain(outer: Tuple[int, int, int, int], inner: Tuple[int, int, int, int]) -> bool:
        """Check if one bounding box completely contains another."""
        return (inner[0] >= outer[0] and  # left
                inner[1] >= outer[1] and  # top
                inner[2] <= outer[2] and  # right
                inner[3] <= outer[3])     # bottom
    
    def get_visible_objects(self) -> Set[Any]:
        """Get all objects that are currently visible.
        
        Returns:
            Set of visible objects.
        """
        return self.context.get_visible_objects()
    
    def is_visible(self, obj: Any) -> bool:
        """Check if an object is currently visible.
        
        Args:
            obj: The object to check.
            
        Returns:
            bool: True if the object is visible.
        """
        return self.context.is_visible(obj)
