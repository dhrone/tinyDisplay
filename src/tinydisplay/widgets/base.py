#!/usr/bin/env python3
"""
Abstract Widget Base Classes

Provides the foundation for all widgets in the tinyDisplay framework.
Implements reactive data binding, positioning, lifecycle management, and
rendering abstractions.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional, Set, Callable, Union
from dataclasses import dataclass
import time
import threading
from enum import Enum

from ..core.ring_buffer import RingBuffer, BufferEntry

# Import lifecycle management components
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .lifecycle import LifecycleEvent, emit_lifecycle_event
else:
    try:
        from .lifecycle import LifecycleEvent, emit_lifecycle_event
    except ImportError:
        # Fallback for cases where lifecycle module isn't available yet
        LifecycleEvent = None
        emit_lifecycle_event = lambda *args, **kwargs: None


class WidgetState(Enum):
    """Widget lifecycle states."""
    CREATED = "created"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    HIDDEN = "hidden"
    DESTROYED = "destroyed"


class VisibilityState(Enum):
    """Widget visibility states."""
    VISIBLE = "visible"
    HIDDEN = "hidden"
    FADING_IN = "fading_in"
    FADING_OUT = "fading_out"
    COLLAPSED = "collapsed"  # Hidden and takes no space


@dataclass
class VisibilityAnimation:
    """Configuration for visibility animations."""
    duration: float = 0.3  # Animation duration in seconds
    easing: str = "ease_in_out"  # Easing function
    on_complete: Optional[Callable] = None  # Callback when animation completes
    
    
@dataclass
class TransparencyConfig:
    """Configuration for transparency behavior."""
    inherit_from_parent: bool = True
    min_alpha: float = 0.0
    max_alpha: float = 1.0
    blend_mode: str = "normal"  # Future: support different blend modes


@dataclass(frozen=True)
class WidgetBounds:
    """Widget boundary information."""
    x: int
    y: int
    width: int
    height: int
    
    @property
    def right(self) -> int:
        return self.x + self.width
    
    @property
    def bottom(self) -> int:
        return self.y + self.height
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if point is within widget bounds."""
        return (self.x <= x < self.right and 
                self.y <= y < self.bottom)
    
    def contains_bounds(self, other: 'WidgetBounds') -> bool:
        """Check if other bounds are completely within this bounds."""
        return (self.x <= other.x and 
                self.y <= other.y and
                self.right >= other.right and
                self.bottom >= other.bottom)
    
    def intersects(self, other: 'WidgetBounds') -> bool:
        """Check if this widget intersects with another."""
        return not (self.right <= other.x or 
                   other.right <= self.x or
                   self.bottom <= other.y or 
                   other.bottom <= self.y)
    
    def intersect(self, other: 'WidgetBounds') -> 'WidgetBounds':
        """Get the intersection of this bounds with another bounds."""
        left = max(self.x, other.x)
        top = max(self.y, other.y)
        right = min(self.right, other.right)
        bottom = min(self.bottom, other.bottom)
        
        # If no intersection, return empty bounds
        if left >= right or top >= bottom:
            return WidgetBounds(0, 0, 0, 0)
        
        return WidgetBounds(left, top, right - left, bottom - top)
    
    def union(self, other: 'WidgetBounds') -> 'WidgetBounds':
        """Get the union of this bounds with another bounds."""
        left = min(self.x, other.x)
        top = min(self.y, other.y)
        right = max(self.right, other.right)
        bottom = max(self.bottom, other.bottom)
        
        return WidgetBounds(left, top, right - left, bottom - top)


