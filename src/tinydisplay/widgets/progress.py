#!/usr/bin/env python3
"""
ProgressBar Widget Implementation

Provides progress bar rendering with reactive data binding, smooth animations,
customizable styling, and multiple orientations for the tinyDisplay framework.
"""

from typing import Union, Optional, Tuple, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import threading
import time
import math

from .base import Widget, ReactiveValue, WidgetBounds
from ..core.reactive import ReactiveDataManager


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


class EasingFunction(Enum):
    """Animation easing functions."""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"


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
    """Progress bar widget with reactive data binding and smooth animations.
    
    Supports horizontal and vertical orientations, customizable styling,
    text overlays, and smooth animations with various easing functions.
    Integrates with the reactive system for dynamic progress updates.
    
    Args:
        progress: Progress value (0.0-1.0) or reactive value
        orientation: Bar orientation (horizontal or vertical)
        style: Progress bar styling configuration
        text_position: Position of progress text overlay
        animation: Animation configuration
        **kwargs: Additional widget arguments
        
    Example:
        >>> widget = ProgressBarWidget(0.75, 
        ...                           orientation=ProgressOrientation.HORIZONTAL,
        ...                           style=ProgressStyle(fill_color=(0, 255, 0)))
        >>> widget.bind_data("progress", reactive_data_source)
    """
    
    __slots__ = (
        '_progress', '_orientation', '_style', '_text_position', '_animation',
        '_cached_progress', '_last_render_time', '_animation_lock',
        '_text_overlay', '_custom_text', '_min_value', '_max_value'
    )
    
    def __init__(
        self,
        progress: Union[float, ReactiveValue] = 0.0,
        orientation: ProgressOrientation = ProgressOrientation.HORIZONTAL,
        style: Optional[ProgressStyle] = None,
        text_position: ProgressTextPosition = ProgressTextPosition.CENTER,
        animation: Optional[ProgressAnimation] = None,
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
    def animated_progress(self) -> float:
        """Get current animated progress value."""
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
        """Handle reactive progress updates."""
        self._validate_progress(new_value)
        self._start_animation()
        self._mark_dirty()
    
    def _on_custom_text_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle reactive custom text updates."""
        self._mark_dirty()
    
    def _on_size_changed(self, old_value: Any, new_value: Any) -> None:
        """Handle size changes that require re-rendering."""
        self._mark_dirty()
    
    def _start_animation(self) -> None:
        """Start progress animation to new value."""
        if not self._animation.enabled:
            self._cached_progress = self._normalize_progress(self._progress.value)
            return
        
        with self._animation_lock:
            current_time = time.time()
            new_target = self._normalize_progress(self._progress.value)
            
            # Set up animation
            self._animation.start_time = current_time
            self._animation.start_value = self._animation.current_value or self._cached_progress
            self._animation.target_value = new_target
    
    def _update_animation(self, current_time: float) -> None:
        """Update animation progress."""
        with self._animation_lock:
            if (self._animation.start_time is None or 
                self._animation.start_value is None or 
                self._animation.target_value is None):
                return
            
            # Calculate animation progress
            elapsed = current_time - self._animation.start_time
            progress = min(elapsed / self._animation.duration, 1.0)
            
            if progress >= 1.0:
                # Animation complete
                self._animation.current_value = self._animation.target_value
                self._cached_progress = self._animation.target_value
                self._animation.start_time = None
            else:
                # Apply easing function
                eased_progress = self._apply_easing(progress, self._animation.easing)
                
                # Interpolate between start and target
                start_val = self._animation.start_value
                target_val = self._animation.target_value
                self._animation.current_value = start_val + (target_val - start_val) * eased_progress
    
    def _apply_easing(self, progress: float, easing: EasingFunction) -> float:
        """Apply easing function to animation progress."""
        if easing == EasingFunction.LINEAR:
            return progress
        elif easing == EasingFunction.EASE_IN:
            return progress * progress
        elif easing == EasingFunction.EASE_OUT:
            return 1.0 - (1.0 - progress) * (1.0 - progress)
        elif easing == EasingFunction.EASE_IN_OUT:
            if progress < 0.5:
                return 2.0 * progress * progress
            else:
                return 1.0 - 2.0 * (1.0 - progress) * (1.0 - progress)
        elif easing == EasingFunction.BOUNCE:
            if progress < 0.5:
                return 2.0 * progress * progress
            else:
                return 1.0 - 2.0 * (1.0 - progress) * (1.0 - progress) * abs(math.sin(progress * math.pi * 4))
        elif easing == EasingFunction.ELASTIC:
            if progress == 0.0 or progress == 1.0:
                return progress
            return math.pow(2, -10 * progress) * math.sin((progress - 0.1) * 2 * math.pi / 0.4) + 1.0
        else:
            return progress
    
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