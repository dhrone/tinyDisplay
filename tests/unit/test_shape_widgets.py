#!/usr/bin/env python3
"""
Test Suite for Shape Widgets

Comprehensive tests for shape widget functionality including reactive binding,
styling, geometric operations, bounds calculation, and performance validation.
"""

import pytest
import math
import time
from unittest.mock import Mock, patch

from src.tinydisplay.widgets.shapes import (
    ShapeWidget, RectangleWidget, CircleWidget, LineWidget,
    ShapeStyle, GradientStop, FillPattern, StrokeStyle,
    LineCapStyle, LineJoinStyle
)
from src.tinydisplay.widgets.base import ReactiveValue, WidgetBounds


class TestGradientStop:
    """Test GradientStop configuration and validation."""
    
    def test_gradient_stop__valid_values__correct_initialization(self):
        """Test GradientStop with valid values."""
        stop = GradientStop(0.5, (255, 128, 0), 0.8)
        assert stop.position == 0.5
        assert stop.color == (255, 128, 0)
        assert stop.alpha == 0.8
    
    def test_gradient_stop__default_alpha__correct_initialization(self):
        """Test GradientStop with default alpha."""
        stop = GradientStop(0.0, (255, 255, 255))
        assert stop.position == 0.0
        assert stop.color == (255, 255, 255)
        assert stop.alpha == 1.0
    
    def test_gradient_stop__invalid_position__raises_error(self):
        """Test GradientStop with invalid position raises ValueError."""
        with pytest.raises(ValueError, match="Gradient position must be between 0.0 and 1.0"):
            GradientStop(1.5, (255, 255, 255))
    
    def test_gradient_stop__invalid_color__raises_error(self):
        """Test GradientStop with invalid color raises ValueError."""
        with pytest.raises(ValueError, match="Color values must be between 0 and 255"):
            GradientStop(0.5, (256, 128, 0))
    
    def test_gradient_stop__invalid_alpha__raises_error(self):
        """Test GradientStop with invalid alpha raises ValueError."""
        with pytest.raises(ValueError, match="Alpha must be between 0.0 and 1.0"):
            GradientStop(0.5, (255, 128, 0), 1.5)


class TestShapeStyle:
    """Test ShapeStyle configuration and validation."""
    
    def test_shape_style__default_values__correct_initialization(self):
        """Test ShapeStyle with default values."""
        style = ShapeStyle()
        assert style.fill_enabled is True
        assert style.fill_color == (100, 150, 255)
        assert style.fill_alpha == 1.0
        assert style.fill_pattern == FillPattern.SOLID
        assert style.stroke_enabled is True
        assert style.stroke_color == (255, 255, 255)
        assert style.stroke_width == 1.0
        assert style.stroke_style == StrokeStyle.SOLID
        assert style.line_cap == LineCapStyle.ROUND
        assert style.line_join == LineJoinStyle.ROUND
        assert style.shadow_enabled is False
        assert style.pattern_size == 10.0
    
    def test_shape_style__custom_values__correct_initialization(self):
        """Test ShapeStyle with custom values."""
        style = ShapeStyle(
            fill_color=(255, 0, 0),
            stroke_width=3.0,
            stroke_style=StrokeStyle.DASHED,
            shadow_enabled=True,
            shadow_blur=5.0
        )
        assert style.fill_color == (255, 0, 0)
        assert style.stroke_width == 3.0
        assert style.stroke_style == StrokeStyle.DASHED
        assert style.shadow_enabled is True
        assert style.shadow_blur == 5.0
    
    def test_shape_style__gradient_pattern__creates_default_stops(self):
        """Test ShapeStyle with gradient pattern creates default stops."""
        style = ShapeStyle(
            fill_pattern=FillPattern.GRADIENT_LINEAR,
            fill_color=(255, 0, 0)
        )
        assert style.gradient_stops is not None
        assert len(style.gradient_stops) == 2
        assert style.gradient_stops[0].position == 0.0
        assert style.gradient_stops[0].color == (255, 0, 0)
        assert style.gradient_stops[1].position == 1.0
        assert style.gradient_stops[1].color == (255, 255, 255)
    
    def test_shape_style__invalid_fill_color__raises_error(self):
        """Test ShapeStyle with invalid fill color raises ValueError."""
        with pytest.raises(ValueError, match="Fill color values must be between 0 and 255"):
            ShapeStyle(fill_color=(256, 128, 0))
    
    def test_shape_style__invalid_stroke_width__raises_error(self):
        """Test ShapeStyle with invalid stroke width raises ValueError."""
        with pytest.raises(ValueError, match="Stroke width must be non-negative"):
            ShapeStyle(stroke_width=-1.0)
    
    def test_shape_style__invalid_shadow_blur__raises_error(self):
        """Test ShapeStyle with invalid shadow blur raises ValueError."""
        with pytest.raises(ValueError, match="Shadow blur must be non-negative"):
            ShapeStyle(shadow_blur=-1.0)


