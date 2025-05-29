#!/usr/bin/env python3
"""
Reactive System Debugging Tools

Provides comprehensive debugging utilities for the reactive data binding system,
including dependency visualization, update tracing, and performance profiling.
"""

from typing import Dict, List, Set, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
import threading
import time
import json
from collections import defaultdict, deque
from enum import Enum
import weakref

from .reactive import ReactiveValue, ReactiveChange, ReactiveValueType
from .dependencies import DependencyGraph, DependencyEdge, get_dependency_graph
from .streams import ReactiveDataStream, get_stream_manager


class DebugLevel(Enum):
    """Debug logging levels."""
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ReactiveEvent:
    """Represents a reactive system event for debugging."""
    timestamp: float
    event_type: str
    source_id: str
    target_id: Optional[str] = None
    old_value: Any = None
    new_value: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Performance metrics for reactive operations."""
    operation_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    average_time: float = 0.0
    last_operation_time: float = 0.0


class ReactiveTracer:
    """Traces reactive value updates and dependency changes."""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self._events: deque = deque(maxlen=max_events)
        self._active_traces: Set[str] = set()
        self._trace_filters: Dict[str, Callable[[ReactiveEvent], bool]] = {}
        self._lock = threading.RLock()
        self._enabled = True
        
    def enable(self) -> None:
        """Enable tracing."""
        self._enabled = True
        
    def disable(self) -> None:
        """Disable tracing."""
        self._enabled = False
        
    def is_enabled(self) -> bool:
        """Check if tracing is enabled."""
        return self._enabled
        
    def start_trace(self, reactive_id: str, filter_func: Optional[Callable[[ReactiveEvent], bool]] = None) -> None:
        """Start tracing a specific reactive value."""
        with self._lock:
            self._active_traces.add(reactive_id)
            if filter_func:
                self._trace_filters[reactive_id] = filter_func
                
    def stop_trace(self, reactive_id: str) -> None:
        """Stop tracing a specific reactive value."""
        with self._lock:
            self._active_traces.discard(reactive_id)
            self._trace_filters.pop(reactive_id, None)
            
    def trace_event(self, event: ReactiveEvent) -> None:
        """Record a reactive event."""
        if not self._enabled:
            return
            
        with self._lock:
            # Check if we should trace this event
            should_trace = (
                not self._active_traces or 
                event.source_id in self._active_traces or
                (event.target_id and event.target_id in self._active_traces)
            )
            
            if should_trace:
                # Apply filters
                filter_func = self._trace_filters.get(event.source_id)
                if filter_func and not filter_func(event):
                    return
                    
                self._events.append(event)
                
    def get_events(self, reactive_id: Optional[str] = None, 
                   event_type: Optional[str] = None,
                   since: Optional[float] = None,
                   limit: Optional[int] = None) -> List[ReactiveEvent]:
        """Get traced events with optional filtering."""
        with self._lock:
            events = list(self._events)
            
            # Apply filters
            if reactive_id:
                events = [e for e in events if e.source_id == reactive_id or e.target_id == reactive_id]
                
            if event_type:
                events = [e for e in events if e.event_type == event_type]
                
            if since:
                events = [e for e in events if e.timestamp >= since]
                
            # Sort by timestamp (most recent first)
            events.sort(key=lambda e: e.timestamp, reverse=True)
            
            if limit:
                events = events[:limit]
                
            return events
            
    def clear_events(self) -> None:
        """Clear all traced events."""
        with self._lock:
            self._events.clear()
            
    def get_trace_summary(self, reactive_id: str) -> Dict[str, Any]:
        """Get a summary of traces for a reactive value."""
        events = self.get_events(reactive_id)
        
        if not events:
            return {'reactive_id': reactive_id, 'event_count': 0}
            
        event_types = defaultdict(int)
        for event in events:
            event_types[event.event_type] += 1
            
        return {
            'reactive_id': reactive_id,
            'event_count': len(events),
            'event_types': dict(event_types),
            'first_event': events[-1].timestamp if events else None,
            'last_event': events[0].timestamp if events else None,
            'time_span': events[0].timestamp - events[-1].timestamp if len(events) > 1 else 0
        }


class ReactiveProfiler:
    """Profiles performance of reactive operations."""
    
    def __init__(self):
        self._metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self._active_operations: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._enabled = True
        
    def enable(self) -> None:
        """Enable profiling."""
        self._enabled = True
        
    def disable(self) -> None:
        """Disable profiling."""
        self._enabled = False
        
    def start_operation(self, operation_id: str) -> None:
        """Start timing an operation."""
        if not self._enabled:
            return
            
        with self._lock:
            self._active_operations[operation_id] = time.perf_counter()
            
    def end_operation(self, operation_id: str) -> float:
        """End timing an operation and record metrics."""
        if not self._enabled:
            return 0.0
            
        with self._lock:
            start_time = self._active_operations.pop(operation_id, None)
            if start_time is None:
                return 0.0
                
            duration = time.perf_counter() - start_time
            metrics = self._metrics[operation_id]
            
            metrics.operation_count += 1
            metrics.total_time += duration
            metrics.min_time = min(metrics.min_time, duration)
            metrics.max_time = max(metrics.max_time, duration)
            metrics.average_time = metrics.total_time / metrics.operation_count
            metrics.last_operation_time = duration
            
            return duration
            
    def get_metrics(self, operation_id: Optional[str] = None) -> Dict[str, PerformanceMetrics]:
        """Get performance metrics."""
        with self._lock:
            if operation_id:
                return {operation_id: self._metrics.get(operation_id, PerformanceMetrics())}
            else:
                return dict(self._metrics)
                
    def reset_metrics(self, operation_id: Optional[str] = None) -> None:
        """Reset performance metrics."""
        with self._lock:
            if operation_id:
                self._metrics.pop(operation_id, None)
            else:
                self._metrics.clear()
                
    def get_performance_report(self) -> Dict[str, Any]:
        """Get a comprehensive performance report."""
        with self._lock:
            report = {
                'total_operations': sum(m.operation_count for m in self._metrics.values()),
                'total_time': sum(m.total_time for m in self._metrics.values()),
                'operations': {}
            }
            
            for op_id, metrics in self._metrics.items():
                if metrics.operation_count > 0:
                    report['operations'][op_id] = {
                        'count': metrics.operation_count,
                        'total_time': metrics.total_time,
                        'average_time': metrics.average_time,
                        'min_time': metrics.min_time,
                        'max_time': metrics.max_time,
                        'last_time': metrics.last_operation_time
                    }
                    
            return report


class ReactiveInspector:
    """Inspects reactive system state and relationships."""
    
    def __init__(self, dependency_graph: Optional[DependencyGraph] = None):
        self.dependency_graph = dependency_graph or get_dependency_graph()
        self._reactive_values: Dict[str, ReactiveValue] = {}
        self._lock = threading.RLock()
        
    def register_reactive_value(self, reactive_id: str, reactive_value: ReactiveValue) -> None:
        """Register a reactive value for inspection."""
        with self._lock:
            self._reactive_values[reactive_id] = reactive_value
            
    def unregister_reactive_value(self, reactive_id: str) -> None:
        """Unregister a reactive value."""
        with self._lock:
            self._reactive_values.pop(reactive_id, None)
            
    def get_reactive_value_info(self, reactive_id: str) -> Dict[str, Any]:
        """Get detailed information about a reactive value."""
        reactive_value = self._reactive_values.get(reactive_id)
        if not reactive_value:
            return {'error': f'Reactive value {reactive_id} not found'}
            
        dependencies = self.dependency_graph.get_dependencies(reactive_id)
        dependents = self.dependency_graph.get_dependents(reactive_id)
        
        return {
            'id': reactive_id,
            'type': reactive_value.value_type.value,
            'current_value': str(reactive_value.value)[:100],  # Truncate long values
            'is_dirty': reactive_value.is_dirty,
            'dependencies': dependencies,
            'dependents': dependents,
            'dependency_count': len(dependencies),
            'dependent_count': len(dependents),
            'change_history_count': len(reactive_value.get_change_history()),
            'last_update': getattr(reactive_value, '_last_update_time', None)
        }
        
    def get_dependency_chain(self, reactive_id: str, max_depth: int = 10) -> Dict[str, Any]:
        """Get the full dependency chain for a reactive value."""
        def build_chain(node_id: str, depth: int, visited: Set[str]) -> Dict[str, Any]:
            if depth >= max_depth or node_id in visited:
                return {'id': node_id, 'truncated': True}
                
            visited.add(node_id)
            dependencies = self.dependency_graph.get_dependencies(node_id)
            
            chain = {
                'id': node_id,
                'dependencies': [
                    build_chain(dep_id, depth + 1, visited.copy())
                    for dep_id in dependencies
                ]
            }
            
            return chain
            
        return build_chain(reactive_id, 0, set())
        
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the system."""
        return self.dependency_graph.detect_cycles()
        
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        cycles = self.find_circular_dependencies()
        stats = self.dependency_graph.get_stats()
        
        # Calculate health score (0-100)
        health_score = 100
        if cycles:
            health_score -= len(cycles) * 20  # Penalize cycles heavily
            
        if stats.average_update_time > 0.1:  # More than 100ms average
            health_score -= 30
        elif stats.average_update_time > 0.05:  # More than 50ms average
            health_score -= 15
            
        health_score = max(0, health_score)
        
        return {
            'health_score': health_score,
            'total_reactive_values': len(self._reactive_values),
            'total_dependencies': stats.total_edges,
            'circular_dependencies': len(cycles),
            'average_update_time': stats.average_update_time,
            'max_update_time': stats.max_update_time,
            'update_count': stats.update_count,
            'issues': self._detect_issues()
        }
        
    def _detect_issues(self) -> List[Dict[str, Any]]:
        """Detect potential issues in the reactive system."""
        issues = []
        
        # Check for circular dependencies
        cycles = self.find_circular_dependencies()
        for cycle in cycles:
            issues.append({
                'type': 'circular_dependency',
                'severity': 'high',
                'description': f'Circular dependency detected: {" -> ".join(cycle)}',
                'nodes': cycle
            })
            
        # Check for performance issues
        stats = self.dependency_graph.get_stats()
        if stats.average_update_time > 0.1:
            issues.append({
                'type': 'performance',
                'severity': 'medium',
                'description': f'High average update time: {stats.average_update_time:.3f}s',
                'metric': stats.average_update_time
            })
            
        # Check for orphaned reactive values
        for reactive_id, reactive_value in self._reactive_values.items():
            dependencies = self.dependency_graph.get_dependencies(reactive_id)
            dependents = self.dependency_graph.get_dependents(reactive_id)
            
            if not dependencies and not dependents:
                issues.append({
                    'type': 'orphaned_value',
                    'severity': 'low',
                    'description': f'Reactive value {reactive_id} has no dependencies or dependents',
                    'node': reactive_id
                })
                
        return issues


