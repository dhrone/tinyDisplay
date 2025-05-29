#!/usr/bin/env python3
"""
Advanced Clipping System

Provides sophisticated clipping algorithms and management for canvas composition including:
- Rectangular clipping with efficient algorithms
- Overflow detection and prevention mechanisms
- Clipping region management for nested canvases
- Clipping optimization for performance
- Visual debugging tools for clipping regions
"""

from typing import List, Optional, Set, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import threading

from ..widgets.base import WidgetBounds


class ClippingMode(Enum):
    """Clipping behavior modes."""
    NONE = "none"                    # No clipping applied
    STRICT = "strict"                # Strict rectangular clipping
    SOFT = "soft"                    # Soft clipping with fade effects
    OVERFLOW_HIDDEN = "overflow_hidden"  # Hide overflow content
    OVERFLOW_SCROLL = "overflow_scroll"  # Enable scrolling for overflow


@dataclass
class ClippingRegion:
    """Defines a clipping region with bounds and properties.
    
    Represents a rectangular clipping area with configurable behavior
    for how content should be handled when it extends beyond the bounds.
    """
    bounds: WidgetBounds
    mode: ClippingMode = ClippingMode.STRICT
    enabled: bool = True
    clip_children: bool = True
    fade_distance: int = 0  # Distance for soft clipping fade effect
    priority: int = 0       # Higher priority regions take precedence
    
    def intersects(self, other_bounds: WidgetBounds) -> bool:
        """Check if this clipping region intersects with given bounds.
        
        Args:
            other_bounds: Bounds to check intersection with
            
        Returns:
            True if regions intersect
        """
        return self.bounds.intersects(other_bounds)
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if point is within clipping region.
        
        Args:
            x, y: Point coordinates
            
        Returns:
            True if point is within region
        """
        return self.bounds.contains_point(x, y)
    
    def contains_bounds(self, bounds: WidgetBounds) -> bool:
        """Check if bounds are completely within clipping region.
        
        Args:
            bounds: Bounds to check
            
        Returns:
            True if bounds are completely contained
        """
        return self.bounds.contains_bounds(bounds)
    
    def clip_bounds(self, bounds: WidgetBounds) -> WidgetBounds:
        """Clip bounds to this region.
        
        Args:
            bounds: Bounds to clip
            
        Returns:
            Clipped bounds
        """
        return self.bounds.intersect(bounds)


class ClippingManager:
    """Advanced clipping management for canvas composition.
    
    Manages a stack of clipping regions with support for nested clipping,
    priority-based region selection, and efficient clipping calculations.
    """
    
    def __init__(self):
        self._clipping_stack: List[ClippingRegion] = []
        self._active_region: Optional[WidgetBounds] = None
        self._region_cache: Dict[str, WidgetBounds] = {}
        self._debug_enabled = False
        self._lock = threading.RLock()
    
    def push_clipping_region(self, region: ClippingRegion) -> None:
        """Push a new clipping region onto the stack.
        
        Args:
            region: Clipping region to add
        """
        with self._lock:
            self._clipping_stack.append(region)
            self._update_active_region()
            self._invalidate_cache()
    
    def pop_clipping_region(self) -> Optional[ClippingRegion]:
        """Pop the top clipping region from the stack.
        
        Returns:
            The removed clipping region, or None if stack was empty
        """
        with self._lock:
            if self._clipping_stack:
                region = self._clipping_stack.pop()
                self._update_active_region()
                self._invalidate_cache()
                return region
            return None
    
    def clear_clipping_regions(self) -> None:
        """Clear all clipping regions."""
        with self._lock:
            self._clipping_stack.clear()
            self._active_region = None
            self._invalidate_cache()
    
    def get_active_clipping_bounds(self) -> Optional[WidgetBounds]:
        """Get the currently active clipping bounds.
        
        Returns:
            Active clipping bounds, or None if no clipping active
        """
        return self._active_region
    
    def is_widget_visible(self, widget_bounds: WidgetBounds) -> bool:
        """Check if widget is visible within active clipping region.
        
        Args:
            widget_bounds: Bounds of widget to check
            
        Returns:
            True if widget is at least partially visible
        """
        if self._active_region is None:
            return True
        return self._active_region.intersects(widget_bounds)
    
    def is_widget_fully_visible(self, widget_bounds: WidgetBounds) -> bool:
        """Check if widget is fully visible within active clipping region.
        
        Args:
            widget_bounds: Bounds of widget to check
            
        Returns:
            True if widget is completely visible
        """
        if self._active_region is None:
            return True
        return self._active_region.contains_bounds(widget_bounds)
    
    def clip_widget_bounds(self, widget_bounds: WidgetBounds) -> WidgetBounds:
        """Clip widget bounds to active clipping region.
        
        Args:
            widget_bounds: Original widget bounds
            
        Returns:
            Clipped widget bounds
        """
        if self._active_region is None:
            return widget_bounds
        return self._active_region.intersect(widget_bounds)
    
    def get_clipping_regions_for_bounds(self, bounds: WidgetBounds) -> List[ClippingRegion]:
        """Get all clipping regions that affect the given bounds.
        
        Args:
            bounds: Bounds to check against
            
        Returns:
            List of clipping regions that intersect with bounds
        """
        with self._lock:
            affecting_regions = []
            for region in self._clipping_stack:
                if region.enabled and region.intersects(bounds):
                    affecting_regions.append(region)
            return affecting_regions
    
    def calculate_visible_area(self, bounds: WidgetBounds) -> float:
        """Calculate the percentage of bounds that are visible.
        
        Args:
            bounds: Bounds to calculate visibility for
            
        Returns:
            Percentage of area visible (0.0 to 1.0)
        """
        if self._active_region is None:
            return 1.0
        
        clipped_bounds = self.clip_widget_bounds(bounds)
        if clipped_bounds.width <= 0 or clipped_bounds.height <= 0:
            return 0.0
        
        original_area = bounds.width * bounds.height
        visible_area = clipped_bounds.width * clipped_bounds.height
        
        return visible_area / original_area if original_area > 0 else 0.0
    
    def enable_debug_mode(self, enabled: bool = True) -> None:
        """Enable or disable debug mode for clipping visualization.
        
        Args:
            enabled: Whether to enable debug mode
        """
        self._debug_enabled = enabled
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about current clipping state.
        
        Returns:
            Dictionary with debug information
        """
        with self._lock:
            return {
                'active_region': self._active_region,
                'stack_depth': len(self._clipping_stack),
                'regions': [
                    {
                        'bounds': region.bounds,
                        'mode': region.mode.value,
                        'enabled': region.enabled,
                        'priority': region.priority
                    }
                    for region in self._clipping_stack
                ],
                'cache_size': len(self._region_cache)
            }
    
    def _update_active_region(self) -> None:
        """Update the active clipping region based on stack."""
        if not self._clipping_stack:
            self._active_region = None
            return
        
        # Find all enabled regions and sort by priority
        enabled_regions = [r for r in self._clipping_stack if r.enabled]
        if not enabled_regions:
            self._active_region = None
            return
        
        # Sort by priority (higher priority first)
        enabled_regions.sort(key=lambda r: r.priority, reverse=True)
        
        # Intersect all enabled clipping regions
        active_bounds = None
        for region in enabled_regions:
            if region.mode in (ClippingMode.STRICT, ClippingMode.OVERFLOW_HIDDEN):
                if active_bounds is None:
                    active_bounds = region.bounds
                else:
                    active_bounds = active_bounds.intersect(region.bounds)
        
        self._active_region = active_bounds
    
    def _invalidate_cache(self) -> None:
        """Invalidate the region cache."""
        self._region_cache.clear()