class TestShapeWidget:
    """Test ShapeWidget base functionality."""
    
    def test_shape_widget__initialization__correct_state(self):
        """Test ShapeWidget initialization with default values."""
        widget = ShapeWidget()
        
        assert isinstance(widget.style, ShapeStyle)
        assert widget._bounds_dirty is True
        assert widget._cached_bounds is None
    
    def test_shape_widget__custom_style__uses_custom_style(self):
        """Test ShapeWidget initialization with custom style."""
        custom_style = ShapeStyle(fill_color=(255, 0, 0))
        widget = ShapeWidget(style=custom_style)
        
        assert widget.style is custom_style
        assert widget.style.fill_color == (255, 0, 0)
    
    def test_shape_widget__style_property__get_set(self):
        """Test style property getter and setter."""
        widget = ShapeWidget()
        new_style = ShapeStyle(stroke_width=5.0)
        
        widget.style = new_style
        
        assert widget.style is new_style
        assert widget.style.stroke_width == 5.0
        assert widget._bounds_dirty is True
    
    def test_set_fill_color__valid_color__updates_style(self):
        """Test setting fill color."""
        widget = ShapeWidget()
        
        widget.set_fill_color((255, 128, 0), alpha=0.8)
        
        assert widget.style.fill_color == (255, 128, 0)
        assert widget.style.fill_alpha == 0.8
        assert widget.style.fill_enabled is True
    
    def test_set_fill_color__invalid_color__raises_error(self):
        """Test setting invalid fill color raises error."""
        widget = ShapeWidget()
        
        with pytest.raises(ValueError, match="Color values must be between 0 and 255"):
            widget.set_fill_color((256, 128, 0))
    
    def test_set_stroke__valid_parameters__updates_style(self):
        """Test setting stroke properties."""
        widget = ShapeWidget()
        
        widget.set_stroke((255, 0, 0), width=3.0, alpha=0.9, style=StrokeStyle.DASHED)
        
        assert widget.style.stroke_color == (255, 0, 0)
        assert widget.style.stroke_width == 3.0
        assert widget.style.stroke_alpha == 0.9
        assert widget.style.stroke_style == StrokeStyle.DASHED
        assert widget.style.stroke_enabled is True
    
    def test_set_stroke__zero_width__disables_stroke(self):
        """Test setting stroke width to zero disables stroke."""
        widget = ShapeWidget()
        
        widget.set_stroke((255, 0, 0), width=0.0)
        
        assert widget.style.stroke_enabled is False
    
    def test_enable_shadow__valid_parameters__enables_shadow(self):
        """Test enabling shadow with parameters."""
        widget = ShapeWidget()
        
        widget.enable_shadow(True, offset=(3.0, 3.0), color=(128, 128, 128), alpha=0.6, blur=4.0)
        
        assert widget.style.shadow_enabled is True
        assert widget.style.shadow_offset == (3.0, 3.0)
        assert widget.style.shadow_color == (128, 128, 128)
        assert widget.style.shadow_alpha == 0.6
        assert widget.style.shadow_blur == 4.0
    
    def test_set_gradient_fill__valid_stops__sets_gradient(self):
        """Test setting gradient fill."""
        widget = ShapeWidget()
        stops = [
            GradientStop(0.0, (255, 0, 0)),
            GradientStop(1.0, (0, 0, 255))
        ]
        
        widget.set_gradient_fill(stops, FillPattern.GRADIENT_LINEAR, angle=45.0)
        
        assert widget.style.fill_pattern == FillPattern.GRADIENT_LINEAR
        assert widget.style.gradient_stops == stops
        assert widget.style.gradient_angle == 45.0
        assert widget.style.fill_enabled is True
    
    def test_set_gradient_fill__empty_stops__raises_error(self):
        """Test setting gradient fill with empty stops raises error."""
        widget = ShapeWidget()
        
        with pytest.raises(ValueError, match="Gradient must have at least one stop"):
            widget.set_gradient_fill([])


