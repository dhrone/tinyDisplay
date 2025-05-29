"""
Deterministic Animation Framework for Multi-Core Frame Pre-computation

This module provides pure functional animation primitives that produce identical
results regardless of execution context, enabling safe distributed frame computation
across multiple CPU cores.

Key Principles:
1. Pure Functions: Animation state queries have no side effects
2. Deterministic Output: Same input time always produces identical results
3. Immutable State: Animation definitions are immutable after creation
4. Cross-Core Safety: Safe for concurrent execution across multiple cores
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from src.tinydisplay.widgets.progress import EasingFunction


@dataclass(frozen=True)
class AnimationState:
    """Immutable animation state at a specific point in time.
    
    This represents the complete state of an animation at a given timestamp,
    including position, rotation, scale, opacity, and any custom properties.
    All fields are immutable to ensure deterministic behavior.
    """
    timestamp: float
    position: Tuple[float, float]
    rotation: float = 0.0
    scale: Tuple[float, float] = (1.0, 1.0)
    opacity: float = 1.0
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate animation state parameters."""
        if self.timestamp < 0.0:
            raise ValueError("Timestamp must be non-negative")
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError("Opacity must be between 0.0 and 1.0")
        if self.scale[0] < 0.0 or self.scale[1] < 0.0:
            raise ValueError("Scale values must be non-negative")
    
    def interpolate_to(self, target: 'AnimationState', progress: float) -> 'AnimationState':
        """Create interpolated state between this and target state.
        
        Args:
            target: Target animation state
            progress: Interpolation progress (0.0 to 1.0)
            
        Returns:
            New AnimationState representing interpolated values
        """
        if not (0.0 <= progress <= 1.0):
            raise ValueError("Progress must be between 0.0 and 1.0")
        
        # Linear interpolation for all properties
        interp_timestamp = self.timestamp + (target.timestamp - self.timestamp) * progress
        interp_position = (
            self.position[0] + (target.position[0] - self.position[0]) * progress,
            self.position[1] + (target.position[1] - self.position[1]) * progress
        )
        interp_rotation = self.rotation + (target.rotation - self.rotation) * progress
        interp_scale = (
            self.scale[0] + (target.scale[0] - self.scale[0]) * progress,
            self.scale[1] + (target.scale[1] - self.scale[1]) * progress
        )
        interp_opacity = self.opacity + (target.opacity - self.opacity) * progress
        
        # Interpolate custom properties (only numeric types)
        interp_custom = {}
        for key in set(self.custom_properties.keys()) | set(target.custom_properties.keys()):
            start_val = self.custom_properties.get(key, 0.0)
            end_val = target.custom_properties.get(key, 0.0)
            if isinstance(start_val, (int, float)) and isinstance(end_val, (int, float)):
                interp_custom[key] = start_val + (end_val - start_val) * progress
            else:
                # Non-numeric properties use step interpolation
                interp_custom[key] = start_val if progress < 0.5 else end_val
        
        return AnimationState(
            timestamp=interp_timestamp,
            position=interp_position,
            rotation=interp_rotation,
            scale=interp_scale,
            opacity=interp_opacity,
            custom_properties=interp_custom
        )
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize animation state for cross-core communication."""
        return {
            'timestamp': self.timestamp,
            'position': self.position,
            'rotation': self.rotation,
            'scale': self.scale,
            'opacity': self.opacity,
            'custom_properties': self.custom_properties
        }
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'AnimationState':
        """Deserialize animation state from cross-core communication."""
        return cls(
            timestamp=data['timestamp'],
            position=tuple(data['position']),
            rotation=data['rotation'],
            scale=tuple(data['scale']),
            opacity=data['opacity'],
            custom_properties=data.get('custom_properties', {})
        )


class DeterministicEasing:
    """Pure functional easing functions with guaranteed deterministic behavior.
    
    All easing functions are implemented as pure mathematical functions that
    produce identical output for identical input across all execution contexts.
    """
    
    @staticmethod
    def linear(t: float) -> float:
        """Linear easing function."""
        return t
    
    @staticmethod
    def ease_in(t: float) -> float:
        """Quadratic ease-in function."""
        return t * t
    
    @staticmethod
    def ease_out(t: float) -> float:
        """Quadratic ease-out function."""
        return 1.0 - (1.0 - t) * (1.0 - t)
    
    @staticmethod
    def ease_in_out(t: float) -> float:
        """Quadratic ease-in-out function."""
        if t < 0.5:
            return 2.0 * t * t
        else:
            return 1.0 - 2.0 * (1.0 - t) * (1.0 - t)
    
    @staticmethod
    def ease_in_cubic(t: float) -> float:
        """Cubic ease-in function."""
        return t * t * t
    
    @staticmethod
    def ease_out_cubic(t: float) -> float:
        """Cubic ease-out function."""
        return 1.0 - (1.0 - t) * (1.0 - t) * (1.0 - t)
    
    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        """Cubic ease-in-out function."""
        if t < 0.5:
            return 4.0 * t * t * t
        else:
            return 1.0 - 4.0 * (1.0 - t) * (1.0 - t) * (1.0 - t)
    
    @staticmethod
    def bounce(t: float) -> float:
        """Deterministic bounce easing function."""
        if t < 1.0 / 2.75:
            return 7.5625 * t * t
        elif t < 2.0 / 2.75:
            t -= 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t -= 2.25 / 2.75
            return 7.5625 * t * t + 0.9375
        else:
            t -= 2.625 / 2.75
            return 7.5625 * t * t + 0.984375
    
    @staticmethod
    def elastic(t: float) -> float:
        """Deterministic elastic easing function."""
        if t == 0.0 or t == 1.0:
            return t
        
        # Use deterministic constants for elastic behavior
        period = 0.4
        amplitude = 1.0
        s = period / (2 * math.pi) * math.asin(1.0 / amplitude)
        
        return amplitude * math.pow(2, -10 * t) * math.sin((t - s) * 2 * math.pi / period) + 1.0
    
    @classmethod
    def get_easing_function(cls, easing: Union[EasingFunction, str]) -> Callable[[float], float]:
        """Get easing function by name or enum."""
        if isinstance(easing, EasingFunction):
            easing_name = easing.value
        else:
            easing_name = easing
        
        easing_map = {
            'linear': cls.linear,
            'ease_in': cls.ease_in,
            'ease_out': cls.ease_out,
            'ease_in_out': cls.ease_in_out,
            'ease_in_cubic': cls.ease_in_cubic,
            'ease_out_cubic': cls.ease_out_cubic,
            'ease_in_out_cubic': cls.ease_in_out_cubic,
            'bounce': cls.bounce,
            'elastic': cls.elastic,
        }
        
        return easing_map.get(easing_name, cls.linear)


@dataclass(frozen=True)
class AnimationDefinition:
    """Immutable animation definition for deterministic playback.
    
    Defines all parameters needed to compute animation state at any point in time.
    Once created, the definition is immutable to ensure deterministic behavior.
    """
    start_time: float
    duration: float
    start_state: AnimationState
    end_state: AnimationState
    easing: str = "linear"
    repeat_count: int = 1
    repeat_mode: str = "restart"  # "restart", "reverse", "mirror"
    
    def __post_init__(self):
        """Validate animation definition parameters."""
        if self.duration <= 0.0:
            raise ValueError("Duration must be positive")
        if self.start_time < 0.0:
            raise ValueError("Start time must be non-negative")
        if self.repeat_count < 1:
            raise ValueError("Repeat count must be at least 1")
        if self.repeat_mode not in ("restart", "reverse", "mirror"):
            raise ValueError("Repeat mode must be 'restart', 'reverse', or 'mirror'")
    
    @property
    def end_time(self) -> float:
        """Calculate animation end time."""
        return self.start_time + (self.duration * self.repeat_count)
    
    def is_active_at(self, time_t: float) -> bool:
        """Check if animation is active at given time."""
        return self.start_time <= time_t <= self.end_time
    
    def is_completed_at(self, time_t: float) -> bool:
        """Check if animation is completed at given time."""
        return time_t > self.end_time
    
    def get_local_progress(self, time_t: float) -> float:
        """Calculate local animation progress (0.0 to 1.0) at given time."""
        if time_t <= self.start_time:
            return 0.0
        if time_t >= self.end_time:
            return 1.0
        
        # Calculate progress within current repeat cycle
        elapsed = time_t - self.start_time
        cycle_progress = (elapsed % self.duration) / self.duration
        cycle_number = int(elapsed // self.duration)
        
        # Apply repeat mode
        if self.repeat_mode == "reverse" and cycle_number % 2 == 1:
            cycle_progress = 1.0 - cycle_progress
        elif self.repeat_mode == "mirror":
            if cycle_number % 2 == 1:
                cycle_progress = 1.0 - cycle_progress
        
        return cycle_progress
    
    def state_at(self, time_t: float) -> AnimationState:
        """Calculate animation state at specific time (pure function).
        
        This is the core deterministic function that must produce identical
        results regardless of execution context or CPU core.
        
        Args:
            time_t: Time to query animation state
            
        Returns:
            AnimationState at the specified time
        """
        if not self.is_active_at(time_t):
            if time_t < self.start_time:
                return self.start_state
            else:
                return self.end_state
        
        # Calculate eased progress
        local_progress = self.get_local_progress(time_t)
        easing_func = DeterministicEasing.get_easing_function(self.easing)
        eased_progress = easing_func(local_progress)
        
        # Interpolate between start and end states
        return self.start_state.interpolate_to(self.end_state, eased_progress)
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize animation definition for cross-core communication."""
        return {
            'start_time': self.start_time,
            'duration': self.duration,
            'start_state': self.start_state.serialize(),
            'end_state': self.end_state.serialize(),
            'easing': self.easing,
            'repeat_count': self.repeat_count,
            'repeat_mode': self.repeat_mode
        }
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'AnimationDefinition':
        """Deserialize animation definition from cross-core communication."""
        return cls(
            start_time=data['start_time'],
            duration=data['duration'],
            start_state=AnimationState.deserialize(data['start_state']),
            end_state=AnimationState.deserialize(data['end_state']),
            easing=data['easing'],
            repeat_count=data['repeat_count'],
            repeat_mode=data['repeat_mode']
        )


