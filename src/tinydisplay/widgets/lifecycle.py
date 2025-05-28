#!/usr/bin/env python3
"""
Widget Lifecycle Management System

Provides comprehensive lifecycle management for widgets including:
- Widget pools for performance optimization
- Lifecycle event management and hooks
- Widget state transitions and validation
- Resource cleanup and memory management
"""

from typing import Dict, List, Set, Optional, Callable, Any, Type, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
import weakref
from collections import defaultdict, deque

from .base import Widget, WidgetState

T = TypeVar('T', bound=Widget)


class LifecycleEvent(Enum):
    """Widget lifecycle events."""
    CREATED = "created"
    INITIALIZED = "initialized"
    ACTIVATED = "activated"
    RENDERED = "rendered"
    HIDDEN = "hidden"
    DESTROYED = "destroyed"
    UPDATED = "updated"
    VISIBILITY_CHANGED = "visibility_changed"
    ALPHA_CHANGED = "alpha_changed"
    POSITION_CHANGED = "position_changed"
    SIZE_CHANGED = "size_changed"
    PARENT_CHANGED = "parent_changed"
    CHILD_ADDED = "child_added"
    CHILD_REMOVED = "child_removed"


@dataclass
class LifecycleEventInfo:
    """Information about a lifecycle event."""
    event: LifecycleEvent
    widget: Widget
    timestamp: float
    old_value: Any = None
    new_value: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WidgetPoolConfig:
    """Configuration for widget pools."""
    max_pool_size: int = 100
    cleanup_interval: float = 60.0  # seconds
    max_idle_time: float = 300.0  # seconds
    enable_preallocation: bool = True
    preallocation_count: int = 10