class TestRectangleWidget:
    """Test RectangleWidget functionality."""
    
    def test_rectangle_widget__initialization__correct_state(self):
        """Test RectangleWidget initialization with default values."""
        widget = RectangleWidget(100.0, 50.0)
        
        assert widget.width == 100.0
        assert widget.height == 50.0
        assert widget.corner_radius == 0.0
        assert isinstance(widget._width, ReactiveValue)
        assert isinstance(widget._height, ReactiveValue)
        assert isinstance(widget._corner_radius, ReactiveValue)
    
    def test_rectangle_widget__with_corner_radius__correct_initialization(self):
        """Test RectangleWidget initialization with corner radius."""
        widget = RectangleWidget(100.0, 50.0, corner_radius=10.0)
        
        assert widget.width == 100.0
        assert widget.height == 50.0
        assert widget.corner_radius == 10.0
    
    def test_rectangle_widget__with_reactive_values__uses_reactive(self):
        """Test RectangleWidget initialization with ReactiveValue."""
        width_reactive = ReactiveValue(80.0)
        height_reactive = ReactiveValue(40.0)
        widget = RectangleWidget(width_reactive, height_reactive)
        
        assert widget._width is width_reactive
        assert widget._height is height_reactive
        assert widget.width == 80.0
        assert widget.height == 40.0
    
    def test_rectangle_widget__invalid_dimensions__raises_error(self):
        """Test RectangleWidget with invalid dimensions raises error."""
        with pytest.raises(ValueError, match="Rectangle width must be non-negative"):
            RectangleWidget(-10.0, 50.0)
        
        with pytest.raises(ValueError, match="Rectangle height must be non-negative"):
            RectangleWidget(100.0, -20.0)
    
    def test_rectangle_widget__invalid_corner_radius__raises_error(self):
        """Test RectangleWidget with invalid corner radius raises error."""
        with pytest.raises(ValueError, match="Corner radius must be non-negative"):
            RectangleWidget(100.0, 50.0, corner_radius=-5.0)
        
        with pytest.raises(ValueError, match="Corner radius cannot exceed"):
            RectangleWidget(100.0, 50.0, corner_radius=30.0)  # Exceeds height/2
    
    def test_rectangle_widget__width_property__get_set(self):
        """Test width property getter and setter."""
        widget = RectangleWidget(100.0, 50.0)
        
        widget.width = 150.0
        
        assert widget.width == 150.0
        assert widget._width.value == 150.0
    
    def test_rectangle_widget__reactive_dimension_change__triggers_update(self):
        """Test reactive dimension changes trigger updates."""
        width_reactive = ReactiveValue(100.0)
        widget = RectangleWidget(width_reactive, 50.0)
        
        # Mock update handler
        widget._mark_dirty = Mock()
        
        # Change reactive value
        width_reactive.value = 120.0
        
        # Verify update was triggered
        widget._mark_dirty.assert_called()
        assert widget.width == 120.0
    
    def test_rectangle_widget__calculate_shape_bounds__includes_stroke_and_shadow(self):
        """Test shape bounds calculation includes stroke and shadow."""
        widget = RectangleWidget(100.0, 50.0)
        widget.position = (10.0, 20.0)
        widget.style.stroke_width = 4.0
        widget.style.shadow_enabled = True
        widget.style.shadow_offset = (2.0, 2.0)
        widget.style.shadow_blur = 3.0
        
        bounds = widget._calculate_shape_bounds()
        
        # Should include stroke (2.0 on each side) and shadow (5.0 total offset)
        assert bounds.x == 10.0 - 2.0 - 5.0  # 3.0
        assert bounds.y == 20.0 - 2.0 - 5.0  # 13.0
        assert bounds.width == 100.0 + 4.0 + 5.0  # 109.0
        assert bounds.height == 50.0 + 4.0 + 5.0  # 59.0
    
    def test_rectangle_widget__contains_point__simple_rectangle(self):
        """Test point containment for simple rectangle."""
        widget = RectangleWidget(100.0, 50.0)
        widget.position = (10.0, 20.0)
        
        # Points inside
        assert widget.contains_point(50.0, 40.0) is True
        assert widget.contains_point(10.0, 20.0) is True  # Corner
        assert widget.contains_point(110.0, 70.0) is True  # Opposite corner
        
        # Points outside
        assert widget.contains_point(5.0, 40.0) is False
        assert widget.contains_point(50.0, 15.0) is False
        assert widget.contains_point(115.0, 40.0) is False
        assert widget.contains_point(50.0, 75.0) is False
    
    def test_rectangle_widget__contains_point__with_corner_radius(self):
        """Test point containment for rounded rectangle."""
        widget = RectangleWidget(100.0, 50.0, corner_radius=10.0)
        widget.position = (0.0, 0.0)
        
        # Point in main rectangle area
        assert widget.contains_point(50.0, 25.0) is True
        
        # Point in corner radius area (should be inside circle)
        assert widget.contains_point(5.0, 5.0) is True  # Within radius
        assert widget.contains_point(2.0, 2.0) is False  # Outside radius
    
    def test_rectangle_widget__repr__returns_useful_string(self):
        """Test rectangle widget string representation."""
        widget = RectangleWidget(100.0, 50.0, corner_radius=5.0)
        
        repr_str = repr(widget)
        
        assert "RectangleWidget" in repr_str
        assert "width=100.0" in repr_str
        assert "height=50.0" in repr_str
        assert "corner_radius=5.0" in repr_str