class OverflowDetector:
    """Detects and handles widget overflow conditions.
    
    Provides utilities for detecting when widgets extend beyond their
    container bounds and offers strategies for handling overflow.
    """
    
    def __init__(self):
        self._overflow_handlers: Dict[str, callable] = {}
    
    def detect_overflow(self, widget_bounds: WidgetBounds, 
                       container_bounds: WidgetBounds) -> Dict[str, bool]:
        """Detect overflow conditions for a widget.
        
        Args:
            widget_bounds: Bounds of the widget
            container_bounds: Bounds of the container
            
        Returns:
            Dictionary indicating overflow directions
        """
        return {
            'left': widget_bounds.x < container_bounds.x,
            'right': widget_bounds.right > container_bounds.right,
            'top': widget_bounds.y < container_bounds.y,
            'bottom': widget_bounds.bottom > container_bounds.bottom,
            'any': (
                widget_bounds.x < container_bounds.x or
                widget_bounds.right > container_bounds.right or
                widget_bounds.y < container_bounds.y or
                widget_bounds.bottom > container_bounds.bottom
            )
        }
    
    def calculate_overflow_amount(self, widget_bounds: WidgetBounds,
                                 container_bounds: WidgetBounds) -> Dict[str, int]:
        """Calculate the amount of overflow in each direction.
        
        Args:
            widget_bounds: Bounds of the widget
            container_bounds: Bounds of the container
            
        Returns:
            Dictionary with overflow amounts in pixels
        """
        return {
            'left': max(0, container_bounds.x - widget_bounds.x),
            'right': max(0, widget_bounds.right - container_bounds.right),
            'top': max(0, container_bounds.y - widget_bounds.y),
            'bottom': max(0, widget_bounds.bottom - container_bounds.bottom)
        }
    
    def suggest_overflow_strategy(self, widget_bounds: WidgetBounds,
                                 container_bounds: WidgetBounds) -> str:
        """Suggest an overflow handling strategy.
        
        Args:
            widget_bounds: Bounds of the widget
            container_bounds: Bounds of the container
            
        Returns:
            Suggested strategy name
        """
        overflow = self.detect_overflow(widget_bounds, container_bounds)
        
        if not overflow['any']:
            return 'none'
        
        overflow_amount = self.calculate_overflow_amount(widget_bounds, container_bounds)
        total_overflow = sum(overflow_amount.values())
        
        # Simple heuristics for strategy selection
        if total_overflow < 20:
            return 'clip'  # Small overflow, just clip
        elif widget_bounds.width > container_bounds.width * 1.5:
            return 'scroll'  # Large content, enable scrolling
        else:
            return 'resize'  # Medium overflow, consider resizing
    
    def register_overflow_handler(self, strategy: str, handler: callable) -> None:
        """Register a custom overflow handler.
        
        Args:
            strategy: Name of the strategy
            handler: Function to handle overflow
        """
        self._overflow_handlers[strategy] = handler
    
    def handle_overflow(self, strategy: str, widget_bounds: WidgetBounds,
                       container_bounds: WidgetBounds) -> WidgetBounds:
        """Handle overflow using the specified strategy.
        
        Args:
            strategy: Strategy to use
            widget_bounds: Original widget bounds
            container_bounds: Container bounds
            
        Returns:
            Adjusted widget bounds
        """
        if strategy in self._overflow_handlers:
            return self._overflow_handlers[strategy](widget_bounds, container_bounds)
        
        # Built-in strategies
        if strategy == 'clip':
            return container_bounds.intersect(widget_bounds)
        elif strategy == 'resize':
            # Resize to fit container
            return WidgetBounds(
                container_bounds.x,
                container_bounds.y,
                min(widget_bounds.width, container_bounds.width),
                min(widget_bounds.height, container_bounds.height)
            )
        else:
            return widget_bounds  # No change