class WidgetPool(Generic[T]):
    """Pool for reusing widget instances to improve performance."""
    
    def __init__(self, widget_class: Type[T], config: WidgetPoolConfig):
        self._widget_class = widget_class
        self._config = config
        self._available: deque[T] = deque()
        self._in_use: Set[T] = set()
        self._creation_times: Dict[T, float] = {}
        self._lock = threading.RLock()
        
        # Pre-allocate widgets if enabled
        if config.enable_preallocation:
            self._preallocate_widgets()
    
    def acquire(self, widget_id: Optional[str] = None) -> T:
        """Acquire a widget from the pool.
        
        Args:
            widget_id: Optional widget ID
            
        Returns:
            Widget instance
        """
        with self._lock:
            if self._available:
                widget = self._available.popleft()
                self._in_use.add(widget)
                
                # Reset widget state
                self._reset_widget(widget, widget_id)
                return widget
            else:
                # Create new widget if pool is empty
                widget = self._create_widget(widget_id)
                self._in_use.add(widget)
                return widget
    
    def release(self, widget: T) -> None:
        """Release a widget back to the pool.
        
        Args:
            widget: Widget to release
        """
        with self._lock:
            if widget in self._in_use:
                self._in_use.remove(widget)
                
                # Clean up widget state
                self._cleanup_widget(widget)
                
                # Add back to pool if under limit
                if len(self._available) < self._config.max_pool_size:
                    self._available.append(widget)
                    self._creation_times[widget] = time.time()
                else:
                    # Destroy widget if pool is full
                    widget.destroy()
                    self._creation_times.pop(widget, None)
    
    def cleanup_idle_widgets(self) -> int:
        """Clean up widgets that have been idle too long.
        
        Returns:
            Number of widgets cleaned up
        """
        current_time = time.time()
        cleaned_count = 0
        
        with self._lock:
            widgets_to_remove = []
            
            for widget in list(self._available):
                creation_time = self._creation_times.get(widget, current_time)
                if current_time - creation_time > self._config.max_idle_time:
                    widgets_to_remove.append(widget)
            
            for widget in widgets_to_remove:
                self._available.remove(widget)
                widget.destroy()
                self._creation_times.pop(widget, None)
                cleaned_count += 1
        
        return cleaned_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics.
        
        Returns:
            Dictionary with pool statistics
        """
        with self._lock:
            return {
                'widget_class': self._widget_class.__name__,
                'available_count': len(self._available),
                'in_use_count': len(self._in_use),
                'total_count': len(self._available) + len(self._in_use),
                'max_pool_size': self._config.max_pool_size
            }
    
    def _preallocate_widgets(self) -> None:
        """Pre-allocate widgets for the pool."""
        for _ in range(self._config.preallocation_count):
            widget = self._create_widget()
            self._available.append(widget)
            self._creation_times[widget] = time.time()
    
    def _create_widget(self, widget_id: Optional[str] = None) -> T:
        """Create a new widget instance."""
        return self._widget_class(widget_id)
    
    def _reset_widget(self, widget: T, widget_id: Optional[str] = None) -> None:
        """Reset widget to initial state."""
        # Reset core properties
        if widget_id:
            widget._widget_id = widget_id
        widget._state = WidgetState.CREATED
        widget._dirty = True
        widget.visible = True
        widget.alpha = 1.0
        widget.position = (0, 0)
        widget.size = (100, 20)
        
        # Clear lifecycle hooks
        widget._lifecycle_hooks.clear()
        
        # Reset reactive bindings
        widget._cleanup_reactive_bindings()
    
    def _cleanup_widget(self, widget: T) -> None:
        """Clean up widget before returning to pool."""
        # Stop any animations
        widget._current_animation = None
        
        # Clear parent-child relationships
        widget.set_parent_widget(None)
        
        # Clear lifecycle hooks
        widget._lifecycle_hooks.clear()
        
        # Clean up reactive bindings
        widget._cleanup_reactive_bindings()


class LifecycleManager:
    """Manages widget lifecycle events and hooks."""
    
    def __init__(self):
        self._global_hooks: Dict[LifecycleEvent, Set[Callable]] = defaultdict(set)
        self._widget_hooks: Dict[Widget, Dict[LifecycleEvent, Set[Callable]]] = defaultdict(lambda: defaultdict(set))
        self._event_history: deque[LifecycleEventInfo] = deque(maxlen=1000)
        self._widget_pools: Dict[Type[Widget], WidgetPool] = {}
        self._lock = threading.RLock()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
    
    def register_global_hook(self, event: LifecycleEvent, callback: Callable) -> None:
        """Register a global lifecycle hook.
        
        Args:
            event: Lifecycle event to hook
            callback: Callback function
        """
        with self._lock:
            self._global_hooks[event].add(callback)
    
    def unregister_global_hook(self, event: LifecycleEvent, callback: Callable) -> None:
        """Unregister a global lifecycle hook.
        
        Args:
            event: Lifecycle event to unhook
            callback: Callback function
        """
        with self._lock:
            self._global_hooks[event].discard(callback)
    
    def register_widget_hook(self, widget: Widget, event: LifecycleEvent, callback: Callable) -> None:
        """Register a widget-specific lifecycle hook.
        
        Args:
            widget: Widget to hook
            event: Lifecycle event to hook
            callback: Callback function
        """
        with self._lock:
            self._widget_hooks[widget][event].add(callback)
    
    def unregister_widget_hook(self, widget: Widget, event: LifecycleEvent, callback: Callable) -> None:
        """Unregister a widget-specific lifecycle hook.
        
        Args:
            widget: Widget to unhook
            event: Lifecycle event to unhook
            callback: Callback function
        """
        with self._lock:
            if widget in self._widget_hooks:
                self._widget_hooks[widget][event].discard(callback)
    
    def emit_event(self, event: LifecycleEvent, widget: Widget, 
                   old_value: Any = None, new_value: Any = None,
                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """Emit a lifecycle event.
        
        Args:
            event: Lifecycle event
            widget: Widget that triggered the event
            old_value: Previous value (for change events)
            new_value: New value (for change events)
            metadata: Additional event metadata
        """
        event_info = LifecycleEventInfo(
            event=event,
            widget=widget,
            timestamp=time.time(),
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {}
        )
        
        with self._lock:
            # Add to event history
            self._event_history.append(event_info)
            
            # Call global hooks
            for callback in self._global_hooks[event].copy():
                try:
                    callback(event_info)
                except Exception as e:
                    print(f"Error in global lifecycle hook {event}: {e}")
            
            # Call widget-specific hooks
            if widget in self._widget_hooks:
                for callback in self._widget_hooks[widget][event].copy():
                    try:
                        callback(event_info)
                    except Exception as e:
                        print(f"Error in widget lifecycle hook {event}: {e}")
    
    def create_widget_pool(self, widget_class: Type[T], 
                          config: Optional[WidgetPoolConfig] = None) -> WidgetPool[T]:
        """Create a widget pool for the given widget class.
        
        Args:
            widget_class: Widget class to pool
            config: Pool configuration
            
        Returns:
            Widget pool instance
        """
        if config is None:
            config = WidgetPoolConfig()
        
        with self._lock:
            if widget_class not in self._widget_pools:
                self._widget_pools[widget_class] = WidgetPool(widget_class, config)
            return self._widget_pools[widget_class]
    
    def get_widget_pool(self, widget_class: Type[T]) -> Optional[WidgetPool[T]]:
        """Get existing widget pool for the given widget class.
        
        Args:
            widget_class: Widget class
            
        Returns:
            Widget pool instance or None
        """
        return self._widget_pools.get(widget_class)
    
    def get_event_history(self, widget: Optional[Widget] = None, 
                         event: Optional[LifecycleEvent] = None,
                         limit: int = 100) -> List[LifecycleEventInfo]:
        """Get lifecycle event history.
        
        Args:
            widget: Filter by widget (optional)
            event: Filter by event type (optional)
            limit: Maximum number of events to return
            
        Returns:
            List of lifecycle events
        """
        with self._lock:
            events = list(self._event_history)
            
            # Apply filters
            if widget:
                events = [e for e in events if e.widget == widget]
            if event:
                events = [e for e in events if e.event == event]
            
            # Apply limit
            return events[-limit:] if limit > 0 else events
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get statistics for all widget pools.
        
        Returns:
            Dictionary with pool statistics
        """
        with self._lock:
            return {
                widget_class.__name__: pool.get_stats()
                for widget_class, pool in self._widget_pools.items()
            }
    
    def cleanup_destroyed_widgets(self) -> int:
        """Clean up references to destroyed widgets.
        
        Returns:
            Number of widgets cleaned up
        """
        cleaned_count = 0
        
        with self._lock:
            # Clean up widget hooks for destroyed widgets
            widgets_to_remove = []
            for widget in self._widget_hooks:
                if widget.state == WidgetState.DESTROYED:
                    widgets_to_remove.append(widget)
            
            for widget in widgets_to_remove:
                del self._widget_hooks[widget]
                cleaned_count += 1
        
        return cleaned_count
    
    def _cleanup_worker(self) -> None:
        """Background worker for cleanup tasks."""
        while True:
            try:
                time.sleep(60)  # Run cleanup every minute
                
                # Clean up destroyed widgets
                self.cleanup_destroyed_widgets()
                
                # Clean up idle widgets in pools
                for pool in self._widget_pools.values():
                    pool.cleanup_idle_widgets()
                    
            except Exception as e:
                print(f"Error in lifecycle cleanup worker: {e}")