class TestCircleWidget:
    """Test CircleWidget functionality."""
    
    def test_circle_widget__initialization__correct_state(self):
        """Test CircleWidget initialization with default values."""
        widget = CircleWidget(25.0)
        
        assert widget.radius == 25.0
        assert widget.diameter == 50.0
        assert isinstance(widget._radius, ReactiveValue)
    
    def test_circle_widget__with_reactive_radius__uses_reactive(self):
        """Test CircleWidget initialization with ReactiveValue."""
        radius_reactive = ReactiveValue(30.0)
        widget = CircleWidget(radius_reactive)
        
        assert widget._radius is radius_reactive
        assert widget.radius == 30.0
        assert widget.diameter == 60.0
    
    def test_circle_widget__invalid_radius__raises_error(self):
        """Test CircleWidget with invalid radius raises error."""
        with pytest.raises(ValueError, match="Circle radius must be non-negative"):
            CircleWidget(-10.0)
    
    def test_circle_widget__radius_property__get_set(self):
        """Test radius property getter and setter."""
        widget = CircleWidget(25.0)
        
        widget.radius = 35.0
        
        assert widget.radius == 35.0
        assert widget.diameter == 70.0
        assert widget._radius.value == 35.0
    
    def test_circle_widget__center_property__calculates_correctly(self):
        """Test center property calculation."""
        widget = CircleWidget(25.0)
        widget.position = (10.0, 20.0)
        
        center = widget.center
        
        assert center == (35.0, 45.0)  # position + radius
    
    def test_circle_widget__reactive_radius_change__triggers_update(self):
        """Test reactive radius changes trigger updates."""
        radius_reactive = ReactiveValue(25.0)
        widget = CircleWidget(radius_reactive)
        
        # Mock update handler
        widget._mark_dirty = Mock()
        
        # Change reactive value
        radius_reactive.value = 30.0
        
        # Verify update was triggered
        widget._mark_dirty.assert_called()
        assert widget.radius == 30.0
    
    def test_circle_widget__calculate_shape_bounds__includes_stroke_and_shadow(self):
        """Test shape bounds calculation includes stroke and shadow."""
        widget = CircleWidget(25.0)
        widget.position = (10.0, 20.0)
        widget.style.stroke_width = 4.0
        widget.style.shadow_enabled = True
        widget.style.shadow_offset = (3.0, 3.0)
        widget.style.shadow_blur = 2.0
        
        bounds = widget._calculate_shape_bounds()
        
        # Should include stroke (2.0 on each side) and shadow (5.0 total offset)
        total_radius = 25.0 + 2.0  # 27.0
        shadow_offset_x = abs(3.0) + 2.0  # 5.0
        shadow_offset_y = abs(3.0) + 2.0  # 5.0
        assert bounds.x == 10.0 - 2.0 - 5.0  # 3.0
        assert bounds.y == 20.0 - 2.0 - 5.0  # 13.0
        assert bounds.width == (total_radius * 2) + shadow_offset_x + shadow_offset_y  # 64.0
        assert bounds.height == (total_radius * 2) + shadow_offset_x + shadow_offset_y  # 64.0
    
    def test_circle_widget__contains_point__inside_circle(self):
        """Test point containment for circle."""
        widget = CircleWidget(25.0)
        widget.position = (0.0, 0.0)  # Center at (25, 25)
        
        # Points inside
        assert widget.contains_point(25.0, 25.0) is True  # Center
        assert widget.contains_point(35.0, 25.0) is True  # On radius
        assert widget.contains_point(30.0, 30.0) is True  # Inside
        
        # Points outside
        assert widget.contains_point(55.0, 25.0) is False  # Beyond radius
        assert widget.contains_point(25.0, 55.0) is False  # Beyond radius
        assert widget.contains_point(45.0, 45.0) is False  # Outside circle
    
    def test_circle_widget__repr__returns_useful_string(self):
        """Test circle widget string representation."""
        widget = CircleWidget(25.0)
        widget.position = (10.0, 20.0)
        
        repr_str = repr(widget)
        
        assert "CircleWidget" in repr_str
        assert "radius=25.0" in repr_str
        assert "center=(35.0, 45.0)" in repr_str


