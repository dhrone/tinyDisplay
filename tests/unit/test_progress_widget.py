#!/usr/bin/env python3
"""
Test Suite for ProgressBarWidget

Comprehensive tests for progress bar widget functionality including reactive binding,
animations, styling, orientations, text overlays, and performance validation.
"""

import pytest
import time
import math
from unittest.mock import Mock, patch, MagicMock

from src.tinydisplay.widgets.progress import (
    ProgressBarWidget, ProgressStyle, ProgressAnimation,
    ProgressOrientation, ProgressTextPosition, EasingFunction,
    ProgressPrediction, ProgressDataPoint
)
from src.tinydisplay.widgets.base import ReactiveValue, WidgetBounds


class TestProgressStyle:
    """Test ProgressStyle configuration and validation."""
    
    def test_progress_style__default_values__correct_initialization(self):
        """Test ProgressStyle with default values."""
        style = ProgressStyle()
        assert style.background_color == (64, 64, 64)
        assert style.fill_color == (0, 150, 255)
        assert style.border_color == (128, 128, 128)
        assert style.border_width == 1
        assert style.border_radius == 0
        assert style.bar_height is None
        assert style.text_color == (255, 255, 255)
        assert style.text_font_size == 12
        assert style.text_font_family == "default"
        assert style.show_percentage is True
        assert style.text_format == "{:.1f}%"
        assert style.gradient_enabled is False
        assert style.shadow_enabled is False
        assert style.pulse_enabled is False
        assert style.pulse_speed == 1.0
        assert style.pulse_intensity == 0.2
    
    def test_progress_style__custom_values__correct_initialization(self):
        """Test ProgressStyle with custom values."""
        style = ProgressStyle(
            background_color=(100, 100, 100),
            fill_color=(255, 0, 0),
            border_width=2,
            text_font_size=16,
            pulse_enabled=True,
            pulse_speed=2.0,
            pulse_intensity=0.5
        )
        assert style.background_color == (100, 100, 100)
        assert style.fill_color == (255, 0, 0)
        assert style.border_width == 2
        assert style.text_font_size == 16
        assert style.pulse_enabled is True
        assert style.pulse_speed == 2.0
        assert style.pulse_intensity == 0.5
    
    def test_progress_style__invalid_background_color__raises_error(self):
        """Test ProgressStyle with invalid background color raises ValueError."""
        with pytest.raises(ValueError, match="Background color values must be between 0 and 255"):
            ProgressStyle(background_color=(256, 128, 128))
    
    def test_progress_style__invalid_fill_color__raises_error(self):
        """Test ProgressStyle with invalid fill color raises ValueError."""
        with pytest.raises(ValueError, match="Fill color values must be between 0 and 255"):
            ProgressStyle(fill_color=(-1, 128, 128))
    
    def test_progress_style__invalid_border_width__raises_error(self):
        """Test ProgressStyle with invalid border width raises ValueError."""
        with pytest.raises(ValueError, match="Border width must be non-negative"):
            ProgressStyle(border_width=-1)
    
    def test_progress_style__invalid_text_font_size__raises_error(self):
        """Test ProgressStyle with invalid text font size raises ValueError."""
        with pytest.raises(ValueError, match="Text font size must be positive"):
            ProgressStyle(text_font_size=0)
    
    def test_progress_style__invalid_pulse_intensity__raises_error(self):
        """Test ProgressStyle with invalid pulse intensity raises ValueError."""
        with pytest.raises(ValueError, match="Pulse intensity must be between 0.0 and 1.0"):
            ProgressStyle(pulse_intensity=1.5)
    
    def test_progress_style__invalid_pulse_speed__raises_error(self):
        """Test ProgressStyle with invalid pulse speed raises ValueError."""
        with pytest.raises(ValueError, match="Pulse speed must be positive"):
            ProgressStyle(pulse_speed=-1.0)


class TestProgressAnimation:
    """Test ProgressAnimation configuration and validation."""
    
    def test_progress_animation__default_values__correct_initialization(self):
        """Test ProgressAnimation with default values."""
        animation = ProgressAnimation()
        assert animation.enabled is True
        assert animation.duration == 0.3
        assert animation.easing == EasingFunction.EASE_OUT
        assert animation.start_time is None
        assert animation.start_value is None
        assert animation.target_value is None
        assert animation.current_value is None
    
    def test_progress_animation__custom_values__correct_initialization(self):
        """Test ProgressAnimation with custom values."""
        animation = ProgressAnimation(
            enabled=False,
            duration=0.5,
            easing=EasingFunction.BOUNCE
        )
        assert animation.enabled is False
        assert animation.duration == 0.5
        assert animation.easing == EasingFunction.BOUNCE
    
    def test_progress_animation__invalid_duration__raises_error(self):
        """Test ProgressAnimation with invalid duration raises ValueError."""
        with pytest.raises(ValueError, match="Animation duration must be positive"):
            ProgressAnimation(duration=0.0)


