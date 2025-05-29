#!/usr/bin/env python3
"""
Canvas System

Provides canvas and composition functionality for tinyDisplay including:
- Base canvas class for widget composition
- Z-order management for layering
- Positioning and bounds management
- Rendering coordination
- Advanced canvas composition features
- Coordinate transformation utilities
- Clipping and overflow management
- Layout managers for automatic positioning
- Viewport and scrolling support
- Canvas nesting and hierarchical layouts
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

from .transforms import (
    CoordinateMode,
    Position,
    CoordinateTransform,
    CoordinateValidator,
    create_absolute_position,
    create_relative_position,
    create_parent_relative_position
)

from .clipping import (
    ClippingMode,
    ClippingRegion,
    ClippingManager,
    OverflowDetector,
    ClippingOptimizer,
    create_clipping_region,
    clip_bounds_to_region
)

from .layouts import (
    LayoutDirection,
    Alignment,
    WrapMode,
    LayoutConstraints,
    LayoutMargin,
    LayoutManager,
    AbsoluteLayout,
    FlowLayout,
    GridLayout,
    FlexLayout,
    create_absolute_layout,
    create_flow_layout,
    create_grid_layout
)

from .viewport import (
    ScrollDirection,
    ScrollBehavior,
    ScrollBarVisibility,
    ViewportConfig,
    ScrollEvent,
    Viewport,
    ContentVirtualizer,
    create_viewport,
    create_virtualizing_viewport
)

from .nesting import (
    CanvasRelationship,
    CanvasTreeNode,
    NestedCanvas,
    CanvasHierarchyManager,
    get_hierarchy_manager,
    create_nested_canvas,
    find_common_ancestor
)

__all__ = [
    # Base canvas
    'Canvas',
    'CanvasConfig',
    'CanvasState', 
    'ZOrderManager',
    
    # Layering
    'LayerManager',
    'LayerInfo',
    'LayerChange',
    'LayerType',
    'create_standard_layers',
    'optimize_layer_z_orders',
    
    # Coordinate transformation
    'CoordinateMode',
    'Position',
    'CoordinateTransform',
    'CoordinateValidator',
    'create_absolute_position',
    'create_relative_position',
    'create_parent_relative_position',
    
    # Clipping
    'ClippingMode',
    'ClippingRegion',
    'ClippingManager',
    'OverflowDetector',
    'ClippingOptimizer',
    'create_clipping_region',
    'clip_bounds_to_region',
    
    # Layout managers
    'LayoutDirection',
    'Alignment',
    'WrapMode',
    'LayoutConstraints',
    'LayoutMargin',
    'LayoutManager',
    'AbsoluteLayout',
    'FlowLayout',
    'GridLayout',
    'FlexLayout',
    'create_absolute_layout',
    'create_flow_layout',
    'create_grid_layout',
    
    # Viewport and scrolling
    'ScrollDirection',
    'ScrollBehavior',
    'ScrollBarVisibility',
    'ViewportConfig',
    'ScrollEvent',
    'Viewport',
    'ContentVirtualizer',
    'create_viewport',
    'create_virtualizing_viewport',
    
    # Canvas nesting
    'CanvasRelationship',
    'CanvasTreeNode',
    'NestedCanvas',
    'CanvasHierarchyManager',
    'get_hierarchy_manager',
    'create_nested_canvas',
    'find_common_ancestor'
]
