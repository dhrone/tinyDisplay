#!/usr/bin/env python3
"""
Widget Lifecycle Integration

Provides enhanced lifecycle integration for the Widget base class,
including automatic lifecycle event emission and comprehensive
lifecycle management features.
"""

from typing import Dict, Any, Optional, Callable, Type, TypeVar, Tuple
import time
import threading
from functools import wraps

from .base import Widget, WidgetState, VisibilityState, ContainerWidget
from .lifecycle import (
    LifecycleEvent, LifecycleEventInfo, WidgetPool, WidgetPoolConfig,
    emit_lifecycle_event, get_lifecycle_manager, create_widget_pool
)

T = TypeVar('T', bound=Widget)


class LifecycleIntegratedWidget(Widget):
    """Enhanced Widget base class with full lifecycle integration.
    
    This class extends the base Widget class to provide automatic
    lifecycle event emission and enhanced lifecycle management.
    """
    
    def __init__(self, widget_id: Optional[str] = None):
        super().__init__(widget_id)
        
        # Emit creation event
        self._emit_lifecycle_event(LifecycleEvent.CREATED)
    
    def initialize(self) -> None:
        """Initialize the widget with lifecycle event emission."""
        if self._state == WidgetState.CREATED:
            old_state = self._state
            super().initialize()
            self._emit_lifecycle_event(LifecycleEvent.INITIALIZED, old_state, self._state)
    
    def activate(self) -> None:
        """Activate the widget with lifecycle event emission."""
        if self._state in (WidgetState.INITIALIZED, WidgetState.HIDDEN):
            old_state = self._state
            super().activate()
            self._emit_lifecycle_event(LifecycleEvent.ACTIVATED, old_state, self._state)
    
    def hide_widget(self) -> None:
        """Hide the widget with lifecycle event emission."""
        if self._state == WidgetState.ACTIVE:
            old_state = self._state
            super().hide_widget()
            self._emit_lifecycle_event(LifecycleEvent.HIDDEN, old_state, self._state)
    
    def destroy(self) -> None:
        """Destroy the widget with lifecycle event emission."""
        if self._state != WidgetState.DESTROYED:
            old_state = self._state
            super().destroy()
            self._emit_lifecycle_event(LifecycleEvent.DESTROYED, old_state, self._state)
    
    def render(self, canvas: 'Canvas') -> None:
        """Render the widget with lifecycle event emission."""
        # This is abstract in base class, but we can emit the event
        self._emit_lifecycle_event(LifecycleEvent.RENDERED)
    
    @property
    def position(self) -> Tuple[int, int]:
        """Get widget position."""
        return super().position
    
    @position.setter
    def position(self, value: Tuple[int, int]) -> None:
        """Set widget position with lifecycle event emission."""
        old_position = self.position
        super(LifecycleIntegratedWidget, self.__class__).position.fset(self, value)
        if old_position != value:
            self._emit_lifecycle_event(LifecycleEvent.POSITION_CHANGED, old_position, value)
    
    @property
    def size(self) -> Tuple[int, int]:
        """Get widget size."""
        return super().size
    
    @size.setter
    def size(self, value: Tuple[int, int]) -> None:
        """Set widget size with lifecycle event emission."""
        old_size = self.size
        super(LifecycleIntegratedWidget, self.__class__).size.fset(self, value)
        if old_size != value:
            self._emit_lifecycle_event(LifecycleEvent.SIZE_CHANGED, old_size, value)
    
    @property
    def visible(self) -> bool:
        """Get widget visibility."""
        return super().visible
    
    @visible.setter
    def visible(self, value: bool) -> None:
        """Set widget visibility with lifecycle event emission."""
        old_visible = self.visible
        super(LifecycleIntegratedWidget, self.__class__).visible.fset(self, value)
        if old_visible != value:
            self._emit_lifecycle_event(LifecycleEvent.VISIBILITY_CHANGED, old_visible, value)
    
    @property
    def alpha(self) -> float:
        """Get widget alpha."""
        return super().alpha
    
    @alpha.setter
    def alpha(self, value: float) -> None:
        """Set widget alpha with lifecycle event emission."""
        old_alpha = self.alpha
        super(LifecycleIntegratedWidget, self.__class__).alpha.fset(self, value)
        if abs(old_alpha - value) > 0.001:  # Avoid floating point precision issues
            self._emit_lifecycle_event(LifecycleEvent.ALPHA_CHANGED, old_alpha, value)
    
    def set_parent_widget(self, parent: Optional['Widget']) -> None:
        """Set parent widget with lifecycle event emission."""
        old_parent = getattr(self, '_parent_widget', None)
        super().set_parent_widget(parent)
        if old_parent != parent:
            self._emit_lifecycle_event(LifecycleEvent.PARENT_CHANGED, old_parent, parent)
    
    def _mark_dirty(self, old_value: Any = None, new_value: Any = None) -> None:
        """Mark widget as dirty with lifecycle event emission."""
        super()._mark_dirty(old_value, new_value)
        self._emit_lifecycle_event(LifecycleEvent.UPDATED, old_value, new_value)
    
    def _emit_lifecycle_event(self, event: LifecycleEvent, 
                             old_value: Any = None, new_value: Any = None,
                             metadata: Optional[Dict[str, Any]] = None) -> None:
        """Emit a lifecycle event for this widget."""
        try:
            emit_lifecycle_event(event, self, old_value, new_value, metadata)
        except Exception as e:
            print(f"Error emitting lifecycle event {event} for widget {self.widget_id}: {e}")


