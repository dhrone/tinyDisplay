#!/usr/bin/env python3
"""
Animation Utilities for Tick-Based Animation System

Provides high-level utilities for creating tick-based animations, converting
between time and tick durations, and maintaining backward compatibility with
time-based animation APIs.
"""

from typing import Union, Optional, Tuple, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import math

from .tick_based import (
    TickAnimationDefinition, TickAnimationState, TickEasing, EasingFunction
)


# Time conversion utilities (defined first to avoid circular imports)

def seconds_to_ticks(seconds: float, fps: int = 60) -> int:
    """Convert duration in seconds to ticks.
    
    Args:
        seconds: Duration in seconds
        fps: Frames per second (default 60)
        
    Returns:
        Duration in ticks
    """
    if seconds < 0:
        raise ValueError("Duration must be non-negative")
    if fps <= 0:
        raise ValueError("FPS must be positive")
    
    return max(1, int(seconds * fps))


def ticks_to_seconds(ticks: int, fps: int = 60) -> float:
    """Convert duration in ticks to seconds.
    
    Args:
        ticks: Duration in ticks
        fps: Frames per second (default 60)
        
    Returns:
        Duration in seconds
    """
    if ticks < 0:
        raise ValueError("Ticks must be non-negative")
    if fps <= 0:
        raise ValueError("FPS must be positive")
    
    return ticks / fps


def milliseconds_to_ticks(milliseconds: float, fps: int = 60) -> int:
    """Convert duration in milliseconds to ticks.
    
    Args:
        milliseconds: Duration in milliseconds
        fps: Frames per second (default 60)
        
    Returns:
        Duration in ticks
    """
    return seconds_to_ticks(milliseconds / 1000.0, fps)


def ticks_to_milliseconds(ticks: int, fps: int = 60) -> float:
    """Convert duration in ticks to milliseconds.
    
    Args:
        ticks: Duration in ticks
        fps: Frames per second (default 60)
        
    Returns:
        Duration in milliseconds
    """
    return ticks_to_seconds(ticks, fps) * 1000.0


class AnimationPreset(Enum):
    """Predefined animation presets for common use cases."""
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"
    BOUNCE_IN = "bounce_in"
    ELASTIC_IN = "elastic_in"
    PULSE = "pulse"
    SHAKE = "shake"


@dataclass
class AnimationTiming:
    """Animation timing configuration with multiple duration formats."""
    duration_ticks: Optional[int] = None
    duration_seconds: Optional[float] = None
    fps: int = 60  # Frames per second for time-to-tick conversion
    
    def __post_init__(self):
        """Validate and normalize timing parameters."""
        if self.duration_ticks is None and self.duration_seconds is None:
            raise ValueError("Either duration_ticks or duration_seconds must be specified")
        
        if self.duration_ticks is not None and self.duration_seconds is not None:
            raise ValueError("Cannot specify both duration_ticks and duration_seconds")
        
        if self.fps <= 0:
            raise ValueError("FPS must be positive")
        
        # Convert seconds to ticks if needed
        if self.duration_seconds is not None:
            self.duration_ticks = seconds_to_ticks(self.duration_seconds, self.fps)
        
        # Validate final tick duration
        if self.duration_ticks <= 0:
            raise ValueError("Duration must be positive")


@dataclass
class AnimationConfig:
    """Comprehensive animation configuration."""
    timing: AnimationTiming
    easing: Union[str, EasingFunction] = "ease_in_out"
    repeat_count: int = 1
    repeat_mode: str = "restart"  # "restart", "reverse", "mirror"
    delay_ticks: int = 0
    on_complete: Optional[Callable] = None
    
    def __post_init__(self):
        """Validate animation configuration."""
        if self.repeat_count < 1:
            raise ValueError("Repeat count must be at least 1")
        if self.repeat_mode not in ("restart", "reverse", "mirror"):
            raise ValueError("Invalid repeat mode")
        if self.delay_ticks < 0:
            raise ValueError("Delay must be non-negative")
        
        # Normalize easing to string
        if isinstance(self.easing, EasingFunction):
            self.easing = self.easing.value


# Animation creation utilities