class TestProgressBarWidget:
    """Test ProgressBarWidget functionality."""
    
    def test_progress_bar_widget__initialization__correct_state(self):
        """Test ProgressBarWidget initialization with default values."""
        widget = ProgressBarWidget()
        
        assert widget.progress == 0.0
        assert isinstance(widget._progress, ReactiveValue)
        assert widget.orientation == ProgressOrientation.HORIZONTAL
        assert isinstance(widget.style, ProgressStyle)
        assert widget.text_position == ProgressTextPosition.CENTER
        assert isinstance(widget.animation, ProgressAnimation)
        assert widget._min_value == 0.0
        assert widget._max_value == 1.0
        assert widget._cached_progress == 0.0
    
    def test_progress_bar_widget__initialization_with_progress__creates_reactive(self):
        """Test ProgressBarWidget initialization with progress value."""
        widget = ProgressBarWidget(0.75)
        
        assert widget.progress == 0.75
        assert isinstance(widget._progress, ReactiveValue)
        assert widget._progress.value == 0.75
        assert widget._cached_progress == 0.75
    
    def test_progress_bar_widget__initialization_with_reactive__uses_reactive(self):
        """Test ProgressBarWidget initialization with ReactiveValue."""
        reactive_progress = ReactiveValue(0.5)
        widget = ProgressBarWidget(reactive_progress)
        
        assert widget.progress == 0.5
        assert widget._progress is reactive_progress
    
    def test_progress_bar_widget__initialization_with_custom_range__normalizes_correctly(self):
        """Test ProgressBarWidget with custom value range."""
        widget = ProgressBarWidget(50, min_value=0, max_value=100)
        
        assert widget.progress == 50
        assert widget._cached_progress == 0.5  # Normalized to 0.0-1.0
        assert widget._min_value == 0
        assert widget._max_value == 100
    
    def test_progress_bar_widget__invalid_range__raises_error(self):
        """Test ProgressBarWidget with invalid range raises error."""
        with pytest.raises(ValueError, match="min_value must be less than max_value"):
            ProgressBarWidget(min_value=1.0, max_value=0.5)
    
    def test_progress_bar_widget__invalid_progress__raises_error(self):
        """Test ProgressBarWidget with invalid progress raises error."""
        with pytest.raises(ValueError, match="Progress value must be between 0.0 and 1.0"):
            ProgressBarWidget(1.5)
    
    def test_progress_bar_widget__set_progress_value__updates_reactive(self):
        """Test setting progress with numeric value."""
        widget = ProgressBarWidget(0.2)
        
        widget.progress = 0.8
        
        assert widget.progress == 0.8
        assert widget._progress.value == 0.8
    
    def test_progress_bar_widget__set_progress_reactive__replaces_reactive(self):
        """Test setting progress with ReactiveValue."""
        widget = ProgressBarWidget(0.2)
        new_reactive = ReactiveValue(0.9)
        
        widget.progress = new_reactive
        
        assert widget.progress == 0.9
        assert widget._progress is new_reactive
    
    def test_progress_bar_widget__reactive_progress_change__triggers_animation(self):
        """Test that reactive progress changes trigger animation."""
        reactive_progress = ReactiveValue(0.3)
        widget = ProgressBarWidget(reactive_progress)
        
        # Mock animation start
        widget._start_animation = Mock()
        
        # Change reactive value
        reactive_progress.value = 0.7
        
        # Verify animation was started
        widget._start_animation.assert_called()
    
    def test_progress_bar_widget__orientation_property__get_set(self):
        """Test orientation property getter and setter."""
        widget = ProgressBarWidget()
        
        widget.orientation = ProgressOrientation.VERTICAL
        
        assert widget.orientation == ProgressOrientation.VERTICAL
    
    def test_progress_bar_widget__style_property__get_set(self):
        """Test style property getter and setter."""
        widget = ProgressBarWidget()
        new_style = ProgressStyle(fill_color=(255, 0, 0))
        
        widget.style = new_style
        
        assert widget.style is new_style
        assert widget.style.fill_color == (255, 0, 0)
    
    def test_progress_bar_widget__text_position_property__get_set(self):
        """Test text position property getter and setter."""
        widget = ProgressBarWidget()
        
        widget.text_position = ProgressTextPosition.LEFT
        
        assert widget.text_position == ProgressTextPosition.LEFT
    
    def test_progress_bar_widget__animation_property__get_set(self):
        """Test animation property getter and setter."""
        widget = ProgressBarWidget()
        new_animation = ProgressAnimation(duration=0.5, easing=EasingFunction.BOUNCE)
        
        widget.animation = new_animation
        
        assert widget.animation is new_animation
        assert widget.animation.duration == 0.5
        assert widget.animation.easing == EasingFunction.BOUNCE
    
    def test_progress_bar_widget__animated_progress__returns_current_animation_value(self):
        """Test animated_progress property."""
        widget = ProgressBarWidget(0.5)
        widget._animation.enabled = True
        widget._animation.current_value = 0.7
        
        assert widget.animated_progress == 0.7
    
    def test_progress_bar_widget__animated_progress_disabled__returns_cached(self):
        """Test animated_progress when animation is disabled."""
        widget = ProgressBarWidget(0.5)
        widget._animation.enabled = False
        widget._cached_progress = 0.6
        
        assert widget.animated_progress == 0.6
    
    def test_progress_bar_widget__progress_percentage__returns_percentage(self):
        """Test progress_percentage property."""
        widget = ProgressBarWidget(0.75)
        
        assert widget.progress_percentage == 75.0


class TestProgressBarWidgetMethods:
    """Test ProgressBarWidget methods."""
    
    def test_set_custom_text__string__creates_reactive(self):
        """Test setting custom text with string."""
        widget = ProgressBarWidget()
        
        widget.set_custom_text("Loading...")
        
        assert widget._custom_text is not None
        assert widget._custom_text.value == "Loading..."
    
    def test_set_custom_text__reactive__uses_reactive(self):
        """Test setting custom text with ReactiveValue."""
        widget = ProgressBarWidget()
        reactive_text = ReactiveValue("Processing...")
        
        widget.set_custom_text(reactive_text)
        
        assert widget._custom_text is reactive_text
    
    def test_set_custom_text__none__clears_text(self):
        """Test setting custom text to None clears it."""
        widget = ProgressBarWidget()
        widget.set_custom_text("Test")
        
        widget.set_custom_text(None)
        
        assert widget._custom_text is None
    
    def test_set_progress_range__valid_range__updates_range(self):
        """Test setting valid progress range."""
        widget = ProgressBarWidget(50, min_value=0, max_value=100)
        
        widget.set_progress_range(10, 90)
        
        assert widget._min_value == 10
        assert widget._max_value == 90
    
    def test_set_progress_range__invalid_range__raises_error(self):
        """Test setting invalid progress range raises error."""
        widget = ProgressBarWidget()
        
        with pytest.raises(ValueError, match="min_value must be less than max_value"):
            widget.set_progress_range(5.0, 2.0)
    
    def test_set_fill_color__valid_color__updates_style(self):
        """Test setting fill color."""
        widget = ProgressBarWidget()
        
        widget.set_fill_color((255, 0, 0))
        
        assert widget.style.fill_color == (255, 0, 0)
    
    def test_set_fill_color__invalid_color__raises_error(self):
        """Test setting invalid fill color raises error."""
        widget = ProgressBarWidget()
        
        with pytest.raises(ValueError, match="Color values must be between 0 and 255"):
            widget.set_fill_color((256, 0, 0))
    
    def test_set_background_color__valid_color__updates_style(self):
        """Test setting background color."""
        widget = ProgressBarWidget()
        
        widget.set_background_color((50, 50, 50))
        
        assert widget.style.background_color == (50, 50, 50)
    
    def test_enable_pulse__valid_parameters__enables_pulse(self):
        """Test enabling pulse animation."""
        widget = ProgressBarWidget()
        
        widget.enable_pulse(True, speed=2.0, intensity=0.3)
        
        assert widget.style.pulse_enabled is True
        assert widget.style.pulse_speed == 2.0
        assert widget.style.pulse_intensity == 0.3
    
    def test_enable_pulse__invalid_speed__raises_error(self):
        """Test enabling pulse with invalid speed raises error."""
        widget = ProgressBarWidget()
        
        with pytest.raises(ValueError, match="Pulse speed must be positive"):
            widget.enable_pulse(True, speed=-1.0)
    
    def test_enable_pulse__invalid_intensity__raises_error(self):
        """Test enabling pulse with invalid intensity raises error."""
        widget = ProgressBarWidget()
        
        with pytest.raises(ValueError, match="Pulse intensity must be between 0.0 and 1.0"):
            widget.enable_pulse(True, intensity=1.5)
    
    def test_enable_gradient__valid_parameters__enables_gradient(self):
        """Test enabling gradient fill."""
        widget = ProgressBarWidget()
        
        widget.enable_gradient(True, end_color=(0, 255, 0))
        
        assert widget.style.gradient_enabled is True
        assert widget.style.gradient_end_color == (0, 255, 0)
    
    def test_enable_gradient__invalid_color__raises_error(self):
        """Test enabling gradient with invalid color raises error."""
        widget = ProgressBarWidget()
        
        with pytest.raises(ValueError, match="End color values must be between 0 and 255"):
            widget.enable_gradient(True, end_color=(256, 0, 0))


