"""
Tick-Based Animation Framework for Deterministic Rendering

This module provides a tick-based animation system where time is measured in
discrete 'ticks' rather than real-world time. Each tick represents one execution
of the animation system, making rendering completely deterministic and independent
of actual wall-clock time.

Key Principles:
1. Tick-Based Time: All animation timing uses integer tick counts
2. Deterministic Execution: Same tick always produces identical results
3. Render-Frequency Independent: Tick rate determined by render frequency
4. Real-Time Only for Baselining: Wall-clock time only used for performance measurement
"""

import math
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class EasingFunction(Enum):
    """Animation easing functions."""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"


@dataclass(frozen=True)
class TickAnimationState:
    """Immutable animation state at a specific tick.
    
    This represents the complete state of an animation at a given tick,
    including position, rotation, scale, opacity, and any custom properties.
    All fields are immutable to ensure deterministic behavior.
    """
    tick: int
    position: Tuple[float, float]
    rotation: float = 0.0
    scale: Tuple[float, float] = (1.0, 1.0)
    opacity: float = 1.0
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate animation state parameters."""
        if self.tick < 0:
            raise ValueError("Tick must be non-negative")
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError("Opacity must be between 0.0 and 1.0")
        if self.scale[0] < 0.0 or self.scale[1] < 0.0:
            raise ValueError("Scale values must be non-negative")
    
    def interpolate_to(self, target: 'TickAnimationState', progress: float) -> 'TickAnimationState':
        """Create interpolated state between this and target state.
        
        Args:
            target: Target animation state
            progress: Interpolation progress (0.0 to 1.0)
            
        Returns:
            New TickAnimationState representing interpolated values
        """
        if not (0.0 <= progress <= 1.0):
            raise ValueError("Progress must be between 0.0 and 1.0")
        
        # Linear interpolation for all properties
        interp_tick = self.tick + int((target.tick - self.tick) * progress)
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
        
        return TickAnimationState(
            tick=interp_tick,
            position=interp_position,
            rotation=interp_rotation,
            scale=interp_scale,
            opacity=interp_opacity,
            custom_properties=interp_custom
        )
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize animation state for cross-core communication."""
        return {
            'tick': self.tick,
            'position': self.position,
            'rotation': self.rotation,
            'scale': self.scale,
            'opacity': self.opacity,
            'custom_properties': self.custom_properties
        }
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'TickAnimationState':
        """Deserialize animation state from cross-core communication."""
        return cls(
            tick=data['tick'],
            position=tuple(data['position']),
            rotation=data['rotation'],
            scale=tuple(data['scale']),
            opacity=data['opacity'],
            custom_properties=data.get('custom_properties', {})
        )


