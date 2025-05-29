#!/usr/bin/env python3
"""
Canvas Nesting System

Provides hierarchical canvas support for complex layouts including:
- Parent-child canvas relationships
- Coordinate transformation between canvas levels
- Event propagation through canvas hierarchy
- Nested canvas rendering optimization
- Canvas tree traversal and manipulation utilities
"""

from typing import Optional, List, Dict, Any, Set, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import threading
import weakref

from .canvas import Canvas, CanvasConfig, CanvasState
from .transforms import CoordinateTransform
from ..widgets.base import Widget, WidgetBounds


class CanvasRelationship(Enum):
    """Types of canvas relationships."""
    PARENT = "parent"
    CHILD = "child"
    SIBLING = "sibling"
    ANCESTOR = "ancestor"
    DESCENDANT = "descendant"


@dataclass
class CanvasTreeNode:
    """Node in the canvas hierarchy tree."""
    canvas: 'NestedCanvas'
    parent: Optional['CanvasTreeNode'] = None
    children: List['CanvasTreeNode'] = None
    depth: int = 0
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


class NestedCanvas(Canvas):
    """Canvas with support for parent-child relationships.
    
    Extends the base Canvas class to support hierarchical layouts with
    coordinate transformation, event propagation, and nested rendering.
    """
    
    def __init__(self, config: CanvasConfig, parent: Optional['NestedCanvas'] = None, 
                 canvas_id: Optional[str] = None):
        """Initialize nested canvas.
        
        Args:
            config: Canvas configuration
            parent: Optional parent canvas
            canvas_id: Optional canvas identifier
        """
        super().__init__(config, canvas_id)
        
        # Hierarchy management
        self._parent: Optional[NestedCanvas] = None
        self._children: List[NestedCanvas] = []
        self._coordinate_transform: Optional[CoordinateTransform] = None
        self._tree_node: Optional[CanvasTreeNode] = None
        
        # Event propagation
        self._event_propagation_enabled = True
        self._event_bubbling_enabled = True
        self._event_capturing_enabled = True
        
        # Rendering optimization
        self._inherit_clipping = True
        self._inherit_transforms = True
        self._cache_transforms = True
        self._cached_world_transform: Optional[CoordinateTransform] = None
        
        # Thread safety for hierarchy operations
        self._hierarchy_lock = threading.RLock()
        
        # Initialize tree node for root canvas
        if parent is None:
            self._tree_node = CanvasTreeNode(canvas=self, depth=0)
        
        # Set parent if provided
        if parent:
            parent.add_child_canvas(self)
    
    @property
    def parent(self) -> Optional['NestedCanvas']:
        """Get parent canvas."""
        return self._parent
    
    @property
    def children(self) -> List['NestedCanvas']:
        """Get child canvases."""
        return self._children.copy()
    
    @property
    def depth(self) -> int:
        """Get depth in canvas hierarchy (0 for root)."""
        return self._tree_node.depth if self._tree_node else 0
    
    @property
    def is_root(self) -> bool:
        """Check if this is a root canvas."""
        return self._parent is None
    
    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf canvas (no children)."""
        return len(self._children) == 0
    
    @property
    def bounds(self) -> WidgetBounds:
        """Get canvas bounds including position."""
        x, y = self.position
        width, height = self.size
        return WidgetBounds(x, y, width, height)
    
    @property
    def position(self) -> Tuple[int, int]:
        """Get canvas position."""
        return super().position
    
    @position.setter
    def position(self, value: Tuple[int, int]) -> None:
        """Set canvas position and update coordinate transform."""
        super(NestedCanvas, self.__class__).position.fset(self, value)
        if hasattr(self, '_parent'):  # Only update if fully initialized
            self._update_coordinate_transform()
    
    @property
    def size(self) -> Tuple[int, int]:
        """Get canvas size."""
        return super().size
    
    @size.setter
    def size(self, value: Tuple[int, int]) -> None:
        """Set canvas size and update coordinate transform."""
        super(NestedCanvas, self.__class__).size.fset(self, value)
        if hasattr(self, '_parent'):  # Only update if fully initialized
            self._update_coordinate_transform()
    
    @property
    def world_bounds(self) -> WidgetBounds:
        """Get bounds in world (root canvas) coordinates."""
        if self.is_root:
            return self.bounds
        
        # Transform the canvas origin (0, 0) to world coordinates
        world_x, world_y = self.transform_to_world(0, 0)
        return WidgetBounds(world_x, world_y, self.bounds.width, self.bounds.height)
    
    def add_child_canvas(self, child: 'NestedCanvas') -> None:
        """Add a child canvas.
        
        Args:
            child: Child canvas to add
        """
        with self._hierarchy_lock:
            if child in self._children:
                return  # Already a child
            
            # Remove from previous parent if any
            if child._parent:
                child._parent.remove_child_canvas(child)
            
            # Add to children
            self._children.append(child)
            child._parent = self
            child._update_coordinate_transform()
            child._update_tree_node()
            
            # Update depth for child and its descendants
            self._update_descendant_depths(child)
            
            # Initialize child if this canvas is active
            if self._state in (CanvasState.ACTIVE, CanvasState.INITIALIZED):
                if child.state == CanvasState.CREATED:
                    child.initialize()
                if self._state == CanvasState.ACTIVE:
                    child.activate()
            
            # Emit event
            self._call_event_handlers('child_canvas_added', child)
    
    def remove_child_canvas(self, child: 'NestedCanvas') -> bool:
        """Remove a child canvas.
        
        Args:
            child: Child canvas to remove
            
        Returns:
            True if child was removed
        """
        with self._hierarchy_lock:
            if child not in self._children:
                return False
            
            # Remove from children
            self._children.remove(child)
            child._parent = None
            child._coordinate_transform = None
            child._tree_node = None
            child._cached_world_transform = None
            
            # Emit event
            self._call_event_handlers('child_canvas_removed', child)
            return True
    
    def get_child_canvas(self, canvas_id: str) -> Optional['NestedCanvas']:
        """Get child canvas by ID.
        
        Args:
            canvas_id: Canvas identifier
            
        Returns:
            Child canvas or None if not found
        """
        for child in self._children:
            if child.widget_id == canvas_id:
                return child
        return None
    
    def find_canvas_by_id(self, canvas_id: str) -> Optional['NestedCanvas']:
        """Find canvas by ID in entire subtree.
        
        Args:
            canvas_id: Canvas identifier
            
        Returns:
            Canvas or None if not found
        """
        if self.widget_id == canvas_id:
            return self
        
        for child in self._children:
            result = child.find_canvas_by_id(canvas_id)
            if result:
                return result
        
        return None
    
    def get_root_canvas(self) -> 'NestedCanvas':
        """Get the root canvas of the hierarchy.
        
        Returns:
            Root canvas
        """
        current = self
        while current._parent:
            current = current._parent
        return current
    
    def get_ancestors(self) -> List['NestedCanvas']:
        """Get all ancestor canvases.
        
        Returns:
            List of ancestors from immediate parent to root
        """
        ancestors = []
        current = self._parent
        while current:
            ancestors.append(current)
            current = current._parent
        return ancestors
    
    def get_descendants(self) -> List['NestedCanvas']:
        """Get all descendant canvases.
        
        Returns:
            List of all descendants in depth-first order
        """
        descendants = []
        for child in self._children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
    
    def get_siblings(self) -> List['NestedCanvas']:
        """Get sibling canvases.
        
        Returns:
            List of sibling canvases
        """
        if not self._parent:
            return []
        
        return [child for child in self._parent._children if child != self]
    
    def get_relationship(self, other: 'NestedCanvas') -> Optional[CanvasRelationship]:
        """Get relationship to another canvas.
        
        Args:
            other: Other canvas
            
        Returns:
            Relationship type or None if no relationship
        """
        if other == self._parent:
            return CanvasRelationship.PARENT
        elif other in self._children:
            return CanvasRelationship.CHILD
        elif other in self.get_siblings():
            return CanvasRelationship.SIBLING
        elif other in self.get_ancestors():
            return CanvasRelationship.ANCESTOR
        elif other in self.get_descendants():
            return CanvasRelationship.DESCENDANT
        else:
            return None
    
    def transform_to_parent(self, x: int, y: int) -> Tuple[int, int]:
        """Transform coordinates to parent space.
        
        Args:
            x, y: Coordinates in this canvas space
            
        Returns:
            Coordinates in parent space
        """
        if self._coordinate_transform:
            return self._coordinate_transform.child_to_parent(x, y)
        return (x, y)
    
    def transform_from_parent(self, x: int, y: int) -> Tuple[int, int]:
        """Transform coordinates from parent space.
        
        Args:
            x, y: Coordinates in parent space
            
        Returns:
            Coordinates in this canvas space
        """
        if self._coordinate_transform:
            return self._coordinate_transform.parent_to_child(x, y)
        return (x, y)
    
    def transform_to_world(self, x: int, y: int) -> Tuple[int, int]:
        """Transform coordinates to world (root canvas) space.
        
        Args:
            x, y: Coordinates in this canvas space
            
        Returns:
            Coordinates in world space
        """
        current_x, current_y = x, y
        current_canvas = self
        
        while current_canvas._parent:
            current_x, current_y = current_canvas.transform_to_parent(current_x, current_y)
            current_canvas = current_canvas._parent
        
        return (current_x, current_y)
    
    def transform_from_world(self, x: int, y: int) -> Tuple[int, int]:
        """Transform coordinates from world (root canvas) space.
        
        Args:
            x, y: Coordinates in world space
            
        Returns:
            Coordinates in this canvas space
        """
        # Get path from root to this canvas
        path = []
        current = self
        while current:
            path.append(current)
            current = current._parent
        path.reverse()  # Root first
        
        # Transform through each level
        current_x, current_y = x, y
        for i in range(1, len(path)):  # Skip root
            canvas = path[i]
            current_x, current_y = canvas.transform_from_parent(current_x, current_y)
        
        return (current_x, current_y)
    
    def get_world_transform(self) -> Optional[CoordinateTransform]:
        """Get cached world transformation.
        
        Returns:
            World transformation or None if root canvas
        """
        if self.is_root:
            return None
        
        if self._cache_transforms and self._cached_world_transform:
            return self._cached_world_transform
        
        # Calculate world transform
        if self._parent and self._coordinate_transform:
            parent_world_transform = self._parent.get_world_transform()
            if parent_world_transform:
                # Combine transformations
                # This is a simplified version - in practice would need proper matrix composition
                self._cached_world_transform = self._coordinate_transform
            else:
                self._cached_world_transform = self._coordinate_transform
        
        return self._cached_world_transform
    
    def invalidate_world_transform(self) -> None:
        """Invalidate cached world transformation."""
        self._cached_world_transform = None
        
        # Invalidate for all descendants
        for child in self._children:
            child.invalidate_world_transform()
    
    def propagate_event_down(self, event_type: str, *args, **kwargs) -> bool:
        """Propagate event down to children (capturing phase).
        
        Args:
            event_type: Type of event
            *args, **kwargs: Event arguments
            
        Returns:
            True if event was handled
        """
        if not self._event_capturing_enabled:
            return False
        
        for child in self._children:
            if child.propagate_event_down(event_type, *args, **kwargs):
                return True
            
            # Handle event at child level
            if hasattr(child, f'_handle_{event_type}'):
                handler = getattr(child, f'_handle_{event_type}')
                if handler(*args, **kwargs):
                    return True
        
        return False
    
    def propagate_event_up(self, event_type: str, *args, **kwargs) -> bool:
        """Propagate event up to parent (bubbling phase).
        
        Args:
            event_type: Type of event
            *args, **kwargs: Event arguments
            
        Returns:
            True if event was handled
        """
        if not self._event_bubbling_enabled or not self._parent:
            return False
        
        # Handle at parent level
        if hasattr(self._parent, f'_handle_{event_type}'):
            handler = getattr(self._parent, f'_handle_{event_type}')
            if handler(*args, **kwargs):
                return True
        
        # Continue bubbling up
        return self._parent.propagate_event_up(event_type, *args, **kwargs)
    
    def render(self, target_canvas: Optional['Canvas'] = None) -> None:
        """Render canvas and all child canvases.
        
        Args:
            target_canvas: Optional target canvas for rendering
        """
        if self._state != CanvasState.ACTIVE:
            return
        
        # Render this canvas
        super().render(target_canvas)
        
        # Render child canvases in z-order
        child_z_orders = [(child.z_order, child) for child in self._children]
        child_z_orders.sort(key=lambda x: x[0])
        
        for _, child in child_z_orders:
            if child.state == CanvasState.ACTIVE and child.visible:
                child.render(self)
    
    def activate(self) -> None:
        """Activate canvas and all child canvases."""
        super().activate()
        
        # Activate children
        for child in self._children:
            if child.state in (CanvasState.INITIALIZED, CanvasState.PAUSED):
                child.activate()
    
    def pause(self) -> None:
        """Pause canvas and all child canvases."""
        super().pause()
        
        # Pause children
        for child in self._children:
            if child.state == CanvasState.ACTIVE:
                child.pause()
    
    def destroy(self) -> None:
        """Destroy canvas and all child canvases."""
        # Destroy children first
        for child in self._children.copy():
            child.destroy()
        
        # Remove from parent
        if self._parent:
            self._parent.remove_child_canvas(self)
        
        super().destroy()
    
    def get_canvas_tree_info(self) -> Dict[str, Any]:
        """Get information about the canvas tree.
        
        Returns:
            Dictionary with tree information
        """
        return {
            'canvas_id': self.widget_id,
            'depth': self.depth,
            'is_root': self.is_root,
            'is_leaf': self.is_leaf,
            'parent_id': self._parent.widget_id if self._parent else None,
            'child_count': len(self._children),
            'child_ids': [child.widget_id for child in self._children],
            'bounds': self.bounds,
            'world_bounds': self.world_bounds,
            'state': self._state.value
        }
    
    def _update_coordinate_transform(self) -> None:
        """Update coordinate transformation based on parent relationship."""
        if self._parent:
            self._coordinate_transform = CoordinateTransform(
                self._parent.bounds,
                self.bounds
            )
            self.invalidate_world_transform()
        else:
            self._coordinate_transform = None
    
    def _update_tree_node(self) -> None:
        """Update tree node information."""
        if self._parent and self._parent._tree_node:
            self._tree_node = CanvasTreeNode(
                canvas=self,
                parent=self._parent._tree_node,
                depth=self._parent._tree_node.depth + 1
            )
            self._parent._tree_node.children.append(self._tree_node)
        else:
            self._tree_node = CanvasTreeNode(canvas=self, depth=0)
    
    def _update_descendant_depths(self, root_child: 'NestedCanvas') -> None:
        """Update depth for all descendants of a child.
        
        Args:
            root_child: Child whose descendants need depth updates
        """
        def update_depth(canvas: NestedCanvas, depth: int):
            if canvas._tree_node:
                canvas._tree_node.depth = depth
            for child in canvas._children:
                update_depth(child, depth + 1)
        
        if root_child._tree_node:
            update_depth(root_child, root_child._tree_node.depth)


class CanvasHierarchyManager:
    """Manages canvas hierarchy operations and utilities.
    
    Provides utilities for traversing, querying, and manipulating
    canvas hierarchies.
    """
    
    def __init__(self):
        self._root_canvases: Set[NestedCanvas] = set()
        self._all_canvases: Dict[str, NestedCanvas] = {}
        self._lock = threading.RLock()
    
    def register_canvas(self, canvas: NestedCanvas) -> None:
        """Register a canvas with the hierarchy manager.
        
        Args:
            canvas: Canvas to register
        """
        with self._lock:
            self._all_canvases[canvas.widget_id] = canvas
            
            if canvas.is_root:
                self._root_canvases.add(canvas)
    
    def unregister_canvas(self, canvas: NestedCanvas) -> None:
        """Unregister a canvas from the hierarchy manager.
        
        Args:
            canvas: Canvas to unregister
        """
        with self._lock:
            self._all_canvases.pop(canvas.widget_id, None)
            self._root_canvases.discard(canvas)
    
    def get_canvas_by_id(self, canvas_id: str) -> Optional[NestedCanvas]:
        """Get canvas by ID.
        
        Args:
            canvas_id: Canvas identifier
            
        Returns:
            Canvas or None if not found
        """
        return self._all_canvases.get(canvas_id)
    
    def get_root_canvases(self) -> List[NestedCanvas]:
        """Get all root canvases.
        
        Returns:
            List of root canvases
        """
        return list(self._root_canvases)
    
    def find_canvases_by_criteria(self, predicate: Callable[[NestedCanvas], bool]) -> List[NestedCanvas]:
        """Find canvases matching criteria.
        
        Args:
            predicate: Function to test each canvas
            
        Returns:
            List of matching canvases
        """
        return [canvas for canvas in self._all_canvases.values() if predicate(canvas)]
    
    def get_hierarchy_stats(self) -> Dict[str, Any]:
        """Get statistics about the canvas hierarchy.
        
        Returns:
            Dictionary with hierarchy statistics
        """
        total_canvases = len(self._all_canvases)
        root_count = len(self._root_canvases)
        
        # Calculate depth statistics
        depths = [canvas.depth for canvas in self._all_canvases.values()]
        max_depth = max(depths) if depths else 0
        avg_depth = sum(depths) / len(depths) if depths else 0
        
        return {
            'total_canvases': total_canvases,
            'root_canvases': root_count,
            'max_depth': max_depth,
            'average_depth': avg_depth,
            'leaf_canvases': len([c for c in self._all_canvases.values() if c.is_leaf])
        }


# Global hierarchy manager instance
_hierarchy_manager = CanvasHierarchyManager()


def get_hierarchy_manager() -> CanvasHierarchyManager:
    """Get the global canvas hierarchy manager.
    
    Returns:
        Global hierarchy manager instance
    """
    return _hierarchy_manager


# Utility functions for canvas nesting
def create_nested_canvas(config: CanvasConfig, parent: Optional[NestedCanvas] = None,
                        canvas_id: Optional[str] = None) -> NestedCanvas:
    """Create a nested canvas.
    
    Args:
        config: Canvas configuration
        parent: Optional parent canvas
        canvas_id: Optional canvas identifier
        
    Returns:
        NestedCanvas instance
    """
    canvas = NestedCanvas(config, parent, canvas_id)
    _hierarchy_manager.register_canvas(canvas)
    return canvas


def find_common_ancestor(canvas1: NestedCanvas, canvas2: NestedCanvas) -> Optional[NestedCanvas]:
    """Find the common ancestor of two canvases.
    
    Args:
        canvas1, canvas2: Canvases to find common ancestor for
        
    Returns:
        Common ancestor canvas or None if no common ancestor
    """
    ancestors1 = set([canvas1] + canvas1.get_ancestors())
    ancestors2 = set([canvas2] + canvas2.get_ancestors())
    
    common_ancestors = ancestors1.intersection(ancestors2)
    if not common_ancestors:
        return None
    
    # Return the deepest common ancestor
    return max(common_ancestors, key=lambda c: c.depth) 