class TestProgressBarWidgetBounds:
    """Test ProgressBarWidget bounds calculation."""
    
    def test_get_progress_bounds__horizontal__correct_bounds(self):
        """Test progress bounds calculation for horizontal orientation."""
        widget = ProgressBarWidget(0.6)
        widget.position = (10, 20)
        widget.size = (100, 30)
        widget._orientation = ProgressOrientation.HORIZONTAL
        
        bounds = widget.get_progress_bounds()
        
        assert bounds.x == 10
        assert bounds.y == 20
        assert bounds.width == 60  # 100 * 0.6
        assert bounds.height == 30
    
    def test_get_progress_bounds__vertical__correct_bounds(self):
        """Test progress bounds calculation for vertical orientation."""
        widget = ProgressBarWidget(0.4)
        widget.position = (15, 25)
        widget.size = (40, 100)
        widget._orientation = ProgressOrientation.VERTICAL
        
        bounds = widget.get_progress_bounds()
        
        assert bounds.x == 15
        assert bounds.y == 85  # 25 + 100 - 40 (fills from bottom)
        assert bounds.width == 40
        assert bounds.height == 40  # 100 * 0.4
    
    def test_get_progress_bounds__zero_progress__empty_bounds(self):
        """Test progress bounds with zero progress."""
        widget = ProgressBarWidget(0.0)
        widget.position = (0, 0)
        widget.size = (100, 20)
        
        bounds = widget.get_progress_bounds()
        
        assert bounds.width == 0
    
    def test_get_progress_bounds__full_progress__full_bounds(self):
        """Test progress bounds with full progress."""
        widget = ProgressBarWidget(1.0)
        widget.position = (0, 0)
        widget.size = (100, 20)
        
        bounds = widget.get_progress_bounds()
        
        assert bounds.width == 100
        assert bounds.height == 20


class TestProgressBarWidgetAnimation:
    """Test ProgressBarWidget animation functionality."""
    
    def test_start_animation__animation_disabled__updates_cached_progress(self):
        """Test animation start when animation is disabled."""
        widget = ProgressBarWidget(0.3)
        widget._animation.enabled = False
        
        widget._start_animation()
        
        assert widget._cached_progress == 0.3
        assert widget._animation.start_time is None
    
    def test_start_animation__animation_enabled__sets_animation_state(self):
        """Test animation start when animation is enabled."""
        widget = ProgressBarWidget(0.3)
        widget._animation.enabled = True
        widget._animation.current_value = 0.2
        
        with patch('time.time', return_value=1000.0):
            widget._start_animation()
        
        assert widget._animation.start_time == 1000.0
        assert widget._animation.start_value == 0.2
        assert widget._animation.target_value == 0.3
    
    def test_update_animation__animation_complete__sets_final_value(self):
        """Test animation update when animation is complete."""
        widget = ProgressBarWidget(0.5)
        widget._animation.enabled = True
        widget._animation.start_time = 1000.0
        widget._animation.start_value = 0.2
        widget._animation.target_value = 0.8
        widget._animation.duration = 0.3
        
        # Simulate time after animation should be complete
        widget._update_animation(1000.5)  # 0.5 seconds later
        
        assert widget._animation.current_value == 0.8
        assert widget._cached_progress == 0.8
        assert widget._animation.start_time is None
    
    def test_update_animation__animation_in_progress__interpolates_value(self):
        """Test animation update during animation progress."""
        widget = ProgressBarWidget(0.5)
        widget._animation.enabled = True
        widget._animation.easing = EasingFunction.LINEAR  # Use linear for predictable test
        widget._animation.start_time = 1000.0
        widget._animation.start_value = 0.2
        widget._animation.target_value = 0.8
        widget._animation.duration = 0.6
        
        # Simulate time halfway through animation
        widget._update_animation(1000.3)  # 0.3 seconds later (50% progress)
        
        # Should be halfway between 0.2 and 0.8
        expected_value = 0.2 + (0.8 - 0.2) * 0.5  # Linear interpolation
        assert abs(widget._animation.current_value - expected_value) < 0.01
    
    def test_apply_easing__linear__returns_progress(self):
        """Test linear easing function."""
        widget = ProgressBarWidget()
        
        result = widget._apply_easing(0.5, EasingFunction.LINEAR)
        
        assert result == 0.5
    
    def test_apply_easing__ease_in__applies_quadratic(self):
        """Test ease-in easing function."""
        widget = ProgressBarWidget()
        
        result = widget._apply_easing(0.5, EasingFunction.EASE_IN)
        
        assert result == 0.25  # 0.5^2
    
    def test_apply_easing__ease_out__applies_inverse_quadratic(self):
        """Test ease-out easing function."""
        widget = ProgressBarWidget()
        
        result = widget._apply_easing(0.5, EasingFunction.EASE_OUT)
        
        expected = 1.0 - (1.0 - 0.5) * (1.0 - 0.5)
        assert result == expected
    
    def test_apply_easing__bounce__applies_bounce_effect(self):
        """Test bounce easing function."""
        widget = ProgressBarWidget()
        
        result = widget._apply_easing(0.8, EasingFunction.BOUNCE)
        
        # Should apply bounce effect (complex calculation)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
    
    def test_apply_easing__elastic__applies_elastic_effect(self):
        """Test elastic easing function."""
        widget = ProgressBarWidget()
        
        result = widget._apply_easing(0.7, EasingFunction.ELASTIC)
        
        # Should apply elastic effect
        assert isinstance(result, float)