class ReactiveValue:
    """Reactive value with automatic dependency tracking and change notification."""
    
    def __init__(self, initial_value: Any = None):
        self._value = initial_value
        self._observers: Set[Callable] = set()
        self._dependencies: Set['ReactiveValue'] = set()
        self._lock = threading.RLock()
        self._last_update = time.time()
    
    @property
    def value(self) -> Any:
        """Get the current value."""
        return self._value
    
    @value.setter
    def value(self, new_value: Any) -> None:
        """Set a new value and notify observers."""
        with self._lock:
            if self._value != new_value:
                old_value = self._value
                self._value = new_value
                self._last_update = time.time()
                self._notify_observers(old_value, new_value)
    
    def bind(self, observer: Callable) -> None:
        """Bind an observer to value changes."""
        with self._lock:
            self._observers.add(observer)
    
    def unbind(self, observer: Callable) -> None:
        """Unbind an observer from value changes."""
        with self._lock:
            self._observers.discard(observer)
    
    def add_dependency(self, dependency: 'ReactiveValue') -> None:
        """Add a dependency that this value depends on."""
        with self._lock:
            self._dependencies.add(dependency)
            dependency.bind(self._on_dependency_changed)
    
    def remove_dependency(self, dependency: 'ReactiveValue') -> None:
        """Remove a dependency."""
        with self._lock:
            self._dependencies.discard(dependency)
            dependency.unbind(self._on_dependency_changed)
    
    def _notify_observers(self, old_value: Any, new_value: Any) -> None:
        """Notify all observers of value change."""
        for observer in self._observers.copy():  # Copy to avoid modification during iteration
            try:
                observer(old_value, new_value)
            except Exception as e:
                # Log error but don't break other observers
                print(f"Error in reactive observer: {e}")
    
    def _on_dependency_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle dependency change - subclasses can override for computed values."""
        pass


class Widget(ABC):
    """Abstract base class for all widgets.
    
    Provides reactive capabilities, positioning, lifecycle management,
    and rendering abstractions for all widget implementations.
    """
    
    def __init__(self, widget_id: Optional[str] = None):
        # Core identity
        self._widget_id = widget_id or f"widget_{id(self)}"
        self._state = WidgetState.CREATED
        
        # Position and size
        self._position = ReactiveValue((0, 0))
        self._size = ReactiveValue((100, 20))
        
        # Visibility and rendering
        self._visible = ReactiveValue(True)
        self._alpha = ReactiveValue(1.0)
        self._z_order = ReactiveValue(0)
        
        # Enhanced visibility and transparency
        self._visibility_state = VisibilityState.VISIBLE
        self._transparency_config = TransparencyConfig()
        self._effective_alpha = 1.0  # Computed alpha including parent inheritance
        self._parent_widget: Optional['Widget'] = None
        
        # Animation state
        self._current_animation: Optional[Dict[str, Any]] = None
        self._animation_start_time = 0.0
        self._animation_start_alpha = 0.0
        self._animation_target_alpha = 0.0
        
        # State management
        self._dirty = True
        self._last_render_time = 0.0
        self._render_cache: Optional[Any] = None
        
        # Reactive bindings
        self._reactive_bindings: Dict[str, ReactiveValue] = {}
        self._data_subscriptions: Set[str] = set()
        
        # Lifecycle hooks
        self._lifecycle_hooks: Dict[str, Set[Callable]] = {
            'initialize': set(),
            'update': set(),
            'render': set(),
            'cleanup': set(),
            'visibility_changed': set(),
            'alpha_changed': set()
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Bind internal reactive values to mark dirty
        self._position.bind(self._mark_dirty)
        self._size.bind(self._mark_dirty)
        self._visible.bind(self._on_visibility_changed)
        self._alpha.bind(self._on_alpha_changed)
        self._z_order.bind(self._mark_dirty)
    
    # Properties
    @property
    def widget_id(self) -> str:
        """Get widget unique identifier."""
        return self._widget_id
    
    @property
    def state(self) -> WidgetState:
        """Get current widget state."""
        return self._state
    
    @property
    def position(self) -> Tuple[int, int]:
        """Get widget position as (x, y) tuple."""
        return self._position.value
    
    @position.setter
    def position(self, value: Tuple[int, int]) -> None:
        """Set widget position."""
        self._position.value = value
    
    @property
    def size(self) -> Tuple[int, int]:
        """Get widget size as (width, height) tuple."""
        return self._size.value
    
    @size.setter
    def size(self, value: Tuple[int, int]) -> None:
        """Set widget size."""
        self._size.value = value
    
    @property
    def bounds(self) -> WidgetBounds:
        """Get widget bounds."""
        x, y = self.position
        width, height = self.size
        return WidgetBounds(x, y, width, height)
    
    @property
    def visible(self) -> bool:
        """Get widget visibility."""
        return self._visible.value
    
    @visible.setter
    def visible(self, value: bool) -> None:
        """Set widget visibility."""
        self._visible.value = value
    
    @property
    def alpha(self) -> float:
        """Get widget transparency (0.0 = transparent, 1.0 = opaque)."""
        return self._alpha.value
    
    @alpha.setter
    def alpha(self, value: float) -> None:
        """Set widget transparency."""
        self._alpha.value = max(0.0, min(1.0, value))
    
    @property
    def z_order(self) -> int:
        """Get widget z-order (higher values render on top)."""
        return self._z_order.value
    
    @z_order.setter
    def z_order(self, value: int) -> None:
        """Set widget z-order."""
        self._z_order.value = value
    
    @property
    def is_dirty(self) -> bool:
        """Check if widget needs re-rendering."""
        return self._dirty
    
    # Enhanced visibility and transparency properties
    @property
    def visibility_state(self) -> VisibilityState:
        """Get current visibility state."""
        return self._visibility_state
    
    @property
    def effective_alpha(self) -> float:
        """Get effective alpha including parent inheritance."""
        return self._effective_alpha
    
    @property
    def transparency_config(self) -> TransparencyConfig:
        """Get transparency configuration."""
        return self._transparency_config
    
    @transparency_config.setter
    def transparency_config(self, config: TransparencyConfig) -> None:
        """Set transparency configuration."""
        self._transparency_config = config
        self._update_effective_alpha()
    
    @property
    def is_animating(self) -> bool:
        """Check if widget is currently animating."""
        return self._current_animation is not None
    
    # Lifecycle methods
    def initialize(self) -> None:
        """Initialize the widget."""
        if self._state == WidgetState.CREATED:
            self._call_lifecycle_hooks('initialize')
            self._state = WidgetState.INITIALIZED
            self._mark_dirty()
    
    def activate(self) -> None:
        """Activate the widget for rendering."""
        if self._state in (WidgetState.INITIALIZED, WidgetState.HIDDEN):
            self._state = WidgetState.ACTIVE
            self._mark_dirty()
    
    def hide_widget(self) -> None:
        """Hide the widget (lifecycle state change)."""
        if self._state == WidgetState.ACTIVE:
            self._state = WidgetState.HIDDEN
            self._mark_dirty()
    
    def destroy(self) -> None:
        """Destroy the widget and clean up resources."""
        if self._state != WidgetState.DESTROYED:
            self._call_lifecycle_hooks('cleanup')
            self._cleanup_reactive_bindings()
            self._state = WidgetState.DESTROYED
    
    # Reactive data binding
    def bind_data(self, property_name: str, reactive_value: ReactiveValue) -> None:
        """Bind a reactive value to a widget property."""
        with self._lock:
            # Unbind existing binding if any
            if property_name in self._reactive_bindings:
                old_binding = self._reactive_bindings[property_name]
                old_binding.unbind(self._on_data_changed)
            
            # Bind new reactive value
            self._reactive_bindings[property_name] = reactive_value
            reactive_value.bind(self._on_data_changed)
            
            # Trigger immediate update
            self._on_data_changed(None, reactive_value.value)
    
    def unbind_data(self, property_name: str) -> None:
        """Unbind a reactive value from a widget property."""
        with self._lock:
            if property_name in self._reactive_bindings:
                binding = self._reactive_bindings.pop(property_name)
                binding.unbind(self._on_data_changed)
    
    def get_reactive_value(self, property_name: str) -> Optional[ReactiveValue]:
        """Get the reactive value bound to a property."""
        return self._reactive_bindings.get(property_name)
    
    # Lifecycle hooks
    def add_lifecycle_hook(self, event: str, callback: Callable) -> None:
        """Add a lifecycle hook callback."""
        if event in self._lifecycle_hooks:
            self._lifecycle_hooks[event].add(callback)
    
    def remove_lifecycle_hook(self, event: str, callback: Callable) -> None:
        """Remove a lifecycle hook callback."""
        if event in self._lifecycle_hooks:
            self._lifecycle_hooks[event].discard(callback)
    
    # Rendering methods
    @abstractmethod
    def render(self, canvas: 'Canvas') -> None:
        """Render the widget to the canvas.
        
        Args:
            canvas: The canvas to render to
        """
        pass
    
    def needs_render(self) -> bool:
        """Check if widget needs rendering."""
        return (self._dirty and 
                self._state == WidgetState.ACTIVE and 
                self.visible)
    
    def mark_clean(self) -> None:
        """Mark widget as clean (rendered)."""
        self._dirty = False
        self._last_render_time = time.time()
    
    # Utility methods
    def contains_point(self, x: int, y: int) -> bool:
        """Check if point is within widget bounds."""
        return self.bounds.contains_point(x, y)
    
    def intersects_widget(self, other: 'Widget') -> bool:
        """Check if this widget intersects with another."""
        return self.bounds.intersects(other.bounds)
    
    # Internal methods
    def _mark_dirty(self, old_value: Any = None, new_value: Any = None) -> None:
        """Mark widget as needing re-render."""
        self._dirty = True
        self._render_cache = None
        self._call_lifecycle_hooks('update')
    
    def _on_data_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle reactive data change."""
        self._mark_dirty(old_value, new_value)
    
    def _call_lifecycle_hooks(self, event: str) -> None:
        """Call all registered lifecycle hooks for an event."""
        for callback in self._lifecycle_hooks.get(event, set()).copy():
            try:
                callback(self)
            except Exception as e:
                print(f"Error in lifecycle hook {event}: {e}")
    
    def _cleanup_reactive_bindings(self) -> None:
        """Clean up all reactive bindings."""
        with self._lock:
            for binding in self._reactive_bindings.values():
                binding.unbind(self._on_data_changed)
            self._reactive_bindings.clear()
    
    # Enhanced visibility methods
    def show(self, animated: bool = False, animation_config: Optional[VisibilityAnimation] = None) -> None:
        """Show the widget.
        
        Args:
            animated: Whether to animate the visibility change
            animation_config: Animation configuration (uses default if None)
        """
        if self._visibility_state == VisibilityState.VISIBLE:
            return
        
        if animated:
            self._start_fade_in_animation(animation_config or VisibilityAnimation())
        else:
            self._visibility_state = VisibilityState.VISIBLE
            self.visible = True
            self._call_lifecycle_hooks('visibility_changed')
    
    def hide(self, animated: bool = False, animation_config: Optional[VisibilityAnimation] = None) -> None:
        """Hide the widget.
        
        Args:
            animated: Whether to animate the visibility change
            animation_config: Animation configuration (uses default if None)
        """
        if self._visibility_state == VisibilityState.HIDDEN:
            return
        
        if animated:
            self._start_fade_out_animation(animation_config or VisibilityAnimation())
        else:
            self._visibility_state = VisibilityState.HIDDEN
            self.visible = False
            self._call_lifecycle_hooks('visibility_changed')
    
    def collapse(self) -> None:
        """Collapse the widget (hidden and takes no space)."""
        self._visibility_state = VisibilityState.COLLAPSED
        self.visible = False
        self._call_lifecycle_hooks('visibility_changed')
    
    def toggle_visibility(self, animated: bool = False, 
                         animation_config: Optional[VisibilityAnimation] = None) -> None:
        """Toggle widget visibility.
        
        Args:
            animated: Whether to animate the visibility change
            animation_config: Animation configuration (uses default if None)
        """
        if self._visibility_state == VisibilityState.VISIBLE:
            self.hide(animated, animation_config)
        else:
            self.show(animated, animation_config)
    
    def set_alpha_animated(self, target_alpha: float, duration: float = 0.3,
                          on_complete: Optional[Callable] = None) -> None:
        """Animate alpha to target value.
        
        Args:
            target_alpha: Target alpha value (0.0 to 1.0)
            duration: Animation duration in seconds
            on_complete: Callback when animation completes
        """
        target_alpha = max(0.0, min(1.0, target_alpha))
        
        if abs(self.alpha - target_alpha) < 0.001:
            if on_complete:
                on_complete()
            return
        
        self._current_animation = {
            'type': 'alpha',
            'duration': duration,
            'on_complete': on_complete
        }
        self._animation_start_time = time.time()
        self._animation_start_alpha = self.alpha
        self._animation_target_alpha = target_alpha
    
    def set_parent_widget(self, parent: Optional['Widget']) -> None:
        """Set parent widget for alpha inheritance.
        
        Args:
            parent: Parent widget or None
        """
        self._parent_widget = parent
        self._update_effective_alpha()
    
    def update_animations(self, current_tick: Optional[int] = None) -> None:
        """Update any running animations.
        
        Args:
            current_tick: Current animation tick for tick-based animations.
                         If None, uses time-based animation (backward compatibility).
        """
        if not self._current_animation:
            return
        
        # Support both tick-based and time-based animations
        if current_tick is not None:
            # Tick-based animation (new system)
            self._update_tick_based_animation(current_tick)
        else:
            # Time-based animation (legacy system for backward compatibility)
            self._update_time_based_animation()
    
    def _update_tick_based_animation(self, current_tick: int) -> None:
        """Update tick-based animations.
        
        Args:
            current_tick: Current animation tick
        """
        if not self._current_animation:
            return
            
        # Convert duration from seconds to ticks (assuming 60 FPS)
        duration_ticks = int(self._current_animation['duration'] * 60)
        start_tick = self._current_animation.get('start_tick', 0)
        elapsed_ticks = current_tick - start_tick
        
        if elapsed_ticks >= duration_ticks:
            # Animation complete
            self._complete_animation()
        else:
            # Update animation progress using tick-based timing
            progress = elapsed_ticks / duration_ticks if duration_ticks > 0 else 1.0
            progress = self._apply_easing(progress, self._current_animation.get('easing', 'ease_in_out'))
            self._apply_animation_progress(progress)
    
    def _update_time_based_animation(self) -> None:
        """Update time-based animations (legacy system)."""
        if not self._current_animation:
            return
            
        current_time = time.time()
        elapsed = current_time - self._animation_start_time
        duration = self._current_animation['duration']
        
        if elapsed >= duration:
            # Animation complete
            self._complete_animation()
        else:
            # Update animation progress using time-based timing
            progress = elapsed / duration
            progress = self._apply_easing(progress, self._current_animation.get('easing', 'ease_in_out'))
            self._apply_animation_progress(progress)
    
    def _complete_animation(self) -> None:
        """Complete the current animation."""
        if self._current_animation['type'] == 'alpha':
            self.alpha = self._animation_target_alpha
        elif self._current_animation['type'] == 'fade_in':
            self.alpha = 1.0
            self._visibility_state = VisibilityState.VISIBLE
            self.visible = True
        elif self._current_animation['type'] == 'fade_out':
            self.alpha = 0.0
            self._visibility_state = VisibilityState.HIDDEN
            self.visible = False
        
        # Call completion callback
        if self._current_animation.get('on_complete'):
            self._current_animation['on_complete']()
        
        self._current_animation = None
        self._call_lifecycle_hooks('visibility_changed')
    
    def _apply_animation_progress(self, progress: float) -> None:
        """Apply animation progress to widget properties.
        
        Args:
            progress: Animation progress from 0.0 to 1.0
        """
        if self._current_animation['type'] == 'alpha':
            current_alpha = self._animation_start_alpha + (
                self._animation_target_alpha - self._animation_start_alpha
            ) * progress
            self.alpha = current_alpha
        elif self._current_animation['type'] == 'fade_in':
            self.alpha = progress
        elif self._current_animation['type'] == 'fade_out':
            self.alpha = 1.0 - progress
    
    def start_tick_based_animation(self, animation_type: str, start_tick: int, 
                                  duration_ticks: int, **kwargs) -> bool:
        """Start a tick-based animation.
        
        Args:
            animation_type: Type of animation ('alpha', 'fade_in', 'fade_out', etc.)
            start_tick: Starting tick for the animation
            duration_ticks: Duration in ticks
            **kwargs: Additional animation parameters
            
        Returns:
            True if animation started successfully, False otherwise
        """
        try:
            # Convert tick duration to seconds for compatibility
            duration_seconds = duration_ticks / 60.0  # Assuming 60 FPS
            
            if animation_type == 'alpha':
                self._animation_start_alpha = self.alpha
                self._animation_target_alpha = kwargs.get('target_alpha', 1.0)
            elif animation_type == 'fade_in':
                self._animation_start_alpha = 0.0
                self._animation_target_alpha = 1.0
                self._visibility_state = VisibilityState.FADING_IN
                self.visible = True
                self.alpha = 0.0
            elif animation_type == 'fade_out':
                self._animation_start_alpha = self.alpha
                self._animation_target_alpha = 0.0
                self._visibility_state = VisibilityState.FADING_OUT
            
            # Store all animation parameters in _current_animation
            self._current_animation = {
                'type': animation_type,
                'duration': duration_seconds,
                'start_tick': start_tick,
                'duration_ticks': duration_ticks,
                'easing': kwargs.get('easing', 'ease_in_out'),
                'on_complete': kwargs.get('on_complete'),
                **kwargs  # Include all additional parameters
            }
            self._animation_start_time = time.time()  # Keep for backward compatibility
            
            return True
            
        except Exception:
            # If animation setup fails, return False
            return False
    
    def _update_effective_alpha(self) -> None:
        """Update effective alpha based on own alpha and parent inheritance."""
        base_alpha = self.alpha
        
        # Apply transparency config constraints
        base_alpha = max(self._transparency_config.min_alpha, 
                        min(self._transparency_config.max_alpha, base_alpha))
        
        # Inherit from parent if configured
        if (self._transparency_config.inherit_from_parent and 
            self._parent_widget is not None):
            parent_alpha = self._parent_widget.effective_alpha
            self._effective_alpha = base_alpha * parent_alpha
        else:
            self._effective_alpha = base_alpha
        
        self._mark_dirty()
    
    def _start_fade_in_animation(self, animation_config: VisibilityAnimation) -> None:
        """Start fade in animation."""
        self._visibility_state = VisibilityState.FADING_IN
        self.visible = True  # Make visible immediately but with alpha 0
        self.alpha = 0.0
        
        self._current_animation = {
            'type': 'fade_in',
            'duration': animation_config.duration,
            'easing': animation_config.easing,
            'on_complete': animation_config.on_complete
        }
        self._animation_start_time = time.time()
        self._animation_start_alpha = 0.0
        self._animation_target_alpha = 1.0
    
    def _start_fade_out_animation(self, animation_config: VisibilityAnimation) -> None:
        """Start fade out animation."""
        self._visibility_state = VisibilityState.FADING_OUT
        
        self._current_animation = {
            'type': 'fade_out',
            'duration': animation_config.duration,
            'easing': animation_config.easing,
            'on_complete': animation_config.on_complete
        }
        self._animation_start_time = time.time()
        self._animation_start_alpha = self.alpha
        self._animation_target_alpha = 0.0
    
    def _apply_easing(self, progress: float, easing: str) -> float:
        """Apply easing function to animation progress."""
        if easing == "linear":
            return progress
        elif easing == "ease_in":
            return progress * progress
        elif easing == "ease_out":
            return 1 - (1 - progress) * (1 - progress)
        elif easing == "ease_in_out":
            if progress < 0.5:
                return 2 * progress * progress
            else:
                return 1 - 2 * (1 - progress) * (1 - progress)
        elif easing == "ease_in_cubic":
            return progress * progress * progress
        elif easing == "ease_out_cubic":
            return 1 - (1 - progress) ** 3
        elif easing == "ease_in_out_cubic":
            if progress < 0.5:
                return 4 * progress * progress * progress
            else:
                return 1 - 4 * (1 - progress) ** 3
        elif easing == "bounce":
            # Simple bounce effect
            if progress < 0.5:
                return 2 * progress * progress
            else:
                return 1 - 2 * (1 - progress) * (1 - progress)
        else:
            # Default to ease_in_out
            if progress < 0.5:
                return 2 * progress * progress
            else:
                return 1 - 2 * (1 - progress) * (1 - progress)
    
    def _on_visibility_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle visibility changes."""
        if new_value:
            self._visibility_state = VisibilityState.VISIBLE
        else:
            # Only set to HIDDEN if not already in a specific hidden state (like COLLAPSED)
            if self._visibility_state not in (VisibilityState.COLLAPSED, VisibilityState.FADING_OUT):
                self._visibility_state = VisibilityState.HIDDEN
        
        self._mark_dirty()
        self._call_lifecycle_hooks('visibility_changed')
    
    def _on_alpha_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle alpha changes."""
        # Clamp alpha to valid range
        clamped_alpha = max(self._transparency_config.min_alpha, 
                           min(self._transparency_config.max_alpha, new_value))
        if clamped_alpha != new_value:
            self._alpha.value = clamped_alpha
            return
        
        self._update_effective_alpha()
        self._mark_dirty()
        self._call_lifecycle_hooks('alpha_changed')
    
    # Widget pooling support methods
    def _reset_for_reuse(self, *args, **kwargs) -> None:
        """Reset widget state for reuse from pool.
        
        This method should be overridden by subclasses to reset their
        specific state when being reused from a widget pool.
        """
        # Reset core state
        self._state = WidgetState.CREATED
        self._dirty = True
        self._last_render_time = 0.0
        self._render_cache = None
        
        # Reset position and size to defaults
        self._position.value = (0, 0)
        self._size.value = (100, 20)
        
        # Reset visibility
        self._visible.value = True
        self._alpha.value = 1.0
        self._z_order.value = 0
        self._visibility_state = VisibilityState.VISIBLE
        self._effective_alpha = 1.0
        
        # Clear animations
        self._current_animation = None
        self._animation_start_time = 0.0
        
        # Clear parent reference
        self._parent_widget = None
        
        # Clear lifecycle hooks
        for hook_set in self._lifecycle_hooks.values():
            hook_set.clear()
        
        # Clear reactive bindings
        self._cleanup_reactive_bindings()
        self._data_subscriptions.clear()
    
    def _cleanup_for_pooling(self) -> None:
        """Clean up widget for return to pool.
        
        This method should be overridden by subclasses to clean up
        resources before returning to the widget pool.
        """
        # Clear render cache
        self._render_cache = None
        
        # Clear any external references
        self._parent_widget = None
        
        # Stop any ongoing animations
        self._current_animation = None
        
        # Clear lifecycle hooks to prevent memory leaks
        for hook_set in self._lifecycle_hooks.values():
            hook_set.clear()
        
        # Unbind all reactive data
        self._cleanup_reactive_bindings()
    
    @property
    def _last_modified(self) -> float:
        """Get timestamp of last modification for caching."""
        return max(
            self._position._last_update,
            self._size._last_update,
            self._visible._last_update,
            self._alpha._last_update,
            self._z_order._last_update
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.widget_id}, pos={self.position}, size={self.size})"


