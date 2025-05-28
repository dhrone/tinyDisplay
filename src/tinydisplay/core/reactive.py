#!/usr/bin/env python3
"""
Reactive Data Binding System

Provides comprehensive reactive data binding capabilities for tinyDisplay,
integrating with the ring buffer system for real-time data streams.
"""

from typing import Dict, List, Set, Any, Callable, Optional, Union, TypeVar, Generic
from dataclasses import dataclass
import threading
import time
import weakref
from abc import ABC, abstractmethod
from enum import Enum

from .ring_buffer import RingBuffer, BufferEntry
from .expressions import ExpressionEvaluator


T = TypeVar('T')


class BindingType(Enum):
    """Types of reactive bindings."""
    DIRECT = "direct"           # Direct value binding
    COMPUTED = "computed"       # Computed from other values
    EXPRESSION = "expression"   # Expression-based binding
    STREAM = "stream"          # Ring buffer stream binding
    TRANSFORM = "transform"     # Transformed value binding


@dataclass
class BindingConfig:
    """Configuration for reactive bindings."""
    binding_type: BindingType
    update_frequency: float = 0.0  # 0 = immediate, >0 = throttled updates
    debounce_time: float = 0.0     # Debounce rapid changes
    transform_function: Optional[Callable] = None
    expression: Optional[str] = None
    ring_buffer_key: Optional[str] = None
    dependencies: List[str] = None


class ReactiveBinding(ABC):
    """Abstract base class for reactive bindings."""
    
    def __init__(self, binding_id: str, config: BindingConfig):
        self.binding_id = binding_id
        self.config = config
        self._observers: Set[Callable] = set()
        self._last_value: Any = None
        self._last_update_time = 0.0
        self._lock = threading.RLock()
        
    @property
    def value(self) -> Any:
        """Get current value."""
        return self._last_value
    
    @abstractmethod
    def update(self) -> bool:
        """Update the binding value. Returns True if value changed."""
        pass
    
    def add_observer(self, observer: Callable) -> None:
        """Add an observer for value changes."""
        with self._lock:
            self._observers.add(observer)
    
    def remove_observer(self, observer: Callable) -> None:
        """Remove an observer."""
        with self._lock:
            self._observers.discard(observer)
    
    def notify_observers(self, old_value: Any, new_value: Any) -> None:
        """Notify all observers of value change."""
        for observer in self._observers.copy():
            try:
                observer(self.binding_id, old_value, new_value)
            except Exception as e:
                print(f"Error in reactive binding observer: {e}")
    
    def _should_update(self) -> bool:
        """Check if binding should update based on throttling/debouncing."""
        current_time = time.time()
        
        # Check update frequency throttling
        if self.config.update_frequency > 0:
            time_since_update = current_time - self._last_update_time
            if time_since_update < (1.0 / self.config.update_frequency):
                return False
        
        return True
    
    def _set_value(self, new_value: Any) -> bool:
        """Set new value and notify observers if changed."""
        with self._lock:
            if self._last_value != new_value:
                old_value = self._last_value
                self._last_value = new_value
                self._last_update_time = time.time()
                self.notify_observers(old_value, new_value)
                return True
            return False


class DirectBinding(ReactiveBinding):
    """Direct value binding."""
    
    def __init__(self, binding_id: str, initial_value: Any = None):
        config = BindingConfig(BindingType.DIRECT)
        super().__init__(binding_id, config)
        self._last_value = initial_value
    
    def set_value(self, value: Any) -> None:
        """Set the value directly."""
        if self._should_update():
            self._set_value(value)
    
    def update(self) -> bool:
        """Direct bindings don't auto-update."""
        return False


class ComputedBinding(ReactiveBinding):
    """Computed binding that depends on other bindings."""
    
    def __init__(self, binding_id: str, compute_function: Callable, dependencies: List[str]):
        config = BindingConfig(
            BindingType.COMPUTED,
            dependencies=dependencies
        )
        super().__init__(binding_id, config)
        self._compute_function = compute_function
        self._dependency_values: Dict[str, Any] = {}
    
    def update_dependency(self, dependency_id: str, value: Any) -> None:
        """Update a dependency value."""
        self._dependency_values[dependency_id] = value
        self.update()
    
    def update(self) -> bool:
        """Recompute value based on dependencies."""
        if not self._should_update():
            return False
        
        try:
            # Only compute if all dependencies are available
            if len(self._dependency_values) >= len(self.config.dependencies or []):
                new_value = self._compute_function(**self._dependency_values)
                return self._set_value(new_value)
        except Exception as e:
            print(f"Error computing binding {self.binding_id}: {e}")
        
        return False


