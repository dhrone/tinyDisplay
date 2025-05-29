#!/usr/bin/env python3
"""
Widget System

Provides the complete widget framework for tinyDisplay including:
- Abstract base classes for all widgets
- Reactive data binding capabilities
- Widget lifecycle management
- Container widgets for composition
- Widget pools for performance optimization
- Lifecycle event management and hooks
"""

from .base import (
    Widget,
    ContainerWidget,
    ReactiveValue,
    WidgetState,
    WidgetBounds,
    VisibilityState,
    VisibilityAnimation,
    TransparencyConfig
)

from .lifecycle import (
    LifecycleEvent,
    LifecycleEventInfo,
    WidgetPool,
    WidgetPoolConfig,
    LifecycleManager,
    get_lifecycle_manager,
    create_widget_pool,
    get_widget_pool,
    emit_lifecycle_event,
    register_global_lifecycle_hook,
    unregister_global_lifecycle_hook
)

from .lifecycle_integration import (
    LifecycleIntegratedWidget,
    LifecycleIntegratedContainerWidget,
    WidgetFactory,
    get_widget_factory,
    create_widget,
    release_widget,
    lifecycle_managed,
    with_lifecycle_hooks
)

from .text import (
    TextWidget,
    FontStyle,
    TextLayout,
    TextAlignment,
    TextWrap,
    FontCache
)

from .image import (
    ImageWidget,
    ImageStyle,
    ImageCache,
    ImageLoadResult,
    ScaleMode,
    ImageFormat,
    ImageFilter
)

from .progress import (
    ProgressBarWidget,
    ProgressStyle,
    ProgressAnimation,
    ProgressOrientation,
    ProgressTextPosition,
    EasingFunction,
    ProgressPrediction,
    ProgressDataPoint
)

from .shapes import (
    ShapeWidget,
    RectangleWidget,
    CircleWidget,
    LineWidget,
    ShapeStyle,
    GradientStop,
    FillPattern,
    StrokeStyle,
    LineCapStyle,
    LineJoinStyle
)

from .styling import (
    WidgetStyle,
    BorderStyle,
    BackgroundStyle,
    VisualEffect,
    Color,
    ColorFormat,
    BorderStyleType,
    BackgroundType,
    EffectType,
    GradientStop
)

from .performance import (
    PerformanceMetrics,
    WidgetPool as PerformanceWidgetPool,
    RenderOptimizer,
    MemoryManager,
    PerformanceMonitor,
    ReactiveOptimizer,
    PerformanceBenchmark,
    OptimizationLevel,
    get_performance_monitor,
    enable_performance_optimization,
    disable_performance_optimization
)

__all__ = [
    # Base widget classes
    'Widget',
    'ContainerWidget', 
    'ReactiveValue',
    'WidgetState',
    'WidgetBounds',
    'VisibilityState',
    'VisibilityAnimation',
    'TransparencyConfig',
    
    # Lifecycle management
    'LifecycleEvent',
    'LifecycleEventInfo',
    'WidgetPool',
    'WidgetPoolConfig',
    'LifecycleManager',
    'get_lifecycle_manager',
    'create_widget_pool',
    'get_widget_pool',
    'emit_lifecycle_event',
    'register_global_lifecycle_hook',
    'unregister_global_lifecycle_hook',
    
    # Lifecycle integration
    'LifecycleIntegratedWidget',
    'LifecycleIntegratedContainerWidget',
    'WidgetFactory',
    'get_widget_factory',
    'create_widget',
    'release_widget',
    'lifecycle_managed',
    'with_lifecycle_hooks',
    
    # Core widgets
    'TextWidget',
    'FontStyle',
    'TextLayout',
    'TextAlignment',
    'TextWrap',
    'FontCache',
    
    # Image widgets
    'ImageWidget',
    'ImageStyle',
    'ImageCache',
    'ImageLoadResult',
    'ScaleMode',
    'ImageFormat',
    'ImageFilter',
    
    # Progress widgets
    'ProgressBarWidget',
    'ProgressStyle',
    'ProgressAnimation',
    'ProgressOrientation',
    'ProgressTextPosition',
    'EasingFunction',
    'ProgressPrediction',
    'ProgressDataPoint',

    # Shape widgets
    'ShapeWidget',
    'RectangleWidget',
    'CircleWidget',
    'LineWidget',
    'ShapeStyle',
    'GradientStop',
    'FillPattern',
    'StrokeStyle',
    'LineCapStyle',
    'LineJoinStyle',

    # Styling
    'WidgetStyle',
    'BorderStyle',
    'BackgroundStyle',
    'VisualEffect',
    'Color',
    'ColorFormat',
    'BorderStyleType',
    'BackgroundType',
    'EffectType',
    'GradientStop',

    # Performance
    'PerformanceMetrics',
    'PerformanceWidgetPool',
    'RenderOptimizer',
    'MemoryManager',
    'PerformanceMonitor',
    'ReactiveOptimizer',
    'PerformanceBenchmark',
    'OptimizationLevel',
    'get_performance_monitor',
    'enable_performance_optimization',
    'disable_performance_optimization'
]