class ContainerWidget(Widget):
    """Base class for widgets that can contain other widgets."""
    
    def __init__(self, widget_id: Optional[str] = None):
        super().__init__(widget_id)
        self._children: Dict[str, Widget] = {}
        self._child_order: list[str] = []
    
    def add_child(self, child: Widget) -> None:
        """Add a child widget."""
        with self._lock:
            if child.widget_id not in self._children:
                self._children[child.widget_id] = child
                self._child_order.append(child.widget_id)
                child.add_lifecycle_hook('update', self._on_child_updated)
                
                # Set up parent-child relationship for alpha inheritance
                child.set_parent_widget(self)
                
                self._mark_dirty()
    
    def remove_child(self, child_id: str) -> Optional[Widget]:
        """Remove a child widget."""
        with self._lock:
            if child_id in self._children:
                child = self._children.pop(child_id)
                self._child_order.remove(child_id)
                child.remove_lifecycle_hook('update', self._on_child_updated)
                
                # Remove parent-child relationship
                child.set_parent_widget(None)
                
                self._mark_dirty()
                return child
            return None
    
    def get_child(self, child_id: str) -> Optional[Widget]:
        """Get a child widget by ID."""
        return self._children.get(child_id)
    
    def get_children(self) -> list[Widget]:
        """Get all child widgets in order."""
        return [self._children[child_id] for child_id in self._child_order 
                if child_id in self._children]
    
    def propagate_visibility_to_children(self, visible: bool) -> None:
        """Propagate visibility state to child widgets.
        
        Args:
            visible: Visibility state to propagate
        """
        for child in self.get_children():
            if visible:
                # Only show children that were previously visible
                if child._visibility_state != VisibilityState.HIDDEN:
                    child.show()
            else:
                child.hide()
    
    def show_all_children(self, animated: bool = False, 
                         animation_config: Optional[VisibilityAnimation] = None) -> None:
        """Show all child widgets.
        
        Args:
            animated: Whether to animate the visibility changes
            animation_config: Animation configuration (uses default if None)
        """
        for child in self.get_children():
            child.show(animated, animation_config)
    
    def hide_all_children(self, animated: bool = False,
                         animation_config: Optional[VisibilityAnimation] = None) -> None:
        """Hide all child widgets.
        
        Args:
            animated: Whether to animate the visibility changes
            animation_config: Animation configuration (uses default if None)
        """
        for child in self.get_children():
            child.hide(animated, animation_config)
    
    def update_all_animations(self, current_tick: Optional[int] = None) -> None:
        """Update animations for this widget and all children.
        
        Args:
            current_tick: Current animation tick for tick-based animations.
                         If None, uses time-based animation (backward compatibility).
        """
        self.update_animations(current_tick)
        for child in self.get_children():
            if hasattr(child, 'update_all_animations'):
                child.update_all_animations(current_tick)
            else:
                child.update_animations(current_tick)
    
    def _on_child_updated(self, child: Widget) -> None:
        """Handle child widget update."""
        self._mark_dirty()
    
    def _on_alpha_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle alpha changes and propagate to children."""
        # Call parent implementation first
        super()._on_alpha_changed(old_value, new_value)
        
        # Propagate to children that inherit from parent
        for child in self.get_children():
            if child._transparency_config.inherit_from_parent:
                child._update_effective_alpha()
    
    def destroy(self) -> None:
        """Destroy container and all children."""
        # Destroy all children first
        for child in self.get_children():
            child.destroy()
        self._children.clear()
        self._child_order.clear()
        super().destroy() 