class ExpressionBinding(ReactiveBinding):
    """Expression-based binding using asteval."""
    
    def __init__(self, binding_id: str, expression: str, evaluator: ExpressionEvaluator):
        config = BindingConfig(
            BindingType.EXPRESSION,
            expression=expression
        )
        super().__init__(binding_id, config)
        self._evaluator = evaluator
        self._expression = expression
    
    def update_context(self, context: Dict[str, Any]) -> None:
        """Update the expression context and recompute."""
        try:
            self._evaluator.update_context(context)
            self.update()
        except Exception as e:
            print(f"Error updating expression context for {self.binding_id}: {e}")
    
    def update(self) -> bool:
        """Evaluate expression and update value."""
        if not self._should_update():
            return False
        
        try:
            new_value = self._evaluator.evaluate(self._expression)
            return self._set_value(new_value)
        except Exception as e:
            print(f"Error evaluating expression for {self.binding_id}: {e}")
            return False


class StreamBinding(ReactiveBinding):
    """Ring buffer stream binding."""
    
    def __init__(self, binding_id: str, ring_buffer: RingBuffer, 
                 transform_function: Optional[Callable] = None):
        config = BindingConfig(
            BindingType.STREAM,
            transform_function=transform_function
        )
        super().__init__(binding_id, config)
        self._ring_buffer = ring_buffer
        self._last_sequence_id = -1
        
        # Note: Ring buffer doesn't have observer pattern, so we'll poll in update()
    
    def update(self) -> bool:
        """Get latest value from ring buffer."""
        if not self._should_update():
            return False
        
        try:
            # Try to peek at the newest entry (last in buffer)
            if not self._ring_buffer.is_empty:
                # Get the most recent entry by peeking at the last position
                count = len(self._ring_buffer)
                if count > 0:
                    latest = self._ring_buffer.peek(count - 1)  # Last entry
                    if latest and latest.sequence_id > self._last_sequence_id:
                        self._last_sequence_id = latest.sequence_id
                        
                        # Apply transform if configured
                        value = latest.value
                        if self.config.transform_function:
                            value = self.config.transform_function(value)
                        
                        return self._set_value(value)
        except Exception as e:
            print(f"Error updating stream binding {self.binding_id}: {e}")
        
        return False
    
    def get_history(self, count: int = 10) -> List[BufferEntry]:
        """Get recent history from ring buffer."""
        try:
            # Get up to 'count' recent entries
            buffer_size = len(self._ring_buffer)
            actual_count = min(count, buffer_size)
            
            entries = []
            for i in range(max(0, buffer_size - actual_count), buffer_size):
                entry = self._ring_buffer.peek(i)
                if entry:
                    entries.append(entry)
            
            return entries
        except Exception as e:
            print(f"Error getting history from ring buffer: {e}")
            return []


