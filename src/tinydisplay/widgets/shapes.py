#!/usr/bin/env python3
"""
Shape Widgets Implementation

Provides shape rendering widgets with reactive data binding, advanced styling,
and geometric operations for the tinyDisplay framework.
"""

from typing import Union, Optional, Tuple, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
import math
import threading

from .base import Widget, ReactiveValue, WidgetBounds
from ..core.reactive import ReactiveDataManager
from ..animation.tick_based import TickAnimationEngine, create_tick_fade_animation


class FillPattern(Enum):
    """Fill pattern types for shapes."""
    SOLID = "solid"
    GRADIENT_LINEAR = "gradient_linear"
    GRADIENT_RADIAL = "gradient_radial"
    PATTERN_DOTS = "pattern_dots"
    PATTERN_STRIPES = "pattern_stripes"
    PATTERN_CHECKERBOARD = "pattern_checkerboard"


class StrokeStyle(Enum):
    """Stroke style types for shape outlines."""
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"
    DASH_DOT = "dash_dot"


class LineCapStyle(Enum):
    """Line cap styles for line endings."""
    BUTT = "butt"
    ROUND = "round"
    SQUARE = "square"


class LineJoinStyle(Enum):
    """Line join styles for line connections."""
    MITER = "miter"
    ROUND = "round"
    BEVEL = "bevel"


@dataclass
class GradientStop:
    """Gradient color stop definition."""
    position: float  # 0.0 to 1.0
    color: Tuple[int, int, int]
    alpha: float = 1.0
    
    def __post_init__(self):
        """Validate gradient stop parameters."""
        if not 0.0 <= self.position <= 1.0:
            raise ValueError("Gradient position must be between 0.0 and 1.0")
        if not all(0 <= c <= 255 for c in self.color):
            raise ValueError("Color values must be between 0 and 255")
        if not 0.0 <= self.alpha <= 1.0:
            raise ValueError("Alpha must be between 0.0 and 1.0")


@dataclass
class ShapeStyle:
    """Comprehensive shape styling configuration."""
    # Fill properties
    fill_enabled: bool = True
    fill_color: Tuple[int, int, int] = (100, 150, 255)
    fill_alpha: float = 1.0
    fill_pattern: FillPattern = FillPattern.SOLID
    
    # Gradient properties (for gradient fills)
    gradient_stops: List[GradientStop] = None
    gradient_angle: float = 0.0  # Degrees for linear gradient
    gradient_center: Tuple[float, float] = (0.5, 0.5)  # Relative center for radial
    
    # Stroke properties
    stroke_enabled: bool = True
    stroke_color: Tuple[int, int, int] = (255, 255, 255)
    stroke_width: float = 1.0
    stroke_alpha: float = 1.0
    stroke_style: StrokeStyle = StrokeStyle.SOLID
    stroke_dash_pattern: List[float] = None  # [dash_length, gap_length, ...]
    
    # Line style properties
    line_cap: LineCapStyle = LineCapStyle.ROUND
    line_join: LineJoinStyle = LineJoinStyle.ROUND
    miter_limit: float = 10.0
    
    # Shadow properties
    shadow_enabled: bool = False
    shadow_offset: Tuple[float, float] = (2.0, 2.0)
    shadow_color: Tuple[int, int, int] = (0, 0, 0)
    shadow_alpha: float = 0.5
    shadow_blur: float = 2.0
    
    # Pattern properties
    pattern_size: float = 10.0
    pattern_spacing: float = 5.0
    pattern_color: Tuple[int, int, int] = (200, 200, 200)
    
    def __post_init__(self):
        """Validate shape style parameters."""
        if not all(0 <= c <= 255 for c in self.fill_color):
            raise ValueError("Fill color values must be between 0 and 255")
        if not all(0 <= c <= 255 for c in self.stroke_color):
            raise ValueError("Stroke color values must be between 0 and 255")
        if not all(0 <= c <= 255 for c in self.shadow_color):
            raise ValueError("Shadow color values must be between 0 and 255")
        if not all(0 <= c <= 255 for c in self.pattern_color):
            raise ValueError("Pattern color values must be between 0 and 255")
        if not 0.0 <= self.fill_alpha <= 1.0:
            raise ValueError("Fill alpha must be between 0.0 and 1.0")
        if not 0.0 <= self.stroke_alpha <= 1.0:
            raise ValueError("Stroke alpha must be between 0.0 and 1.0")
        if not 0.0 <= self.shadow_alpha <= 1.0:
            raise ValueError("Shadow alpha must be between 0.0 and 1.0")
        if self.stroke_width < 0:
            raise ValueError("Stroke width must be non-negative")
        if self.shadow_blur < 0:
            raise ValueError("Shadow blur must be non-negative")
        if self.miter_limit < 1.0:
            raise ValueError("Miter limit must be at least 1.0")
        if self.pattern_size <= 0:
            raise ValueError("Pattern size must be positive")
        if self.pattern_spacing < 0:
            raise ValueError("Pattern spacing must be non-negative")
        
        # Initialize default gradient stops if using gradient
        if (self.fill_pattern in (FillPattern.GRADIENT_LINEAR, FillPattern.GRADIENT_RADIAL) 
            and self.gradient_stops is None):
            self.gradient_stops = [
                GradientStop(0.0, self.fill_color),
                GradientStop(1.0, (255, 255, 255))
            ]


