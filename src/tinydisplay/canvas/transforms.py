#!/usr/bin/env python3
"""
Coordinate Transformation Utilities

Provides coordinate system support for advanced canvas composition including:
- Multiple coordinate modes (absolute, relative, parent-relative)
- Coordinate transformation between nested canvases
- Position validation and bounds checking
- Coordinate space conversion utilities
"""

from typing import Union, Tuple, Optional, Protocol
from dataclasses import dataclass
from enum import Enum
import math

from ..widgets.base import WidgetBounds


class CoordinateMode(Enum):
    """Coordinate system modes for flexible positioning."""
    ABSOLUTE = "absolute"              # Pixel coordinates (default)
    RELATIVE = "relative"              # Percentage coordinates (0.0-1.0)
    PARENT_RELATIVE = "parent_relative"  # Relative to parent canvas bounds


@dataclass
class Position:
    """Enhanced position with coordinate mode support.
    
    Supports multiple coordinate modes for flexible positioning:
    - ABSOLUTE: Direct pixel coordinates
    - RELATIVE: Percentage-based coordinates (0.0-1.0)
    - PARENT_RELATIVE: Relative to parent canvas bounds
    """
    x: Union[int, float]
    y: Union[int, float]
    mode: CoordinateMode = CoordinateMode.ABSOLUTE
    
    def to_absolute(self, canvas_bounds: WidgetBounds, 
                   parent_bounds: Optional[WidgetBounds] = None) -> Tuple[int, int]:
        """Convert position to absolute coordinates.
        
        Args:
            canvas_bounds: Bounds of the target canvas
            parent_bounds: Optional parent canvas bounds for PARENT_RELATIVE mode
            
        Returns:
            Tuple of absolute (x, y) coordinates
            
        Raises:
            ValueError: If coordinate mode is unsupported or parent_bounds missing for PARENT_RELATIVE
        """
        if self.mode == CoordinateMode.ABSOLUTE:
            return (int(self.x), int(self.y))
            
        elif self.mode == CoordinateMode.RELATIVE:
            # Convert percentage to absolute within canvas bounds
            abs_x = int(self.x * canvas_bounds.width) + canvas_bounds.x
            abs_y = int(self.y * canvas_bounds.height) + canvas_bounds.y
            return (abs_x, abs_y)
            
        elif self.mode == CoordinateMode.PARENT_RELATIVE:
            if parent_bounds is None:
                raise ValueError("parent_bounds required for PARENT_RELATIVE coordinate mode")
            # Convert percentage to absolute within parent bounds
            abs_x = int(self.x * parent_bounds.width) + parent_bounds.x
            abs_y = int(self.y * parent_bounds.height) + parent_bounds.y
            return (abs_x, abs_y)
            
        else:
            raise ValueError(f"Unsupported coordinate mode: {self.mode}")
    
    def validate(self) -> bool:
        """Validate position values based on coordinate mode.
        
        Returns:
            True if position is valid for its coordinate mode
        """
        if self.mode == CoordinateMode.ABSOLUTE:
            # Absolute coordinates can be any integer values
            return isinstance(self.x, (int, float)) and isinstance(self.y, (int, float))
            
        elif self.mode in (CoordinateMode.RELATIVE, CoordinateMode.PARENT_RELATIVE):
            # Relative coordinates should be in range [0.0, 1.0]
            return (0.0 <= self.x <= 1.0) and (0.0 <= self.y <= 1.0)
            
        return False
    
    def clamp_to_bounds(self, bounds: WidgetBounds) -> 'Position':
        """Clamp position to stay within specified bounds.
        
        Args:
            bounds: Bounds to clamp position within
            
        Returns:
            New Position instance clamped to bounds
        """
        if self.mode == CoordinateMode.ABSOLUTE:
            clamped_x = max(bounds.x, min(self.x, bounds.right))
            clamped_y = max(bounds.y, min(self.y, bounds.bottom))
            return Position(clamped_x, clamped_y, self.mode)
            
        elif self.mode in (CoordinateMode.RELATIVE, CoordinateMode.PARENT_RELATIVE):
            # Clamp relative coordinates to [0.0, 1.0]
            clamped_x = max(0.0, min(self.x, 1.0))
            clamped_y = max(0.0, min(self.y, 1.0))
            return Position(clamped_x, clamped_y, self.mode)
            
        return self


