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
    ReactiveDataManager,
    ReactiveBinding,
    DirectBinding,
    ComputedBinding,
    ExpressionBinding,
    StreamBinding,
    BindingType,
    BindingConfig,
    get_reactive_manager,
    start_reactive_system,
    stop_reactive_system
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
    'SecurityError'
]