class ShapeWidget(Widget):
    """Base class for all shape widgets with common functionality."""
    
    __slots__ = ('_style', '_cached_bounds', '_bounds_dirty', '_style_lock')
    
    def __init__(self, style: Optional[ShapeStyle] = None, **kwargs):
        super().__init__(**kwargs)
        self._style = style or ShapeStyle()
        self._cached_bounds: Optional[WidgetBounds] = None
        self._bounds_dirty = True
        self._style_lock = threading.RLock()
    
    @property
    def style(self) -> ShapeStyle:
        """Get shape style configuration."""
        return self._style
    
    @style.setter
    def style(self, style: ShapeStyle) -> None:
        """Set shape style configuration."""
        with self._style_lock:
            self._style = style
            self._bounds_dirty = True
            self._mark_dirty()
    
    def set_fill_color(self, color: Tuple[int, int, int], alpha: float = 1.0) -> None:
        """Set fill color and alpha."""
        if not all(0 <= c <= 255 for c in color):
            raise ValueError("Color values must be between 0 and 255")
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("Alpha must be between 0.0 and 1.0")
        
        with self._style_lock:
            self._style.fill_color = color
            self._style.fill_alpha = alpha
            self._style.fill_enabled = True
            self._mark_dirty()
    
    def set_stroke(self, color: Tuple[int, int, int], width: float = 1.0, 
                   alpha: float = 1.0, style: StrokeStyle = StrokeStyle.SOLID) -> None:
        """Set stroke properties."""
        if not all(0 <= c <= 255 for c in color):
            raise ValueError("Color values must be between 0 and 255")
        if width < 0:
            raise ValueError("Stroke width must be non-negative")
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("Alpha must be between 0.0 and 1.0")
        
        with self._style_lock:
            self._style.stroke_color = color
            self._style.stroke_width = width
            self._style.stroke_alpha = alpha
            self._style.stroke_style = style
            self._style.stroke_enabled = width > 0
            self._bounds_dirty = True
            self._mark_dirty()
    
    def enable_shadow(self, enabled: bool = True, offset: Tuple[float, float] = (2.0, 2.0),
                     color: Tuple[int, int, int] = (0, 0, 0), alpha: float = 0.5,
                     blur: float = 2.0) -> None:
        """Enable or configure shadow effect."""
        if not all(0 <= c <= 255 for c in color):
            raise ValueError("Shadow color values must be between 0 and 255")
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("Shadow alpha must be between 0.0 and 1.0")
        if blur < 0:
            raise ValueError("Shadow blur must be non-negative")
        
        with self._style_lock:
            self._style.shadow_enabled = enabled
            if enabled:
                self._style.shadow_offset = offset
                self._style.shadow_color = color
                self._style.shadow_alpha = alpha
                self._style.shadow_blur = blur
            self._bounds_dirty = True
            self._mark_dirty()
    
    def set_gradient_fill(self, stops: List[GradientStop], 
                         pattern: FillPattern = FillPattern.GRADIENT_LINEAR,
                         angle: float = 0.0, center: Tuple[float, float] = (0.5, 0.5)) -> None:
        """Set gradient fill configuration."""
        if not stops:
            raise ValueError("Gradient must have at least one stop")
        if pattern not in (FillPattern.GRADIENT_LINEAR, FillPattern.GRADIENT_RADIAL):
            raise ValueError("Pattern must be a gradient type")
        
        with self._style_lock:
            self._style.fill_pattern = pattern
            self._style.gradient_stops = stops.copy()
            self._style.gradient_angle = angle
            self._style.gradient_center = center
            self._style.fill_enabled = True
            self._mark_dirty()
    
    def get_shape_bounds(self) -> WidgetBounds:
        """Get the bounds of the shape including stroke and shadow."""
        if self._bounds_dirty or self._cached_bounds is None:
            self._cached_bounds = self._calculate_shape_bounds()
            self._bounds_dirty = False
        return self._cached_bounds
    
    def _calculate_shape_bounds(self) -> WidgetBounds:
        """Calculate shape bounds - implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _calculate_shape_bounds")
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is inside the shape."""
        # Default implementation uses bounding box
        bounds = self.get_shape_bounds()
        return bounds.contains_point(x, y)
    
    def intersects_bounds(self, bounds: WidgetBounds) -> bool:
        """Check if shape intersects with given bounds."""
        shape_bounds = self.get_shape_bounds()
        return shape_bounds.intersects(bounds)
    
    def render(self, canvas: 'Canvas') -> None:
        """Render the shape widget to the canvas."""
        if not self.visible or self.alpha <= 0:
            return
        
        # Render shadow first (if enabled)
        if self._style.shadow_enabled:
            self._render_shadow(canvas)
        
        # Render fill
        if self._style.fill_enabled:
            self._render_fill(canvas)
        
        # Render stroke
        if self._style.stroke_enabled and self._style.stroke_width > 0:
            self._render_stroke(canvas)
        
        # Mark as clean
        self.mark_clean()
    
    def _render_shadow(self, canvas: 'Canvas') -> None:
        """Render shape shadow - implemented by subclasses."""
        pass
    
    def _render_fill(self, canvas: 'Canvas') -> None:
        """Render shape fill - implemented by subclasses."""
        pass
    
    def _render_stroke(self, canvas: 'Canvas') -> None:
        """Render shape stroke - implemented by subclasses."""
        pass

    # Tick-based animation methods
    def fade_in_animated(self, duration_ticks: int = 30, easing: str = "ease_out",
                        on_complete: Optional[Callable] = None) -> bool:
        """Animate shape fade in using tick-based animation.
        
        Args:
            duration_ticks: Animation duration in ticks (default 30 = 0.5s at 60fps)
            easing: Easing function name
            on_complete: Callback when animation completes
            
        Returns:
            True if animation started successfully
        """
        return self.start_tick_based_animation(
            animation_type='fade_in',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            easing=easing,
            on_complete=on_complete
        )
    
    def fade_out_animated(self, duration_ticks: int = 30, easing: str = "ease_in",
                         on_complete: Optional[Callable] = None) -> bool:
        """Animate shape fade out using tick-based animation.
        
        Args:
            duration_ticks: Animation duration in ticks (default 30 = 0.5s at 60fps)
            easing: Easing function name
            on_complete: Callback when animation completes
            
        Returns:
            True if animation started successfully
        """
        return self.start_tick_based_animation(
            animation_type='fade_out',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            easing=easing,
            on_complete=on_complete
        )
    
    def set_fill_color_animated(self, target_color: Tuple[int, int, int], 
                               duration_ticks: int = 60, easing: str = "ease_in_out",
                               on_complete: Optional[Callable] = None) -> bool:
        """Animate fill color transition using tick-based animation.
        
        Args:
            target_color: Target RGB color tuple
            duration_ticks: Animation duration in ticks (default 60 = 1s at 60fps)
            easing: Easing function name
            on_complete: Callback when animation completes
            
        Returns:
            True if animation started successfully
        """
        if not all(0 <= c <= 255 for c in target_color):
            raise ValueError("Color values must be between 0 and 255")
        
        current_color = self._style.fill_color
        
        return self.start_tick_based_animation(
            animation_type='fill_color_transition',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            start_color=current_color,
            target_color=target_color,
            easing=easing,
            on_complete=on_complete
        )
    
    def set_stroke_color_animated(self, target_color: Tuple[int, int, int],
                                 duration_ticks: int = 60, easing: str = "ease_in_out",
                                 on_complete: Optional[Callable] = None) -> bool:
        """Animate stroke color transition using tick-based animation.
        
        Args:
            target_color: Target RGB color tuple
            duration_ticks: Animation duration in ticks (default 60 = 1s at 60fps)
            easing: Easing function name
            on_complete: Callback when animation completes
            
        Returns:
            True if animation started successfully
        """
        if not all(0 <= c <= 255 for c in target_color):
            raise ValueError("Color values must be between 0 and 255")
        
        current_color = self._style.stroke_color
        
        return self.start_tick_based_animation(
            animation_type='stroke_color_transition',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            start_color=current_color,
            target_color=target_color,
            easing=easing,
            on_complete=on_complete
        )
    
    def set_fill_alpha_animated(self, target_alpha: float, duration_ticks: int = 60,
                               easing: str = "ease_in_out", 
                               on_complete: Optional[Callable] = None) -> bool:
        """Animate fill alpha transition using tick-based animation.
        
        Args:
            target_alpha: Target alpha value (0.0 to 1.0)
            duration_ticks: Animation duration in ticks (default 60 = 1s at 60fps)
            easing: Easing function name
            on_complete: Callback when animation completes
            
        Returns:
            True if animation started successfully
        """
        if not 0.0 <= target_alpha <= 1.0:
            raise ValueError("Alpha must be between 0.0 and 1.0")
        
        current_alpha = self._style.fill_alpha
        
        return self.start_tick_based_animation(
            animation_type='fill_alpha_transition',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            start_alpha=current_alpha,
            target_alpha=target_alpha,
            easing=easing,
            on_complete=on_complete
        )
    
    def set_stroke_width_animated(self, target_width: float, duration_ticks: int = 60,
                                 easing: str = "ease_in_out",
                                 on_complete: Optional[Callable] = None) -> bool:
        """Animate stroke width transition using tick-based animation.
        
        Args:
            target_width: Target stroke width
            duration_ticks: Animation duration in ticks (default 60 = 1s at 60fps)
            easing: Easing function name
            on_complete: Callback when animation completes
            
        Returns:
            True if animation started successfully
        """
        if target_width < 0:
            raise ValueError("Stroke width must be non-negative")
        
        current_width = self._style.stroke_width
        
        return self.start_tick_based_animation(
            animation_type='stroke_width_transition',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            start_width=current_width,
            target_width=target_width,
            easing=easing,
            on_complete=on_complete
        )
    
    def _apply_animation_progress(self, progress: float) -> None:
        """Apply animation progress to shape widget properties.
        
        Args:
            progress: Animation progress from 0.0 to 1.0
        """
        # Call parent implementation for base animations (alpha, etc.)
        super()._apply_animation_progress(progress)
        
        if not self._current_animation:
            return
        
        animation_type = self._current_animation['type']
        
        if animation_type == 'fill_color_transition':
            # Interpolate between start and target fill colors
            start_color = self._current_animation['start_color']
            target_color = self._current_animation['target_color']
            
            current_color = tuple(
                int(start_color[i] + (target_color[i] - start_color[i]) * progress)
                for i in range(3)
            )
            
            with self._style_lock:
                self._style.fill_color = current_color
                self._mark_dirty()
                
        elif animation_type == 'stroke_color_transition':
            # Interpolate between start and target stroke colors
            start_color = self._current_animation['start_color']
            target_color = self._current_animation['target_color']
            
            current_color = tuple(
                int(start_color[i] + (target_color[i] - start_color[i]) * progress)
                for i in range(3)
            )
            
            with self._style_lock:
                self._style.stroke_color = current_color
                self._mark_dirty()
                
        elif animation_type == 'fill_alpha_transition':
            # Interpolate between start and target fill alpha
            start_alpha = self._current_animation['start_alpha']
            target_alpha = self._current_animation['target_alpha']
            
            current_alpha = start_alpha + (target_alpha - start_alpha) * progress
            
            with self._style_lock:
                self._style.fill_alpha = current_alpha
                self._mark_dirty()
                
        elif animation_type == 'stroke_width_transition':
            # Interpolate between start and target stroke width
            start_width = self._current_animation['start_width']
            target_width = self._current_animation['target_width']
            
            current_width = start_width + (target_width - start_width) * progress
            
            with self._style_lock:
                self._style.stroke_width = current_width
                self._style.stroke_enabled = current_width > 0
                self._bounds_dirty = True
                self._mark_dirty()
    
    def _complete_animation(self) -> None:
        """Complete the current animation and finalize shape properties."""
        if not self._current_animation:
            return
        
        animation_type = self._current_animation['type']
        
        with self._style_lock:
            if animation_type == 'fill_color_transition':
                # Set final fill color
                self._style.fill_color = self._current_animation['target_color']
                
            elif animation_type == 'stroke_color_transition':
                # Set final stroke color
                self._style.stroke_color = self._current_animation['target_color']
                
            elif animation_type == 'fill_alpha_transition':
                # Set final fill alpha
                self._style.fill_alpha = self._current_animation['target_alpha']
                
            elif animation_type == 'stroke_width_transition':
                # Set final stroke width
                target_width = self._current_animation['target_width']
                self._style.stroke_width = target_width
                self._style.stroke_enabled = target_width > 0
                self._bounds_dirty = True
        
        # Call parent implementation to handle completion
        super()._complete_animation()