def create_fade_animation(
    start_opacity: float = 0.0,
    end_opacity: float = 1.0,
    position: Tuple[float, float] = (0.0, 0.0),
    config: Optional[AnimationConfig] = None
) -> TickAnimationDefinition:
    """Create a fade animation.
    
    Args:
        start_opacity: Starting opacity (0.0 to 1.0)
        end_opacity: Ending opacity (0.0 to 1.0)
        position: Widget position
        config: Animation configuration
        
    Returns:
        TickAnimationDefinition for fade animation
    """
    if config is None:
        config = AnimationConfig(timing=AnimationTiming(duration_seconds=0.5))
    
    # Validate opacity values
    if not (0.0 <= start_opacity <= 1.0):
        raise ValueError("Start opacity must be between 0.0 and 1.0")
    if not (0.0 <= end_opacity <= 1.0):
        raise ValueError("End opacity must be between 0.0 and 1.0")
    
    start_state = TickAnimationState(
        tick=0,
        position=position,
        opacity=start_opacity
    )
    
    end_state = TickAnimationState(
        tick=config.timing.duration_ticks,
        position=position,
        opacity=end_opacity
    )
    
    return TickAnimationDefinition(
        start_tick=config.delay_ticks,
        duration_ticks=config.timing.duration_ticks,
        start_state=start_state,
        end_state=end_state,
        easing=config.easing,
        repeat_count=config.repeat_count,
        repeat_mode=config.repeat_mode
    )


def create_slide_animation(
    start_position: Tuple[float, float],
    end_position: Tuple[float, float],
    config: Optional[AnimationConfig] = None
) -> TickAnimationDefinition:
    """Create a slide animation.
    
    Args:
        start_position: Starting position (x, y)
        end_position: Ending position (x, y)
        config: Animation configuration
        
    Returns:
        TickAnimationDefinition for slide animation
    """
    if config is None:
        config = AnimationConfig(timing=AnimationTiming(duration_seconds=0.3))
    
    start_state = TickAnimationState(
        tick=0,
        position=start_position
    )
    
    end_state = TickAnimationState(
        tick=config.timing.duration_ticks,
        position=end_position
    )
    
    return TickAnimationDefinition(
        start_tick=config.delay_ticks,
        duration_ticks=config.timing.duration_ticks,
        start_state=start_state,
        end_state=end_state,
        easing=config.easing,
        repeat_count=config.repeat_count,
        repeat_mode=config.repeat_mode
    )


def create_scale_animation(
    start_scale: Tuple[float, float] = (0.0, 0.0),
    end_scale: Tuple[float, float] = (1.0, 1.0),
    position: Tuple[float, float] = (0.0, 0.0),
    config: Optional[AnimationConfig] = None
) -> TickAnimationDefinition:
    """Create a scale animation.
    
    Args:
        start_scale: Starting scale (x, y)
        end_scale: Ending scale (x, y)
        position: Widget position
        config: Animation configuration
        
    Returns:
        TickAnimationDefinition for scale animation
    """
    if config is None:
        config = AnimationConfig(
            timing=AnimationTiming(duration_seconds=0.4),
            easing="bounce"
        )
    
    # Validate scale values
    if start_scale[0] < 0.0 or start_scale[1] < 0.0:
        raise ValueError("Start scale values must be non-negative")
    if end_scale[0] < 0.0 or end_scale[1] < 0.0:
        raise ValueError("End scale values must be non-negative")
    
    start_state = TickAnimationState(
        tick=0,
        position=position,
        scale=start_scale
    )
    
    end_state = TickAnimationState(
        tick=config.timing.duration_ticks,
        position=position,
        scale=end_scale
    )
    
    return TickAnimationDefinition(
        start_tick=config.delay_ticks,
        duration_ticks=config.timing.duration_ticks,
        start_state=start_state,
        end_state=end_state,
        easing=config.easing,
        repeat_count=config.repeat_count,
        repeat_mode=config.repeat_mode
    )


