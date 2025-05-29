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
import json
import copy

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


class ReactiveValueType(Enum):
    """Types of reactive values for optimization."""
    PRIMITIVE = "primitive"      # int, float, str, bool
    COLLECTION = "collection"    # list, dict, set
    OBJECT = "object"           # custom objects
    COMPUTED = "computed"       # computed/derived values


@dataclass
class ReactiveChange:
    """Represents a change in a reactive value."""
    old_value: Any
    new_value: Any
    timestamp: float
    source: str
    change_type: str = "update"  # "update", "add", "remove", "clear"
    path: Optional[str] = None   # For nested changes in collections


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


class ReactiveValue(Generic[T]):
    """Enhanced reactive value with advanced data type support."""
    
    def __init__(self, initial_value: T, value_type: Optional[ReactiveValueType] = None,
                 reactive_id: Optional[str] = None):
        self._value: T = initial_value
        self._value_type = value_type or self._detect_value_type(initial_value)
        self._reactive_id = reactive_id or f"reactive_{id(self)}"
        self._observers: Set[Callable[[ReactiveChange], None]] = set()
        self._dependencies: Set['ReactiveValue'] = set()
        self._dependents: Set['ReactiveValue'] = weakref.WeakSet()
        self._lock = threading.RLock()
        self._change_history: List[ReactiveChange] = []
        self._max_history = 100
        self._validation_func: Optional[Callable[[T], bool]] = None
        self._transform_func: Optional[Callable[[T], T]] = None
        self._serialization_func: Optional[Callable[[T], str]] = None
        self._deserialization_func: Optional[Callable[[str], T]] = None
        self._is_dirty = False
        self._last_update_time = 0.0
        
    @property
    def value(self) -> T:
        """Get the current value."""
        return self._value
        
    @value.setter
    def value(self, new_value: T) -> None:
        """Set a new value with change notification."""
        with self._lock:
            if self._validation_func and not self._validation_func(new_value):
                raise ValueError(f"Value validation failed for {self._reactive_id}: {new_value}")
                
            if self._transform_func:
                new_value = self._transform_func(new_value)
                
            old_value = self._value
            if not self._values_equal(old_value, new_value):
                self._value = new_value
                self._last_update_time = time.time()
                change = ReactiveChange(
                    old_value=old_value,
                    new_value=new_value,
                    timestamp=self._last_update_time,
                    source=self._reactive_id
                )
                self._record_change(change)
                self._notify_observers(change)
                self._notify_dependents(change)
                self._is_dirty = True
                
    @property
    def reactive_id(self) -> str:
        """Get the reactive ID."""
        return self._reactive_id
        
    @property
    def value_type(self) -> ReactiveValueType:
        """Get the value type."""
        return self._value_type
        
    @property
    def is_dirty(self) -> bool:
        """Check if value has changed since last clean."""
        return self._is_dirty
        
    def mark_clean(self) -> None:
        """Mark value as clean (no pending changes)."""
        self._is_dirty = False
        
    def bind(self, observer: Callable[[ReactiveChange], None]) -> None:
        """Bind an observer to value changes."""
        with self._lock:
            self._observers.add(observer)
            
    def unbind(self, observer: Callable[[ReactiveChange], None]) -> None:
        """Unbind an observer from value changes."""
        with self._lock:
            self._observers.discard(observer)
            
    def add_dependency(self, dependency: 'ReactiveValue') -> None:
        """Add a dependency relationship."""
        with self._lock:
            self._dependencies.add(dependency)
            dependency._dependents.add(self)
            
    def remove_dependency(self, dependency: 'ReactiveValue') -> None:
        """Remove a dependency relationship."""
        with self._lock:
            self._dependencies.discard(dependency)
            dependency._dependents.discard(self)
            
    def set_validation(self, validation_func: Callable[[T], bool]) -> None:
        """Set a validation function for value changes."""
        self._validation_func = validation_func
        
    def set_transform(self, transform_func: Callable[[T], T]) -> None:
        """Set a transformation function for value changes."""
        self._transform_func = transform_func
        
    def set_serialization(self, serialize_func: Callable[[T], str], 
                         deserialize_func: Callable[[str], T]) -> None:
        """Set serialization functions for persistence."""
        self._serialization_func = serialize_func
        self._deserialization_func = deserialize_func
        
    def serialize(self) -> str:
        """Serialize the current value to string."""
        if self._serialization_func:
            return self._serialization_func(self._value)
        else:
            # Default JSON serialization
            try:
                return json.dumps(self._value)
            except (TypeError, ValueError):
                return str(self._value)
                
    def deserialize(self, data: str) -> None:
        """Deserialize and set value from string."""
        if self._deserialization_func:
            self.value = self._deserialization_func(data)
        else:
            # Default JSON deserialization
            try:
                self.value = json.loads(data)
            except (json.JSONDecodeError, TypeError, ValueError):
                # Fallback to string value
                self.value = data
                
    def get_change_history(self, limit: int = None) -> List[ReactiveChange]:
        """Get change history."""
        with self._lock:
            if limit is None:
                return self._change_history.copy()
            else:
                return self._change_history[-limit:]
                
    def clear_history(self) -> None:
        """Clear change history."""
        with self._lock:
            self._change_history.clear()
            
    def get_dependencies(self) -> Set['ReactiveValue']:
        """Get all dependencies."""
        return self._dependencies.copy()
        
    def get_dependents(self) -> Set['ReactiveValue']:
        """Get all dependents."""
        return set(self._dependents)
        
    def _detect_value_type(self, value: Any) -> ReactiveValueType:
        """Detect the type of reactive value for optimization."""
        if isinstance(value, (int, float, str, bool, type(None))):
            return ReactiveValueType.PRIMITIVE
        elif isinstance(value, (list, dict, set, tuple)):
            return ReactiveValueType.COLLECTION
        else:
            return ReactiveValueType.OBJECT
            
    def _values_equal(self, old_value: Any, new_value: Any) -> bool:
        """Check if two values are equal, handling collections properly."""
        try:
            if self._value_type == ReactiveValueType.COLLECTION:
                # Deep comparison for collections
                return self._deep_equal(old_value, new_value)
            else:
                return old_value == new_value
        except Exception:
            # Fallback to identity comparison
            return old_value is new_value
            
    def _deep_equal(self, obj1: Any, obj2: Any) -> bool:
        """Deep equality comparison for complex objects."""
        try:
            if type(obj1) != type(obj2):
                return False
            if isinstance(obj1, dict):
                return (len(obj1) == len(obj2) and 
                       all(k in obj2 and self._deep_equal(v, obj2[k]) 
                           for k, v in obj1.items()))
            elif isinstance(obj1, (list, tuple)):
                return (len(obj1) == len(obj2) and 
                       all(self._deep_equal(a, b) for a, b in zip(obj1, obj2)))
            elif isinstance(obj1, set):
                return obj1 == obj2
            else:
                return obj1 == obj2
        except Exception:
            return False
            
    def _record_change(self, change: ReactiveChange) -> None:
        """Record change in history."""
        self._change_history.append(change)
        if len(self._change_history) > self._max_history:
            self._change_history.pop(0)
            
    def _notify_observers(self, change: ReactiveChange) -> None:
        """Notify all observers of the change."""
        for observer in self._observers.copy():
            try:
                observer(change)
            except Exception as e:
                print(f"Error in reactive observer for {self._reactive_id}: {e}")
                
    def _notify_dependents(self, change: ReactiveChange) -> None:
        """Notify dependent reactive values."""
        for dependent in self._dependents.copy():
            try:
                dependent._on_dependency_changed(self, change)
            except Exception as e:
                print(f"Error in dependent notification for {self._reactive_id}: {e}")
                
    def _on_dependency_changed(self, dependency: 'ReactiveValue', change: ReactiveChange) -> None:
        """Handle dependency change - override in subclasses."""
        pass
        
    def __repr__(self) -> str:
        return f"ReactiveValue(id={self._reactive_id}, type={self._value_type.value}, value={self._value})"