class LifecycleIntegratedContainerWidget(LifecycleIntegratedWidget, ContainerWidget):
    """Enhanced ContainerWidget with full lifecycle integration."""
    
    def __init__(self, widget_id: Optional[str] = None):
        super().__init__(widget_id)
    
    def add_child(self, child: Widget) -> None:
        """Add child widget with lifecycle event emission."""
        super().add_child(child)
        self._emit_lifecycle_event(LifecycleEvent.CHILD_ADDED, None, child)
        
        # Set up parent relationship with lifecycle events
        if hasattr(child, 'set_parent_widget'):
            child.set_parent_widget(self)
    
    def remove_child(self, child_id: str) -> Optional[Widget]:
        """Remove child widget with lifecycle event emission."""
        child = super().remove_child(child_id)
        if child:
            self._emit_lifecycle_event(LifecycleEvent.CHILD_REMOVED, child, None)
            
            # Clear parent relationship
            if hasattr(child, 'set_parent_widget'):
                child.set_parent_widget(None)
        
        return child
    
    def render(self, canvas: 'Canvas') -> None:
        """Render container and children with lifecycle events."""
        self._emit_lifecycle_event(LifecycleEvent.RENDERED)
        
        # Render all children in order
        for child in self.get_children():
            if child.needs_render():
                child.render(canvas)