class DeterministicAnimationEngine:
    """Engine for computing deterministic animation states across multiple animations.
    
    This engine manages multiple concurrent animations and provides deterministic
    state computation that's safe for multi-core execution.
    """
    
    def __init__(self):
        """Initialize deterministic animation engine."""
        self.animations: Dict[str, AnimationDefinition] = {}
    
    def add_animation(self, animation_id: str, definition: AnimationDefinition) -> None:
        """Add animation definition to the engine."""
        self.animations[animation_id] = definition
    
    def remove_animation(self, animation_id: str) -> None:
        """Remove animation from the engine."""
        self.animations.pop(animation_id, None)
    
    def has_animation(self, animation_id: str) -> bool:
        """Check if animation exists in the engine."""
        return animation_id in self.animations
    
    def get_animation(self, animation_id: str) -> Optional[AnimationDefinition]:
        """Get animation definition by ID."""
        return self.animations.get(animation_id)
    
    def get_animation_definitions(self) -> Dict[str, AnimationDefinition]:
        """Get all animation definitions."""
        return self.animations.copy()
    
    def start_animation_at(self, animation_id: str, start_time: float) -> bool:
        """Start animation at specific time (updates animation definition)."""
        if animation_id in self.animations:
            # Create new definition with updated start time
            old_def = self.animations[animation_id]
            new_start_state = AnimationState(
                timestamp=start_time,
                position=old_def.start_state.position,
                rotation=old_def.start_state.rotation,
                scale=old_def.start_state.scale,
                opacity=old_def.start_state.opacity,
                custom_properties=old_def.start_state.custom_properties
            )
            new_end_state = AnimationState(
                timestamp=start_time + old_def.duration,
                position=old_def.end_state.position,
                rotation=old_def.end_state.rotation,
                scale=old_def.end_state.scale,
                opacity=old_def.end_state.opacity,
                custom_properties=old_def.end_state.custom_properties
            )
            
            new_definition = AnimationDefinition(
                start_time=start_time,
                duration=old_def.duration,
                start_state=new_start_state,
                end_state=new_end_state,
                easing=old_def.easing,
                repeat_count=old_def.repeat_count,
                repeat_mode=old_def.repeat_mode
            )
            
            self.animations[animation_id] = new_definition
            return True
        return False
    
    def get_active_animations_at(self, time_t: float) -> List[str]:
        """Get list of animation IDs active at given time."""
        return [
            anim_id for anim_id, definition in self.animations.items()
            if definition.is_active_at(time_t)
        ]
    
    def compute_frame_state(self, time_t: float) -> Dict[str, AnimationState]:
        """Compute complete frame state at specific time (pure function).
        
        This is the main function used for multi-core frame pre-computation.
        It must produce identical results regardless of execution context.
        
        Args:
            time_t: Time to compute frame state
            
        Returns:
            Dictionary mapping animation IDs to their states at time_t
        """
        frame_state = {}
        
        for animation_id, definition in self.animations.items():
            frame_state[animation_id] = definition.state_at(time_t)
        
        return frame_state
    
    def get_frame_at(self, timestamp: float) -> Dict[str, AnimationState]:
        """Alias for compute_frame_state for compatibility with multicore system."""
        return self.compute_frame_state(timestamp)
    
    def serialize_engine_state(self) -> Dict[str, Any]:
        """Serialize entire engine state for cross-core communication."""
        return {
            'animations': {
                anim_id: definition.serialize()
                for anim_id, definition in self.animations.items()
            }
        }
    
    @classmethod
    def deserialize_engine_state(cls, data: Dict[str, Any]) -> 'DeterministicAnimationEngine':
        """Deserialize engine state from cross-core communication."""
        engine = cls()
        
        for anim_id, anim_data in data['animations'].items():
            definition = AnimationDefinition.deserialize(anim_data)
            engine.add_animation(anim_id, definition)
        
        return engine