class ReactiveCollection(ReactiveValue[T]):
    """Reactive collection with granular change notifications."""
    
    def __init__(self, initial_value: T, reactive_id: Optional[str] = None):
        super().__init__(initial_value, ReactiveValueType.COLLECTION, reactive_id)
        self._item_observers: Dict[str, Set[Callable]] = {}
        
    def notify_item_change(self, path: str, old_value: Any, new_value: Any, 
                          change_type: str = "update") -> None:
        """Notify observers of item-level changes."""
        change = ReactiveChange(
            old_value=old_value,
            new_value=new_value,
            timestamp=time.time(),
            source=self._reactive_id,
            change_type=change_type,
            path=path
        )
        
        # Notify general observers
        self._notify_observers(change)
        
        # Notify path-specific observers
        if path in self._item_observers:
            for observer in self._item_observers[path].copy():
                try:
                    observer(change)
                except Exception as e:
                    print(f"Error in item observer for {path}: {e}")
                    
    def bind_item(self, path: str, observer: Callable[[ReactiveChange], None]) -> None:
        """Bind observer to specific item changes."""
        if path not in self._item_observers:
            self._item_observers[path] = set()
        self._item_observers[path].add(observer)
        
    def unbind_item(self, path: str, observer: Callable[[ReactiveChange], None]) -> None:
        """Unbind observer from specific item changes."""
        if path in self._item_observers:
            self._item_observers[path].discard(observer)
            if not self._item_observers[path]:
                del self._item_observers[path]