class TestProgressBarWidgetEffects:
    """Test ProgressBarWidget visual effects."""
    
    def test_calculate_pulse_factor__pulse_disabled__returns_one(self):
        """Test pulse factor calculation when pulse is disabled."""
        widget = ProgressBarWidget()
        widget.style.pulse_enabled = False
        
        factor = widget._calculate_pulse_factor()
        
        assert factor == 1.0
    
    def test_calculate_pulse_factor__pulse_enabled__returns_varying_factor(self):
        """Test pulse factor calculation when pulse is enabled."""
        widget = ProgressBarWidget()
        widget.style.pulse_enabled = True
        widget.style.pulse_speed = 1.0
        widget.style.pulse_intensity = 0.5
        
        with patch('time.time', return_value=0.25):  # 1/4 cycle
            factor = widget._calculate_pulse_factor()
        
        # Should be close to maximum pulse (sin(π/2) = 1)
        expected = 1.0 + (1.0 * 0.5)  # 1 + intensity
        assert abs(factor - expected) < 0.1
    
    def test_apply_pulse_to_color__applies_factor_correctly(self):
        """Test pulse factor application to color."""
        widget = ProgressBarWidget()
        original_color = (100, 150, 200)
        factor = 1.2
        
        result = widget._apply_pulse_to_color(original_color, factor)
        
        expected = (120, 180, 240)  # Each component * 1.2
        assert result == expected
    
    def test_apply_pulse_to_color__clamps_to_valid_range(self):
        """Test pulse color application clamps to valid RGB range."""
        widget = ProgressBarWidget()
        original_color = (200, 200, 200)
        factor = 1.5  # Would exceed 255
        
        result = widget._apply_pulse_to_color(original_color, factor)
        
        assert all(0 <= c <= 255 for c in result)
        assert result == (255, 255, 255)  # Clamped to maximum


class TestProgressBarWidgetTextPosition:
    """Test ProgressBarWidget text position calculation."""
    
    def test_calculate_text_position__center__returns_center(self):
        """Test text position calculation for center position."""
        widget = ProgressBarWidget()
        widget.position = (10, 20)
        widget.size = (100, 40)
        widget._text_position = ProgressTextPosition.CENTER
        
        x, y = widget._calculate_text_position()
        
        assert x == 60  # 10 + 100/2
        assert y == 40  # 20 + 40/2
    
    def test_calculate_text_position__left_horizontal__returns_left_side(self):
        """Test text position calculation for left position in horizontal bar."""
        widget = ProgressBarWidget()
        widget.position = (10, 20)
        widget.size = (100, 40)
        widget._orientation = ProgressOrientation.HORIZONTAL
        widget._text_position = ProgressTextPosition.LEFT
        
        x, y = widget._calculate_text_position()
        
        assert x == 20  # 10 + 10 (padding)
        assert y == 40  # 20 + 40/2
    
    def test_calculate_text_position__left_vertical__returns_top_side(self):
        """Test text position calculation for left position in vertical bar."""
        widget = ProgressBarWidget()
        widget.position = (10, 20)
        widget.size = (40, 100)
        widget._orientation = ProgressOrientation.VERTICAL
        widget._text_position = ProgressTextPosition.LEFT
        
        x, y = widget._calculate_text_position()
        
        assert x == 30  # 10 + 40/2
        assert y == 30  # 20 + 10 (padding)
    
    def test_calculate_text_position__outside_right__returns_outside_position(self):
        """Test text position calculation for outside right position."""
        widget = ProgressBarWidget()
        widget.position = (10, 20)
        widget.size = (100, 40)
        widget._orientation = ProgressOrientation.HORIZONTAL
        widget._text_position = ProgressTextPosition.OUTSIDE_RIGHT
        
        x, y = widget._calculate_text_position()
        
        assert x == 115  # 10 + 100 + 5 (outside padding)
        assert y == 40   # 20 + 40/2


class TestProgressBarWidgetRendering:
    """Test ProgressBarWidget rendering functionality."""
    
    def test_render__invisible_widget__skipped(self):
        """Test that invisible widgets are not rendered."""
        widget = ProgressBarWidget(0.5)
        widget.visible = False
        canvas = Mock()
        
        widget.render(canvas)
        
        # Should not call any canvas methods
        assert not canvas.method_calls
    
    def test_render__zero_alpha__skipped(self):
        """Test that widgets with zero alpha are not rendered."""
        widget = ProgressBarWidget(0.5)
        widget.alpha = 0.0
        canvas = Mock()
        
        widget.render(canvas)
        
        # Should not call any canvas methods
        assert not canvas.method_calls
    
    def test_render__animation_enabled__updates_animation(self):
        """Test that rendering updates animation when enabled."""
        widget = ProgressBarWidget(0.5)
        widget._animation.enabled = True
        widget._update_animation = Mock()
        canvas = Mock()
        
        widget.render(canvas)
        
        widget._update_animation.assert_called_once()
    
    def test_render__calls_all_render_methods(self):
        """Test that rendering calls all component render methods."""
        widget = ProgressBarWidget(0.5)
        widget._render_background = Mock()
        widget._render_progress_fill = Mock()
        widget._render_border = Mock()
        widget._render_text_overlay = Mock()
        widget._render_effects = Mock()
        widget.mark_clean = Mock()
        canvas = Mock()
        
        widget.render(canvas)
        
        widget._render_background.assert_called_once_with(canvas)
        widget._render_progress_fill.assert_called_once_with(canvas)
        widget._render_border.assert_called_once_with(canvas)
        widget._render_text_overlay.assert_called_once_with(canvas)
        widget._render_effects.assert_called_once_with(canvas)
        widget.mark_clean.assert_called_once()