def create_rotation_animation(
    start_rotation: float = 0.0,
    end_rotation: float = 360.0,
    position: Tuple[float, float] = (0.0, 0.0),
    config: Optional[AnimationConfig] = None
) -> TickAnimationDefinition:
    """Create a rotation animation.
    
    Args:
        start_rotation: Starting rotation in degrees
        end_rotation: Ending rotation in degrees
        position: Widget position
        config: Animation configuration
        
    Returns:
        TickAnimationDefinition for rotation animation
    """
    if config is None:
        config = AnimationConfig(timing=AnimationTiming(duration_seconds=1.0))
    
    # Convert degrees to radians
    start_rad = math.radians(start_rotation)
    end_rad = math.radians(end_rotation)
    
    start_state = TickAnimationState(
        tick=0,
        position=position,
        rotation=start_rad
    )
    
    end_state = TickAnimationState(
        tick=config.timing.duration_ticks,
        position=position,
        rotation=end_rad
    )
    
    return TickAnimationDefinition(
        start_tick=config.delay_ticks,
        duration_ticks=config.timing.duration_ticks,
        start_state=start_state,
        end_state=end_state,
        easing=config.easing,
        repeat_count=config.repeat_count,
        repeat_mode=config.repeat_mode
    )


def create_custom_property_animation(
    property_name: str,
    start_value: Any,
    end_value: Any,
    position: Tuple[float, float] = (0.0, 0.0),
    config: Optional[AnimationConfig] = None
) -> TickAnimationDefinition:
    """Create an animation for custom properties.
    
    Args:
        property_name: Name of the custom property
        start_value: Starting value
        end_value: Ending value
        position: Widget position
        config: Animation configuration
        
    Returns:
        TickAnimationDefinition for custom property animation
    """
    if config is None:
        config = AnimationConfig(timing=AnimationTiming(duration_seconds=0.5))
    
    start_state = TickAnimationState(
        tick=0,
        position=position,
        custom_properties={property_name: start_value}
    )
    
    end_state = TickAnimationState(
        tick=config.timing.duration_ticks,
        position=position,
        custom_properties={property_name: end_value}
    )
    
    return TickAnimationDefinition(
        start_tick=config.delay_ticks,
        duration_ticks=config.timing.duration_ticks,
        start_state=start_state,
        end_state=end_state,
        easing=config.easing,
        repeat_count=config.repeat_count,
        repeat_mode=config.repeat_mode
    )


# Animation preset utilities