class ReactiveList(ReactiveCollection[List[T]]):
    """Reactive list with list-specific operations."""
    
    def append(self, item: T) -> None:
        """Append item to list with change notification."""
        with self._lock:
            old_value = copy.deepcopy(self._value)
            self._value.append(item)
            self.notify_item_change(
                path=f"[{len(self._value)-1}]",
                old_value=None,
                new_value=item,
                change_type="add"
            )
            
    def insert(self, index: int, item: T) -> None:
        """Insert item at index with change notification."""
        with self._lock:
            old_value = copy.deepcopy(self._value)
            self._value.insert(index, item)
            self.notify_item_change(
                path=f"[{index}]",
                old_value=None,
                new_value=item,
                change_type="add"
            )
            
    def remove(self, item: T) -> None:
        """Remove item from list with change notification."""
        with self._lock:
            try:
                index = self._value.index(item)
                old_value = self._value[index]
                self._value.remove(item)
                self.notify_item_change(
                    path=f"[{index}]",
                    old_value=old_value,
                    new_value=None,
                    change_type="remove"
                )
            except ValueError:
                pass  # Item not in list
                
    def pop(self, index: int = -1) -> T:
        """Pop item from list with change notification."""
        with self._lock:
            if not self._value:
                raise IndexError("pop from empty list")
            old_value = self._value[index]
            result = self._value.pop(index)
            self.notify_item_change(
                path=f"[{index if index >= 0 else len(self._value)}]",
                old_value=old_value,
                new_value=None,
                change_type="remove"
            )
            return result
            
    def clear(self) -> None:
        """Clear list with change notification."""
        with self._lock:
            old_value = copy.deepcopy(self._value)
            self._value.clear()
            self.notify_item_change(
                path="",
                old_value=old_value,
                new_value=[],
                change_type="clear"
            )
            
    def __setitem__(self, index: int, value: T) -> None:
        """Set item at index with change notification."""
        with self._lock:
            old_value = self._value[index] if 0 <= index < len(self._value) else None
            self._value[index] = value
            self.notify_item_change(
                path=f"[{index}]",
                old_value=old_value,
                new_value=value,
                change_type="update"
            )
            
    def __getitem__(self, index: int) -> T:
        """Get item at index."""
        return self._value[index]
        
    def __len__(self) -> int:
        """Get list length."""
        return len(self._value)


class ReactiveDict(ReactiveCollection[Dict[str, T]]):
    """Reactive dictionary with dict-specific operations."""
    
    def __setitem__(self, key: str, value: T) -> None:
        """Set item with change notification."""
        with self._lock:
            old_value = self._value.get(key)
            self._value[key] = value
            change_type = "update" if old_value is not None else "add"
            self.notify_item_change(
                path=f".{key}",
                old_value=old_value,
                new_value=value,
                change_type=change_type
            )
            
    def __getitem__(self, key: str) -> T:
        """Get item by key."""
        return self._value[key]
        
    def __delitem__(self, key: str) -> None:
        """Delete item with change notification."""
        with self._lock:
            old_value = self._value.get(key)
            if key in self._value:
                del self._value[key]
                self.notify_item_change(
                    path=f".{key}",
                    old_value=old_value,
                    new_value=None,
                    change_type="remove"
                )
                
    def pop(self, key: str, default=None) -> T:
        """Pop item with change notification."""
        with self._lock:
            old_value = self._value.get(key, default)
            result = self._value.pop(key, default)
            if key in self._value or old_value != default:
                self.notify_item_change(
                    path=f".{key}",
                    old_value=old_value,
                    new_value=None,
                    change_type="remove"
                )
            return result
            
    def update(self, other: Dict[str, T]) -> None:
        """Update with another dict with change notifications."""
        with self._lock:
            for key, value in other.items():
                self[key] = value
                
    def clear(self) -> None:
        """Clear dict with change notification."""
        with self._lock:
            old_value = copy.deepcopy(self._value)
            self._value.clear()
            self.notify_item_change(
                path="",
                old_value=old_value,
                new_value={},
                change_type="clear"
            )
            
    def keys(self):
        """Get dict keys."""
        return self._value.keys()
        
    def values(self):
        """Get dict values."""
        return self._value.values()
        
    def items(self):
        """Get dict items."""
        return self._value.items()
        
    def get(self, key: str, default=None):
        """Get item with default."""
        return self._value.get(key, default)
        
    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._value
        
    def __len__(self) -> int:
        """Get dict length."""
        return len(self._value)


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