class CoordinateTransform:
    """Coordinate transformation utilities for nested canvases.
    
    Handles coordinate space conversion between parent and child canvases,
    including scaling, translation, and bounds validation.
    """
    
    def __init__(self, parent_bounds: WidgetBounds, child_bounds: WidgetBounds):
        """Initialize coordinate transformation.
        
        Args:
            parent_bounds: Bounds of the parent canvas
            child_bounds: Bounds of the child canvas within parent space
        """
        self.parent_bounds = parent_bounds
        self.child_bounds = child_bounds
        
        # Calculate transformation parameters
        self._offset_x = child_bounds.x - parent_bounds.x
        self._offset_y = child_bounds.y - parent_bounds.y
        self._scale_x = child_bounds.width / parent_bounds.width if parent_bounds.width > 0 else 1.0
        self._scale_y = child_bounds.height / parent_bounds.height if parent_bounds.height > 0 else 1.0
    
    def parent_to_child(self, x: int, y: int) -> Tuple[int, int]:
        """Transform coordinates from parent to child space.
        
        Args:
            x, y: Coordinates in parent space
            
        Returns:
            Tuple of coordinates in child space
        """
        child_x = x - self.child_bounds.x
        child_y = y - self.child_bounds.y
        return (child_x, child_y)
    
    def child_to_parent(self, x: int, y: int) -> Tuple[int, int]:
        """Transform coordinates from child to parent space.
        
        Args:
            x, y: Coordinates in child space
            
        Returns:
            Tuple of coordinates in parent space
        """
        parent_x = x + self.child_bounds.x
        parent_y = y + self.child_bounds.y
        return (parent_x, parent_y)
    
    def transform_bounds_to_parent(self, bounds: WidgetBounds) -> WidgetBounds:
        """Transform bounds from child to parent space.
        
        Args:
            bounds: Bounds in child space
            
        Returns:
            Bounds transformed to parent space
        """
        parent_x, parent_y = self.child_to_parent(bounds.x, bounds.y)
        return WidgetBounds(parent_x, parent_y, bounds.width, bounds.height)
    
    def transform_bounds_to_child(self, bounds: WidgetBounds) -> WidgetBounds:
        """Transform bounds from parent to child space.
        
        Args:
            bounds: Bounds in parent space
            
        Returns:
            Bounds transformed to child space
        """
        child_x, child_y = self.parent_to_child(bounds.x, bounds.y)
        return WidgetBounds(child_x, child_y, bounds.width, bounds.height)
    
    def is_point_in_child(self, x: int, y: int) -> bool:
        """Check if a point in parent space is within child bounds.
        
        Args:
            x, y: Coordinates in parent space
            
        Returns:
            True if point is within child bounds
        """
        return self.child_bounds.contains_point(x, y)
    
    def get_visible_child_bounds(self) -> WidgetBounds:
        """Get the visible portion of child canvas in child coordinates.
        
        Returns:
            Bounds representing visible area in child coordinate space
        """
        # Calculate intersection of child bounds with parent bounds
        intersection = self.child_bounds.intersect(self.parent_bounds)
        if intersection.width <= 0 or intersection.height <= 0:
            return WidgetBounds(0, 0, 0, 0)  # No visible area
        
        # Convert intersection to child coordinates
        return self.transform_bounds_to_child(intersection)