class TestProgressBarWidgetValidation:
    """Test ProgressBarWidget validation functionality."""
    
    def test_validate_progress__valid_numeric__passes(self):
        """Test progress validation with valid numeric values."""
        widget = ProgressBarWidget()
        
        # Should not raise
        widget._validate_progress(0.5)
        widget._validate_progress(0)
        widget._validate_progress(1)
    
    def test_validate_progress__invalid_type__raises_error(self):
        """Test progress validation with invalid type raises error."""
        widget = ProgressBarWidget()
        
        with pytest.raises(TypeError, match="Progress value must be numeric"):
            widget._validate_progress("invalid")
    
    def test_validate_progress__out_of_range__raises_error(self):
        """Test progress validation with out of range value raises error."""
        widget = ProgressBarWidget()
        
        with pytest.raises(ValueError, match="Progress value must be between 0.0 and 1.0"):
            widget._validate_progress(1.5)
        
        with pytest.raises(ValueError, match="Progress value must be between 0.0 and 1.0"):
            widget._validate_progress(-0.1)
    
    def test_normalize_progress__custom_range__normalizes_correctly(self):
        """Test progress normalization with custom range."""
        widget = ProgressBarWidget(50, min_value=10, max_value=90)
        
        result = widget._normalize_progress(50)
        
        expected = (50 - 10) / (90 - 10)  # 40/80 = 0.5
        assert result == expected
    
    def test_normalize_progress__edge_values__normalizes_correctly(self):
        """Test progress normalization with edge values."""
        widget = ProgressBarWidget(min_value=0, max_value=100)
        
        assert widget._normalize_progress(0) == 0.0
        assert widget._normalize_progress(100) == 1.0
        assert widget._normalize_progress(50) == 0.5


class TestProgressBarWidgetPerformance:
    """Test ProgressBarWidget performance characteristics."""
    
    @pytest.mark.performance
    def test_progress_bar_widget__creation_performance__meets_target(self):
        """Test widget creation performance."""
        start_time = time.perf_counter()
        
        widgets = []
        for i in range(100):
            widget = ProgressBarWidget(i / 100.0)
            widgets.append(widget)
        
        creation_time = time.perf_counter() - start_time
        
        # Should create 100 widgets in under 100ms
        assert creation_time < 0.1
        assert len(widgets) == 100
    
    @pytest.mark.performance
    def test_progress_bar_widget__animation_performance__meets_target(self):
        """Test animation update performance."""
        widget = ProgressBarWidget(0.0)
        widget._animation.enabled = True
        widget._animation.start_time = 1000.0
        widget._animation.start_value = 0.0
        widget._animation.target_value = 1.0
        widget._animation.duration = 0.3
        
        start_time = time.perf_counter()
        
        for i in range(1000):
            current_time = 1000.0 + (i * 0.001)  # Simulate time progression
            widget._update_animation(current_time)
        
        animation_time = time.perf_counter() - start_time
        
        # Should perform 1000 animation updates in under 50ms
        assert animation_time < 0.05
    
    @pytest.mark.performance
    def test_progress_bar_widget__reactive_update_performance__meets_target(self):
        """Test reactive update performance."""
        reactive_progress = ReactiveValue(0.0)
        widget = ProgressBarWidget(reactive_progress)
        
        start_time = time.perf_counter()
        
        for i in range(1000):
            reactive_progress.value = i / 1000.0
        
        update_time = time.perf_counter() - start_time
        
        # Should handle 1000 reactive updates in under 100ms
        assert update_time < 0.1


class TestProgressBarWidgetIntegration:
    """Test ProgressBarWidget integration with other systems."""
    
    def test_progress_bar_widget__reactive_data_manager_integration(self):
        """Test integration with ReactiveDataManager."""
        from src.tinydisplay.core.reactive import ReactiveDataManager
        
        manager = ReactiveDataManager()
        binding = manager.create_direct_binding("progress_value", 0.3)
        
        # Create reactive value and bind to the binding
        reactive_progress = ReactiveValue(0.3)
        widget = ProgressBarWidget(reactive_progress)
        
        # Simulate binding update by directly setting reactive value
        reactive_progress.value = 0.7
        
        # Widget should reflect the change
        assert widget.progress == 0.7
    
    def test_progress_bar_widget__multiple_reactive_bindings(self):
        """Test widget with multiple reactive bindings."""
        progress_reactive = ReactiveValue(0.5)
        text_reactive = ReactiveValue("Loading...")
        
        widget = ProgressBarWidget(progress_reactive)
        widget.set_custom_text(text_reactive)
        
        # Update both values
        progress_reactive.value = 0.8
        text_reactive.value = "Almost done..."
        
        assert widget.progress == 0.8
        assert widget._custom_text.value == "Almost done..."
    
    def test_progress_bar_widget__canvas_integration(self):
        """Test ProgressBarWidget integration with canvas system."""
        widget = ProgressBarWidget(0.6)
        mock_canvas = Mock()
        
        # Should not raise errors
        widget.render(mock_canvas)
        
        # Verify widget state is correct
        assert widget.progress == 0.6
        assert widget.visible is True
    
    def test_progress_bar_widget__repr__returns_useful_string(self):
        """Test widget string representation."""
        widget = ProgressBarWidget(0.75, orientation=ProgressOrientation.VERTICAL)
        
        repr_str = repr(widget)
        
        assert "ProgressBarWidget" in repr_str
        assert "progress=0.75" in repr_str
        assert "vertical" in repr_str
        assert "animated=True" in repr_str
        assert "visible=True" in repr_str


