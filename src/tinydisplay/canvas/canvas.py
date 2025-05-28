#!/usr/bin/env python3
"""
Canvas Base Class

Provides the foundation for all canvas implementations in tinyDisplay.
Handles widget composition, positioning, z-order management, and rendering coordination.
"""

from typing import Dict, List, Optional, Tuple, Set, Any, Callable
from dataclasses import dataclass
import threading
import time
from enum import Enum

from ..widgets.base import Widget, ContainerWidget, WidgetBounds, WidgetState


class CanvasState(Enum):
    """Canvas lifecycle states."""
    CREATED = "created"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    PAUSED = "paused"
    DESTROYED = "destroyed"


@dataclass
class CanvasConfig:
    """Canvas configuration parameters."""
    width: int
    height: int
    background_color: Tuple[int, int, int] = (0, 0, 0)  # RGB
    frame_rate: float = 60.0
    double_buffered: bool = True
    auto_clear: bool = True
    clip_widgets: bool = True


class ZOrderManager:
    """Manages z-order (layering) of widgets on canvas."""
    
    def __init__(self):
        self._widgets: Dict[int, Set[str]] = {}  # z_order -> set of widget_ids
        self._widget_z_orders: Dict[str, int] = {}  # widget_id -> z_order
        self._lock = threading.RLock()
    
    def add_widget(self, widget_id: str, z_order: int) -> None:
        """Add a widget with specified z-order."""
        with self._lock:
            # Remove from old z-order if exists
            self.remove_widget(widget_id)
            
            # Add to new z-order
            if z_order not in self._widgets:
                self._widgets[z_order] = set()
            self._widgets[z_order].add(widget_id)
            self._widget_z_orders[widget_id] = z_order
    
    def remove_widget(self, widget_id: str) -> None:
        """Remove a widget from z-order management."""
        with self._lock:
            if widget_id in self._widget_z_orders:
                old_z_order = self._widget_z_orders.pop(widget_id)
                if old_z_order in self._widgets:
                    self._widgets[old_z_order].discard(widget_id)
                    # Clean up empty z-order levels
                    if not self._widgets[old_z_order]:
                        del self._widgets[old_z_order]
    
    def update_widget_z_order(self, widget_id: str, new_z_order: int) -> None:
        """Update a widget's z-order."""
        self.add_widget(widget_id, new_z_order)
    
    def get_widget_z_order(self, widget_id: str) -> Optional[int]:
        """Get a widget's current z-order."""
        return self._widget_z_orders.get(widget_id)
    
    def get_ordered_widget_ids(self) -> List[str]:
        """Get all widget IDs ordered by z-order (back to front)."""
        with self._lock:
            ordered_ids = []
            for z_order in sorted(self._widgets.keys()):
                # Sort widget IDs within same z-order for consistency
                ordered_ids.extend(sorted(self._widgets[z_order]))
            return ordered_ids
    
    def get_widgets_at_z_order(self, z_order: int) -> Set[str]:
        """Get all widget IDs at a specific z-order."""
        return self._widgets.get(z_order, set()).copy()


