#!/usr/bin/env python3
"""
Canvas System

Provides canvas and composition functionality for tinyDisplay including:
- Base canvas class for widget composition
- Z-order management for layering
- Positioning and bounds management
- Rendering coordination
"""

from .canvas import (
    Canvas,
    CanvasConfig,
    CanvasState,
    ZOrderManager
)

from .layering import (
    LayerManager,
    LayerInfo,
    LayerChange,
    LayerType,
    create_standard_layers,
    optimize_layer_z_orders
)

__all__ = [
    'Canvas',
    'CanvasConfig',
    'CanvasState', 
    'ZOrderManager',
    'LayerManager',
    'LayerInfo',
    'LayerChange',
    'LayerType',
    'create_standard_layers',
    'optimize_layer_z_orders'
]