class TickEasing:
    """Pure functional easing functions for tick-based animations.
    
    All easing functions operate on normalized progress (0.0 to 1.0) and
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
        
        result = amplitude * math.pow(2, -10 * t) * math.sin((t - s) * 2 * math.pi / period) + 1.0
        
        # Clamp result to valid range [0.0, 1.0] to prevent interpolation errors
        return max(0.0, min(1.0, result))
    
    @classmethod
    def get_easing_function(cls, easing: Union[EasingFunction, str]) -> Callable[[float], float]:
        """Get easing function by name or enum."""
        if isinstance(easing, EasingFunction):
            easing_name = easing.value
        else:
            easing_name = easing
        
        easing_map = {
            "linear": cls.linear,
            "ease_in": cls.ease_in,
            "ease_out": cls.ease_out,
            "ease_in_out": cls.ease_in_out,
            "ease_in_cubic": cls.ease_in_cubic,
            "ease_out_cubic": cls.ease_out_cubic,
            "ease_in_out_cubic": cls.ease_in_out_cubic,
            "bounce": cls.bounce,
            "elastic": cls.elastic
        }
        
        return easing_map.get(easing_name, cls.ease_in_out)


@dataclass(frozen=True)
class TickAnimationDefinition:
    """Immutable tick-based animation definition for deterministic playback.
    
    Defines all parameters needed to compute animation state at any tick.
    Once created, the definition is immutable to ensure deterministic behavior.
    """
    start_tick: int
    duration_ticks: int
    start_state: TickAnimationState
    end_state: TickAnimationState
    easing: str = "linear"
    repeat_count: int = 1
    repeat_mode: str = "restart"  # "restart", "reverse", "mirror"
    
    def __post_init__(self):
        """Validate animation definition parameters."""
        if self.start_tick < 0:
            raise ValueError("Start tick must be non-negative")
        if self.duration_ticks <= 0:
            raise ValueError("Duration must be positive")
        if self.repeat_count < 1:
            raise ValueError("Repeat count must be at least 1")
        if self.repeat_mode not in ("restart", "reverse", "mirror"):
            raise ValueError("Invalid repeat mode")
    
    @property
    def end_tick(self) -> int:
        """Get the tick when animation ends."""
        return self.start_tick + (self.duration_ticks * self.repeat_count)
    
    def is_active_at(self, tick: int) -> bool:
        """Check if animation is active at given tick."""
        return self.start_tick <= tick <= self.end_tick
    
    def is_completed_at(self, tick: int) -> bool:
        """Check if animation is completed at given tick."""
        return tick > self.end_tick
    
    def get_local_progress(self, tick: int) -> float:
        """Get local progress within current repeat cycle.
        
        Args:
            tick: Current tick
            
        Returns:
            Progress value between 0.0 and 1.0
        """
        if tick < self.start_tick:
            return 0.0
        if tick >= self.end_tick:
            return 1.0
        
        # Calculate which repeat cycle we're in
        elapsed_ticks = tick - self.start_tick
        cycle_number = elapsed_ticks // self.duration_ticks
        tick_in_cycle = elapsed_ticks % self.duration_ticks
        
        # Calculate base progress within cycle
        progress = tick_in_cycle / self.duration_ticks
        
        # Apply repeat mode
        if self.repeat_mode == "reverse" and cycle_number % 2 == 1:
            progress = 1.0 - progress
        elif self.repeat_mode == "mirror":
            if cycle_number % 2 == 1:
                progress = 1.0 - progress
        
        return progress
    
    def state_at(self, tick: int) -> TickAnimationState:
        """Compute animation state at given tick.
        
        Args:
            tick: Target tick
            
        Returns:
            TickAnimationState at the specified tick
        """
        if tick < self.start_tick:
            return self.start_state
        if tick >= self.end_tick:
            return self.end_state
        
        # Get progress and apply easing
        progress = self.get_local_progress(tick)
        easing_func = TickEasing.get_easing_function(self.easing)
        eased_progress = easing_func(progress)
        
        # Interpolate between start and end states
        return self.start_state.interpolate_to(self.end_state, eased_progress)
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize animation definition for cross-core communication."""
        return {
            'start_tick': self.start_tick,
            'duration_ticks': self.duration_ticks,
            'start_state': self.start_state.serialize(),
            'end_state': self.end_state.serialize(),
            'easing': self.easing,
            'repeat_count': self.repeat_count,
            'repeat_mode': self.repeat_mode
        }
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'TickAnimationDefinition':
        """Deserialize animation definition from cross-core communication."""
        return cls(
            start_tick=data['start_tick'],
            duration_ticks=data['duration_ticks'],
            start_state=TickAnimationState.deserialize(data['start_state']),
            end_state=TickAnimationState.deserialize(data['end_state']),
            easing=data['easing'],
            repeat_count=data['repeat_count'],
            repeat_mode=data['repeat_mode']
        )