class CoordinateValidator:
    """Utilities for validating coordinates and positions."""
    
    @staticmethod
    def validate_position(position: Position, canvas_bounds: WidgetBounds,
                         parent_bounds: Optional[WidgetBounds] = None) -> bool:
        """Validate that a position is valid for the given bounds.
        
        Args:
            position: Position to validate
            canvas_bounds: Target canvas bounds
            parent_bounds: Optional parent bounds for PARENT_RELATIVE mode
            
        Returns:
            True if position is valid
        """
        if not position.validate():
            return False
        
        try:
            abs_x, abs_y = position.to_absolute(canvas_bounds, parent_bounds)
            return canvas_bounds.contains_point(abs_x, abs_y)
        except ValueError:
            return False
    
    @staticmethod
    def clamp_position_to_canvas(position: Position, canvas_bounds: WidgetBounds,
                                parent_bounds: Optional[WidgetBounds] = None) -> Position:
        """Clamp position to stay within canvas bounds.
        
        Args:
            position: Position to clamp
            canvas_bounds: Canvas bounds to clamp within
            parent_bounds: Optional parent bounds for PARENT_RELATIVE mode
            
        Returns:
            New Position clamped to canvas bounds
        """
        try:
            abs_x, abs_y = position.to_absolute(canvas_bounds, parent_bounds)
            
            # Clamp to canvas bounds
            clamped_x = max(canvas_bounds.x, min(abs_x, canvas_bounds.right - 1))
            clamped_y = max(canvas_bounds.y, min(abs_y, canvas_bounds.bottom - 1))
            
            # Convert back to original coordinate mode
            if position.mode == CoordinateMode.ABSOLUTE:
                return Position(clamped_x, clamped_y, position.mode)
                
            elif position.mode == CoordinateMode.RELATIVE:
                rel_x = (clamped_x - canvas_bounds.x) / canvas_bounds.width if canvas_bounds.width > 0 else 0.0
                rel_y = (clamped_y - canvas_bounds.y) / canvas_bounds.height if canvas_bounds.height > 0 else 0.0
                return Position(rel_x, rel_y, position.mode)
                
            elif position.mode == CoordinateMode.PARENT_RELATIVE and parent_bounds:
                rel_x = (clamped_x - parent_bounds.x) / parent_bounds.width if parent_bounds.width > 0 else 0.0
                rel_y = (clamped_y - parent_bounds.y) / parent_bounds.height if parent_bounds.height > 0 else 0.0
                return Position(rel_x, rel_y, position.mode)
                
        except ValueError:
            pass
        
        # Fallback: return original position
        return position
    
    @staticmethod
    def distance_between_positions(pos1: Position, pos2: Position, 
                                  canvas_bounds: WidgetBounds,
                                  parent_bounds: Optional[WidgetBounds] = None) -> float:
        """Calculate distance between two positions.
        
        Args:
            pos1, pos2: Positions to calculate distance between
            canvas_bounds: Canvas bounds for coordinate conversion
            parent_bounds: Optional parent bounds for PARENT_RELATIVE mode
            
        Returns:
            Distance between positions in pixels
        """
        try:
            x1, y1 = pos1.to_absolute(canvas_bounds, parent_bounds)
            x2, y2 = pos2.to_absolute(canvas_bounds, parent_bounds)
            return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        except ValueError:
            return float('inf')


# Utility functions for common coordinate operations
def create_absolute_position(x: int, y: int) -> Position:
    """Create an absolute position.
    
    Args:
        x, y: Absolute coordinates
        
    Returns:
        Position with ABSOLUTE coordinate mode
    """
    return Position(x, y, CoordinateMode.ABSOLUTE)


def create_relative_position(x: float, y: float) -> Position:
    """Create a relative position.
    
    Args:
        x, y: Relative coordinates (0.0-1.0)
        
    Returns:
        Position with RELATIVE coordinate mode
    """
    return Position(x, y, CoordinateMode.RELATIVE)


def create_parent_relative_position(x: float, y: float) -> Position:
    """Create a parent-relative position.
    
    Args:
        x, y: Parent-relative coordinates (0.0-1.0)
        
    Returns:
        Position with PARENT_RELATIVE coordinate mode
    """
    return Position(x, y, CoordinateMode.PARENT_RELATIVE) 