class ReactiveDataManager:
    """Central manager for reactive data bindings."""
    
    def __init__(self):
        self._bindings: Dict[str, ReactiveBinding] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}  # binding_id -> dependents
        self._ring_buffers: Dict[str, RingBuffer] = {}
        self._expression_evaluator = ExpressionEvaluator()
        self._lock = threading.RLock()
        
        # Update thread for periodic updates
        self._update_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
    
    def start(self) -> None:
        """Start the reactive data manager."""
        if not self._running:
            self._running = True
            self._stop_event.clear()
            self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self._update_thread.start()
    
    def stop(self) -> None:
        """Stop the reactive data manager."""
        if self._running:
            self._running = False
            self._stop_event.set()
            if self._update_thread:
                self._update_thread.join(timeout=1.0)
    
    # Binding management
    def create_direct_binding(self, binding_id: str, initial_value: Any = None) -> DirectBinding:
        """Create a direct value binding."""
        binding = DirectBinding(binding_id, initial_value)
        self._register_binding(binding)
        return binding
    
    def create_computed_binding(self, binding_id: str, compute_function: Callable, 
                              dependencies: List[str]) -> ComputedBinding:
        """Create a computed binding."""
        binding = ComputedBinding(binding_id, compute_function, dependencies)
        self._register_binding(binding)
        
        # Set up dependency relationships
        for dep_id in dependencies:
            self._add_dependency(dep_id, binding_id)
            
            # Subscribe to dependency changes
            if dep_id in self._bindings:
                self._bindings[dep_id].add_observer(
                    lambda bid, old, new, b=binding, d=dep_id: b.update_dependency(d, new)
                )
        
        return binding
    
    def create_expression_binding(self, binding_id: str, expression: str) -> ExpressionBinding:
        """Create an expression-based binding."""
        binding = ExpressionBinding(binding_id, expression, self._expression_evaluator)
        self._register_binding(binding)
        return binding
    
    def create_stream_binding(self, binding_id: str, ring_buffer_key: str,
                            transform_function: Optional[Callable] = None) -> StreamBinding:
        """Create a ring buffer stream binding."""
        if ring_buffer_key not in self._ring_buffers:
            raise ValueError(f"Ring buffer '{ring_buffer_key}' not found")
        
        ring_buffer = self._ring_buffers[ring_buffer_key]
        binding = StreamBinding(binding_id, ring_buffer, transform_function)
        self._register_binding(binding)
        return binding
    
    def remove_binding(self, binding_id: str) -> bool:
        """Remove a binding."""
        with self._lock:
            if binding_id in self._bindings:
                binding = self._bindings.pop(binding_id)
                
                # Clean up dependencies
                if binding_id in self._dependency_graph:
                    del self._dependency_graph[binding_id]
                
                # Remove from dependents
                for deps in self._dependency_graph.values():
                    deps.discard(binding_id)
                
                return True
            return False
    
    # Ring buffer management
    def register_ring_buffer(self, key: str, ring_buffer: RingBuffer) -> None:
        """Register a ring buffer for stream bindings."""
        self._ring_buffers[key] = ring_buffer
    
    def unregister_ring_buffer(self, key: str) -> bool:
        """Unregister a ring buffer."""
        if key in self._ring_buffers:
            del self._ring_buffers[key]
            return True
        return False
    
    def get_ring_buffer(self, key: str) -> Optional[RingBuffer]:
        """Get a registered ring buffer."""
        return self._ring_buffers.get(key)
    
    # Value access
    def get_value(self, binding_id: str) -> Any:
        """Get current value of a binding."""
        binding = self._bindings.get(binding_id)
        return binding.value if binding else None
    
    def set_value(self, binding_id: str, value: Any) -> bool:
        """Set value for a direct binding."""
        binding = self._bindings.get(binding_id)
        if isinstance(binding, DirectBinding):
            binding.set_value(value)
            return True
        return False
    
    def update_expression_context(self, context: Dict[str, Any]) -> None:
        """Update context for all expression bindings."""
        for binding in self._bindings.values():
            if isinstance(binding, ExpressionBinding):
                binding.update_context(context)
    
    # Observation
    def observe_binding(self, binding_id: str, observer: Callable) -> bool:
        """Add an observer to a binding."""
        binding = self._bindings.get(binding_id)
        if binding:
            binding.add_observer(observer)
            return True
        return False
    
    def unobserve_binding(self, binding_id: str, observer: Callable) -> bool:
        """Remove an observer from a binding."""
        binding = self._bindings.get(binding_id)
        if binding:
            binding.remove_observer(observer)
            return True
        return False
    
    # Statistics
    def get_binding_stats(self) -> Dict[str, Any]:
        """Get statistics about bindings."""
        return {
            'total_bindings': len(self._bindings),
            'binding_types': {
                bt.value: len([b for b in self._bindings.values() 
                              if b.config.binding_type == bt])
                for bt in BindingType
            },
            'ring_buffers': len(self._ring_buffers),
            'dependency_relationships': sum(len(deps) for deps in self._dependency_graph.values())
        }
    
    # Internal methods
    def _register_binding(self, binding: ReactiveBinding) -> None:
        """Register a binding."""
        with self._lock:
            self._bindings[binding.binding_id] = binding
    
    def _add_dependency(self, dependency_id: str, dependent_id: str) -> None:
        """Add a dependency relationship."""
        if dependency_id not in self._dependency_graph:
            self._dependency_graph[dependency_id] = set()
        self._dependency_graph[dependency_id].add(dependent_id)
    
    def _update_loop(self) -> None:
        """Main update loop for periodic binding updates."""
        while not self._stop_event.is_set():
            try:
                # Update all bindings
                for binding in list(self._bindings.values()):
                    binding.update()
                
                # Sleep for a short time
                time.sleep(0.016)  # ~60fps update rate
                
            except Exception as e:
                print(f"Error in reactive data update loop: {e}")
                time.sleep(0.1)  # Longer sleep on error


# Global reactive data manager instance
_reactive_manager: Optional[ReactiveDataManager] = None


def get_reactive_manager() -> ReactiveDataManager:
    """Get the global reactive data manager."""
    global _reactive_manager
    if _reactive_manager is None:
        _reactive_manager = ReactiveDataManager()
    return _reactive_manager


def start_reactive_system() -> None:
    """Start the global reactive system."""
    get_reactive_manager().start()


def stop_reactive_system() -> None:
    """Stop the global reactive system."""
    if _reactive_manager:
        _reactive_manager.stop() 