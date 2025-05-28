#!/usr/bin/env python3
"""
Rendering System

Provides the core rendering pipeline for tinyDisplay including:
- Rendering engine with frame timing
- Memory management for embedded devices
- Display adapter abstraction
- Performance monitoring and statistics
"""

from .engine import (
    RenderingEngine,
    RenderingConfig,
    RenderingState,
    FrameStats,
    FrameTimer,
    MemoryManager,
    DisplayAdapter
)

__all__ = [
    'RenderingEngine',
    'RenderingConfig',
    'RenderingState',
    'FrameStats',
    'FrameTimer',
    'MemoryManager',
    'DisplayAdapter'
]