class TickAnimationEngine:
    """Engine for computing tick-based animation states across multiple animations.
    
    This engine manages multiple concurrent animations and provides deterministic
    state computation that's safe for multi-core execution using tick-based timing.
    """
    
    def __init__(self):
        """Initialize tick-based animation engine."""
        self.animations: Dict[str, TickAnimationDefinition] = {}
        self.current_tick: int = 0
    
    def add_animation(self, animation_id: str, definition: TickAnimationDefinition) -> None:
        """Add animation definition to the engine."""
        self.animations[animation_id] = definition
    
    def remove_animation(self, animation_id: str) -> None:
        """Remove animation definition from the engine."""
        self.animations.pop(animation_id, None)
    
    def has_animation(self, animation_id: str) -> bool:
        """Check if animation exists in the engine."""
        return animation_id in self.animations
    
    def get_animation(self, animation_id: str) -> Optional[TickAnimationDefinition]:
        """Get animation definition by ID."""
        return self.animations.get(animation_id)
    
    def get_animation_definitions(self) -> Dict[str, TickAnimationDefinition]:
        """Get all animation definitions."""
        return self.animations.copy()
    
    def start_animation_at(self, animation_id: str, start_tick: int) -> bool:
        """Start animation at specific tick.
        
        Args:
            animation_id: Animation identifier
            start_tick: Tick to start animation
            
        Returns:
            True if animation was started, False if not found
        """
        if animation_id not in self.animations:
            return False
        
        # Create new animation definition with updated start tick
        original = self.animations[animation_id]
        updated = TickAnimationDefinition(
            start_tick=start_tick,
            duration_ticks=original.duration_ticks,
            start_state=original.start_state,
            end_state=original.end_state,
            easing=original.easing,
            repeat_count=original.repeat_count,
            repeat_mode=original.repeat_mode
        )
        
        self.animations[animation_id] = updated
        return True
    
    def advance_tick(self) -> None:
        """Advance the engine to the next tick."""
        self.current_tick += 1
    
    def set_current_tick(self, tick: int) -> None:
        """Set the current tick (for seeking/jumping)."""
        if tick < 0:
            raise ValueError("Tick must be non-negative")
        self.current_tick = tick
    
    def get_active_animations_at(self, tick: int) -> List[str]:
        """Get list of active animation IDs at given tick."""
        active = []
        for animation_id, definition in self.animations.items():
            if definition.is_active_at(tick):
                active.append(animation_id)
        return active
    
    def compute_frame_state(self, tick: int) -> Dict[str, TickAnimationState]:
        """Compute complete frame state at given tick.
        
        Args:
            tick: Target tick
            
        Returns:
            Dictionary mapping animation IDs to their states at the tick
        """
        frame_state = {}
        for animation_id, definition in self.animations.items():
            if definition.is_active_at(tick):
                frame_state[animation_id] = definition.state_at(tick)
        return frame_state
    
    def get_frame_at(self, tick: int) -> Dict[str, TickAnimationState]:
        """Get frame state at specific tick (alias for compute_frame_state)."""
        return self.compute_frame_state(tick)
    
    def predict_frame_at_tick(self, target_tick: int) -> Dict[str, TickAnimationState]:
        """Predict animation states at future tick.
        
        Pure function - deterministic across cores. This method is specifically
        designed for multi-core frame pre-computation.
        
        Args:
            target_tick: Future tick to predict
            
        Returns:
            Complete frame state for target tick
        """
        return self.compute_frame_state(target_tick)
    
    def predict_frame_range(self, start_tick: int, end_tick: int) -> Dict[int, Dict[str, TickAnimationState]]:
        """Batch prediction for multiple future frames.
        
        Optimized for multi-core worker distribution. Each tick prediction
        is independent and can be computed on separate cores.
        
        Args:
            start_tick: Starting tick for prediction range
            end_tick: Ending tick for prediction range (inclusive)
            
        Returns:
            Dictionary mapping ticks to their complete frame states
        """
        frame_predictions = {}
        for tick in range(start_tick, end_tick + 1):
            frame_predictions[tick] = self.predict_frame_at_tick(tick)
        return frame_predictions
    
    def get_prediction_workload(self, start_tick: int, num_frames: int, num_workers: int) -> List[Tuple[int, int]]:
        """Generate workload distribution for multi-core frame prediction.
        
        Divides frame prediction work into balanced chunks for worker distribution.
        
        Args:
            start_tick: Starting tick for prediction
            num_frames: Number of frames to predict
            num_workers: Number of worker cores available
            
        Returns:
            List of (start_tick, end_tick) tuples for each worker
        """
        if num_workers <= 0 or num_frames <= 0:
            return []
        
        frames_per_worker = max(1, num_frames // num_workers)
        workload = []
        
        current_tick = start_tick
        for worker_id in range(num_workers):
            if current_tick >= start_tick + num_frames:
                break
            
            # Calculate end tick for this worker
            if worker_id == num_workers - 1:
                # Last worker gets remaining frames
                end_tick = start_tick + num_frames - 1
            else:
                end_tick = min(current_tick + frames_per_worker - 1, start_tick + num_frames - 1)
            
            if current_tick <= end_tick:
                workload.append((current_tick, end_tick))
            
            current_tick = end_tick + 1
        
        return workload
    
    def serialize_engine_state(self) -> Dict[str, Any]:
        """Serialize engine state for cross-core communication."""
        return {
            'current_tick': self.current_tick,
            'animations': {
                animation_id: definition.serialize()
                for animation_id, definition in self.animations.items()
            }
        }
    
    @classmethod
    def deserialize_engine_state(cls, data: Dict[str, Any]) -> 'TickAnimationEngine':
        """Deserialize engine state from cross-core communication."""
        engine = cls()
        engine.current_tick = data['current_tick']
        
        for animation_id, animation_data in data['animations'].items():
            definition = TickAnimationDefinition.deserialize(animation_data)
            engine.add_animation(animation_id, definition)
        
        return engine


class TickFramePredictor:
    """Predicts future animation frames using tick-based timing.
    
    This predictor can compute animation states for future ticks, enabling
    multi-core pre-computation and smooth animation playback.
    """
    
    def __init__(self, lookahead_ticks: int = 120):  # 2 seconds at 60fps
        """Initialize tick-based frame predictor.
        
        Args:
            lookahead_ticks: Number of ticks to predict ahead
        """
        self.lookahead_ticks = lookahead_ticks
        self.engine: Optional[TickAnimationEngine] = None
    
    def set_engine(self, engine: TickAnimationEngine) -> None:
        """Set the animation engine to use for predictions."""
        self.engine = engine
    
    def predict_frame_at(self, target_tick: int) -> Dict[str, TickAnimationState]:
        """Predict animation frame state at target tick.
        
        Args:
            target_tick: Tick to predict
            
        Returns:
            Predicted frame state
        """
        if not self.engine:
            return {}
        
        return self.engine.compute_frame_state(target_tick)
    
    def generate_prediction_ticks(self, start_tick: int) -> List[int]:
        """Generate list of ticks for prediction.
        
        Args:
            start_tick: Starting tick
            
        Returns:
            List of ticks to predict
        """
        return list(range(start_tick, start_tick + self.lookahead_ticks))
    
    def validate_determinism(self, tick: int, num_iterations: int = 100) -> bool:
        """Validate that animation computation is deterministic.
        
        Args:
            tick: Tick to test
            num_iterations: Number of iterations to test
            
        Returns:
            True if all iterations produce identical results
        """
        if not self.engine:
            return False
        
        # Compute reference frame
        reference_frame = self.engine.compute_frame_state(tick)
        
        # Test multiple iterations
        for _ in range(num_iterations):
            test_frame = self.engine.compute_frame_state(tick)
            
            # Compare frames
            if len(test_frame) != len(reference_frame):
                return False
            
            for animation_id in reference_frame:
                if animation_id not in test_frame:
                    return False
                
                ref_state = reference_frame[animation_id]
                test_state = test_frame[animation_id]
                
                # Compare all state properties
                if (ref_state.tick != test_state.tick or
                    ref_state.position != test_state.position or
                    ref_state.rotation != test_state.rotation or
                    ref_state.scale != test_state.scale or
                    ref_state.opacity != test_state.opacity or
                    ref_state.custom_properties != test_state.custom_properties):
                    return False
        
        return True


# Convenience functions for creating common tick-based animations

def create_tick_fade_animation(start_tick: int, duration_ticks: int, 
                              start_opacity: float = 0.0, end_opacity: float = 1.0,
                              position: Tuple[float, float] = (0.0, 0.0),
                              easing: str = "ease_out") -> TickAnimationDefinition:
    """Create a tick-based fade animation.
    
    Args:
        start_tick: Tick to start animation
        duration_ticks: Animation duration in ticks
        start_opacity: Starting opacity (0.0 to 1.0)
        end_opacity: Ending opacity (0.0 to 1.0)
        position: Widget position
        easing: Easing function name
        
    Returns:
        TickAnimationDefinition for fade animation
    """
    start_state = TickAnimationState(
        tick=start_tick,
        position=position,
        opacity=start_opacity
    )
    
    end_state = TickAnimationState(
        tick=start_tick + duration_ticks,
        position=position,
        opacity=end_opacity
    )
    
    return TickAnimationDefinition(
        start_tick=start_tick,
        duration_ticks=duration_ticks,
        start_state=start_state,
        end_state=end_state,
        easing=easing
    )


def create_tick_slide_animation(start_tick: int, duration_ticks: int,
                               start_position: Tuple[float, float],
                               end_position: Tuple[float, float],
                               easing: str = "ease_in_out") -> TickAnimationDefinition:
    """Create a tick-based slide animation.
    
    Args:
        start_tick: Tick to start animation
        duration_ticks: Animation duration in ticks
        start_position: Starting position (x, y)
        end_position: Ending position (x, y)
        easing: Easing function name
        
    Returns:
        TickAnimationDefinition for slide animation
    """
    start_state = TickAnimationState(
        tick=start_tick,
        position=start_position
    )
    
    end_state = TickAnimationState(
        tick=start_tick + duration_ticks,
        position=end_position
    )
    
    return TickAnimationDefinition(
        start_tick=start_tick,
        duration_ticks=duration_ticks,
        start_state=start_state,
        end_state=end_state,
        easing=easing
    )


def create_tick_scale_animation(start_tick: int, duration_ticks: int,
                               start_scale: Tuple[float, float] = (0.0, 0.0),
                               end_scale: Tuple[float, float] = (1.0, 1.0),
                               position: Tuple[float, float] = (0.0, 0.0),
                               easing: str = "bounce") -> TickAnimationDefinition:
    """Create a tick-based scale animation.
    
    Args:
        start_tick: Tick to start animation
        duration_ticks: Animation duration in ticks
        start_scale: Starting scale (x, y)
        end_scale: Ending scale (x, y)
        position: Widget position
        easing: Easing function name
        
    Returns:
        TickAnimationDefinition for scale animation
    """
    start_state = TickAnimationState(
        tick=start_tick,
        position=position,
        scale=start_scale
    )
    
    end_state = TickAnimationState(
        tick=start_tick + duration_ticks,
        position=position,
        scale=end_scale
    )
    
    return TickAnimationDefinition(
        start_tick=start_tick,
        duration_ticks=duration_ticks,
        start_state=start_state,
        end_state=end_state,
        easing=easing
    ) 