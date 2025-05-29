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
    ProgressOrientation, ProgressTextPosition, EasingFunction
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 