# Global lifecycle manager instance
_lifecycle_manager = LifecycleManager()


def get_lifecycle_manager() -> LifecycleManager:
    """Get the global lifecycle manager instance."""
    return _lifecycle_manager


def create_widget_pool(widget_class: Type[T], 
                      config: Optional[WidgetPoolConfig] = None) -> WidgetPool[T]:
    """Create a widget pool for the given widget class."""
    return _lifecycle_manager.create_widget_pool(widget_class, config)


def get_widget_pool(widget_class: Type[T]) -> Optional[WidgetPool[T]]:
    """Get existing widget pool for the given widget class."""
    return _lifecycle_manager.get_widget_pool(widget_class)


def emit_lifecycle_event(event: LifecycleEvent, widget: Widget,
                        old_value: Any = None, new_value: Any = None,
                        metadata: Optional[Dict[str, Any]] = None) -> None:
    """Emit a lifecycle event."""
    _lifecycle_manager.emit_event(event, widget, old_value, new_value, metadata)


def register_global_lifecycle_hook(event: LifecycleEvent, callback: Callable) -> None:
    """Register a global lifecycle hook."""
    _lifecycle_manager.register_global_hook(event, callback)


def unregister_global_lifecycle_hook(event: LifecycleEvent, callback: Callable) -> None:
    """Unregister a global lifecycle hook."""
    _lifecycle_manager.unregister_global_hook(event, callback) 