class ReactiveDebugger:
    """Main debugging interface for the reactive system."""
    
    def __init__(self):
        self.tracer = ReactiveTracer()
        self.profiler = ReactiveProfiler()
        self.inspector = ReactiveInspector()
        self._log_handlers: List[Callable[[DebugLevel, str], None]] = []
        self._lock = threading.RLock()
        
        # Auto-register reactive values from streams
        self._auto_register_streams()
        
    def _auto_register_streams(self) -> None:
        """Automatically register reactive values from stream manager."""
        try:
            stream_manager = get_stream_manager()
            for stream_id in stream_manager.list_streams():
                stream = stream_manager.get_stream(stream_id)
                if stream:
                    self.inspector.register_reactive_value(
                        stream_id, 
                        stream.get_reactive_value()
                    )
        except Exception:
            pass  # Stream manager might not be initialized
            
    def add_log_handler(self, handler: Callable[[DebugLevel, str], None]) -> None:
        """Add a log handler for debug messages."""
        with self._lock:
            self._log_handlers.append(handler)
            
    def remove_log_handler(self, handler: Callable[[DebugLevel, str], None]) -> None:
        """Remove a log handler."""
        with self._lock:
            if handler in self._log_handlers:
                self._log_handlers.remove(handler)
                
    def log(self, level: DebugLevel, message: str) -> None:
        """Log a debug message."""
        with self._lock:
            for handler in self._log_handlers:
                try:
                    handler(level, message)
                except Exception as e:
                    print(f"Error in debug log handler: {e}")
                    
    def trace_reactive_change(self, reactive_id: str, change: ReactiveChange) -> None:
        """Trace a reactive value change."""
        event = ReactiveEvent(
            timestamp=change.timestamp,
            event_type='value_change',
            source_id=reactive_id,
            old_value=change.old_value,
            new_value=change.new_value,
            metadata={
                'change_type': change.change_type,
                'path': change.path
            }
        )
        self.tracer.trace_event(event)
        
    def trace_dependency_update(self, from_id: str, to_id: str) -> None:
        """Trace a dependency update."""
        event = ReactiveEvent(
            timestamp=time.time(),
            event_type='dependency_update',
            source_id=from_id,
            target_id=to_id
        )
        self.tracer.trace_event(event)
        
    def profile_operation(self, operation_name: str):
        """Context manager for profiling operations."""
        return ProfiledOperation(self.profiler, operation_name)
        
    def get_debug_report(self) -> Dict[str, Any]:
        """Get a comprehensive debug report."""
        return {
            'system_health': self.inspector.get_system_health(),
            'performance_metrics': self.profiler.get_performance_report(),
            'recent_events': self.tracer.get_events(limit=50),
            'dependency_graph': self.inspector.dependency_graph.visualize_graph(),
            'timestamp': time.time()
        }
        
    def export_debug_data(self, filepath: str) -> None:
        """Export debug data to a file."""
        debug_data = self.get_debug_report()
        
        try:
            with open(filepath, 'w') as f:
                json.dump(debug_data, f, indent=2, default=str)
            self.log(DebugLevel.INFO, f"Debug data exported to {filepath}")
        except Exception as e:
            self.log(DebugLevel.ERROR, f"Failed to export debug data: {e}")
            
    def visualize_dependencies(self, reactive_id: str) -> str:
        """Generate a text-based visualization of dependencies."""
        chain = self.inspector.get_dependency_chain(reactive_id)
        
        def format_chain(node: Dict[str, Any], indent: int = 0) -> str:
            prefix = "  " * indent
            result = f"{prefix}{node['id']}\n"
            
            if 'dependencies' in node:
                for dep in node['dependencies']:
                    result += format_chain(dep, indent + 1)
                    
            return result
            
        return format_chain(chain)


class ProfiledOperation:
    """Context manager for profiling operations."""
    
    def __init__(self, profiler: ReactiveProfiler, operation_name: str):
        self.profiler = profiler
        self.operation_name = operation_name
        
    def __enter__(self):
        self.profiler.start_operation(self.operation_name)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.profiler.end_operation(self.operation_name)


# Global debugger instance
_global_debugger: Optional[ReactiveDebugger] = None


def get_reactive_debugger() -> ReactiveDebugger:
    """Get the global reactive debugger instance."""
    global _global_debugger
    if _global_debugger is None:
        _global_debugger = ReactiveDebugger()
    return _global_debugger


def trace_reactive_change(reactive_id: str, change: ReactiveChange) -> None:
    """Convenience function to trace reactive changes."""
    get_reactive_debugger().trace_reactive_change(reactive_id, change)


def profile_reactive_operation(operation_name: str):
    """Convenience function to profile reactive operations."""
    return get_reactive_debugger().profile_operation(operation_name)


def debug_reactive_system() -> Dict[str, Any]:
    """Get a debug report for the reactive system."""
    return get_reactive_debugger().get_debug_report() 