class RectangleWidget(ShapeWidget):
    """Rectangle shape widget with reactive dimensions and styling."""
    
    __slots__ = ('_width', '_height', '_corner_radius')
    
    def __init__(
        self,
        width: Union[float, ReactiveValue],
        height: Union[float, ReactiveValue],
        corner_radius: Union[float, ReactiveValue] = 0.0,
        style: Optional[ShapeStyle] = None,
        **kwargs
    ):
        super().__init__(style=style, **kwargs)
        
        # Reactive dimensions
        self._width = self._ensure_reactive(width)
        self._height = self._ensure_reactive(height)
        self._corner_radius = self._ensure_reactive(corner_radius)
        
        # Bind to reactive updates
        self._width.bind(self._on_dimension_changed)
        self._height.bind(self._on_dimension_changed)
        self._corner_radius.bind(self._on_dimension_changed)
        
        # Validate initial values
        self._validate_dimensions()
    
    @property
    def width(self) -> float:
        """Get rectangle width."""
        return self._width.value
    
    @width.setter
    def width(self, value: Union[float, ReactiveValue]) -> None:
        """Set rectangle width."""
        if isinstance(value, ReactiveValue):
            self._width.unbind(self._on_dimension_changed)
            self._width = value
            self._width.bind(self._on_dimension_changed)
        else:
            self._width.value = value
        self._validate_dimensions()
        self._bounds_dirty = True
        self._mark_dirty()
    
    @property
    def height(self) -> float:
        """Get rectangle height."""
        return self._height.value
    
    @height.setter
    def height(self, value: Union[float, ReactiveValue]) -> None:
        """Set rectangle height."""
        if isinstance(value, ReactiveValue):
            self._height.unbind(self._on_dimension_changed)
            self._height = value
            self._height.bind(self._on_dimension_changed)
        else:
            self._height.value = value
        self._validate_dimensions()
        self._bounds_dirty = True
        self._mark_dirty()
    
    @property
    def corner_radius(self) -> float:
        """Get corner radius."""
        return self._corner_radius.value
    
    @corner_radius.setter
    def corner_radius(self, value: Union[float, ReactiveValue]) -> None:
        """Set corner radius."""
        if isinstance(value, ReactiveValue):
            self._corner_radius.unbind(self._on_dimension_changed)
            self._corner_radius = value
            self._corner_radius.bind(self._on_dimension_changed)
        else:
            self._corner_radius.value = value
        self._validate_dimensions()
        self._bounds_dirty = True
        self._mark_dirty()
    
    def _ensure_reactive(self, value: Union[float, ReactiveValue]) -> ReactiveValue:
        """Convert numeric values to ReactiveValue instances."""
        if isinstance(value, ReactiveValue):
            return value
        return ReactiveValue(float(value))
    
    def _validate_dimensions(self) -> None:
        """Validate rectangle dimensions."""
        if self.width < 0:
            raise ValueError("Rectangle width must be non-negative")
        if self.height < 0:
            raise ValueError("Rectangle height must be non-negative")
        if self.corner_radius < 0:
            raise ValueError("Corner radius must be non-negative")
        
        # Corner radius cannot exceed half the smaller dimension
        max_radius = min(self.width, self.height) / 2
        if self.corner_radius > max_radius:
            raise ValueError(f"Corner radius cannot exceed {max_radius} for current dimensions")
    
    def _on_dimension_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle reactive dimension updates."""
        self._validate_dimensions()
        self._bounds_dirty = True
        self._mark_dirty()
    
    def _calculate_shape_bounds(self) -> WidgetBounds:
        """Calculate rectangle bounds including stroke and shadow."""
        x, y = self.position
        width = self.width
        height = self.height
        
        # Account for stroke width
        stroke_offset = self._style.stroke_width / 2 if self._style.stroke_enabled else 0
        
        # Account for shadow
        shadow_offset_x = shadow_offset_y = 0
        if self._style.shadow_enabled:
            shadow_offset_x = abs(self._style.shadow_offset[0]) + self._style.shadow_blur
            shadow_offset_y = abs(self._style.shadow_offset[1]) + self._style.shadow_blur
        
        # Calculate total bounds
        total_x = x - stroke_offset - shadow_offset_x
        total_y = y - stroke_offset - shadow_offset_y
        total_width = width + 2 * stroke_offset + shadow_offset_x
        total_height = height + 2 * stroke_offset + shadow_offset_y
        
        return WidgetBounds(total_x, total_y, total_width, total_height)
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is inside the rectangle (considering corner radius)."""
        rect_x, rect_y = self.position
        
        # Quick bounds check
        if not (rect_x <= x <= rect_x + self.width and rect_y <= y <= rect_y + self.height):
            return False
        
        # If no corner radius, simple rectangle check
        if self.corner_radius <= 0:
            return True
        
        # Check corner radius regions
        radius = self.corner_radius
        
        # Define corner regions
        corners = [
            (rect_x + radius, rect_y + radius),  # Top-left
            (rect_x + self.width - radius, rect_y + radius),  # Top-right
            (rect_x + radius, rect_y + self.height - radius),  # Bottom-left
            (rect_x + self.width - radius, rect_y + self.height - radius)  # Bottom-right
        ]
        
        # Check if point is in a corner region
        for corner_x, corner_y in corners:
            if (abs(x - corner_x) <= radius and abs(y - corner_y) <= radius):
                # Check if point is within the corner circle
                distance = math.sqrt((x - corner_x) ** 2 + (y - corner_y) ** 2)
                return distance <= radius
        
        return True
    
    def _render_fill(self, canvas: 'Canvas') -> None:
        """Render rectangle fill."""
        # Placeholder for canvas integration
        pass
    
    def _render_stroke(self, canvas: 'Canvas') -> None:
        """Render rectangle stroke."""
        # Placeholder for canvas integration
        pass
    
    def _render_shadow(self, canvas: 'Canvas') -> None:
        """Render rectangle shadow."""
        # Placeholder for canvas integration
        pass
    
    def __repr__(self) -> str:
        return f"RectangleWidget(id={self.widget_id}, size=({self.width}x{self.height}), pos={self.position})"
    
    # Rectangle-specific tick-based animation methods
    def set_width_animated(self, target_width: float, duration_ticks: int = 60,
                          easing: str = "ease_in_out", on_complete: Optional[Callable] = None) -> bool:
        """Animate rectangle width using tick-based animation.
        
        Args:
            target_width: Target width value
            duration_ticks: Animation duration in ticks (default 60 = 1s at 60fps)
            easing: Easing function name
            on_complete: Callback when animation completes
            
        Returns:
            True if animation started successfully
        """
        if target_width <= 0:
            raise ValueError("Width must be positive")
        
        current_width = self.width
        
        return self.start_tick_based_animation(
            animation_type='width_transition',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            start_width=current_width,
            target_width=target_width,
            easing=easing,
            on_complete=on_complete
        )
    
    def set_height_animated(self, target_height: float, duration_ticks: int = 60,
                           easing: str = "ease_in_out", on_complete: Optional[Callable] = None) -> bool:
        """Animate rectangle height using tick-based animation.
        
        Args:
            target_height: Target height value
            duration_ticks: Animation duration in ticks (default 60 = 1s at 60fps)
            easing: Easing function name
            on_complete: Callback when animation completes
            
        Returns:
            True if animation started successfully
        """
        if target_height <= 0:
            raise ValueError("Height must be positive")
        
        current_height = self.height
        
        return self.start_tick_based_animation(
            animation_type='height_transition',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            start_height=current_height,
            target_height=target_height,
            easing=easing,
            on_complete=on_complete
        )
    
    def set_size_animated(self, target_width: float, target_height: float, 
                         duration_ticks: int = 60, easing: str = "ease_in_out",
                         on_complete: Optional[Callable] = None) -> bool:
        """Animate rectangle size (width and height) using tick-based animation.
        
        Args:
            target_width: Target width value
            target_height: Target height value
            duration_ticks: Animation duration in ticks (default 60 = 1s at 60fps)
            easing: Easing function name
            on_complete: Callback when animation completes
            
        Returns:
            True if animation started successfully
        """
        if target_width <= 0 or target_height <= 0:
            raise ValueError("Width and height must be positive")
        
        current_width = self.width
        current_height = self.height
        
        return self.start_tick_based_animation(
            animation_type='size_transition',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            start_width=current_width,
            start_height=current_height,
            target_width=target_width,
            target_height=target_height,
            easing=easing,
            on_complete=on_complete
        )
    
    def set_corner_radius_animated(self, target_radius: float, duration_ticks: int = 60,
                                  easing: str = "ease_in_out", 
                                  on_complete: Optional[Callable] = None) -> bool:
        """Animate corner radius using tick-based animation.
        
        Args:
            target_radius: Target corner radius value
            duration_ticks: Animation duration in ticks (default 60 = 1s at 60fps)
            easing: Easing function name
            on_complete: Callback when animation completes
            
        Returns:
            True if animation started successfully
        """
        if target_radius < 0:
            raise ValueError("Corner radius must be non-negative")
        
        current_radius = self.corner_radius
        
        return self.start_tick_based_animation(
            animation_type='corner_radius_transition',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            start_radius=current_radius,
            target_radius=target_radius,
            easing=easing,
            on_complete=on_complete
        )
    
    def _apply_animation_progress(self, progress: float) -> None:
        """Apply animation progress to rectangle properties.
        
        Args:
            progress: Animation progress from 0.0 to 1.0
        """
        # Call parent implementation for base shape animations
        super()._apply_animation_progress(progress)
        
        if not self._current_animation:
            return
        
        animation_type = self._current_animation['type']
        
        if animation_type == 'width_transition':
            # Interpolate between start and target width
            start_width = self._current_animation['start_width']
            target_width = self._current_animation['target_width']
            
            current_width = start_width + (target_width - start_width) * progress
            self._width.value = current_width
            
        elif animation_type == 'height_transition':
            # Interpolate between start and target height
            start_height = self._current_animation['start_height']
            target_height = self._current_animation['target_height']
            
            current_height = start_height + (target_height - start_height) * progress
            self._height.value = current_height
            
        elif animation_type == 'size_transition':
            # Interpolate both width and height
            start_width = self._current_animation['start_width']
            start_height = self._current_animation['start_height']
            target_width = self._current_animation['target_width']
            target_height = self._current_animation['target_height']
            
            current_width = start_width + (target_width - start_width) * progress
            current_height = start_height + (target_height - start_height) * progress
            
            self._width.value = current_width
            self._height.value = current_height
            
        elif animation_type == 'corner_radius_transition':
            # Interpolate between start and target corner radius
            start_radius = self._current_animation['start_radius']
            target_radius = self._current_animation['target_radius']
            
            current_radius = start_radius + (target_radius - start_radius) * progress
            self._corner_radius.value = current_radius
    
    def _complete_animation(self) -> None:
        """Complete the current animation and finalize rectangle properties."""
        if not self._current_animation:
            return
        
        animation_type = self._current_animation['type']
        
        if animation_type == 'width_transition':
            # Set final width
            self._width.value = self._current_animation['target_width']
            
        elif animation_type == 'height_transition':
            # Set final height
            self._height.value = self._current_animation['target_height']
            
        elif animation_type == 'size_transition':
            # Set final size
            self._width.value = self._current_animation['target_width']
            self._height.value = self._current_animation['target_height']
            
        elif animation_type == 'corner_radius_transition':
            # Set final corner radius
            self._corner_radius.value = self._current_animation['target_radius']
        
        # Call parent implementation to handle completion
        super()._complete_animation()