class FramePredictor:
    """Frame prediction system for multi-core animation pre-computation."""
    
    def __init__(self, lookahead_seconds: float = 2.0, fps: int = 60):
        """Initialize frame predictor.
        
        Args:
            lookahead_seconds: How far ahead to predict frames
            fps: Target frames per second
        """
        self.lookahead_seconds = lookahead_seconds
        self.fps = fps
        self.frame_duration = 1.0 / fps
        self.animation_engine = DeterministicAnimationEngine()
    
    def predict_frame_at(self, target_time: float) -> Dict[str, AnimationState]:
        """Predict frame state at specific future time.
        
        This function is designed for multi-core execution and produces
        deterministic results regardless of execution context.
        
        Args:
            target_time: Future time to predict frame state
            
        Returns:
            Complete frame state at target time
        """
        return self.animation_engine.compute_frame_state(target_time)
    
    def generate_prediction_timepoints(self, start_time: float) -> List[float]:
        """Generate list of timepoints for frame prediction."""
        timepoints = []
        current_time = start_time
        end_time = start_time + self.lookahead_seconds
        
        while current_time <= end_time:
            timepoints.append(current_time)
            current_time += self.frame_duration
        
        return timepoints
    
    def validate_determinism(self, time_t: float, num_iterations: int = 100) -> bool:
        """Validate that frame prediction is deterministic.
        
        Runs the same prediction multiple times and verifies identical results.
        
        Args:
            time_t: Time to test
            num_iterations: Number of iterations to test
            
        Returns:
            True if all iterations produce identical results
        """
        if not self.animation_engine.animations:
            return True
        
        # Get reference result
        reference_result = self.predict_frame_at(time_t)
        
        # Test multiple iterations
        for _ in range(num_iterations):
            test_result = self.predict_frame_at(time_t)
            
            # Compare results
            if len(test_result) != len(reference_result):
                return False
            
            for anim_id in reference_result:
                if anim_id not in test_result:
                    return False
                
                ref_state = reference_result[anim_id]
                test_state = test_result[anim_id]
                
                # Check all state properties for exact equality
                if (ref_state.timestamp != test_state.timestamp or
                    ref_state.position != test_state.position or
                    ref_state.rotation != test_state.rotation or
                    ref_state.scale != test_state.scale or
                    ref_state.opacity != test_state.opacity or
                    ref_state.custom_properties != test_state.custom_properties):
                    return False
        
        return True


