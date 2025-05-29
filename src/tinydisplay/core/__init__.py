#!/usr/bin/env python3
"""
Core Framework Components

Provides the foundational components for tinyDisplay including:
- High-performance ring buffer for data streams
- Reactive data binding system
- SQLite database integration
- Expression evaluation with asteval
- Performance monitoring utilities
"""

from .ring_buffer import (
    RingBuffer,
    BufferEntry,
    BufferFullError,
    BufferEmptyError
)

from .reactive import (
    ReactiveValue, ReactiveValueType, ReactiveChange, ReactiveCollection,
    ReactiveList, ReactiveDict, ReactiveBinding, DirectBinding, ComputedBinding,
    ExpressionBinding, StreamBinding, ReactiveDataManager, BindingType, BindingConfig,
    get_reactive_manager, start_reactive_system, stop_reactive_system
)

from .database import (
    ReactiveStateManager,
    DatabaseConfig,
    SerializationFormat,
    DatabaseError,
    ConnectionPoolError,
    SchemaError,
    get_db_connection
)

from .expressions import (
    ExpressionEvaluator,
    ExpressionError,
    SecurityError
)

from .dependencies import (
    DependencyGraph, DependencyEdge, DependencyType, DependencyStats,
    DependencyTracker, get_dependency_graph, get_dependency_tracker,
    reset_dependency_system
)

from .streams import (
    ReactiveDataStream, StreamManager, StreamType, StreamProcessingMode,
    StreamConfig, StreamStats, get_stream_manager, create_ring_buffer_stream,
    create_sqlite_stream, create_hybrid_stream
)

from .debug import (
    ReactiveDebugger, ReactiveTracer, ReactiveProfiler, ReactiveInspector,
    DebugLevel, ReactiveEvent, PerformanceMetrics, get_reactive_debugger,
    trace_reactive_change, profile_reactive_operation, debug_reactive_system
)

__all__ = [
    # Ring Buffer
    'RingBuffer',
    'BufferEntry',
    'BufferFullError',
    'BufferEmptyError',
    
    # Reactive System
    'ReactiveDataManager',
    'ReactiveBinding',
    'DirectBinding',
    'ComputedBinding',
    'ExpressionBinding',
    'StreamBinding',
    'BindingType',
    'BindingConfig',
    'get_reactive_manager',
    'start_reactive_system',
    'stop_reactive_system',
    
    # Database
    'ReactiveStateManager',
    'DatabaseConfig',
    'SerializationFormat',
    'DatabaseError',
    'ConnectionPoolError',
    'SchemaError',
    'get_db_connection',
    
    # Expressions
    'ExpressionEvaluator',
    'ExpressionError',
    'SecurityError',

    # Reactive Data Binding System (Story 2.3)
    'ReactiveValue',
    'ReactiveValueType',
    'ReactiveChange',
    'ReactiveCollection',
    'ReactiveList',
    'ReactiveDict',
    'ReactiveBinding',
    'DirectBinding',
    'ComputedBinding',
    'ExpressionBinding',
    'StreamBinding',
    'ReactiveDataManager',
    'BindingType',
    'BindingConfig',
    'get_reactive_manager',
    'start_reactive_system',
    'stop_reactive_system',

    # Dependencies
    'DependencyGraph',
    'DependencyEdge',
    'DependencyType',
    'DependencyStats',
    'DependencyTracker',
    'get_dependency_graph',
    'get_dependency_tracker',
    'reset_dependency_system',

    # Streams
    'ReactiveDataStream',
    'StreamManager',
    'StreamType',
    'StreamProcessingMode',
    'StreamConfig',
    'StreamStats',
    'get_stream_manager',
    'create_ring_buffer_stream',
    'create_sqlite_stream',
    'create_hybrid_stream',

    # Debug
    'ReactiveDebugger',
    'ReactiveTracer',
    'ReactiveProfiler',
    'ReactiveInspector',
    'DebugLevel',
    'ReactiveEvent',
    'PerformanceMetrics',
    'get_reactive_debugger',
    'trace_reactive_change',
    'profile_reactive_operation',
    'debug_reactive_system'
]