class CircleWidget(ShapeWidget):
    """Circle shape widget with reactive radius and styling."""
    
    __slots__ = ('_radius',)
    
    def __init__(
        self,
        radius: Union[float, ReactiveValue],
        style: Optional[ShapeStyle] = None,
        **kwargs
    ):
        super().__init__(style=style, **kwargs)
        
        # Reactive radius
        self._radius = self._ensure_reactive(radius)
        self._radius.bind(self._on_radius_changed)
        
        # Validate initial value
        self._validate_radius()
    
    @property
    def radius(self) -> float:
        """Get circle radius."""
        return self._radius.value
    
    @radius.setter
    def radius(self, value: Union[float, ReactiveValue]) -> None:
        """Set circle radius."""
        if isinstance(value, ReactiveValue):
            self._radius.unbind(self._on_radius_changed)
            self._radius = value
            self._radius.bind(self._on_radius_changed)
        else:
            self._radius.value = value
        self._validate_radius()
        self._bounds_dirty = True
        self._mark_dirty()
    
    @property
    def diameter(self) -> float:
        """Get circle diameter."""
        return self.radius * 2
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get circle center point."""
        x, y = self.position
        return (x + self.radius, y + self.radius)
    
    def _ensure_reactive(self, value: Union[float, ReactiveValue]) -> ReactiveValue:
        """Convert numeric values to ReactiveValue instances."""
        if isinstance(value, ReactiveValue):
            return value
        return ReactiveValue(float(value))
    
    def _validate_radius(self) -> None:
        """Validate circle radius."""
        if self.radius < 0:
            raise ValueError("Circle radius must be non-negative")
    
    def _on_radius_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle reactive radius updates."""
        self._validate_radius()
        self._bounds_dirty = True
        self._mark_dirty()
    
    def _calculate_shape_bounds(self) -> WidgetBounds:
        """Calculate circle bounds including stroke and shadow."""
        x, y = self.position
        radius = self.radius
        
        # Account for stroke width
        stroke_offset = self._style.stroke_width / 2 if self._style.stroke_enabled else 0
        
        # Account for shadow
        shadow_offset_x = shadow_offset_y = 0
        if self._style.shadow_enabled:
            shadow_offset_x = abs(self._style.shadow_offset[0]) + self._style.shadow_blur
            shadow_offset_y = abs(self._style.shadow_offset[1]) + self._style.shadow_blur
        
        # Calculate total bounds
        total_radius = radius + stroke_offset
        total_x = x - stroke_offset - shadow_offset_x
        total_y = y - stroke_offset - shadow_offset_y
        total_size = (total_radius * 2) + shadow_offset_x + shadow_offset_y
        
        return WidgetBounds(total_x, total_y, total_size, total_size)
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is inside the circle."""
        center_x, center_y = self.center
        distance = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
        return distance <= self.radius
    
    def _render_fill(self, canvas: 'Canvas') -> None:
        """Render circle fill."""
        # Placeholder for canvas integration
        pass
    
    def _render_stroke(self, canvas: 'Canvas') -> None:
        """Render circle stroke."""
        # Placeholder for canvas integration
        pass
    
    def _render_shadow(self, canvas: 'Canvas') -> None:
        """Render circle shadow."""
        # Placeholder for canvas integration
        pass
    
    def __repr__(self) -> str:
        return (f"CircleWidget(id={self.widget_id}, radius={self.radius}, "
                f"center={self.center}, visible={self.visible})")


class LineWidget(ShapeWidget):
    """Line shape widget with reactive endpoints and styling."""
    
    __slots__ = ('_start_point', '_end_point')
    
    def __init__(
        self,
        start_point: Union[Tuple[float, float], ReactiveValue],
        end_point: Union[Tuple[float, float], ReactiveValue],
        style: Optional[ShapeStyle] = None,
        **kwargs
    ):
        super().__init__(style=style, **kwargs)
        
        # Reactive endpoints
        self._start_point = self._ensure_reactive(start_point)
        self._end_point = self._ensure_reactive(end_point)
        
        # Bind to reactive updates
        self._start_point.bind(self._on_endpoint_changed)
        self._end_point.bind(self._on_endpoint_changed)
        
        # Validate initial values
        self._validate_endpoints()
    
    @property
    def start_point(self) -> Tuple[float, float]:
        """Get line start point."""
        return self._start_point.value
    
    @start_point.setter
    def start_point(self, value: Union[Tuple[float, float], ReactiveValue]) -> None:
        """Set line start point."""
        if isinstance(value, ReactiveValue):
            self._start_point.unbind(self._on_endpoint_changed)
            self._start_point = value
            self._start_point.bind(self._on_endpoint_changed)
        else:
            self._start_point.value = value
        self._validate_endpoints()
        self._bounds_dirty = True
        self._mark_dirty()
    
    @property
    def end_point(self) -> Tuple[float, float]:
        """Get line end point."""
        return self._end_point.value
    
    @end_point.setter
    def end_point(self, value: Union[Tuple[float, float], ReactiveValue]) -> None:
        """Set line end point."""
        if isinstance(value, ReactiveValue):
            self._end_point.unbind(self._on_endpoint_changed)
            self._end_point = value
            self._end_point.bind(self._on_endpoint_changed)
        else:
            self._end_point.value = value
        self._validate_endpoints()
        self._bounds_dirty = True
        self._mark_dirty()
    
    @property
    def length(self) -> float:
        """Get line length."""
        x1, y1 = self.start_point
        x2, y2 = self.end_point
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    @property
    def angle(self) -> float:
        """Get line angle in radians."""
        x1, y1 = self.start_point
        x2, y2 = self.end_point
        return math.atan2(y2 - y1, x2 - x1)
    
    @property
    def angle_degrees(self) -> float:
        """Get line angle in degrees."""
        return math.degrees(self.angle)
    
    def _ensure_reactive(self, value: Union[Tuple[float, float], ReactiveValue]) -> ReactiveValue:
        """Convert tuple values to ReactiveValue instances."""
        if isinstance(value, ReactiveValue):
            return value
        if isinstance(value, (tuple, list)) and len(value) == 2:
            try:
                return ReactiveValue((float(value[0]), float(value[1])))
            except (TypeError, ValueError):
                raise ValueError("Point coordinates must be numeric")
        raise ValueError("Point must be a tuple of two numbers or ReactiveValue")
    
    def _validate_endpoints(self) -> None:
        """Validate line endpoints."""
        start = self.start_point
        end = self.end_point
        
        if not (isinstance(start, (tuple, list)) and len(start) == 2):
            raise ValueError("Start point must be a tuple of two numbers")
        if not (isinstance(end, (tuple, list)) and len(end) == 2):
            raise ValueError("End point must be a tuple of two numbers")
        
        # Check for valid numeric values
        try:
            float(start[0]), float(start[1])
            float(end[0]), float(end[1])
        except (TypeError, ValueError):
            raise ValueError("Point coordinates must be numeric")
    
    def _on_endpoint_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle reactive endpoint updates."""
        self._validate_endpoints()
        self._bounds_dirty = True
        self._mark_dirty()
    
    def _calculate_shape_bounds(self) -> WidgetBounds:
        """Calculate line bounds including stroke and shadow."""
        x1, y1 = self.start_point
        x2, y2 = self.end_point
        
        # Basic line bounds
        min_x = min(x1, x2)
        max_x = max(x1, x2)
        min_y = min(y1, y2)
        max_y = max(y1, y2)
        
        # Account for stroke width
        stroke_offset = self._style.stroke_width / 2 if self._style.stroke_enabled else 0
        
        # Account for shadow
        shadow_offset_x = shadow_offset_y = 0
        if self._style.shadow_enabled:
            shadow_offset_x = abs(self._style.shadow_offset[0]) + self._style.shadow_blur
            shadow_offset_y = abs(self._style.shadow_offset[1]) + self._style.shadow_blur
        
        # Calculate total bounds
        total_x = min_x - stroke_offset - shadow_offset_x
        total_y = min_y - stroke_offset - shadow_offset_y
        total_width = (max_x - min_x) + 2 * stroke_offset + shadow_offset_x
        total_height = (max_y - min_y) + 2 * stroke_offset + shadow_offset_y
        
        # Ensure minimum size for zero-length lines
        total_width = max(total_width, 2 * stroke_offset + shadow_offset_x)
        total_height = max(total_height, 2 * stroke_offset + shadow_offset_y)
        
        return WidgetBounds(total_x, total_y, total_width, total_height)
    
    def contains_point(self, x: float, y: float, tolerance: float = 5.0) -> bool:
        """Check if point is near the line within tolerance."""
        x1, y1 = self.start_point
        x2, y2 = self.end_point
        
        # Calculate distance from point to line segment
        line_length_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
        
        if line_length_sq == 0:
            # Line is a point
            distance = math.sqrt((x - x1) ** 2 + (y - y1) ** 2)
        else:
            # Calculate projection of point onto line
            t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / line_length_sq))
            projection_x = x1 + t * (x2 - x1)
            projection_y = y1 + t * (y2 - y1)
            distance = math.sqrt((x - projection_x) ** 2 + (y - projection_y) ** 2)
        
        # Include stroke width in tolerance
        effective_tolerance = tolerance + (self._style.stroke_width / 2 if self._style.stroke_enabled else 0)
        return distance <= effective_tolerance
    
    def _render_fill(self, canvas: 'Canvas') -> None:
        """Lines don't have fill - skip."""
        pass
    
    def _render_stroke(self, canvas: 'Canvas') -> None:
        """Render line stroke."""
        # Placeholder for canvas integration
        pass
    
    def _render_shadow(self, canvas: 'Canvas') -> None:
        """Render line shadow."""
        # Placeholder for canvas integration
        pass
    
    def __repr__(self) -> str:
        return (f"LineWidget(id={self.widget_id}, start={self.start_point}, end={self.end_point}, "
                f"length={self.length:.1f}, angle={self.angle_degrees:.1f}°, visible={self.visible})") 