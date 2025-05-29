#!/usr/bin/env python3
"""
Backward Compatibility Layer for Time-Based Animations

Provides legacy time-based animation APIs that internally convert to and use
the new tick-based animation system. This ensures existing code continues to
work while benefiting from the deterministic tick-based system.
"""

from typing import Union, Optional, Tuple, Dict, Any, Callable
import warnings
from dataclasses import dataclass

from .tick_based import TickAnimationDefinition, TickAnimationState, TickAnimationEngine
from .utilities import (
    AnimationConfig, AnimationTiming, seconds_to_ticks, 
    create_fade_animation, create_slide_animation, create_scale_animation
)


@dataclass
class LegacyAnimationConfig:
    """Legacy animation configuration using time-based parameters."""
    duration: float  # Duration in seconds
    easing: str = "ease_in_out"
    repeat: int = 1
    delay: float = 0.0  # Delay in seconds
    fps: int = 60  # Target FPS for conversion
    on_complete: Optional[Callable] = None
    
    def to_tick_config(self) -> AnimationConfig:
        """Convert to new tick-based animation config."""
        return AnimationConfig(
            timing=AnimationTiming(duration_seconds=self.duration, fps=self.fps),
            easing=self.easing,
            repeat_count=self.repeat,
            delay_ticks=seconds_to_ticks(self.delay, self.fps),
            on_complete=self.on_complete
        )