class Canvas(ContainerWidget):
    """Base canvas class for widget composition and rendering.
    
    Provides:
    - Widget composition and positioning
    - Z-order management for layering
    - Rendering coordination
    - Clipping and bounds management
    - Frame timing and synchronization
    """
    
    def __init__(self, config: CanvasConfig, canvas_id: Optional[str] = None):
        super().__init__(canvas_id or "canvas")
        
        # Configuration
        self._config = config
        self._state = CanvasState.CREATED
        
        # Override size from config
        self.size = (config.width, config.height)
        
        # Z-order management
        self._z_order_manager = ZOrderManager()
        
        # Rendering state
        self._dirty_regions: Set[WidgetBounds] = set()
        self._last_render_time = 0.0
        self._frame_count = 0
        self._target_frame_time = 1.0 / config.frame_rate
        
        # Widget tracking
        self._widget_positions: Dict[str, Tuple[int, int]] = {}
        self._widget_bounds_cache: Dict[str, WidgetBounds] = {}
        
        # Event handling
        self._event_handlers: Dict[str, Set[Callable]] = {
            'widget_added': set(),
            'widget_removed': set(),
            'widget_moved': set(),
            'render_complete': set()
        }
        
        # Thread safety
        self._render_lock = threading.RLock()
    
    # Properties
    @property
    def config(self) -> CanvasConfig:
        """Get canvas configuration."""
        return self._config
    
    @property
    def state(self) -> CanvasState:
        """Get canvas state."""
        return self._state
    
    @property
    def width(self) -> int:
        """Get canvas width."""
        return self._config.width
    
    @property
    def height(self) -> int:
        """Get canvas height."""
        return self._config.height
    
    @property
    def bounds(self) -> WidgetBounds:
        """Get canvas bounds."""
        return WidgetBounds(0, 0, self.width, self.height)
    
    @property
    def frame_rate(self) -> float:
        """Get target frame rate."""
        return self._config.frame_rate
    
    @property
    def frame_count(self) -> int:
        """Get current frame count."""
        return self._frame_count
    
    # Lifecycle methods
    def initialize(self) -> None:
        """Initialize the canvas."""
        if self._state == CanvasState.CREATED:
            super().initialize()
            self._state = CanvasState.INITIALIZED
            self._call_event_handlers('canvas_initialized')
    
    def activate(self) -> None:
        """Activate the canvas for rendering."""
        if self._state in (CanvasState.INITIALIZED, CanvasState.PAUSED):
            super().activate()
            self._state = CanvasState.ACTIVE
            self._call_event_handlers('canvas_activated')
    
    def pause(self) -> None:
        """Pause canvas rendering."""
        if self._state == CanvasState.ACTIVE:
            self._state = CanvasState.PAUSED
            self._call_event_handlers('canvas_paused')
    
    def destroy(self) -> None:
        """Destroy canvas and all widgets."""
        if self._state != CanvasState.DESTROYED:
            self._state = CanvasState.DESTROYED
            super().destroy()
            self._z_order_manager = ZOrderManager()  # Reset
            self._call_event_handlers('canvas_destroyed')
    
    # Widget management
    def add_widget(self, widget: Widget, position: Optional[Tuple[int, int]] = None, 
                   z_order: Optional[int] = None) -> None:
        """Add a widget to the canvas.
        
        Args:
            widget: Widget to add
            position: Optional position override
            z_order: Optional z-order override
        """
        with self._render_lock:
            # Add to container
            super().add_child(widget)
            
            # Set position if provided
            if position is not None:
                widget.position = position
            
            # Set z-order if provided
            if z_order is not None:
                widget.z_order = z_order
            
            # Register with z-order manager
            self._z_order_manager.add_widget(widget.widget_id, widget.z_order)
            
            # Track position
            self._widget_positions[widget.widget_id] = widget.position
            self._update_widget_bounds_cache(widget)
            
            # Initialize widget if canvas is active
            if self._state in (CanvasState.ACTIVE, CanvasState.INITIALIZED):
                if widget.state == WidgetState.CREATED:
                    widget.initialize()
                if self._state == CanvasState.ACTIVE:
                    widget.activate()
            
            # Mark dirty region
            self._add_dirty_region(widget.bounds)
            
            # Bind to widget changes
            widget.add_lifecycle_hook('update', self._on_widget_updated)
            
            self._call_event_handlers('widget_added', widget)
    
    def remove_widget(self, widget_id: str) -> Optional[Widget]:
        """Remove a widget from the canvas."""
        with self._render_lock:
            widget = super().remove_child(widget_id)
            if widget:
                # Remove from z-order manager
                self._z_order_manager.remove_widget(widget_id)
                
                # Clean up tracking
                self._widget_positions.pop(widget_id, None)
                old_bounds = self._widget_bounds_cache.pop(widget_id, None)
                
                # Mark dirty region
                if old_bounds:
                    self._add_dirty_region(old_bounds)
                
                # Unbind from widget changes
                widget.remove_lifecycle_hook('update', self._on_widget_updated)
                
                self._call_event_handlers('widget_removed', widget)
            
            return widget
    
    def move_widget(self, widget_id: str, new_position: Tuple[int, int]) -> bool:
        """Move a widget to a new position.
        
        Args:
            widget_id: ID of widget to move
            new_position: New (x, y) position
            
        Returns:
            True if widget was moved, False if widget not found
        """
        widget = self.get_child(widget_id)
        if widget:
            with self._render_lock:
                # Mark old position dirty
                old_bounds = self._widget_bounds_cache.get(widget_id)
                if old_bounds:
                    self._add_dirty_region(old_bounds)
                
                # Update position
                widget.position = new_position
                self._widget_positions[widget_id] = new_position
                self._update_widget_bounds_cache(widget)
                
                # Mark new position dirty
                self._add_dirty_region(widget.bounds)
                
                self._call_event_handlers('widget_moved', widget, new_position)
            return True
        return False
    
    def set_widget_z_order(self, widget_id: str, z_order: int) -> bool:
        """Set a widget's z-order.
        
        Args:
            widget_id: ID of widget
            z_order: New z-order value
            
        Returns:
            True if z-order was set, False if widget not found
        """
        widget = self.get_child(widget_id)
        if widget:
            with self._render_lock:
                old_z_order = widget.z_order
                widget.z_order = z_order
                self._z_order_manager.update_widget_z_order(widget_id, z_order)
                
                # Mark widget dirty if z-order changed
                if old_z_order != z_order:
                    self._add_dirty_region(widget.bounds)
                
            return True
        return False
    
    # Rendering methods
    def render(self, target_canvas: Optional['Canvas'] = None) -> None:
        """Render the canvas and all widgets.
        
        Args:
            target_canvas: Optional target canvas for nested rendering
        """
        if self._state != CanvasState.ACTIVE:
            return
        
        with self._render_lock:
            start_time = time.time()
            
            # Clear canvas if configured
            if self._config.auto_clear:
                self._clear_canvas()
            
            # Get widgets in z-order
            ordered_widget_ids = self._z_order_manager.get_ordered_widget_ids()
            
            # Render each widget
            rendered_count = 0
            for widget_id in ordered_widget_ids:
                widget = self.get_child(widget_id)
                if widget and widget.needs_render():
                    if self._should_render_widget(widget):
                        self._render_widget(widget)
                        widget.mark_clean()
                        rendered_count += 1
            
            # Clear dirty regions
            self._dirty_regions.clear()
            
            # Update frame timing
            self._frame_count += 1
            self._last_render_time = time.time()
            
            # Mark canvas clean
            self.mark_clean()
            
            self._call_event_handlers('render_complete', {
                'frame_count': self._frame_count,
                'widgets_rendered': rendered_count,
                'render_time': self._last_render_time - start_time
            })
    
    def needs_render(self) -> bool:
        """Check if canvas needs rendering."""
        if not super().needs_render():
            return False
        
        # Check if any widgets need rendering
        for widget in self.get_children():
            if widget.needs_render():
                return True
        
        # Check if there are dirty regions
        return len(self._dirty_regions) > 0
    
    # Utility methods
    def get_widgets_at_position(self, x: int, y: int) -> List[Widget]:
        """Get all widgets at a specific position, ordered by z-order (top to bottom)."""
        widgets = []
        ordered_widget_ids = reversed(self._z_order_manager.get_ordered_widget_ids())
        
        for widget_id in ordered_widget_ids:
            widget = self.get_child(widget_id)
            if widget and widget.visible and widget.contains_point(x, y):
                widgets.append(widget)
        
        return widgets
    
    def get_widget_at_position(self, x: int, y: int) -> Optional[Widget]:
        """Get the topmost widget at a specific position."""
        widgets = self.get_widgets_at_position(x, y)
        return widgets[0] if widgets else None
    
    def get_widgets_in_region(self, bounds: WidgetBounds) -> List[Widget]:
        """Get all widgets that intersect with a region."""
        widgets = []
        for widget in self.get_children():
            if widget.visible and widget.bounds.intersects(bounds):
                widgets.append(widget)
        return widgets
    
    def is_position_valid(self, x: int, y: int) -> bool:
        """Check if position is within canvas bounds."""
        return 0 <= x < self.width and 0 <= y < self.height
    
    def clip_bounds_to_canvas(self, bounds: WidgetBounds) -> WidgetBounds:
        """Clip widget bounds to canvas boundaries."""
        x = max(0, min(bounds.x, self.width))
        y = max(0, min(bounds.y, self.height))
        right = max(x, min(bounds.right, self.width))
        bottom = max(y, min(bounds.bottom, self.height))
        
        return WidgetBounds(x, y, right - x, bottom - y)
    
    # Event handling
    def add_event_handler(self, event: str, handler: Callable) -> None:
        """Add an event handler."""
        if event in self._event_handlers:
            self._event_handlers[event].add(handler)
    
    def remove_event_handler(self, event: str, handler: Callable) -> None:
        """Remove an event handler."""
        if event in self._event_handlers:
            self._event_handlers[event].discard(handler)
    
    # Internal methods
    def _clear_canvas(self) -> None:
        """Clear the canvas - to be implemented by subclasses."""
        pass
    
    def _render_widget(self, widget: Widget) -> None:
        """Render a single widget - to be implemented by subclasses."""
        # Default implementation calls widget's render method
        widget.render(self)
    
    def _should_render_widget(self, widget: Widget) -> bool:
        """Check if a widget should be rendered."""
        if not widget.visible or widget.alpha <= 0:
            return False
        
        # Check if widget is within canvas bounds (if clipping enabled)
        if self._config.clip_widgets:
            canvas_bounds = self.bounds
            if not widget.bounds.intersects(canvas_bounds):
                return False
        
        return True
    
    def _add_dirty_region(self, bounds: WidgetBounds) -> None:
        """Add a region that needs re-rendering."""
        if self._config.clip_widgets:
            bounds = self.clip_bounds_to_canvas(bounds)
        self._dirty_regions.add(bounds)
        self._mark_dirty()
    
    def _update_widget_bounds_cache(self, widget: Widget) -> None:
        """Update cached bounds for a widget."""
        self._widget_bounds_cache[widget.widget_id] = widget.bounds
    
    def _on_widget_updated(self, widget: Widget) -> None:
        """Handle widget update."""
        # Update position tracking if changed
        current_position = widget.position
        if widget.widget_id in self._widget_positions:
            old_position = self._widget_positions[widget.widget_id]
            if old_position != current_position:
                self._widget_positions[widget.widget_id] = current_position
                self._call_event_handlers('widget_moved', widget, current_position)
        
        # Update z-order if changed
        current_z_order = widget.z_order
        cached_z_order = self._z_order_manager.get_widget_z_order(widget.widget_id)
        if cached_z_order != current_z_order:
            self._z_order_manager.update_widget_z_order(widget.widget_id, current_z_order)
        
        # Update bounds cache and mark dirty
        old_bounds = self._widget_bounds_cache.get(widget.widget_id)
        new_bounds = widget.bounds
        
        if old_bounds:
            self._add_dirty_region(old_bounds)
        self._add_dirty_region(new_bounds)
        self._update_widget_bounds_cache(widget)
        
        super()._on_child_updated(widget)
    
    def _call_event_handlers(self, event: str, *args, **kwargs) -> None:
        """Call all registered event handlers for an event."""
        for handler in self._event_handlers.get(event, set()).copy():
            try:
                handler(*args, **kwargs)
            except Exception as e:
                print(f"Error in canvas event handler {event}: {e}")
    
    def __repr__(self) -> str:
        return (f"Canvas(id={self.widget_id}, size={self.width}x{self.height}, "
                f"widgets={len(self._children)}, state={self._state.value})") 