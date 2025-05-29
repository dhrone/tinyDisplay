#!/usr/bin/env python3
"""
Viewport and Scrolling System

Provides viewport management for scrollable content areas including:
- Scrollable content areas with smooth scrolling
- Viewport clipping and content virtualization
- Scroll event handling and gesture support
- Scroll performance optimization for large content
- Viewport debugging and visualization tools
"""

from typing import Optional, Tuple, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import time
import math

from ..widgets.base import WidgetBounds


class ScrollDirection(Enum):
    """Scroll direction options."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    BOTH = "both"
    NONE = "none"


class ScrollBehavior(Enum):
    """Scroll behavior modes."""
    AUTO = "auto"        # Automatic scrolling based on content
    SMOOTH = "smooth"    # Smooth animated scrolling
    INSTANT = "instant"  # Immediate scrolling without animation


class ScrollBarVisibility(Enum):
    """Scroll bar visibility options."""
    AUTO = "auto"        # Show when needed
    ALWAYS = "always"    # Always visible
    NEVER = "never"      # Never visible
    HOVER = "hover"      # Show on hover


@dataclass
class ViewportConfig:
    """Configuration for viewport behavior."""
    width: int
    height: int
    content_width: int
    content_height: int
    scroll_x: int = 0
    scroll_y: int = 0
    enable_horizontal_scroll: bool = True
    enable_vertical_scroll: bool = True
    smooth_scrolling: bool = True
    scroll_speed: float = 100.0  # pixels per second
    scroll_acceleration: float = 2.0
    scroll_deceleration: float = 0.8
    bounce_enabled: bool = True
    bounce_distance: int = 20
    scrollbar_visibility: ScrollBarVisibility = ScrollBarVisibility.AUTO
    scrollbar_width: int = 12
    virtualization_enabled: bool = True
    virtualization_buffer: int = 100  # pixels


@dataclass
class ScrollEvent:
    """Scroll event data."""
    delta_x: int
    delta_y: int
    scroll_x: int
    scroll_y: int
    timestamp: float
    source: str = "unknown"  # mouse, touch, keyboard, programmatic


class Viewport:
    """Viewport for scrollable content areas.
    
    Manages a scrollable viewport that can display a portion of larger content,
    with support for smooth scrolling, content virtualization, and scroll events.
    """
    
    def __init__(self, config: ViewportConfig):
        """Initialize viewport with configuration.
        
        Args:
            config: Viewport configuration
        """
        self.config = config
        self._scroll_x = float(config.scroll_x)
        self._scroll_y = float(config.scroll_y)
        self._target_scroll_x = float(config.scroll_x)
        self._target_scroll_y = float(config.scroll_y)
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._last_update_time = time.time()
        
        # Event handling
        self._scroll_listeners: List[Callable[[ScrollEvent], None]] = []
        self._lock = threading.RLock()
        
        # Virtualization
        self._visible_items: Dict[str, Any] = {}
        self._item_cache: Dict[str, Any] = {}
        
        # Scrollbar state
        self._scrollbar_hover = False
        self._scrollbar_drag = False
    
    @property
    def scroll_x(self) -> int:
        """Get current horizontal scroll position."""
        return int(self._scroll_x)
    
    @property
    def scroll_y(self) -> int:
        """Get current vertical scroll position."""
        return int(self._scroll_y)
    
    @property
    def visible_bounds(self) -> WidgetBounds:
        """Get the currently visible bounds in content coordinates."""
        return WidgetBounds(
            self.scroll_x,
            self.scroll_y,
            self.config.width,
            self.config.height
        )
    
    @property
    def content_bounds(self) -> WidgetBounds:
        """Get the total content bounds."""
        return WidgetBounds(0, 0, self.config.content_width, self.config.content_height)
    
    @property
    def can_scroll_horizontal(self) -> bool:
        """Check if horizontal scrolling is possible."""
        return (self.config.enable_horizontal_scroll and 
                self.config.content_width > self.config.width)
    
    @property
    def can_scroll_vertical(self) -> bool:
        """Check if vertical scrolling is possible."""
        return (self.config.enable_vertical_scroll and 
                self.config.content_height > self.config.height)
    
    @property
    def scroll_progress_x(self) -> float:
        """Get horizontal scroll progress (0.0 to 1.0)."""
        if not self.can_scroll_horizontal:
            return 0.0
        max_scroll = self.config.content_width - self.config.width
        return self.scroll_x / max_scroll if max_scroll > 0 else 0.0
    
    @property
    def scroll_progress_y(self) -> float:
        """Get vertical scroll progress (0.0 to 1.0)."""
        if not self.can_scroll_vertical:
            return 0.0
        max_scroll = self.config.content_height - self.config.height
        return self.scroll_y / max_scroll if max_scroll > 0 else 0.0
    
    def scroll_to(self, x: Optional[int] = None, y: Optional[int] = None, 
                  behavior: ScrollBehavior = ScrollBehavior.AUTO) -> None:
        """Scroll to specific coordinates.
        
        Args:
            x: Target horizontal scroll position (None to keep current)
            y: Target vertical scroll position (None to keep current)
            behavior: Scroll behavior (smooth, instant, auto)
        """
        with self._lock:
            # Store old positions for delta calculation
            old_scroll_x = self.scroll_x
            old_scroll_y = self.scroll_y
            
            # Use current position if not specified
            target_x = x if x is not None else self.scroll_x
            target_y = y if y is not None else self.scroll_y
            
            # Clamp scroll values to valid range
            target_x = self._clamp_scroll_x(target_x)
            target_y = self._clamp_scroll_y(target_y)
            
            # Determine if we should use smooth scrolling
            use_smooth = (behavior == ScrollBehavior.SMOOTH or 
                         (behavior == ScrollBehavior.AUTO and self.config.smooth_scrolling))
            
            if use_smooth:
                self._target_scroll_x = float(target_x)
                self._target_scroll_y = float(target_y)
            else:
                self._scroll_x = float(target_x)
                self._scroll_y = float(target_y)
                self._target_scroll_x = float(target_x)
                self._target_scroll_y = float(target_y)
                self._velocity_x = 0.0
                self._velocity_y = 0.0
            
            # Calculate actual deltas
            delta_x = self.scroll_x - old_scroll_x
            delta_y = self.scroll_y - old_scroll_y
            
            # Emit scroll event with actual deltas
            if delta_x != 0 or delta_y != 0:
                self._emit_scroll_event(delta_x, delta_y, "programmatic")
    
    def scroll_by(self, delta_x: int = 0, delta_y: int = 0,
                  behavior: ScrollBehavior = ScrollBehavior.AUTO) -> None:
        """Scroll by relative amount.
        
        Args:
            delta_x: Horizontal scroll delta
            delta_y: Vertical scroll delta
            behavior: Scroll behavior
        """
        target_x = self.scroll_x + delta_x if delta_x != 0 else None
        target_y = self.scroll_y + delta_y if delta_y != 0 else None
        self.scroll_to(target_x, target_y, behavior)
    
    def scroll_into_view(self, bounds: WidgetBounds, 
                        behavior: ScrollBehavior = ScrollBehavior.AUTO) -> None:
        """Scroll to make the specified bounds visible.
        
        Args:
            bounds: Bounds to make visible
            behavior: Scroll behavior
        """
        visible = self.visible_bounds
        
        # Calculate required scroll adjustments
        scroll_x = None
        scroll_y = None
        
        # Horizontal scrolling
        if bounds.x < visible.x:
            # Scroll left to show left edge
            scroll_x = bounds.x
        elif bounds.right > visible.right:
            # Scroll right to show right edge
            scroll_x = bounds.right - self.config.width
        
        # Vertical scrolling
        if bounds.y < visible.y:
            # Scroll up to show top edge
            scroll_y = bounds.y
        elif bounds.bottom > visible.bottom:
            # Scroll down to show bottom edge
            scroll_y = bounds.bottom - self.config.height
        
        if scroll_x is not None or scroll_y is not None:
            self.scroll_to(scroll_x, scroll_y, behavior)
    
    def update_smooth_scroll(self, delta_time: float) -> bool:
        """Update smooth scrolling animation.
        
        Args:
            delta_time: Time elapsed since last update
            
        Returns:
            True if scrolling animation is still active
        """
        if not self.config.smooth_scrolling:
            return False
        
        with self._lock:
            changed = False
            
            # Update horizontal scroll
            if abs(self._target_scroll_x - self._scroll_x) > 0.5:
                # Calculate velocity towards target
                distance_x = self._target_scroll_x - self._scroll_x
                target_velocity_x = distance_x * self.config.scroll_acceleration
                
                # Apply velocity with deceleration
                self._velocity_x += (target_velocity_x - self._velocity_x) * delta_time * 5.0
                
                # Update position
                old_scroll_x = self._scroll_x
                self._scroll_x += self._velocity_x * delta_time
                self._scroll_x = self._clamp_scroll_x(self._scroll_x)
                
                if abs(self._scroll_x - old_scroll_x) > 0.1:
                    changed = True
            else:
                self._scroll_x = self._target_scroll_x
                self._velocity_x = 0.0
            
            # Update vertical scroll
            if abs(self._target_scroll_y - self._scroll_y) > 0.5:
                # Calculate velocity towards target
                distance_y = self._target_scroll_y - self._scroll_y
                target_velocity_y = distance_y * self.config.scroll_acceleration
                
                # Apply velocity with deceleration
                self._velocity_y += (target_velocity_y - self._velocity_y) * delta_time * 5.0
                
                # Update position
                old_scroll_y = self._scroll_y
                self._scroll_y += self._velocity_y * delta_time
                self._scroll_y = self._clamp_scroll_y(self._scroll_y)
                
                if abs(self._scroll_y - old_scroll_y) > 0.1:
                    changed = True
            else:
                self._scroll_y = self._target_scroll_y
                self._velocity_y = 0.0
            
            self._last_update_time = time.time()
            return changed
    
    def handle_wheel_scroll(self, delta_x: int, delta_y: int) -> None:
        """Handle mouse wheel scroll input.
        
        Args:
            delta_x: Horizontal scroll delta
            delta_y: Vertical scroll delta
        """
        # Apply scroll speed multiplier
        scaled_delta_x = int(delta_x * self.config.scroll_speed / 100.0)
        scaled_delta_y = int(delta_y * self.config.scroll_speed / 100.0)
        
        self.scroll_by(scaled_delta_x, scaled_delta_y)
        self._emit_scroll_event(scaled_delta_x, scaled_delta_y, "mouse")
    
    def handle_touch_scroll(self, delta_x: int, delta_y: int, velocity_x: float = 0.0, velocity_y: float = 0.0) -> None:
        """Handle touch scroll input with momentum.
        
        Args:
            delta_x: Horizontal scroll delta
            delta_y: Vertical scroll delta
            velocity_x: Horizontal velocity for momentum
            velocity_y: Vertical velocity for momentum
        """
        self.scroll_by(delta_x, delta_y)
        
        # Apply momentum if provided
        if abs(velocity_x) > 10 or abs(velocity_y) > 10:
            momentum_x = int(velocity_x * 0.5)  # Scale down momentum
            momentum_y = int(velocity_y * 0.5)
            
            # Add momentum to target scroll
            self._target_scroll_x += momentum_x
            self._target_scroll_y += momentum_y
            
            # Clamp targets
            self._target_scroll_x = self._clamp_scroll_x(self._target_scroll_x)
            self._target_scroll_y = self._clamp_scroll_y(self._target_scroll_y)
        
        self._emit_scroll_event(delta_x, delta_y, "touch")
    
    def is_point_in_content(self, x: int, y: int) -> bool:
        """Check if a point is within the content area.
        
        Args:
            x, y: Point coordinates in viewport space
            
        Returns:
            True if point is within content
        """
        content_x = x + self.scroll_x
        content_y = y + self.scroll_y
        return self.content_bounds.contains_point(content_x, content_y)
    
    def viewport_to_content_coords(self, x: int, y: int) -> Tuple[int, int]:
        """Convert viewport coordinates to content coordinates.
        
        Args:
            x, y: Coordinates in viewport space
            
        Returns:
            Coordinates in content space
        """
        return (x + self.scroll_x, y + self.scroll_y)
    
    def content_to_viewport_coords(self, x: int, y: int) -> Tuple[int, int]:
        """Convert content coordinates to viewport coordinates.
        
        Args:
            x, y: Coordinates in content space
            
        Returns:
            Coordinates in viewport space
        """
        return (x - self.scroll_x, y - self.scroll_y)
    
    def get_visible_content_bounds(self) -> WidgetBounds:
        """Get the bounds of content visible in the viewport.
        
        Returns:
            Bounds of visible content in content coordinates
        """
        return self.visible_bounds.intersect(self.content_bounds)
    
    def add_scroll_listener(self, listener: Callable[[ScrollEvent], None]) -> None:
        """Add a scroll event listener.
        
        Args:
            listener: Function to call on scroll events
        """
        self._scroll_listeners.append(listener)
    
    def remove_scroll_listener(self, listener: Callable[[ScrollEvent], None]) -> None:
        """Remove a scroll event listener.
        
        Args:
            listener: Function to remove
        """
        if listener in self._scroll_listeners:
            self._scroll_listeners.remove(listener)
    
    def update_content_size(self, width: int, height: int) -> None:
        """Update the content size.
        
        Args:
            width: New content width
            height: New content height
        """
        self.config.content_width = width
        self.config.content_height = height
        
        # Clamp current scroll position to new bounds
        self._scroll_x = self._clamp_scroll_x(self._scroll_x)
        self._scroll_y = self._clamp_scroll_y(self._scroll_y)
        self._target_scroll_x = self._clamp_scroll_x(self._target_scroll_x)
        self._target_scroll_y = self._clamp_scroll_y(self._target_scroll_y)
    
    def get_scrollbar_bounds(self, direction: ScrollDirection) -> Optional[WidgetBounds]:
        """Get scrollbar bounds for the specified direction.
        
        Args:
            direction: Scroll direction
            
        Returns:
            Scrollbar bounds or None if not visible
        """
        if self.config.scrollbar_visibility == ScrollBarVisibility.NEVER:
            return None
        
        if direction == ScrollDirection.HORIZONTAL and self.can_scroll_horizontal:
            # Horizontal scrollbar at bottom
            scrollbar_height = self.config.scrollbar_width
            scrollbar_y = self.config.height - scrollbar_height
            
            # Calculate thumb position and size
            progress = self.scroll_progress_x
            thumb_width = max(20, int(self.config.width * (self.config.width / self.config.content_width)))
            thumb_x = int((self.config.width - thumb_width) * progress)
            
            return WidgetBounds(thumb_x, scrollbar_y, thumb_width, scrollbar_height)
        
        elif direction == ScrollDirection.VERTICAL and self.can_scroll_vertical:
            # Vertical scrollbar at right
            scrollbar_width = self.config.scrollbar_width
            scrollbar_x = self.config.width - scrollbar_width
            
            # Calculate thumb position and size
            progress = self.scroll_progress_y
            thumb_height = max(20, int(self.config.height * (self.config.height / self.config.content_height)))
            thumb_y = int((self.config.height - thumb_height) * progress)
            
            return WidgetBounds(scrollbar_x, thumb_y, scrollbar_width, thumb_height)
        
        return None
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about viewport state.
        
        Returns:
            Dictionary with debug information
        """
        return {
            'scroll_position': (self.scroll_x, self.scroll_y),
            'target_position': (int(self._target_scroll_x), int(self._target_scroll_y)),
            'velocity': (self._velocity_x, self._velocity_y),
            'visible_bounds': self.visible_bounds,
            'content_bounds': self.content_bounds,
            'can_scroll': (self.can_scroll_horizontal, self.can_scroll_vertical),
            'scroll_progress': (self.scroll_progress_x, self.scroll_progress_y),
            'listeners': len(self._scroll_listeners)
        }
    
    def _clamp_scroll_x(self, scroll_x: float) -> float:
        """Clamp horizontal scroll to valid range."""
        if not self.can_scroll_horizontal:
            return 0.0
        
        max_scroll = self.config.content_width - self.config.width
        min_scroll = 0.0
        
        if self.config.bounce_enabled:
            # Allow some bounce beyond bounds
            min_bounce = -self.config.bounce_distance
            max_bounce = max_scroll + self.config.bounce_distance
            return max(min_bounce, min(scroll_x, max_bounce))
        else:
            return max(min_scroll, min(scroll_x, max_scroll))
    
    def _clamp_scroll_y(self, scroll_y: float) -> float:
        """Clamp vertical scroll to valid range."""
        if not self.can_scroll_vertical:
            return 0.0
        
        max_scroll = self.config.content_height - self.config.height
        min_scroll = 0.0
        
        if self.config.bounce_enabled:
            # Allow some bounce beyond bounds
            min_bounce = -self.config.bounce_distance
            max_bounce = max_scroll + self.config.bounce_distance
            return max(min_bounce, min(scroll_y, max_bounce))
        else:
            return max(min_scroll, min(scroll_y, max_scroll))
    
    def _emit_scroll_event(self, delta_x: int, delta_y: int, source: str) -> None:
        """Emit a scroll event to all listeners.
        
        Args:
            delta_x: Horizontal scroll delta
            delta_y: Vertical scroll delta
            source: Event source
        """
        event = ScrollEvent(
            delta_x=delta_x,
            delta_y=delta_y,
            scroll_x=self.scroll_x,
            scroll_y=self.scroll_y,
            timestamp=time.time(),
            source=source
        )
        
        for listener in self._scroll_listeners.copy():
            try:
                listener(event)
            except Exception as e:
                print(f"Error in scroll listener: {e}")