class LegacyAnimationAPI:
    """Legacy animation API that provides time-based methods."""
    
    def __init__(self, fps: int = 60, show_deprecation_warnings: bool = True):
        """Initialize legacy animation API.
        
        Args:
            fps: Target frames per second for time-to-tick conversion
            show_deprecation_warnings: Whether to show deprecation warnings
        """
        self.fps = fps
        self.show_deprecation_warnings = show_deprecation_warnings
    
    def _warn_deprecated(self, method_name: str, replacement: str) -> None:
        """Show deprecation warning for legacy methods."""
        if self.show_deprecation_warnings:
            warnings.warn(
                f"{method_name} is deprecated. Use {replacement} instead.",
                DeprecationWarning,
                stacklevel=3
            )
    
    def create_fade_in(
        self,
        duration: float = 0.5,
        easing: str = "ease_out",
        position: Tuple[float, float] = (0.0, 0.0),
        on_complete: Optional[Callable] = None
    ) -> TickAnimationDefinition:
        """Create fade in animation using legacy time-based API.
        
        Args:
            duration: Animation duration in seconds
            easing: Easing function name
            position: Widget position
            on_complete: Completion callback
            
        Returns:
            TickAnimationDefinition (converted from time-based parameters)
        """
        self._warn_deprecated(
            "create_fade_in", 
            "create_preset_animation(AnimationPreset.FADE_IN)"
        )
        
        config = AnimationConfig(
            timing=AnimationTiming(duration_seconds=duration, fps=self.fps),
            easing=easing,
            on_complete=on_complete
        )
        
        return create_fade_animation(0.0, 1.0, position, config)
    
    def create_fade_out(
        self,
        duration: float = 0.3,
        easing: str = "ease_in",
        position: Tuple[float, float] = (0.0, 0.0),
        on_complete: Optional[Callable] = None
    ) -> TickAnimationDefinition:
        """Create fade out animation using legacy time-based API.
        
        Args:
            duration: Animation duration in seconds
            easing: Easing function name
            position: Widget position
            on_complete: Completion callback
            
        Returns:
            TickAnimationDefinition (converted from time-based parameters)
        """
        self._warn_deprecated(
            "create_fade_out", 
            "create_preset_animation(AnimationPreset.FADE_OUT)"
        )
        
        config = AnimationConfig(
            timing=AnimationTiming(duration_seconds=duration, fps=self.fps),
            easing=easing,
            on_complete=on_complete
        )
        
        return create_fade_animation(1.0, 0.0, position, config)
    
    def create_slide_left(
        self,
        distance: float = 100.0,
        duration: float = 0.3,
        easing: str = "ease_in_out",
        position: Tuple[float, float] = (0.0, 0.0),
        on_complete: Optional[Callable] = None
    ) -> TickAnimationDefinition:
        """Create slide left animation using legacy time-based API.
        
        Args:
            distance: Distance to slide in pixels
            duration: Animation duration in seconds
            easing: Easing function name
            position: Target position
            on_complete: Completion callback
            
        Returns:
            TickAnimationDefinition (converted from time-based parameters)
        """
        self._warn_deprecated(
            "create_slide_left", 
            "create_preset_animation(AnimationPreset.SLIDE_LEFT)"
        )
        
        config = AnimationConfig(
            timing=AnimationTiming(duration_seconds=duration, fps=self.fps),
            easing=easing,
            on_complete=on_complete
        )
        
        start_pos = (position[0] + distance, position[1])
        return create_slide_animation(start_pos, position, config)
    
    def create_slide_right(
        self,
        distance: float = 100.0,
        duration: float = 0.3,
        easing: str = "ease_in_out",
        position: Tuple[float, float] = (0.0, 0.0),
        on_complete: Optional[Callable] = None
    ) -> TickAnimationDefinition:
        """Create slide right animation using legacy time-based API.
        
        Args:
            distance: Distance to slide in pixels
            duration: Animation duration in seconds
            easing: Easing function name
            position: Starting position
            on_complete: Completion callback
            
        Returns:
            TickAnimationDefinition (converted from time-based parameters)
        """
        self._warn_deprecated(
            "create_slide_right", 
            "create_preset_animation(AnimationPreset.SLIDE_RIGHT)"
        )
        
        config = AnimationConfig(
            timing=AnimationTiming(duration_seconds=duration, fps=self.fps),
            easing=easing,
            on_complete=on_complete
        )
        
        end_pos = (position[0] + distance, position[1])
        return create_slide_animation(position, end_pos, config)
    
    def create_scale_up(
        self,
        duration: float = 0.4,
        easing: str = "bounce",
        position: Tuple[float, float] = (0.0, 0.0),
        on_complete: Optional[Callable] = None
    ) -> TickAnimationDefinition:
        """Create scale up animation using legacy time-based API.
        
        Args:
            duration: Animation duration in seconds
            easing: Easing function name
            position: Widget position
            on_complete: Completion callback
            
        Returns:
            TickAnimationDefinition (converted from time-based parameters)
        """
        self._warn_deprecated(
            "create_scale_up", 
            "create_preset_animation(AnimationPreset.SCALE_IN)"
        )
        
        config = AnimationConfig(
            timing=AnimationTiming(duration_seconds=duration, fps=self.fps),
            easing=easing,
            on_complete=on_complete
        )
        
        return create_scale_animation((0.0, 0.0), (1.0, 1.0), position, config)
    
    def create_scale_down(
        self,
        duration: float = 0.3,
        easing: str = "ease_in",
        position: Tuple[float, float] = (0.0, 0.0),
        on_complete: Optional[Callable] = None
    ) -> TickAnimationDefinition:
        """Create scale down animation using legacy time-based API.
        
        Args:
            duration: Animation duration in seconds
            easing: Easing function name
            position: Widget position
            on_complete: Completion callback
            
        Returns:
            TickAnimationDefinition (converted from time-based parameters)
        """
        self._warn_deprecated(
            "create_scale_down", 
            "create_preset_animation(AnimationPreset.SCALE_OUT)"
        )
        
        config = AnimationConfig(
            timing=AnimationTiming(duration_seconds=duration, fps=self.fps),
            easing=easing,
            on_complete=on_complete
        )
        
        return create_scale_animation((1.0, 1.0), (0.0, 0.0), position, config)
    
    def create_custom_animation(
        self,
        start_state: Dict[str, Any],
        end_state: Dict[str, Any],
        duration: float,
        easing: str = "ease_in_out",
        position: Tuple[float, float] = (0.0, 0.0),
        on_complete: Optional[Callable] = None
    ) -> TickAnimationDefinition:
        """Create custom animation using legacy time-based API.
        
        Args:
            start_state: Starting animation state properties
            end_state: Ending animation state properties
            duration: Animation duration in seconds
            easing: Easing function name
            position: Widget position
            on_complete: Completion callback
            
        Returns:
            TickAnimationDefinition (converted from time-based parameters)
        """
        self._warn_deprecated(
            "create_custom_animation", 
            "create_fade_animation, create_slide_animation, or create_scale_animation"
        )
        
        duration_ticks = seconds_to_ticks(duration, self.fps)
        
        # Convert legacy state dictionaries to TickAnimationState
        start_tick_state = TickAnimationState(
            tick=0,
            position=position,
            opacity=start_state.get('opacity', 1.0),
            rotation=start_state.get('rotation', 0.0),
            scale=start_state.get('scale', (1.0, 1.0)),
            custom_properties=start_state.get('custom_properties', {})
        )
        
        end_tick_state = TickAnimationState(
            tick=duration_ticks,
            position=position,
            opacity=end_state.get('opacity', 1.0),
            rotation=end_state.get('rotation', 0.0),
            scale=end_state.get('scale', (1.0, 1.0)),
            custom_properties=end_state.get('custom_properties', {})
        )
        
        return TickAnimationDefinition(
            start_tick=0,
            duration_ticks=duration_ticks,
            start_state=start_tick_state,
            end_state=end_tick_state,
            easing=easing
        )