class ClippingOptimizer:
    """Optimizes clipping operations for performance.
    
    Provides caching and optimization strategies to minimize
    the computational cost of clipping operations.
    """
    
    def __init__(self):
        self._clip_cache: Dict[Tuple, WidgetBounds] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._max_cache_size = 1000
    
    def get_cached_clip(self, widget_bounds: WidgetBounds,
                       clip_bounds: WidgetBounds) -> Optional[WidgetBounds]:
        """Get cached clipping result.
        
        Args:
            widget_bounds: Original widget bounds
            clip_bounds: Clipping bounds
            
        Returns:
            Cached result or None if not found
        """
        cache_key = (
            widget_bounds.x, widget_bounds.y, widget_bounds.width, widget_bounds.height,
            clip_bounds.x, clip_bounds.y, clip_bounds.width, clip_bounds.height
        )
        
        if cache_key in self._clip_cache:
            self._cache_hits += 1
            return self._clip_cache[cache_key]
        
        self._cache_misses += 1
        return None
    
    def cache_clip_result(self, widget_bounds: WidgetBounds, clip_bounds: WidgetBounds,
                         result: WidgetBounds) -> None:
        """Cache a clipping result.
        
        Args:
            widget_bounds: Original widget bounds
            clip_bounds: Clipping bounds
            result: Clipping result to cache
        """
        if len(self._clip_cache) >= self._max_cache_size:
            # Simple LRU: remove oldest entries
            keys_to_remove = list(self._clip_cache.keys())[:100]
            for key in keys_to_remove:
                del self._clip_cache[key]
        
        cache_key = (
            widget_bounds.x, widget_bounds.y, widget_bounds.width, widget_bounds.height,
            clip_bounds.x, clip_bounds.y, clip_bounds.width, clip_bounds.height
        )
        
        self._clip_cache[cache_key] = result
    
    def optimized_clip(self, widget_bounds: WidgetBounds,
                      clip_bounds: WidgetBounds) -> WidgetBounds:
        """Perform optimized clipping with caching.
        
        Args:
            widget_bounds: Bounds to clip
            clip_bounds: Clipping bounds
            
        Returns:
            Clipped bounds
        """
        # Check cache first
        cached_result = self.get_cached_clip(widget_bounds, clip_bounds)
        if cached_result is not None:
            return cached_result
        
        # Perform clipping
        result = clip_bounds.intersect(widget_bounds)
        
        # Cache result
        self.cache_clip_result(widget_bounds, clip_bounds, result)
        
        return result
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'cache_size': len(self._clip_cache),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': hit_rate,
            'max_cache_size': self._max_cache_size
        }
    
    def clear_cache(self) -> None:
        """Clear the clipping cache."""
        self._clip_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0


# Utility functions for common clipping operations
def create_clipping_region(x: int, y: int, width: int, height: int,
                          mode: ClippingMode = ClippingMode.STRICT) -> ClippingRegion:
    """Create a clipping region with specified bounds.
    
    Args:
        x, y: Top-left coordinates
        width, height: Dimensions
        mode: Clipping mode
        
    Returns:
        ClippingRegion instance
    """
    bounds = WidgetBounds(x, y, width, height)
    return ClippingRegion(bounds, mode)


def clip_bounds_to_region(bounds: WidgetBounds, region: ClippingRegion) -> WidgetBounds:
    """Clip bounds to a clipping region.
    
    Args:
        bounds: Bounds to clip
        region: Clipping region
        
    Returns:
        Clipped bounds
    """
    if not region.enabled:
        return bounds
    
    return region.clip_bounds(bounds) 