class WidgetFactory:
    """Factory for creating widgets with lifecycle management."""
    
    def __init__(self):
        self._pools: Dict[Type[Widget], WidgetPool] = {}
        self._creation_stats: Dict[str, int] = {}
        self._lock = threading.RLock()
    
    def create_widget(self, widget_class: Type[T], 
                     widget_id: Optional[str] = None,
                     use_pool: bool = True,
                     pool_config: Optional[WidgetPoolConfig] = None) -> T:
        """Create a widget instance with optional pooling.
        
        Args:
            widget_class: Widget class to create
            widget_id: Optional widget ID
            use_pool: Whether to use widget pooling
            pool_config: Pool configuration (if creating new pool)
            
        Returns:
            Widget instance
        """
        with self._lock:
            if use_pool:
                # Get or create pool
                if widget_class not in self._pools:
                    self._pools[widget_class] = create_widget_pool(widget_class, pool_config)
                
                # Check if pool has available widgets
                pool = self._pools[widget_class]
                pool_stats_before = pool.get_stats()
                
                # Acquire from pool
                widget = pool.acquire(widget_id)
                
                # Check if a new widget was created (pool was empty)
                pool_stats_after = pool.get_stats()
                if pool_stats_after['total_count'] > pool_stats_before['total_count']:
                    # New widget was created, update stats
                    class_name = widget_class.__name__
                    self._creation_stats[class_name] = self._creation_stats.get(class_name, 0) + 1
            else:
                # Create directly
                widget = widget_class(widget_id)
                # Update creation stats
                class_name = widget_class.__name__
                self._creation_stats[class_name] = self._creation_stats.get(class_name, 0) + 1
            
            return widget
    
    def release_widget(self, widget: Widget) -> None:
        """Release a widget back to its pool (if pooled).
        
        Args:
            widget: Widget to release
        """
        widget_class = type(widget)
        if widget_class in self._pools:
            self._pools[widget_class].release(widget)
        else:
            # Not pooled, just destroy
            widget.destroy()
    
    def get_creation_stats(self) -> Dict[str, Any]:
        """Get widget creation statistics.
        
        Returns:
            Dictionary with creation statistics
        """
        with self._lock:
            pool_stats = {}
            for widget_class, pool in self._pools.items():
                pool_stats[widget_class.__name__] = pool.get_stats()
            
            return {
                'creation_counts': self._creation_stats.copy(),
                'pool_stats': pool_stats,
                'total_pools': len(self._pools)
            }
    
    def cleanup_pools(self) -> Dict[str, int]:
        """Clean up idle widgets in all pools.
        
        Returns:
            Dictionary with cleanup counts per pool
        """
        cleanup_counts = {}
        for widget_class, pool in self._pools.items():
            count = pool.cleanup_idle_widgets()
            cleanup_counts[widget_class.__name__] = count
        
        return cleanup_counts


# Global widget factory instance
_widget_factory = WidgetFactory()


def get_widget_factory() -> WidgetFactory:
    """Get the global widget factory instance."""
    return _widget_factory


def create_widget(widget_class: Type[T], 
                 widget_id: Optional[str] = None,
                 use_pool: bool = True,
                 pool_config: Optional[WidgetPoolConfig] = None) -> T:
    """Create a widget using the global factory."""
    return _widget_factory.create_widget(widget_class, widget_id, use_pool, pool_config)


def release_widget(widget: Widget) -> None:
    """Release a widget using the global factory."""
    _widget_factory.release_widget(widget)


def lifecycle_managed(widget_class: Type[T]) -> Type[T]:
    """Decorator to add lifecycle management to a widget class.
    
    Args:
        widget_class: Widget class to enhance
        
    Returns:
        Enhanced widget class with lifecycle management
    """
    
    class LifecycleManagedWidget(widget_class, LifecycleIntegratedWidget):
        """Widget class enhanced with lifecycle management."""
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
    
    # Preserve class name and module
    LifecycleManagedWidget.__name__ = widget_class.__name__
    LifecycleManagedWidget.__qualname__ = widget_class.__qualname__
    LifecycleManagedWidget.__module__ = widget_class.__module__
    
    return LifecycleManagedWidget


def with_lifecycle_hooks(**hooks: Callable) -> Callable:
    """Decorator to add lifecycle hooks to a widget method.
    
    Args:
        **hooks: Lifecycle hooks (e.g., before_render=callback, after_render=callback)
        
    Returns:
        Decorated method
    """
    
    def decorator(method: Callable) -> Callable:
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            # Call before hooks
            before_hook = hooks.get(f'before_{method.__name__}')
            if before_hook:
                before_hook(self, *args, **kwargs)
            
            # Call original method
            result = method(self, *args, **kwargs)
            
            # Call after hooks
            after_hook = hooks.get(f'after_{method.__name__}')
            if after_hook:
                after_hook(self, result, *args, **kwargs)
            
            return result
        
        return wrapper
    
    return decorator 