class ContentVirtualizer:
    """Content virtualization for large scrollable areas.
    
    Manages rendering only the visible portion of large content areas
    to maintain performance with thousands of items.
    """
    
    def __init__(self, viewport: Viewport, item_height: int = 30):
        """Initialize content virtualizer.
        
        Args:
            viewport: Associated viewport
            item_height: Height of each item (for uniform items)
        """
        self.viewport = viewport
        self.item_height = item_height
        self._items: List[Any] = []
        self._visible_items: Dict[int, Any] = {}
        self._item_cache: Dict[int, Any] = {}
        self._cache_size = 100
    
    def set_items(self, items: List[Any]) -> None:
        """Set the list of items to virtualize.
        
        Args:
            items: List of items
        """
        self._items = items
        
        # Update content height based on item count
        content_height = len(items) * self.item_height
        self.viewport.update_content_size(self.viewport.config.content_width, content_height)
        
        # Clear caches
        self._visible_items.clear()
        self._item_cache.clear()
    
    def get_visible_items(self) -> Dict[int, Tuple[int, Any]]:
        """Get currently visible items with their positions.
        
        Returns:
            Dictionary mapping item index to (y_position, item_data)
        """
        visible_bounds = self.viewport.get_visible_content_bounds()
        
        # Calculate visible item range
        start_index = max(0, visible_bounds.y // self.item_height)
        end_index = min(len(self._items), (visible_bounds.bottom + self.item_height - 1) // self.item_height)
        
        visible_items = {}
        for i in range(start_index, end_index):
            if i < len(self._items):
                y_position = i * self.item_height
                visible_items[i] = (y_position, self._items[i])
        
        self._visible_items = visible_items
        return visible_items
    
    def get_item_bounds(self, index: int) -> WidgetBounds:
        """Get bounds for a specific item.
        
        Args:
            index: Item index
            
        Returns:
            Item bounds in content coordinates
        """
        y = index * self.item_height
        return WidgetBounds(0, y, self.viewport.config.content_width, self.item_height)
    
    def scroll_to_item(self, index: int, behavior: ScrollBehavior = ScrollBehavior.AUTO) -> None:
        """Scroll to make a specific item visible.
        
        Args:
            index: Item index to scroll to
            behavior: Scroll behavior
        """
        if 0 <= index < len(self._items):
            item_bounds = self.get_item_bounds(index)
            self.viewport.scroll_into_view(item_bounds, behavior)


# Utility functions for viewport management
def create_viewport(width: int, height: int, content_width: int, content_height: int,
                   smooth_scrolling: bool = True) -> Viewport:
    """Create a viewport with basic configuration.
    
    Args:
        width, height: Viewport dimensions
        content_width, content_height: Content dimensions
        smooth_scrolling: Whether to enable smooth scrolling
        
    Returns:
        Viewport instance
    """
    config = ViewportConfig(
        width=width,
        height=height,
        content_width=content_width,
        content_height=content_height,
        smooth_scrolling=smooth_scrolling,
        bounce_enabled=False  # Disable bounce for predictable behavior
    )
    return Viewport(config)


def create_virtualizing_viewport(width: int, height: int, items: List[Any],
                               item_height: int = 30) -> Tuple[Viewport, ContentVirtualizer]:
    """Create a viewport with content virtualization.
    
    Args:
        width, height: Viewport dimensions
        items: List of items to virtualize
        item_height: Height of each item
        
    Returns:
        Tuple of (Viewport, ContentVirtualizer)
    """
    content_height = len(items) * item_height
    viewport = create_viewport(width, height, width, content_height)
    virtualizer = ContentVirtualizer(viewport, item_height)
    virtualizer.set_items(items)
    
    return viewport, virtualizer 