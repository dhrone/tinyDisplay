#!/usr/bin/env python3
"""
ProgressBar Widget Implementation

Provides progress bar rendering with reactive data binding, smooth animations,
customizable styling, multiple orientations, and predictive progress estimation
for the tinyDisplay framework.
"""

from typing import Union, Optional, Tuple, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum
import threading
import time
import math

from .base import Widget, ReactiveValue, WidgetBounds
from ..core.reactive import ReactiveDataManager
from ..core.ring_buffer import RingBuffer
from ..animation.tick_based import TickAnimationEngine, create_tick_fade_animation, EasingFunction


class ProgressOrientation(Enum):
    """Progress bar orientation modes."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class ProgressTextPosition(Enum):
    """Progress text overlay positions."""
    NONE = "none"          # No text overlay
    CENTER = "center"      # Center of progress bar
    LEFT = "left"          # Left side (or top for vertical)
    RIGHT = "right"        # Right side (or bottom for vertical)
    OUTSIDE_LEFT = "outside_left"    # Outside left edge
    OUTSIDE_RIGHT = "outside_right"  # Outside right edge


@dataclass
class ProgressDataPoint:
    """Historical progress data point for predictive analysis."""
    value: float
    timestamp: float
    
    def __post_init__(self):
        """Validate data point parameters."""
        if not isinstance(self.value, (int, float)):
            raise TypeError("Progress value must be numeric")
        if not isinstance(self.timestamp, (int, float)):
            raise TypeError("Timestamp must be numeric")
        if self.timestamp < 0:
            raise ValueError("Timestamp must be non-negative")


@dataclass
class ProgressPrediction:
    """Predictive progress configuration and state."""
    enabled: bool = False
    min_samples: int = 3  # Minimum data points for reliable prediction
    max_samples: int = 10  # Maximum samples to keep for rate calculation
    max_prediction_time: float = 5.0  # Maximum seconds to predict ahead
    confidence_decay_rate: float = 0.8  # Confidence decay per second
    min_confidence: float = 0.1  # Minimum confidence to show prediction
    rate_smoothing: float = 0.7  # Smoothing factor for rate calculation (0.0-1.0)
    
    # Internal prediction state
    current_rate: Optional[float] = None
    confidence: float = 1.0
    last_prediction_time: Optional[float] = None
    
    def __post_init__(self):
        """Validate prediction parameters."""
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2")
        if self.max_samples < self.min_samples:
            raise ValueError("max_samples must be >= min_samples")
        if self.max_prediction_time <= 0.0:
            raise ValueError("max_prediction_time must be positive")
        if not 0.0 <= self.confidence_decay_rate <= 1.0:
            raise ValueError("confidence_decay_rate must be between 0.0 and 1.0")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0.0 and 1.0")
        if not 0.0 <= self.rate_smoothing <= 1.0:
            raise ValueError("rate_smoothing must be between 0.0 and 1.0")


@dataclass
class ProgressStyle:
    """Progress bar styling configuration."""
    # Bar colors
    background_color: Tuple[int, int, int] = (64, 64, 64)
    fill_color: Tuple[int, int, int] = (0, 150, 255)
    border_color: Tuple[int, int, int] = (128, 128, 128)
    
    # Dimensions
    border_width: int = 1
    border_radius: int = 0
    bar_height: Optional[int] = None  # None = use widget height
    
    # Text styling
    text_color: Tuple[int, int, int] = (255, 255, 255)
    text_font_size: int = 12
    text_font_family: str = "default"
    show_percentage: bool = True
    text_format: str = "{:.1f}%"  # Format string for percentage
    
    # Effects
    gradient_enabled: bool = False
    gradient_end_color: Optional[Tuple[int, int, int]] = None
    shadow_enabled: bool = False
    shadow_offset: Tuple[int, int] = (2, 2)
    shadow_color: Tuple[int, int, int] = (0, 0, 0)
    shadow_blur: int = 2
    
    # Animation
    pulse_enabled: bool = False
    pulse_speed: float = 1.0  # Pulses per second
    pulse_intensity: float = 0.2  # Brightness variation (0.0-1.0)
    
    # Predictive progress styling
    prediction_color: Tuple[int, int, int] = (100, 200, 255)  # Lighter blue for predictions
    prediction_alpha: float = 0.6  # Transparency for predicted portion
    show_prediction_indicator: bool = True  # Show visual indicator for predicted vs actual
    
    def __post_init__(self):
        """Validate progress style parameters."""
        if not all(0 <= c <= 255 for c in self.background_color):
            raise ValueError("Background color values must be between 0 and 255")
        if not all(0 <= c <= 255 for c in self.fill_color):
            raise ValueError("Fill color values must be between 0 and 255")
        if not all(0 <= c <= 255 for c in self.border_color):
            raise ValueError("Border color values must be between 0 and 255")
        if not all(0 <= c <= 255 for c in self.text_color):
            raise ValueError("Text color values must be between 0 and 255")
        if not all(0 <= c <= 255 for c in self.prediction_color):
            raise ValueError("Prediction color values must be between 0 and 255")
        if self.border_width < 0:
            raise ValueError("Border width must be non-negative")
        if self.border_radius < 0:
            raise ValueError("Border radius must be non-negative")
        if self.text_font_size <= 0:
            raise ValueError("Text font size must be positive")
        if not 0.0 <= self.pulse_intensity <= 1.0:
            raise ValueError("Pulse intensity must be between 0.0 and 1.0")
        if self.pulse_speed <= 0.0:
            raise ValueError("Pulse speed must be positive")
        if not 0.0 <= self.prediction_alpha <= 1.0:
            raise ValueError("Prediction alpha must be between 0.0 and 1.0")


@dataclass
class ProgressAnimation:
    """Progress bar animation configuration."""
    enabled: bool = True
    duration: float = 0.3  # Animation duration in seconds
    easing: EasingFunction = EasingFunction.EASE_OUT
    
    # Internal animation state
    start_time: Optional[float] = None
    start_value: Optional[float] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    
    def __post_init__(self):
        """Validate animation parameters."""
        if self.duration <= 0.0:
            raise ValueError("Animation duration must be positive")


class ProgressBarWidget(Widget):
    """Progress bar widget with reactive data binding, smooth animations, and predictive progress.
    
    Supports horizontal and vertical orientations, customizable styling,
    text overlays, smooth animations with various easing functions, and
    predictive progress estimation that forecasts progress between data updates.
    Integrates with the reactive system for dynamic progress updates.
    
    Args:
        progress: Progress value (0.0-1.0) or reactive value
        orientation: Bar orientation (horizontal or vertical)
        style: Progress bar styling configuration
        text_position: Position of progress text overlay
        animation: Animation configuration
        prediction: Predictive progress configuration
        **kwargs: Additional widget arguments
        
    Example:
        >>> # Basic progress bar
        >>> widget = ProgressBarWidget(0.75)
        
        >>> # With predictive progress for file downloads
        >>> prediction = ProgressPrediction(enabled=True, max_prediction_time=10.0)
        >>> widget = ProgressBarWidget(0.0, prediction=prediction)
        >>> widget.bind_data("progress", download_progress_source)
    """
    
    __slots__ = (
        '_progress', '_orientation', '_style', '_text_position', '_animation', '_prediction',
        '_cached_progress', '_last_render_time', '_animation_lock',
        '_text_overlay', '_custom_text', '_min_value', '_max_value',
        '_progress_history', '_last_update_time', '_last_known_progress'
    )
    
    def __init__(
        self,
        progress: Union[float, ReactiveValue] = 0.0,
        orientation: ProgressOrientation = ProgressOrientation.HORIZONTAL,
        style: Optional[ProgressStyle] = None,
        text_position: ProgressTextPosition = ProgressTextPosition.CENTER,
        animation: Optional[ProgressAnimation] = None,
        prediction: Optional[ProgressPrediction] = None,
        min_value: float = 0.0,
        max_value: float = 1.0,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        
        # Progress configuration
        self._progress = self._ensure_reactive(progress)
        self._progress.bind(self._on_progress_changed)
        self._orientation = orientation
        self._style = style or ProgressStyle()
        self._text_position = text_position
        self._animation = animation or ProgressAnimation()
        self._prediction = prediction or ProgressPrediction()
        
        # Value range
        self._min_value = min_value
        self._max_value = max_value
        if min_value >= max_value:
            raise ValueError("min_value must be less than max_value")
        
        # Animation state
        self._cached_progress = self._normalize_progress(self._progress.value)
        self._last_render_time = 0.0
        self._animation_lock = threading.RLock()
        
        # Text overlay
        self._text_overlay: Optional[str] = None
        self._custom_text: Optional[ReactiveValue] = None
        
        # Predictive progress state
        self._progress_history: List[ProgressDataPoint] = []
        self._last_update_time = time.time()
        self._last_known_progress = self._cached_progress
        
        # Validate initial progress
        self._validate_progress(self._progress.value)
        
        # Initialize animation
        if self._animation.enabled:
            self._animation.current_value = self._cached_progress
        
        # Bind to size changes for re-rendering
        self._size.bind(self._on_size_changed)
    
    @property
    def progress(self) -> float:
        """Get current progress value."""
        return self._progress.value
    
    @progress.setter
    def progress(self, value: Union[float, ReactiveValue]) -> None:
        """Set progress value."""
        if isinstance(value, ReactiveValue):
            self._progress.unbind(self._on_progress_changed)
            self._progress = value
            self._progress.bind(self._on_progress_changed)
        else:
            self._progress.value = value
        self._validate_progress(self._progress.value)
        self._start_animation()
    
    @property
    def orientation(self) -> ProgressOrientation:
        """Get current orientation."""
        return self._orientation
    
    @orientation.setter
    def orientation(self, orientation: ProgressOrientation) -> None:
        """Set orientation."""
        self._orientation = orientation
        self._mark_dirty()
    
    @property
    def style(self) -> ProgressStyle:
        """Get current style."""
        return self._style
    
    @style.setter
    def style(self, style: ProgressStyle) -> None:
        """Set style."""
        self._style = style
        self._mark_dirty()
    
    @property
    def text_position(self) -> ProgressTextPosition:
        """Get current text position."""
        return self._text_position
    
    @text_position.setter
    def text_position(self, position: ProgressTextPosition) -> None:
        """Set text position."""
        self._text_position = position
        self._mark_dirty()
    
    @property
    def animation(self) -> ProgressAnimation:
        """Get animation configuration."""
        return self._animation
    
    @animation.setter
    def animation(self, animation: ProgressAnimation) -> None:
        """Set animation configuration."""
        self._animation = animation
        if animation.enabled and animation.current_value is None:
            animation.current_value = self._cached_progress
    
    @property
    def prediction(self) -> ProgressPrediction:
        """Get prediction configuration."""
        return self._prediction
    
    @prediction.setter
    def prediction(self, prediction: ProgressPrediction) -> None:
        """Set prediction configuration."""
        self._prediction = prediction
        if not prediction.enabled:
            # Clear prediction state when disabled
            self._progress_history.clear()
            prediction.current_rate = None
            prediction.confidence = 1.0
    
    @property
    def animated_progress(self) -> float:
        """Get current animated progress value (includes predictions)."""
        current_time = time.time()
        
        # Use predictive progress if enabled and conditions are met
        if (self._prediction.enabled and 
            self._should_use_prediction(current_time)):
            return self._get_predictive_progress(current_time)
        
        # Fall back to standard animation
        if not self._animation.enabled:
            return self._cached_progress
        
        with self._animation_lock:
            if self._animation.current_value is not None:
                return self._animation.current_value
            return self._cached_progress
    
    @property
    def progress_percentage(self) -> float:
        """Get progress as percentage (0-100)."""
        return self.animated_progress * 100.0
    
    @property
    def prediction_confidence(self) -> float:
        """Get current prediction confidence (0.0-1.0)."""
        if not self._prediction.enabled:
            return 0.0
        return self._prediction.confidence
    
    @property
    def is_predicting(self) -> bool:
        """Check if widget is currently showing predicted progress."""
        if not self._prediction.enabled:
            return False
        current_time = time.time()
        return self._should_use_prediction(current_time)
    
    @property
    def progress_rate(self) -> Optional[float]:
        """Get current progress rate (progress units per second)."""
        return self._prediction.current_rate
    
    def set_custom_text(self, text: Union[str, ReactiveValue, None]) -> None:
        """Set custom text overlay instead of percentage."""
        if text is None:
            self._custom_text = None
        else:
            self._custom_text = self._ensure_reactive(text)
            self._custom_text.bind(self._on_custom_text_changed)
        self._mark_dirty()
    
    def set_progress_range(self, min_value: float, max_value: float) -> None:
        """Set the progress value range."""
        if min_value >= max_value:
            raise ValueError("min_value must be less than max_value")
        self._min_value = min_value
        self._max_value = max_value
        self._validate_progress(self._progress.value)
        self._mark_dirty()
    
    def set_fill_color(self, color: Tuple[int, int, int]) -> None:
        """Set progress bar fill color."""
        if not all(0 <= c <= 255 for c in color):
            raise ValueError("Color values must be between 0 and 255")
        self._style.fill_color = color
        self._mark_dirty()
    
    def set_background_color(self, color: Tuple[int, int, int]) -> None:
        """Set progress bar background color."""
        if not all(0 <= c <= 255 for c in color):
            raise ValueError("Color values must be between 0 and 255")
        self._style.background_color = color
        self._mark_dirty()
    
    def enable_pulse(self, enabled: bool = True, speed: float = 1.0, intensity: float = 0.2) -> None:
        """Enable or disable pulse animation."""
        self._style.pulse_enabled = enabled
        if enabled:
            if speed <= 0.0:
                raise ValueError("Pulse speed must be positive")
            if not 0.0 <= intensity <= 1.0:
                raise ValueError("Pulse intensity must be between 0.0 and 1.0")
            self._style.pulse_speed = speed
            self._style.pulse_intensity = intensity
        self._mark_dirty()
    
    def enable_gradient(self, enabled: bool = True, end_color: Optional[Tuple[int, int, int]] = None) -> None:
        """Enable or disable gradient fill."""
        self._style.gradient_enabled = enabled
        if enabled and end_color:
            if not all(0 <= c <= 255 for c in end_color):
                raise ValueError("End color values must be between 0 and 255")
            self._style.gradient_end_color = end_color
        self._mark_dirty()
    
    def get_progress_bounds(self) -> WidgetBounds:
        """Get the bounds of the filled progress area."""
        progress = self.animated_progress
        x, y = self.position
        width, height = self.size
        
        if self._orientation == ProgressOrientation.HORIZONTAL:
            fill_width = int(width * progress)
            return WidgetBounds(x, y, fill_width, height)
        else:
            fill_height = int(height * progress)
            # Vertical progress fills from bottom up
            fill_y = y + height - fill_height
            return WidgetBounds(x, fill_y, width, fill_height)
    
    def render(self, canvas: 'Canvas') -> None:
        """Render the progress bar widget to the canvas."""
        if not self.visible or self.alpha <= 0:
            return
        
        current_time = time.time()
        self._last_render_time = current_time
        
        # Update animation if enabled
        if self._animation.enabled:
            self._update_animation(current_time)
        
        # Render progress bar components
        self._render_background(canvas)
        self._render_progress_fill(canvas)
        self._render_border(canvas)
        self._render_text_overlay(canvas)
        self._render_effects(canvas)
        
        # Mark as clean
        self.mark_clean()
    
    def _ensure_reactive(self, value: Any) -> ReactiveValue:
        """Convert values to ReactiveValue instances."""
        if isinstance(value, ReactiveValue):
            return value
        return ReactiveValue(value)
    
    def _validate_progress(self, value: float) -> None:
        """Validate progress value is within acceptable range."""
        if not isinstance(value, (int, float)):
            raise TypeError(f"Progress value must be numeric, got {type(value)}")
        if not self._min_value <= value <= self._max_value:
            raise ValueError(f"Progress value must be between {self._min_value} and {self._max_value}, got {value}")
    
    def _normalize_progress(self, value: float) -> float:
        """Normalize progress value to 0.0-1.0 range."""
        return (value - self._min_value) / (self._max_value - self._min_value)
    
    def _on_progress_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle reactive progress updates with prediction tracking."""
        self._validate_progress(new_value)
        
        # Update prediction tracking
        current_time = time.time()
        normalized_progress = self._normalize_progress(new_value)
        
        if self._prediction.enabled:
            # Add data point to prediction history
            self._add_progress_data_point(normalized_progress, current_time)
            
            # Update tracking variables
            self._last_update_time = current_time
            self._last_known_progress = normalized_progress
        
        self._start_animation()
        self._mark_dirty()
    
    def _on_custom_text_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle reactive custom text updates."""
        self._mark_dirty()
    
    def _on_size_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle size changes that require re-rendering."""
        self._mark_dirty()
    
    def _start_animation(self) -> None:
        """Start progress animation using tick-based system."""
        if not self._animation.enabled:
            return
        
        # Convert duration from seconds to ticks (assuming 60 FPS)
        duration_ticks = int(self._animation.duration * 60)
        
        # Start tick-based animation
        self.start_tick_based_animation(
            animation_type='progress_transition',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            start_value=self._animation.start_value,
            target_value=self._animation.target_value,
            easing=self._animation.easing.value
        )
    
    def _update_animation(self, current_time: float) -> None:
        """Update progress animation - now handled by tick-based system."""
        # This method is kept for backward compatibility but animation
        # is now handled by the tick-based system in update_animations()
        pass
    
    # Tick-based animation methods
    def set_progress_animated(self, target_progress: float, duration_ticks: int = 60,
                             easing: str = "ease_out", on_complete: Optional[Callable] = None) -> bool:
        """Animate progress to target value using tick-based animation.
        
        Args:
            target_progress: Target progress value (0.0 to 1.0)
            duration_ticks: Animation duration in ticks (default 60 = 1s at 60fps)
            easing: Easing function name
            on_complete: Callback when animation completes
            
        Returns:
            True if animation started successfully
        """
        self._validate_progress(target_progress)
        current_progress = self._normalize_progress(self._progress.value)
        
        return self.start_tick_based_animation(
            animation_type='progress_transition',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            start_value=current_progress,
            target_value=target_progress,
            easing=easing,
            on_complete=on_complete
        )
    
    def pulse_animated(self, duration_ticks: int = 120, intensity: float = 0.3,
                      on_complete: Optional[Callable] = None) -> bool:
        """Animate progress bar pulse effect using tick-based animation.
        
        Args:
            duration_ticks: Animation duration in ticks (default 120 = 2s at 60fps)
            intensity: Pulse intensity (0.0 to 1.0)
            on_complete: Callback when animation completes
            
        Returns:
            True if animation started successfully
        """
        if not 0.0 <= intensity <= 1.0:
            raise ValueError("Pulse intensity must be between 0.0 and 1.0")
        
        return self.start_tick_based_animation(
            animation_type='pulse',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            intensity=intensity,
            easing='ease_in_out',
            on_complete=on_complete
        )
    
    def fill_color_animated(self, target_color: Tuple[int, int, int], duration_ticks: int = 60,
                           easing: str = "ease_in_out", on_complete: Optional[Callable] = None) -> bool:
        """Animate progress bar fill color transition using tick-based animation.
        
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
            animation_type='color_transition',
            start_tick=0,  # Will be set by rendering engine
            duration_ticks=duration_ticks,
            start_color=current_color,
            target_color=target_color,
            easing=easing,
            on_complete=on_complete
        )
    
    def fade_in_animated(self, duration_ticks: int = 30, easing: str = "ease_out",
                        on_complete: Optional[Callable] = None) -> bool:
        """Animate progress bar fade in using tick-based animation.
        
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
        """Animate progress bar fade out using tick-based animation.
        
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
    
    def _apply_animation_progress(self, progress: float) -> None:
        """Apply animation progress to progress bar properties.
        
        Args:
            progress: Animation progress from 0.0 to 1.0
        """
        # Call parent implementation for base animations (alpha, etc.)
        super()._apply_animation_progress(progress)
        
        if not self._current_animation:
            return
        
        animation_type = self._current_animation['type']
        
        if animation_type == 'progress_transition':
            # Interpolate between start and target progress values
            start_value = self._current_animation['start_value']
            target_value = self._current_animation['target_value']
            
            current_value = start_value + (target_value - start_value) * progress
            
            # Update animation current value
            self._animation.current_value = current_value
            self._mark_dirty()
            
        elif animation_type == 'pulse':
            # Apply pulse effect to fill color brightness
            intensity = self._current_animation['intensity']
            
            # Create sine wave pulse effect
            import math
            pulse_factor = 1.0 + intensity * math.sin(progress * math.pi * 2)
            
            # Apply pulse to fill color
            base_color = self._style.fill_color
            pulsed_color = tuple(
                min(255, int(base_color[i] * pulse_factor))
                for i in range(3)
            )
            
            # Temporarily store pulsed color (would need proper implementation)
            self._mark_dirty()
            
        elif animation_type == 'color_transition':
            # Interpolate between start and target colors
            start_color = self._current_animation['start_color']
            target_color = self._current_animation['target_color']
            
            current_color = tuple(
                int(start_color[i] + (target_color[i] - start_color[i]) * progress)
                for i in range(3)
            )
            
            # Update fill color
            self._style.fill_color = current_color
            self._mark_dirty()
    
    def _complete_animation(self) -> None:
        """Complete the current animation and finalize progress bar properties."""
        if not self._current_animation:
            return
        
        animation_type = self._current_animation['type']
        
        if animation_type == 'progress_transition':
            # Set final progress value
            target_value = self._current_animation['target_value']
            self._animation.current_value = target_value
            
            # Update actual progress if this was a direct progress animation
            if 'target_progress' in self._current_animation:
                self._progress.value = self._current_animation['target_progress']
            
        elif animation_type == 'color_transition':
            # Set final color
            self._style.fill_color = self._current_animation['target_color']
            
        elif animation_type == 'pulse':
            # Restore original fill color after pulse
            # (pulse effect should not permanently change color)
            pass
        
        # Call parent implementation to handle completion
        super()._complete_animation()
    
    def _render_background(self, canvas: 'Canvas') -> None:
        """Render progress bar background."""
        # This is a placeholder for actual canvas integration
        # Real implementation would integrate with the canvas rendering backend
        pass
    
    def _render_progress_fill(self, canvas: 'Canvas') -> None:
        """Render progress bar fill with optional gradient and pulse effects."""
        progress_bounds = self.get_progress_bounds()
        
        # Calculate fill color with pulse effect
        fill_color = self._style.fill_color
        if self._style.pulse_enabled:
            pulse_factor = self._calculate_pulse_factor()
            fill_color = self._apply_pulse_to_color(fill_color, pulse_factor)
        
        # Render fill (placeholder for canvas integration)
        pass
    
    def _render_border(self, canvas: 'Canvas') -> None:
        """Render progress bar border."""
        if self._style.border_width > 0:
            # Render border (placeholder for canvas integration)
            pass
    
    def _render_text_overlay(self, canvas: 'Canvas') -> None:
        """Render progress text overlay."""
        if self._text_position == ProgressTextPosition.NONE:
            return
        
        # Get text to display
        if self._custom_text:
            text = str(self._custom_text.value)
        elif self._style.show_percentage:
            percentage = self.progress_percentage
            text = self._style.text_format.format(percentage)
        else:
            return
        
        # Calculate text position
        text_x, text_y = self._calculate_text_position()
        
        # Render text (placeholder for canvas integration)
        pass
    
    def _render_effects(self, canvas: 'Canvas') -> None:
        """Render visual effects like shadows."""
        if self._style.shadow_enabled:
            # Render shadow (placeholder for canvas integration)
            pass
    
    def _calculate_pulse_factor(self) -> float:
        """Calculate pulse animation factor."""
        if not self._style.pulse_enabled:
            return 1.0
        
        current_time = time.time()
        pulse_cycle = (current_time * self._style.pulse_speed) % 1.0
        pulse_wave = math.sin(pulse_cycle * 2 * math.pi)
        return 1.0 + (pulse_wave * self._style.pulse_intensity)
    
    def _apply_pulse_to_color(self, color: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
        """Apply pulse factor to color."""
        r, g, b = color
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return (r, g, b)
    
    def _calculate_text_position(self) -> Tuple[int, int]:
        """Calculate text overlay position."""
        x, y = self.position
        width, height = self.size
        
        if self._text_position == ProgressTextPosition.CENTER:
            return (x + width // 2, y + height // 2)
        elif self._text_position == ProgressTextPosition.LEFT:
            if self._orientation == ProgressOrientation.HORIZONTAL:
                return (x + 10, y + height // 2)
            else:
                return (x + width // 2, y + 10)
        elif self._text_position == ProgressTextPosition.RIGHT:
            if self._orientation == ProgressOrientation.HORIZONTAL:
                return (x + width - 10, y + height // 2)
            else:
                return (x + width // 2, y + height - 10)
        elif self._text_position == ProgressTextPosition.OUTSIDE_LEFT:
            if self._orientation == ProgressOrientation.HORIZONTAL:
                return (x - 5, y + height // 2)
            else:
                return (x + width // 2, y - 5)
        elif self._text_position == ProgressTextPosition.OUTSIDE_RIGHT:
            if self._orientation == ProgressOrientation.HORIZONTAL:
                return (x + width + 5, y + height // 2)
            else:
                return (x + width // 2, y + height + 5)
        else:
            return (x + width // 2, y + height // 2)
    
    def __repr__(self) -> str:
        return (f"ProgressBarWidget(id={self.widget_id}, progress={self.progress:.2f}, "
                f"orientation={self._orientation.value}, animated={self._animation.enabled}, visible={self.visible})")
    
    def enable_prediction(self, enabled: bool = True, max_prediction_time: float = 5.0, 
                         min_samples: int = 3) -> None:
        """Enable or disable predictive progress."""
        self._prediction.enabled = enabled
        if enabled:
            self._prediction.max_prediction_time = max_prediction_time
            self._prediction.min_samples = min_samples
        else:
            # Clear prediction state
            self._progress_history.clear()
            self._prediction.current_rate = None
            self._prediction.confidence = 1.0
        self._mark_dirty()
    
    def get_prediction_info(self) -> Dict[str, Any]:
        """Get detailed prediction information for debugging/monitoring."""
        return {
            'enabled': self._prediction.enabled,
            'is_predicting': self.is_predicting,
            'confidence': self.prediction_confidence,
            'rate': self.progress_rate,
            'samples_count': len(self._progress_history),
            'time_since_last_update': time.time() - self._last_update_time,
            'predicted_progress': self.animated_progress if self.is_predicting else None
        }
    
    def clear_prediction_history(self) -> None:
        """Clear prediction history and reset prediction state."""
        self._progress_history.clear()
        self._prediction.current_rate = None
        self._prediction.confidence = 1.0
        self._prediction.last_prediction_time = None
    
    def _should_use_prediction(self, current_time: float) -> bool:
        """Determine if predictive progress should be used."""
        if not self._prediction.enabled:
            return False
        
        # Need minimum samples for prediction
        if len(self._progress_history) < self._prediction.min_samples:
            return False
        
        # Check if we're within prediction time window
        time_since_update = current_time - self._last_update_time
        if time_since_update > self._prediction.max_prediction_time:
            return False
        
        # Check if confidence is above minimum threshold
        if self._prediction.confidence < self._prediction.min_confidence:
            return False
        
        # Only predict if we have a positive rate (progress is advancing)
        if self._prediction.current_rate is None or self._prediction.current_rate <= 0:
            return False
        
        return True
    
    def _get_predictive_progress(self, current_time: float) -> float:
        """Calculate predicted progress based on historical data."""
        if not self._should_use_prediction(current_time):
            return self._cached_progress
        
        # Update confidence based on time elapsed
        self._update_prediction_confidence(current_time)
        
        # Calculate predicted progress
        time_since_update = current_time - self._last_update_time
        predicted_progress = self._last_known_progress + (self._prediction.current_rate * time_since_update)
        
        # Apply confidence factor to blend between known and predicted
        confidence_factor = self._prediction.confidence
        blended_progress = (self._last_known_progress * (1 - confidence_factor) + 
                           predicted_progress * confidence_factor)
        
        # Clamp to valid range
        return max(0.0, min(1.0, blended_progress))
    
    def _update_prediction_confidence(self, current_time: float) -> None:
        """Update prediction confidence based on time elapsed."""
        if self._prediction.last_prediction_time is None:
            self._prediction.last_prediction_time = current_time
            return
        
        # Decay confidence over time
        time_delta = current_time - self._prediction.last_prediction_time
        decay_factor = math.pow(self._prediction.confidence_decay_rate, time_delta)
        self._prediction.confidence = max(
            self._prediction.min_confidence,
            self._prediction.confidence * decay_factor
        )
        
        self._prediction.last_prediction_time = current_time
    
    def _calculate_progress_rate(self) -> Optional[float]:
        """Calculate progress rate from historical data points."""
        if len(self._progress_history) < 2:
            return None
        
        # Use recent samples for rate calculation
        recent_samples = self._progress_history[-self._prediction.min_samples:]
        
        if len(recent_samples) < 2:
            return None
        
        # Calculate rates between consecutive points
        rates = []
        for i in range(1, len(recent_samples)):
            prev_point = recent_samples[i - 1]
            curr_point = recent_samples[i]
            
            time_delta = curr_point.timestamp - prev_point.timestamp
            if time_delta > 0:
                rate = (curr_point.value - prev_point.value) / time_delta
                rates.append(rate)
        
        if not rates:
            return None
        
        # Calculate smoothed average rate
        if self._prediction.current_rate is None:
            # First rate calculation
            new_rate = sum(rates) / len(rates)
        else:
            # Smooth with previous rate
            current_avg = sum(rates) / len(rates)
            smoothing = self._prediction.rate_smoothing
            new_rate = (self._prediction.current_rate * smoothing + 
                       current_avg * (1 - smoothing))
        
        return new_rate
    
    def _add_progress_data_point(self, progress: float, timestamp: float) -> None:
        """Add a new progress data point to history."""
        # Create new data point
        data_point = ProgressDataPoint(progress, timestamp)
        
        # Add to history
        self._progress_history.append(data_point)
        
        # Limit history size
        if len(self._progress_history) > self._prediction.max_samples:
            self._progress_history.pop(0)
        
        # Recalculate rate
        self._prediction.current_rate = self._calculate_progress_rate()
        
        # Reset confidence for new data
        self._prediction.confidence = 1.0
        self._prediction.last_prediction_time = timestamp 