class LegacyWidgetAnimationMixin:
    """Mixin class to add legacy time-based animation methods to widgets."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._legacy_api = LegacyAnimationAPI()
    
    def animate_fade_in(
        self,
        duration: float = 0.5,
        easing: str = "ease_out",
        on_complete: Optional[Callable] = None
    ) -> bool:
        """Legacy fade in animation method.
        
        Args:
            duration: Animation duration in seconds
            easing: Easing function name
            on_complete: Completion callback
            
        Returns:
            True if animation started successfully
        """
        warnings.warn(
            "animate_fade_in is deprecated. Use fade_in_animated() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        duration_ticks = seconds_to_ticks(duration, self._legacy_api.fps)
        return self.fade_in_animated(duration_ticks, easing, on_complete)
    
    def animate_fade_out(
        self,
        duration: float = 0.3,
        easing: str = "ease_in",
        on_complete: Optional[Callable] = None
    ) -> bool:
        """Legacy fade out animation method.
        
        Args:
            duration: Animation duration in seconds
            easing: Easing function name
            on_complete: Completion callback
            
        Returns:
            True if animation started successfully
        """
        warnings.warn(
            "animate_fade_out is deprecated. Use fade_out_animated() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        duration_ticks = seconds_to_ticks(duration, self._legacy_api.fps)
        return self.fade_out_animated(duration_ticks, easing, on_complete)
    
    def animate_to_position(
        self,
        target_position: Tuple[float, float],
        duration: float = 0.3,
        easing: str = "ease_in_out",
        on_complete: Optional[Callable] = None
    ) -> bool:
        """Legacy position animation method.
        
        Args:
            target_position: Target position (x, y)
            duration: Animation duration in seconds
            easing: Easing function name
            on_complete: Completion callback
            
        Returns:
            True if animation started successfully
        """
        warnings.warn(
            "animate_to_position is deprecated. Use position-based tick animations instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # This would need to be implemented by specific widget types
        # as it requires access to widget-specific animation methods
        duration_ticks = seconds_to_ticks(duration, self._legacy_api.fps)
        
        # For now, return False as this needs widget-specific implementation
        return False
    
    def animate_alpha(
        self,
        target_alpha: float,
        duration: float = 0.3,
        easing: str = "ease_in_out",
        on_complete: Optional[Callable] = None
    ) -> bool:
        """Legacy alpha animation method.
        
        Args:
            target_alpha: Target alpha value (0.0 to 1.0)
            duration: Animation duration in seconds
            easing: Easing function name
            on_complete: Completion callback
            
        Returns:
            True if animation started successfully
        """
        warnings.warn(
            "animate_alpha is deprecated. Use set_alpha_animated() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Convert to tick-based call
        self.set_alpha_animated(target_alpha, duration, on_complete)
        return True


# Global legacy API instance for backward compatibility
legacy_animation_api = LegacyAnimationAPI()


# Legacy function aliases for backward compatibility
def create_fade_in_animation(duration: float = 0.5, **kwargs) -> TickAnimationDefinition:
    """Legacy function to create fade in animation."""
    return legacy_animation_api.create_fade_in(duration, **kwargs)


def create_fade_out_animation(duration: float = 0.3, **kwargs) -> TickAnimationDefinition:
    """Legacy function to create fade out animation."""
    return legacy_animation_api.create_fade_out(duration, **kwargs)


def create_slide_animation_legacy(
    direction: str,
    distance: float = 100.0,
    duration: float = 0.3,
    **kwargs
) -> TickAnimationDefinition:
    """Legacy function to create slide animation.
    
    Args:
        direction: Slide direction ('left', 'right', 'up', 'down')
        distance: Distance to slide
        duration: Animation duration in seconds
        **kwargs: Additional parameters
        
    Returns:
        TickAnimationDefinition for slide animation
    """
    if direction == 'left':
        return legacy_animation_api.create_slide_left(distance, duration, **kwargs)
    elif direction == 'right':
        return legacy_animation_api.create_slide_right(distance, duration, **kwargs)
    else:
        raise ValueError(f"Unsupported slide direction: {direction}")


def create_scale_animation_legacy(
    scale_type: str,
    duration: float = 0.4,
    **kwargs
) -> TickAnimationDefinition:
    """Legacy function to create scale animation.
    
    Args:
        scale_type: Scale type ('up', 'down', 'in', 'out')
        duration: Animation duration in seconds
        **kwargs: Additional parameters
        
    Returns:
        TickAnimationDefinition for scale animation
    """
    if scale_type in ('up', 'in'):
        return legacy_animation_api.create_scale_up(duration, **kwargs)
    elif scale_type in ('down', 'out'):
        return legacy_animation_api.create_scale_down(duration, **kwargs)
    else:
        raise ValueError(f"Unsupported scale type: {scale_type}")


# Migration utilities
def convert_time_duration_to_ticks(duration_seconds: float, fps: int = 60) -> int:
    """Convert time-based duration to tick-based duration.
    
    Args:
        duration_seconds: Duration in seconds
        fps: Target frames per second
        
    Returns:
        Duration in ticks
    """
    return seconds_to_ticks(duration_seconds, fps)


def convert_legacy_easing_name(legacy_easing: str) -> str:
    """Convert legacy easing names to new easing names.
    
    Args:
        legacy_easing: Legacy easing function name
        
    Returns:
        New easing function name
    """
    # Mapping of legacy names to new names
    easing_map = {
        'linear': 'linear',
        'ease': 'ease_in_out',
        'ease-in': 'ease_in',
        'ease-out': 'ease_out',
        'ease-in-out': 'ease_in_out',
        'cubic-bezier': 'ease_in_out',  # Simplified mapping
        'bounce': 'bounce',
        'elastic': 'elastic'
    }
    
    return easing_map.get(legacy_easing, 'ease_in_out')


def migrate_animation_config(legacy_config: Dict[str, Any]) -> AnimationConfig:
    """Migrate legacy animation configuration to new format.
    
    Args:
        legacy_config: Legacy animation configuration dictionary
        
    Returns:
        New AnimationConfig object
    """
    duration = legacy_config.get('duration', 0.5)
    easing = convert_legacy_easing_name(legacy_config.get('easing', 'ease_in_out'))
    repeat = legacy_config.get('repeat', 1)
    delay = legacy_config.get('delay', 0.0)
    fps = legacy_config.get('fps', 60)
    
    return AnimationConfig(
        timing=AnimationTiming(duration_seconds=duration, fps=fps),
        easing=easing,
        repeat_count=repeat,
        delay_ticks=seconds_to_ticks(delay, fps),
        on_complete=legacy_config.get('on_complete')
    ) 