class TestProgressDataPoint:
    """Test ProgressDataPoint functionality."""
    
    def test_progress_data_point__valid_values__correct_initialization(self):
        """Test ProgressDataPoint with valid values."""
        point = ProgressDataPoint(0.5, 1000.0)
        assert point.value == 0.5
        assert point.timestamp == 1000.0
    
    def test_progress_data_point__invalid_value_type__raises_error(self):
        """Test ProgressDataPoint with invalid value type raises TypeError."""
        with pytest.raises(TypeError, match="Progress value must be numeric"):
            ProgressDataPoint("invalid", 1000.0)
    
    def test_progress_data_point__invalid_timestamp_type__raises_error(self):
        """Test ProgressDataPoint with invalid timestamp type raises TypeError."""
        with pytest.raises(TypeError, match="Timestamp must be numeric"):
            ProgressDataPoint(0.5, "invalid")
    
    def test_progress_data_point__negative_timestamp__raises_error(self):
        """Test ProgressDataPoint with negative timestamp raises ValueError."""
        with pytest.raises(ValueError, match="Timestamp must be non-negative"):
            ProgressDataPoint(0.5, -1.0)


class TestProgressPrediction:
    """Test ProgressPrediction configuration and validation."""
    
    def test_progress_prediction__default_values__correct_initialization(self):
        """Test ProgressPrediction with default values."""
        prediction = ProgressPrediction()
        assert prediction.enabled is False
        assert prediction.min_samples == 3
        assert prediction.max_samples == 10
        assert prediction.max_prediction_time == 5.0
        assert prediction.confidence_decay_rate == 0.8
        assert prediction.min_confidence == 0.1
        assert prediction.rate_smoothing == 0.7
        assert prediction.current_rate is None
        assert prediction.confidence == 1.0
        assert prediction.last_prediction_time is None
    
    def test_progress_prediction__custom_values__correct_initialization(self):
        """Test ProgressPrediction with custom values."""
        prediction = ProgressPrediction(
            enabled=True,
            min_samples=5,
            max_samples=20,
            max_prediction_time=10.0,
            confidence_decay_rate=0.9,
            min_confidence=0.2,
            rate_smoothing=0.8
        )
        assert prediction.enabled is True
        assert prediction.min_samples == 5
        assert prediction.max_samples == 20
        assert prediction.max_prediction_time == 10.0
        assert prediction.confidence_decay_rate == 0.9
        assert prediction.min_confidence == 0.2
        assert prediction.rate_smoothing == 0.8
    
    def test_progress_prediction__invalid_min_samples__raises_error(self):
        """Test ProgressPrediction with invalid min_samples raises ValueError."""
        with pytest.raises(ValueError, match="min_samples must be at least 2"):
            ProgressPrediction(min_samples=1)
    
    def test_progress_prediction__invalid_max_samples__raises_error(self):
        """Test ProgressPrediction with invalid max_samples raises ValueError."""
        with pytest.raises(ValueError, match="max_samples must be >= min_samples"):
            ProgressPrediction(min_samples=5, max_samples=3)
    
    def test_progress_prediction__invalid_max_prediction_time__raises_error(self):
        """Test ProgressPrediction with invalid max_prediction_time raises ValueError."""
        with pytest.raises(ValueError, match="max_prediction_time must be positive"):
            ProgressPrediction(max_prediction_time=0.0)
    
    def test_progress_prediction__invalid_confidence_decay_rate__raises_error(self):
        """Test ProgressPrediction with invalid confidence_decay_rate raises ValueError."""
        with pytest.raises(ValueError, match="confidence_decay_rate must be between 0.0 and 1.0"):
            ProgressPrediction(confidence_decay_rate=1.5)
    
    def test_progress_prediction__invalid_min_confidence__raises_error(self):
        """Test ProgressPrediction with invalid min_confidence raises ValueError."""
        with pytest.raises(ValueError, match="min_confidence must be between 0.0 and 1.0"):
            ProgressPrediction(min_confidence=1.5)
    
    def test_progress_prediction__invalid_rate_smoothing__raises_error(self):
        """Test ProgressPrediction with invalid rate_smoothing raises ValueError."""
        with pytest.raises(ValueError, match="rate_smoothing must be between 0.0 and 1.0"):
            ProgressPrediction(rate_smoothing=1.5)