def create_preset_animation(
    preset: AnimationPreset,
    position: Tuple[float, float] = (0.0, 0.0),
    config: Optional[AnimationConfig] = None
) -> TickAnimationDefinition:
    """Create an animation from a preset.
    
    Args:
        preset: Animation preset type
        position: Widget position
        config: Animation configuration (uses preset defaults if None)
        
    Returns:
        TickAnimationDefinition for preset animation
    """
    if preset == AnimationPreset.FADE_IN:
        if config is None:
            config = AnimationConfig(
                timing=AnimationTiming(duration_seconds=0.5),
                easing="ease_out"
            )
        return create_fade_animation(0.0, 1.0, position, config)
    
    elif preset == AnimationPreset.FADE_OUT:
        if config is None:
            config = AnimationConfig(
                timing=AnimationTiming(duration_seconds=0.3),
                easing="ease_in"
            )
        return create_fade_animation(1.0, 0.0, position, config)
    
    elif preset == AnimationPreset.SLIDE_LEFT:
        if config is None:
            config = AnimationConfig(
                timing=AnimationTiming(duration_seconds=0.3),
                easing="ease_in_out"
            )
        start_pos = (position[0] + 100, position[1])
        return create_slide_animation(start_pos, position, config)
    
    elif preset == AnimationPreset.SLIDE_RIGHT:
        if config is None:
            config = AnimationConfig(
                timing=AnimationTiming(duration_seconds=0.3),
                easing="ease_in_out"
            )
        end_pos = (position[0] + 100, position[1])
        return create_slide_animation(position, end_pos, config)
    
    elif preset == AnimationPreset.SLIDE_UP:
        if config is None:
            config = AnimationConfig(
                timing=AnimationTiming(duration_seconds=0.3),
                easing="ease_in_out"
            )
        start_pos = (position[0], position[1] + 50)
        return create_slide_animation(start_pos, position, config)
    
    elif preset == AnimationPreset.SLIDE_DOWN:
        if config is None:
            config = AnimationConfig(
                timing=AnimationTiming(duration_seconds=0.3),
                easing="ease_in_out"
            )
        end_pos = (position[0], position[1] + 50)
        return create_slide_animation(position, end_pos, config)
    
    elif preset == AnimationPreset.SCALE_IN:
        if config is None:
            config = AnimationConfig(
                timing=AnimationTiming(duration_seconds=0.4),
                easing="bounce"
            )
        return create_scale_animation((0.0, 0.0), (1.0, 1.0), position, config)
    
    elif preset == AnimationPreset.SCALE_OUT:
        if config is None:
            config = AnimationConfig(
                timing=AnimationTiming(duration_seconds=0.3),
                easing="ease_in"
            )
        return create_scale_animation((1.0, 1.0), (0.0, 0.0), position, config)
    
    elif preset == AnimationPreset.BOUNCE_IN:
        if config is None:
            config = AnimationConfig(
                timing=AnimationTiming(duration_seconds=0.6),
                easing="bounce"
            )
        return create_scale_animation((0.0, 0.0), (1.0, 1.0), position, config)
    
    elif preset == AnimationPreset.ELASTIC_IN:
        if config is None:
            config = AnimationConfig(
                timing=AnimationTiming(duration_seconds=0.8),
                easing="elastic"
            )
        return create_scale_animation((0.0, 0.0), (1.0, 1.0), position, config)
    
    elif preset == AnimationPreset.PULSE:
        if config is None:
            config = AnimationConfig(
                timing=AnimationTiming(duration_seconds=1.0),
                easing="ease_in_out",
                repeat_count=3,
                repeat_mode="mirror"
            )
        return create_scale_animation((1.0, 1.0), (1.2, 1.2), position, config)
    
    elif preset == AnimationPreset.SHAKE:
        if config is None:
            config = AnimationConfig(
                timing=AnimationTiming(duration_seconds=0.5),
                easing="linear",
                repeat_count=5,
                repeat_mode="mirror"
            )
        shake_pos = (position[0] + 10, position[1])
        return create_slide_animation(position, shake_pos, config)
    
    else:
        raise ValueError(f"Unknown animation preset: {preset}")


# Backward compatibility layer

def create_time_based_animation(
    duration_seconds: float,
    start_opacity: float = 0.0,
    end_opacity: float = 1.0,
    position: Tuple[float, float] = (0.0, 0.0),
    easing: str = "ease_out",
    fps: int = 60
) -> TickAnimationDefinition:
    """Create tick-based animation from time-based parameters (backward compatibility).
    
    Args:
        duration_seconds: Animation duration in seconds
        start_opacity: Starting opacity
        end_opacity: Ending opacity
        position: Widget position
        easing: Easing function name
        fps: Frames per second for conversion
        
    Returns:
        TickAnimationDefinition converted from time-based parameters
    """
    config = AnimationConfig(
        timing=AnimationTiming(duration_seconds=duration_seconds, fps=fps),
        easing=easing
    )
    
    return create_fade_animation(start_opacity, end_opacity, position, config)


def convert_legacy_animation_params(
    duration: float,
    easing: str = "ease_in_out",
    repeat: int = 1,
    fps: int = 60,
    **kwargs
) -> AnimationConfig:
    """Convert legacy time-based animation parameters to new tick-based config.
    
    Args:
        duration: Duration in seconds
        easing: Easing function name
        repeat: Repeat count
        fps: Frames per second
        **kwargs: Additional parameters
        
    Returns:
        AnimationConfig with converted parameters
    """
    return AnimationConfig(
        timing=AnimationTiming(duration_seconds=duration, fps=fps),
        easing=easing,
        repeat_count=repeat,
        **kwargs
    )


# Animation validation utilities