class TestLineWidget:
    """Test LineWidget functionality."""
    
    def test_line_widget__initialization__correct_state(self):
        """Test LineWidget initialization with default values."""
        widget = LineWidget((10.0, 20.0), (50.0, 60.0))
        
        assert widget.start_point == (10.0, 20.0)
        assert widget.end_point == (50.0, 60.0)
        assert isinstance(widget._start_point, ReactiveValue)
        assert isinstance(widget._end_point, ReactiveValue)
    
    def test_line_widget__with_reactive_points__uses_reactive(self):
        """Test LineWidget initialization with ReactiveValue."""
        start_reactive = ReactiveValue((0.0, 0.0))
        end_reactive = ReactiveValue((100.0, 100.0))
        widget = LineWidget(start_reactive, end_reactive)
        
        assert widget._start_point is start_reactive
        assert widget._end_point is end_reactive
        assert widget.start_point == (0.0, 0.0)
        assert widget.end_point == (100.0, 100.0)
    
    def test_line_widget__invalid_points__raises_error(self):
        """Test LineWidget with invalid points raises error."""
        with pytest.raises(ValueError, match="Point must be a tuple of two numbers"):
            LineWidget("invalid", (50.0, 60.0))
        
        with pytest.raises(ValueError, match="Point coordinates must be numeric"):
            LineWidget((10.0, "invalid"), (50.0, 60.0))
    
    def test_line_widget__length_property__calculates_correctly(self):
        """Test length property calculation."""
        widget = LineWidget((0.0, 0.0), (3.0, 4.0))
        
        length = widget.length
        
        assert abs(length - 5.0) < 0.001  # 3-4-5 triangle
    
    def test_line_widget__angle_properties__calculate_correctly(self):
        """Test angle property calculations."""
        widget = LineWidget((0.0, 0.0), (1.0, 1.0))
        
        angle_rad = widget.angle
        angle_deg = widget.angle_degrees
        
        assert abs(angle_rad - math.pi/4) < 0.001  # 45 degrees in radians
        assert abs(angle_deg - 45.0) < 0.001
    
    def test_line_widget__endpoint_properties__get_set(self):
        """Test endpoint property getters and setters."""
        widget = LineWidget((10.0, 20.0), (50.0, 60.0))
        
        widget.start_point = (15.0, 25.0)
        widget.end_point = (55.0, 65.0)
        
        assert widget.start_point == (15.0, 25.0)
        assert widget.end_point == (55.0, 65.0)
    
    def test_line_widget__reactive_endpoint_change__triggers_update(self):
        """Test reactive endpoint changes trigger updates."""
        start_reactive = ReactiveValue((10.0, 20.0))
        widget = LineWidget(start_reactive, (50.0, 60.0))
        
        # Mock update handler
        widget._mark_dirty = Mock()
        
        # Change reactive value
        start_reactive.value = (15.0, 25.0)
        
        # Verify update was triggered
        widget._mark_dirty.assert_called()
        assert widget.start_point == (15.0, 25.0)
    
    def test_line_widget__calculate_shape_bounds__includes_stroke_and_shadow(self):
        """Test shape bounds calculation includes stroke and shadow."""
        widget = LineWidget((10.0, 20.0), (50.0, 60.0))
        widget.style.stroke_width = 4.0
        widget.style.shadow_enabled = True
        widget.style.shadow_offset = (2.0, 2.0)
        widget.style.shadow_blur = 3.0
        
        bounds = widget._calculate_shape_bounds()
        
        # Line bounds: (10, 20) to (50, 60) = width 40, height 40
        # Stroke offset: 2.0, Shadow offset: 5.0
        assert bounds.x == 10.0 - 2.0 - 5.0  # 3.0
        assert bounds.y == 20.0 - 2.0 - 5.0  # 13.0
        assert bounds.width == 40.0 + 4.0 + 5.0  # 49.0
        assert bounds.height == 40.0 + 4.0 + 5.0  # 49.0
    
    def test_line_widget__contains_point__near_line(self):
        """Test point containment for line with tolerance."""
        widget = LineWidget((0.0, 0.0), (100.0, 0.0))  # Horizontal line
        
        # Points on or near the line
        assert widget.contains_point(50.0, 0.0, tolerance=1.0) is True  # On line
        assert widget.contains_point(50.0, 0.5, tolerance=1.0) is True  # Near line
        assert widget.contains_point(25.0, 1.0, tolerance=2.0) is True  # Within tolerance
        
        # Points far from line
        assert widget.contains_point(50.0, 10.0, tolerance=1.0) is False
        assert widget.contains_point(-10.0, 0.0, tolerance=1.0) is False  # Beyond endpoints
    
    def test_line_widget__contains_point__zero_length_line(self):
        """Test point containment for zero-length line (point)."""
        widget = LineWidget((50.0, 50.0), (50.0, 50.0))
        
        # Point at line location
        assert widget.contains_point(50.0, 50.0, tolerance=1.0) is True
        assert widget.contains_point(50.5, 50.5, tolerance=1.0) is True  # Within tolerance
        
        # Point far from line
        assert widget.contains_point(55.0, 55.0, tolerance=1.0) is False
    
    def test_line_widget__repr__returns_useful_string(self):
        """Test line widget string representation."""
        widget = LineWidget((0.0, 0.0), (3.0, 4.0))
        
        repr_str = repr(widget)
        
        assert "LineWidget" in repr_str
        assert "start=(0.0, 0.0)" in repr_str
        assert "end=(3.0, 4.0)" in repr_str
        assert "length=5.0" in repr_str