class TestProgressBarWidgetPredictive:
    """Test ProgressBarWidget predictive progress functionality."""
    
    def test_progress_bar_widget__with_prediction__initializes_correctly(self):
        """Test ProgressBarWidget initialization with prediction configuration."""
        prediction = ProgressPrediction(enabled=True, max_prediction_time=10.0)
        widget = ProgressBarWidget(0.2, prediction=prediction)
        
        assert widget.prediction.enabled is True
        assert widget.prediction.max_prediction_time == 10.0
        assert len(widget._progress_history) == 0
        assert widget.is_predicting is False  # No history yet
        assert widget.prediction_confidence == 1.0
        assert widget.progress_rate is None
    
    def test_progress_bar_widget__prediction_property__get_set(self):
        """Test prediction property getter and setter."""
        widget = ProgressBarWidget()
        new_prediction = ProgressPrediction(enabled=True, min_samples=5)
        
        widget.prediction = new_prediction
        
        assert widget.prediction is new_prediction
        assert widget.prediction.enabled is True
        assert widget.prediction.min_samples == 5
    
    def test_progress_bar_widget__disable_prediction__clears_state(self):
        """Test disabling prediction clears prediction state."""
        prediction = ProgressPrediction(enabled=True)
        widget = ProgressBarWidget(0.2, prediction=prediction)
        
        # Add some history
        widget._add_progress_data_point(0.3, 1000.0)
        widget._add_progress_data_point(0.4, 1001.0)
        
        # Disable prediction
        widget.prediction = ProgressPrediction(enabled=False)
        
        assert len(widget._progress_history) == 0
        assert widget.prediction.current_rate is None
        assert widget.prediction.confidence == 1.0
    
    def test_enable_prediction__enables_with_parameters(self):
        """Test enable_prediction method."""
        widget = ProgressBarWidget()
        
        widget.enable_prediction(True, max_prediction_time=15.0, min_samples=4)
        
        assert widget.prediction.enabled is True
        assert widget.prediction.max_prediction_time == 15.0
        assert widget.prediction.min_samples == 4
    
    def test_enable_prediction__disable__clears_state(self):
        """Test enable_prediction with False clears state."""
        widget = ProgressBarWidget()
        widget._add_progress_data_point(0.3, 1000.0)
        
        widget.enable_prediction(False)
        
        assert widget.prediction.enabled is False
        assert len(widget._progress_history) == 0
        assert widget.prediction.current_rate is None
    
    def test_get_prediction_info__returns_complete_info(self):
        """Test get_prediction_info returns comprehensive information."""
        prediction = ProgressPrediction(enabled=True)
        widget = ProgressBarWidget(0.2, prediction=prediction)
        
        info = widget.get_prediction_info()
        
        assert 'enabled' in info
        assert 'is_predicting' in info
        assert 'confidence' in info
        assert 'rate' in info
        assert 'samples_count' in info
        assert 'time_since_last_update' in info
        assert 'predicted_progress' in info
        assert info['enabled'] is True
        assert info['samples_count'] == 0
    
    def test_clear_prediction_history__clears_all_state(self):
        """Test clear_prediction_history clears all prediction state."""
        widget = ProgressBarWidget()
        widget._add_progress_data_point(0.3, 1000.0)
        widget._add_progress_data_point(0.4, 1001.0)
        widget._prediction.current_rate = 0.1
        
        widget.clear_prediction_history()
        
        assert len(widget._progress_history) == 0
        assert widget._prediction.current_rate is None
        assert widget._prediction.confidence == 1.0
        assert widget._prediction.last_prediction_time is None
    
    def test_add_progress_data_point__adds_to_history(self):
        """Test _add_progress_data_point adds data to history."""
        widget = ProgressBarWidget()
        
        widget._add_progress_data_point(0.3, 1000.0)
        widget._add_progress_data_point(0.4, 1001.0)
        
        assert len(widget._progress_history) == 2
        assert widget._progress_history[0].value == 0.3
        assert widget._progress_history[0].timestamp == 1000.0
        assert widget._progress_history[1].value == 0.4
        assert widget._progress_history[1].timestamp == 1001.0
    
    def test_add_progress_data_point__limits_history_size(self):
        """Test _add_progress_data_point limits history to max_samples."""
        prediction = ProgressPrediction(max_samples=3)
        widget = ProgressBarWidget(prediction=prediction)
        
        # Add more than max_samples
        for i in range(5):
            widget._add_progress_data_point(i * 0.1, 1000.0 + i)
        
        assert len(widget._progress_history) == 3
        # Should keep the most recent samples
        assert abs(widget._progress_history[0].value - 0.2) < 0.01
        assert abs(widget._progress_history[1].value - 0.3) < 0.01
        assert abs(widget._progress_history[2].value - 0.4) < 0.01
    
    def test_calculate_progress_rate__insufficient_data__returns_none(self):
        """Test _calculate_progress_rate with insufficient data returns None."""
        widget = ProgressBarWidget()
        
        # No data
        assert widget._calculate_progress_rate() is None
        
        # Only one data point
        widget._add_progress_data_point(0.3, 1000.0)
        assert widget._calculate_progress_rate() is None
    
    def test_calculate_progress_rate__calculates_rate_correctly(self):
        """Test _calculate_progress_rate calculates rate correctly."""
        widget = ProgressBarWidget()
        
        # Add data points with known rate: 0.1 progress per second
        widget._add_progress_data_point(0.2, 1000.0)
        widget._add_progress_data_point(0.3, 1001.0)  # +0.1 in 1 second
        widget._add_progress_data_point(0.4, 1002.0)  # +0.1 in 1 second
        
        rate = widget._calculate_progress_rate()
        
        assert rate is not None
        assert abs(rate - 0.1) < 0.01  # Should be approximately 0.1
    
    def test_calculate_progress_rate__smooths_with_previous_rate(self):
        """Test _calculate_progress_rate smooths with previous rate."""
        widget = ProgressBarWidget()
        widget._prediction.rate_smoothing = 0.5  # 50% smoothing
        
        # First, establish an initial rate by adding some data points
        widget._add_progress_data_point(0.1, 1000.0)
        widget._add_progress_data_point(0.15, 1001.0)  # Rate of 0.05
        
        # Verify initial rate
        initial_rate = widget._prediction.current_rate
        assert initial_rate is not None
        assert abs(initial_rate - 0.05) < 0.01
        
        # Now add a new data point with a different rate
        widget._add_progress_data_point(0.35, 1002.0)  # Rate of 0.2 from previous point
        
        # The calculation uses all recent samples:
        # Rates: 0.1->0.15 = 0.05, 0.15->0.35 = 0.2
        # Average: (0.05 + 0.2) / 2 = 0.125
        # Smoothed: 0.05 * 0.5 + 0.125 * 0.5 = 0.0875
        smoothed_rate = widget._prediction.current_rate
        assert smoothed_rate is not None
        assert abs(smoothed_rate - 0.0875) < 0.01
    
    def test_should_use_prediction__disabled__returns_false(self):
        """Test _should_use_prediction returns False when disabled."""
        widget = ProgressBarWidget()
        widget._prediction.enabled = False
        
        assert widget._should_use_prediction(time.time()) is False
    
    def test_should_use_prediction__insufficient_samples__returns_false(self):
        """Test _should_use_prediction returns False with insufficient samples."""
        prediction = ProgressPrediction(enabled=True, min_samples=3)
        widget = ProgressBarWidget(prediction=prediction)
        
        # Add only 2 samples (less than min_samples)
        widget._add_progress_data_point(0.2, 1000.0)
        widget._add_progress_data_point(0.3, 1001.0)
        
        assert widget._should_use_prediction(time.time()) is False
    
    def test_should_use_prediction__too_old__returns_false(self):
        """Test _should_use_prediction returns False when prediction is too old."""
        prediction = ProgressPrediction(enabled=True, max_prediction_time=2.0)
        widget = ProgressBarWidget(prediction=prediction)
        
        # Add sufficient samples
        widget._add_progress_data_point(0.2, 1000.0)
        widget._add_progress_data_point(0.3, 1001.0)
        widget._add_progress_data_point(0.4, 1002.0)
        
        # Set last update time to be too old
        widget._last_update_time = time.time() - 5.0  # 5 seconds ago
        
        assert widget._should_use_prediction(time.time()) is False
    
    def test_should_use_prediction__low_confidence__returns_false(self):
        """Test _should_use_prediction returns False with low confidence."""
        prediction = ProgressPrediction(enabled=True, min_confidence=0.5)
        widget = ProgressBarWidget(prediction=prediction)
        
        # Add sufficient samples
        widget._add_progress_data_point(0.2, 1000.0)
        widget._add_progress_data_point(0.3, 1001.0)
        widget._add_progress_data_point(0.4, 1002.0)
        
        # Set low confidence
        widget._prediction.confidence = 0.3
        
        assert widget._should_use_prediction(time.time()) is False
    
    def test_should_use_prediction__negative_rate__returns_false(self):
        """Test _should_use_prediction returns False with negative rate."""
        prediction = ProgressPrediction(enabled=True)
        widget = ProgressBarWidget(prediction=prediction)
        
        # Add samples with negative rate
        widget._add_progress_data_point(0.4, 1000.0)
        widget._add_progress_data_point(0.3, 1001.0)  # Decreasing progress
        widget._add_progress_data_point(0.2, 1002.0)
        
        assert widget._should_use_prediction(time.time()) is False
    
    def test_should_use_prediction__valid_conditions__returns_true(self):
        """Test _should_use_prediction returns True with valid conditions."""
        prediction = ProgressPrediction(enabled=True)
        widget = ProgressBarWidget(prediction=prediction)
        
        # Add sufficient samples with positive rate
        current_time = time.time()
        widget._add_progress_data_point(0.2, current_time - 2)
        widget._add_progress_data_point(0.3, current_time - 1)
        widget._add_progress_data_point(0.4, current_time)
        widget._last_update_time = current_time
        
        assert widget._should_use_prediction(current_time + 1) is True
    
    def test_get_predictive_progress__calculates_prediction(self):
        """Test _get_predictive_progress calculates predicted progress."""
        prediction = ProgressPrediction(enabled=True)
        widget = ProgressBarWidget(prediction=prediction)
        
        # Set up prediction state
        current_time = time.time()
        widget._last_known_progress = 0.5
        widget._last_update_time = current_time - 2.0  # 2 seconds ago
        widget._prediction.current_rate = 0.1  # 0.1 progress per second
        widget._prediction.confidence = 1.0
        
        # Mock should_use_prediction to return True
        widget._should_use_prediction = Mock(return_value=True)
        
        predicted = widget._get_predictive_progress(current_time)
        
        # Should predict: 0.5 + (0.1 * 2) = 0.7
        assert abs(predicted - 0.7) < 0.01
    
    def test_get_predictive_progress__blends_with_confidence(self):
        """Test _get_predictive_progress blends prediction with confidence."""
        prediction = ProgressPrediction(enabled=True)
        widget = ProgressBarWidget(prediction=prediction)
        
        # Set up prediction state
        current_time = time.time()
        widget._last_known_progress = 0.5
        widget._last_update_time = current_time - 1.0  # 1 second ago
        widget._prediction.current_rate = 0.2  # 0.2 progress per second
        widget._prediction.confidence = 0.5  # 50% confidence
        
        # Mock should_use_prediction to return True
        widget._should_use_prediction = Mock(return_value=True)
        
        predicted = widget._get_predictive_progress(current_time)
        
        # Predicted would be: 0.5 + (0.2 * 1) = 0.7
        # Blended: 0.5 * (1 - 0.5) + 0.7 * 0.5 = 0.25 + 0.35 = 0.6
        assert abs(predicted - 0.6) < 0.01
    
    def test_update_prediction_confidence__decays_over_time(self):
        """Test _update_prediction_confidence decays confidence over time."""
        prediction = ProgressPrediction(enabled=True, confidence_decay_rate=0.8)
        widget = ProgressBarWidget(prediction=prediction)
        
        # Set initial state
        initial_time = 1000.0
        widget._prediction.confidence = 1.0
        widget._prediction.last_prediction_time = initial_time
        
        # Update after 1 second
        widget._update_prediction_confidence(initial_time + 1.0)
        
        # Confidence should decay: 1.0 * (0.8^1) = 0.8
        assert abs(widget._prediction.confidence - 0.8) < 0.01
    
    def test_update_prediction_confidence__respects_minimum(self):
        """Test _update_prediction_confidence respects minimum confidence."""
        prediction = ProgressPrediction(enabled=True, confidence_decay_rate=0.1, min_confidence=0.2)
        widget = ProgressBarWidget(prediction=prediction)
        
        # Set initial state
        initial_time = 1000.0
        widget._prediction.confidence = 0.3
        widget._prediction.last_prediction_time = initial_time
        
        # Update after long time to force decay below minimum
        widget._update_prediction_confidence(initial_time + 10.0)
        
        # Should not go below min_confidence
        assert widget._prediction.confidence >= 0.2
    
    def test_animated_progress__uses_prediction_when_enabled(self):
        """Test animated_progress uses prediction when conditions are met."""
        prediction = ProgressPrediction(enabled=True)
        widget = ProgressBarWidget(0.3, prediction=prediction)
        
        # Mock prediction methods
        widget._should_use_prediction = Mock(return_value=True)
        widget._get_predictive_progress = Mock(return_value=0.6)
        
        result = widget.animated_progress
        
        assert result == 0.6
        widget._should_use_prediction.assert_called_once()
        widget._get_predictive_progress.assert_called_once()
    
    def test_animated_progress__falls_back_to_animation(self):
        """Test animated_progress falls back to standard animation when prediction disabled."""
        widget = ProgressBarWidget(0.4)
        widget._animation.enabled = True
        widget._animation.current_value = 0.5
        
        result = widget.animated_progress
        
        assert result == 0.5
    
    def test_reactive_progress_change__updates_prediction_history(self):
        """Test reactive progress changes update prediction history."""
        prediction = ProgressPrediction(enabled=True)
        reactive_progress = ReactiveValue(0.2)
        widget = ProgressBarWidget(reactive_progress, prediction=prediction)
        
        # Change reactive value
        reactive_progress.value = 0.4
        
        # Should have added data point to history
        assert len(widget._progress_history) > 0
        assert widget._progress_history[-1].value == 0.4
        assert widget._last_known_progress == 0.4


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 