# Factory functions for common animation types

def create_fade_animation(start_time: float, duration: float, 
                         start_opacity: float = 0.0, end_opacity: float = 1.0,
                         position: Tuple[float, float] = (0.0, 0.0),
                         easing: str = "ease_out") -> AnimationDefinition:
    """Create fade animation definition."""
    start_state = AnimationState(
        timestamp=start_time,
        position=position,
        opacity=start_opacity
    )
    end_state = AnimationState(
        timestamp=start_time + duration,
        position=position,
        opacity=end_opacity
    )
    
    return AnimationDefinition(
        start_time=start_time,
        duration=duration,
        start_state=start_state,
        end_state=end_state,
        easing=easing
    )


def create_slide_animation(start_time: float, duration: float,
                          start_position: Tuple[float, float],
                          end_position: Tuple[float, float],
                          easing: str = "ease_in_out") -> AnimationDefinition:
    """Create slide animation definition."""
    start_state = AnimationState(
        timestamp=start_time,
        position=start_position
    )
    end_state = AnimationState(
        timestamp=start_time + duration,
        position=end_position
    )
    
    return AnimationDefinition(
        start_time=start_time,
        duration=duration,
        start_state=start_state,
        end_state=end_state,
        easing=easing
    )


def create_scale_animation(start_time: float, duration: float,
                          start_scale: Tuple[float, float] = (0.0, 0.0),
                          end_scale: Tuple[float, float] = (1.0, 1.0),
                          position: Tuple[float, float] = (0.0, 0.0),
                          easing: str = "bounce") -> AnimationDefinition:
    """Create scale animation definition."""
    start_state = AnimationState(
        timestamp=start_time,
        position=position,
        scale=start_scale
    )
    end_state = AnimationState(
        timestamp=start_time + duration,
        position=position,
        scale=end_scale
    )
    
    return AnimationDefinition(
        start_time=start_time,
        duration=duration,
        start_state=start_state,
        end_state=end_state,
        easing=easing
    ) 