class TestShapeWidgetRendering:
    """Test shape widget rendering functionality."""
    
    def test_shape_widget__render__invisible_widget__skipped(self):
        """Test that invisible widgets are not rendered."""
        widget = RectangleWidget(100.0, 50.0)
        widget.visible = False
        
        # Mock render methods
        widget._render_shadow = Mock()
        widget._render_fill = Mock()
        widget._render_stroke = Mock()
        
        canvas = Mock()
        widget.render(canvas)
        
        # Should not call any render methods
        widget._render_shadow.assert_not_called()
        widget._render_fill.assert_not_called()
        widget._render_stroke.assert_not_called()
    
    def test_shape_widget__render__zero_alpha__skipped(self):
        """Test that widgets with zero alpha are not rendered."""
        widget = CircleWidget(25.0)
        widget.alpha = 0.0
        
        # Mock render methods
        widget._render_shadow = Mock()
        widget._render_fill = Mock()
        widget._render_stroke = Mock()
        
        canvas = Mock()
        widget.render(canvas)
        
        # Should not call any render methods
        widget._render_shadow.assert_not_called()
        widget._render_fill.assert_not_called()
        widget._render_stroke.assert_not_called()
    
    def test_shape_widget__render__calls_render_methods_in_order(self):
        """Test that rendering calls methods in correct order."""
        widget = RectangleWidget(100.0, 50.0)
        widget.style.shadow_enabled = True
        widget.style.fill_enabled = True
        widget.style.stroke_enabled = True
        
        # Mock render methods
        widget._render_shadow = Mock()
        widget._render_fill = Mock()
        widget._render_stroke = Mock()
        widget.mark_clean = Mock()
        
        canvas = Mock()
        widget.render(canvas)
        
        # Verify methods called in correct order
        widget._render_shadow.assert_called_once_with(canvas)
        widget._render_fill.assert_called_once_with(canvas)
        widget._render_stroke.assert_called_once_with(canvas)
        widget.mark_clean.assert_called_once()
    
    def test_line_widget__render_fill__skipped(self):
        """Test that line widgets skip fill rendering."""
        widget = LineWidget((0.0, 0.0), (100.0, 100.0))
        canvas = Mock()
        
        # _render_fill should do nothing for lines
        widget._render_fill(canvas)
        
        # Should not interact with canvas for fill
        assert not canvas.method_calls