def validate_animation_definition(definition: TickAnimationDefinition) -> bool:
    """Validate a tick animation definition.
    
    Args:
        definition: Animation definition to validate
        
    Returns:
        True if valid, raises ValueError if invalid
    """
    # Validate basic parameters
    if definition.start_tick < 0:
        raise ValueError("Start tick must be non-negative")
    
    if definition.duration_ticks <= 0:
        raise ValueError("Duration must be positive")
    
    if definition.repeat_count < 1:
        raise ValueError("Repeat count must be at least 1")
    
    if definition.repeat_mode not in ("restart", "reverse", "mirror"):
        raise ValueError("Invalid repeat mode")
    
    # Validate easing function
    valid_easing_functions = {
        "linear", "ease_in", "ease_out", "ease_in_out",
        "ease_in_cubic", "ease_out_cubic", "ease_in_out_cubic",
        "bounce", "elastic"
    }
    if definition.easing not in valid_easing_functions:
        raise ValueError(f"Unknown easing function: {definition.easing}")
    
    # Validate animation states
    if definition.start_state.tick != 0:
        raise ValueError("Start state tick must be 0")
    
    if definition.end_state.tick != definition.duration_ticks:
        raise ValueError("End state tick must equal duration")
    
    # Validate opacity values
    if not (0.0 <= definition.start_state.opacity <= 1.0):
        raise ValueError("Start state opacity must be between 0.0 and 1.0")
    
    if not (0.0 <= definition.end_state.opacity <= 1.0):
        raise ValueError("End state opacity must be between 0.0 and 1.0")
    
    # Validate scale values
    if (definition.start_state.scale[0] < 0.0 or definition.start_state.scale[1] < 0.0):
        raise ValueError("Start state scale values must be non-negative")
    
    if (definition.end_state.scale[0] < 0.0 or definition.end_state.scale[1] < 0.0):
        raise ValueError("End state scale values must be non-negative")
    
    return True


def validate_animation_config(config: AnimationConfig) -> bool:
    """Validate an animation configuration.
    
    Args:
        config: Animation configuration to validate
        
    Returns:
        True if valid, raises ValueError if invalid
    """
    # Timing validation is handled in AnimationTiming.__post_init__
    # Config validation is handled in AnimationConfig.__post_init__
    
    # Additional validation
    valid_easing_functions = {
        "linear", "ease_in", "ease_out", "ease_in_out",
        "ease_in_cubic", "ease_out_cubic", "ease_in_out_cubic",
        "bounce", "elastic"
    }
    if config.easing not in valid_easing_functions:
        raise ValueError(f"Unknown easing function: {config.easing}")
    
    return True


# Animation sequence utilities

def create_animation_sequence(
    animations: list[TickAnimationDefinition],
    gap_ticks: int = 0
) -> list[TickAnimationDefinition]:
    """Create a sequence of animations with proper timing.
    
    Args:
        animations: List of animation definitions
        gap_ticks: Gap between animations in ticks
        
    Returns:
        List of animation definitions with adjusted start times
    """
    if not animations:
        return []
    
    sequenced = []
    current_start_tick = 0
    
    for animation in animations:
        # Create new animation with adjusted start tick
        sequenced_animation = TickAnimationDefinition(
            start_tick=current_start_tick,
            duration_ticks=animation.duration_ticks,
            start_state=animation.start_state,
            end_state=animation.end_state,
            easing=animation.easing,
            repeat_count=animation.repeat_count,
            repeat_mode=animation.repeat_mode
        )
        
        sequenced.append(sequenced_animation)
        
        # Update start tick for next animation
        current_start_tick += animation.duration_ticks * animation.repeat_count + gap_ticks
    
    return sequenced


def create_parallel_animations(
    animations: list[TickAnimationDefinition],
    start_tick: int = 0
) -> list[TickAnimationDefinition]:
    """Create parallel animations that start at the same time.
    
    Args:
        animations: List of animation definitions
        start_tick: Start tick for all animations
        
    Returns:
        List of animation definitions with synchronized start times
    """
    parallel = []
    
    for animation in animations:
        # Create new animation with synchronized start tick
        parallel_animation = TickAnimationDefinition(
            start_tick=start_tick,
            duration_ticks=animation.duration_ticks,
            start_state=animation.start_state,
            end_state=animation.end_state,
            easing=animation.easing,
            repeat_count=animation.repeat_count,
            repeat_mode=animation.repeat_mode
        )
        
        parallel.append(parallel_animation)
    
    return parallel 