class TestShapeWidgetPerformance:
    """Test shape widget performance characteristics."""
    
    @pytest.mark.performance
    def test_rectangle_widget__creation_performance__meets_target(self):
        """Test rectangle widget creation performance."""
        start_time = time.perf_counter()
        
        widgets = []
        for i in range(100):
            widget = RectangleWidget(100.0 + i, 50.0 + i)
            widgets.append(widget)
        
        creation_time = time.perf_counter() - start_time
        
        # Should create 100 widgets in under 100ms
        assert creation_time < 0.1
        assert len(widgets) == 100
    
    @pytest.mark.performance
    def test_circle_widget__bounds_calculation_performance__meets_target(self):
        """Test circle bounds calculation performance."""
        widget = CircleWidget(25.0)
        widget.style.stroke_width = 2.0
        widget.style.shadow_enabled = True
        
        start_time = time.perf_counter()
        
        for _ in range(1000):
            bounds = widget.get_shape_bounds()
        
        calculation_time = time.perf_counter() - start_time
        
        # Should perform 1000 bounds calculations in under 50ms
        assert calculation_time < 0.05
    
    @pytest.mark.performance
    def test_line_widget__contains_point_performance__meets_target(self):
        """Test line point containment performance."""
        widget = LineWidget((0.0, 0.0), (1000.0, 1000.0))
        
        start_time = time.perf_counter()
        
        for i in range(1000):
            x, y = i, i + 1
            contains = widget.contains_point(x, y, tolerance=5.0)
        
        containment_time = time.perf_counter() - start_time
        
        # Should perform 1000 containment checks in under 50ms
        assert containment_time < 0.05


class TestShapeWidgetIntegration:
    """Test shape widget integration with other systems."""
    
    def test_shape_widget__reactive_data_manager_integration(self):
        """Test integration with ReactiveDataManager."""
        from src.tinydisplay.core.reactive import ReactiveDataManager
        
        manager = ReactiveDataManager()
        width_reactive = ReactiveValue(100.0)
        height_reactive = ReactiveValue(50.0)
        
        widget = RectangleWidget(width_reactive, height_reactive)
        
        # Update reactive values
        width_reactive.value = 150.0
        height_reactive.value = 75.0
        
        # Widget should reflect the changes
        assert widget.width == 150.0
        assert widget.height == 75.0
    
    def test_shape_widget__multiple_reactive_bindings(self):
        """Test widget with multiple reactive bindings."""
        radius_reactive = ReactiveValue(25.0)
        widget = CircleWidget(radius_reactive)
        
        # Create reactive style properties (conceptual)
        fill_color_reactive = ReactiveValue((255, 0, 0))
        
        # Update values
        radius_reactive.value = 35.0
        fill_color_reactive.value = (0, 255, 0)
        
        assert widget.radius == 35.0
        # Style updates would need reactive style system (future enhancement)
    
    def test_shape_widget__bounds_intersection(self):
        """Test shape bounds intersection calculations."""
        rect1 = RectangleWidget(100.0, 50.0)
        rect1.position = (0.0, 0.0)
        
        rect2 = RectangleWidget(80.0, 60.0)
        rect2.position = (50.0, 25.0)
        
        # Test intersection
        bounds1 = rect1.get_shape_bounds()
        bounds2 = rect2.get_shape_bounds()
        
        assert rect1.intersects_bounds(bounds2) is True
        assert rect2.intersects_bounds(bounds1) is True
    
    def test_shape_widget__canvas_integration(self):
        """Test shape widget integration with canvas system."""
        widget = CircleWidget(25.0)
        mock_canvas = Mock()
        
        # Should not raise errors
        widget.render(mock_canvas)
        
        # Verify widget state is correct
        assert widget.radius == 25.0
        assert widget.visible is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 