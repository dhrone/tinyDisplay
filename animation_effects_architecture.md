# Animation Effects Architecture Design Document

## 1. Executive Summary

This document defines the architecture for a comprehensive animation effects system that extends the existing tinyDisplay framework's tick-based animation engine. The system will provide deterministic, composable animation effects that can be applied to any widget type while maintaining architectural separation between widgets and animation logic.

### 1.1 Key Requirements Addressed

- **Architectural Separation**: Animation effects are distinct from widgets
- **Universal Application**: Any widget can have effects applied
- **Deterministic Behavior**: Predictable animation states for any tick
- **Future State Queries**: Widgets can render future versions at specific ticks
- **State Change Resilience**: Animation recalculation only on widget state changes
- **DSL Extension**: Expanded Domain-Specific Language supporting visual effects

### 1.2 Core Principles

1. **Effect Composition**: Multiple effects can be stacked and combined
2. **Tick-Based Timing**: All effects operate on the existing tick system
3. **Deterministic Computation**: Same inputs always produce same outputs
4. **Memory Efficiency**: Optimized for resource-constrained displays
5. **Widget Agnostic**: Effects work with any widget implementing the IAnimatable interface

## 2. System Architecture Overview

### 2.1 Component Hierarchy

```
AnimationEffectsSystem
├── EffectEngine (manages all effects)
├── EffectRegistry (effect type definitions)
├── EffectStack (manages effect composition)
├── EffectApplicator (applies effects to widgets)
├── DSLCompiler (parses extended DSL)
└── StatePredictor (future state calculations)

Widget System Integration
├── IAnimatable (interface for animation-ready widgets)
├── AnimationProxy (wrapper for widget animation state)
└── EffectBinding (links effects to widgets)
```

### 2.2 Core Interfaces

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum

class EffectType(Enum):
    """Types of animation effects."""
    TRANSFORM = "transform"        # Position, scale, rotation
    VISUAL = "visual"             # Opacity, color, filters
    PHYSICS = "physics"           # Bounce, spring, gravity
    PROCEDURAL = "procedural"     # Wave, jitter, drift
    COMPOSITE = "composite"       # Multi-effect combinations

@dataclass
class EffectState:
    """State of an animation effect at a specific tick."""
    tick: int
    properties: Dict[str, Any]  # Effect-specific properties
    active: bool = True
    progress: float = 0.0       # 0.0 to 1.0 completion
    
class IAnimatable(ABC):
    """Interface for widgets that support animation effects."""
    
    @abstractmethod
    def get_animation_properties(self) -> Dict[str, Any]:
        """Get current animatable properties."""
        pass
    
    @abstractmethod
    def apply_animation_state(self, properties: Dict[str, Any]) -> None:
        """Apply animation state to widget."""
        pass
    
    @abstractmethod
    def get_bounds_at_tick(self, tick: int) -> WidgetBounds:
        """Get widget bounds at specific tick."""
        pass
    
    @abstractmethod
    def clone_for_prediction(self) -> 'IAnimatable':
        """Create a clone for future state prediction."""
        pass

class IEffect(ABC):
    """Base interface for all animation effects."""
    
    @abstractmethod
    def get_effect_type(self) -> EffectType:
        """Get the type of this effect."""
        pass
    
    @abstractmethod
    def compute_state_at_tick(self, tick: int, base_properties: Dict[str, Any]) -> EffectState:
        """Compute effect state at specific tick."""
        pass
    
    @abstractmethod
    def get_duration_ticks(self) -> Optional[int]:
        """Get effect duration in ticks (None for infinite)."""
        pass
    
    @abstractmethod
    def is_active_at_tick(self, tick: int) -> bool:
        """Check if effect is active at given tick."""
        pass
```

## 3. Core Components Design

### 3.1 EffectEngine

The central orchestrator managing all animation effects.

```python
class EffectEngine:
    """Central engine for managing and computing animation effects."""
    
    def __init__(self, tick_engine: TickAnimationEngine):
        self.tick_engine = tick_engine
        self.effect_stacks: Dict[str, EffectStack] = {}  # widget_id -> stack
        self.effect_registry = EffectRegistry()
        self.state_cache: Dict[Tuple[str, int], EffectState] = {}
        
    def attach_effect(self, widget_id: str, effect: IEffect, 
                     priority: int = 0) -> str:
        """Attach effect to widget with specified priority."""
        
    def detach_effect(self, widget_id: str, effect_id: str) -> bool:
        """Remove effect from widget."""
        
    def compute_widget_state_at_tick(self, widget_id: str, 
                                   tick: int) -> Dict[str, Any]:
        """Compute final animated state for widget at tick."""
        
    def predict_future_states(self, widget_id: str, 
                            start_tick: int, duration: int) -> List[Dict[str, Any]]:
        """Predict widget states for range of future ticks."""
        
    def invalidate_cache_for_widget(self, widget_id: str) -> None:
        """Clear cache when widget state changes."""
```

### 3.2 EffectStack

Manages composition and ordering of multiple effects on a single widget.

```python
class EffectStack:
    """Manages multiple effects applied to a single widget."""
    
    def __init__(self, widget_id: str):
        self.widget_id = widget_id
        self.effects: List[Tuple[IEffect, int, str]] = []  # (effect, priority, id)
        self.base_properties: Dict[str, Any] = {}
        
    def add_effect(self, effect: IEffect, priority: int = 0) -> str:
        """Add effect with priority (higher = applied later)."""
        
    def remove_effect(self, effect_id: str) -> bool:
        """Remove effect by ID."""
        
    def compute_composite_state(self, tick: int) -> Dict[str, Any]:
        """Compute final state by applying all effects in order."""
        
    def get_active_effects_at_tick(self, tick: int) -> List[IEffect]:
        """Get effects active at specified tick."""

class CompositeEffect(IEffect):
    """Composite effect that manages multiple sub-effects with timing control."""
    
    def __init__(self, start_tick: int, execution_mode: str = "parallel"):
        self.start_tick = start_tick
        self.execution_mode = execution_mode  # "parallel", "sequential", "mixed"
        self.sub_effects: List[IEffect] = []
        self.timing_map: Dict[str, int] = {}  # effect_id -> start_offset
        self.blocks: List[Tuple[str, List[IEffect]]] = []  # (block_type, effects)
        self.duration_cache: Optional[int] = None
        
    def add_effect(self, effect: IEffect, delay: int = 0) -> str:
        """Add individual effect (uses default execution mode)."""
        effect_id = f"effect_{len(self.sub_effects)}"
        self.sub_effects.append(effect)
        
        if self.execution_mode == "parallel":
            # Default: parallel execution with optional delay
            self.timing_map[effect_id] = delay
        else:
            # Sequential: calculate start time based on previous effects
            start_offset = sum(e.get_duration_ticks() or 0 for e in self.sub_effects[:-1])
            self.timing_map[effect_id] = start_offset
            
        self._invalidate_duration_cache()
        return effect_id
        
    def add_parallel_block(self, effects: List[IEffect]) -> str:
        """Add a PARALLEL block of effects."""
        block_id = f"block_{len(self.blocks)}"
        self.blocks.append(("parallel", effects))
        
        # Calculate start time for this block
        if len(self.blocks) == 1:
            # First block starts at composite start time
            block_start = 0
        else:
            # Subsequent blocks start after previous blocks complete
            block_start = self._calculate_previous_blocks_duration()
            
        # All effects in parallel block start at the same time (block start)
        for i, effect in enumerate(effects):
            effect_id = f"{block_id}_effect_{i}"
            self.sub_effects.append(effect)
            self.timing_map[effect_id] = block_start
            
        self._invalidate_duration_cache()
        return block_id
        
    def add_sequential_block(self, effects: List[IEffect]) -> str:
        """Add a SEQUENTIAL block of effects."""
        block_id = f"block_{len(self.blocks)}"
        self.blocks.append(("sequential", effects))
        
        # Calculate start time for this block
        if len(self.blocks) == 1:
            block_start = 0
        else:
            block_start = self._calculate_previous_blocks_duration()
            
        # Effects in sequential block start after each other
        current_offset = block_start
        for i, effect in enumerate(effects):
            effect_id = f"{block_id}_effect_{i}"
            self.sub_effects.append(effect)
            self.timing_map[effect_id] = current_offset
            
            # Next effect starts after this one completes
            effect_duration = effect.get_duration_ticks() or 0
            current_offset += effect_duration
            
        self._invalidate_duration_cache()
        return block_id
        
    def _calculate_previous_blocks_duration(self) -> int:
        """Calculate total duration of all previous blocks."""
        total_duration = 0
        
        for block_type, block_effects in self.blocks[:-1]:  # Exclude current block
            if block_type == "parallel":
                # Duration is maximum of all effects in block
                block_duration = max(
                    effect.get_duration_ticks() or 0 
                    for effect in block_effects
                )
            else:  # sequential
                # Duration is sum of all effects in block
                block_duration = sum(
                    effect.get_duration_ticks() or 0 
                    for effect in block_effects
                )
            total_duration += block_duration
            
        return total_duration
        
    def compute_state_at_tick(self, tick: int, base_properties: Dict[str, Any]) -> EffectState:
        """Compute composite effect state at specific tick."""
        if not self.is_active_at_tick(tick):
            return EffectState(tick, {}, active=False)
            
        composite_properties = base_properties.copy()
        active_effects = 0
        
        for i, effect in enumerate(self.sub_effects):
            effect_id = f"effect_{i}" if i < len(self.sub_effects) - len(self._get_block_effects()) else self._get_block_effect_id(i)
            effect_start_tick = self.start_tick + self.timing_map.get(effect_id, 0)
            
            if effect.is_active_at_tick(tick - effect_start_tick):
                effect_state = effect.compute_state_at_tick(
                    tick - effect_start_tick, composite_properties
                )
                
                if effect_state.active:
                    # Apply effect properties to composite state
                    # Order matters: later effects can override earlier ones
                    composite_properties.update(effect_state.properties)
                    active_effects += 1
        
        return EffectState(
            tick=tick,
            properties=composite_properties,
            active=active_effects > 0,
            progress=self._calculate_composite_progress(tick)
        )
        
    def get_duration_ticks(self) -> Optional[int]:
        """Get total duration of composite effect."""
        if self.duration_cache is not None:
            return self.duration_cache
            
        if self.blocks:
            # Calculate duration based on blocks
            total_duration = 0
            for block_type, block_effects in self.blocks:
                if block_type == "parallel":
                    # Block duration is maximum of all effects
                    block_duration = max(
                        effect.get_duration_ticks() or 0 
                        for effect in block_effects
                    )
                else:  # sequential
                    # Block duration is sum of all effects
                    block_duration = sum(
                        effect.get_duration_ticks() or 0 
                        for effect in block_effects
                    )
                total_duration += block_duration
                
        else:
            # Calculate duration based on individual effects and execution mode
            if self.execution_mode == "parallel":
                # Duration is the maximum of all effects (considering delays)
                total_duration = max(
                    self.timing_map.get(f"effect_{i}", 0) + (effect.get_duration_ticks() or 0)
                    for i, effect in enumerate(self.sub_effects)
                )
            else:  # sequential
                # Duration is the sum of all effects
                total_duration = sum(
                    effect.get_duration_ticks() or 0 
                    for effect in self.sub_effects
                )
                
        self.duration_cache = total_duration
        return total_duration
        
    def _get_block_effects(self) -> List[IEffect]:
        """Get all effects from blocks."""
        block_effects = []
        for _, effects in self.blocks:
            block_effects.extend(effects)
        return block_effects
        
    def _get_block_effect_id(self, index: int) -> str:
        """Get effect ID for block-based effect."""
        # Implementation to map index to block effect ID
        pass
        
    def _calculate_composite_progress(self, tick: int) -> float:
        """Calculate overall progress of composite effect."""
        duration = self.get_duration_ticks()
        if duration is None or duration == 0:
            return 0.0
        elapsed = tick - self.start_tick
        return min(1.0, max(0.0, elapsed / duration))
        
    def _invalidate_duration_cache(self) -> None:
        """Invalidate cached duration when effects change."""
        self.duration_cache = None
```

### 3.3 Effect Implementations

#### 3.3.1 Transform Effects

```python
class TranslateEffect(IEffect):
    """Position translation effect."""
    
    def __init__(self, start_tick: int, duration_ticks: int,
                 start_pos: Tuple[int, int], end_pos: Tuple[int, int],
                 easing: str = "linear"):
        self.start_tick = start_tick
        self.duration_ticks = duration_ticks
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.easing = easing
        
    def compute_state_at_tick(self, tick: int, base_properties: Dict[str, Any]) -> EffectState:
        if not self.is_active_at_tick(tick):
            return EffectState(tick, {}, active=False)
            
        progress = (tick - self.start_tick) / self.duration_ticks
        eased_progress = apply_easing(progress, self.easing)
        
        current_x = interpolate(self.start_pos[0], self.end_pos[0], eased_progress)
        current_y = interpolate(self.start_pos[1], self.end_pos[1], eased_progress)
        
        return EffectState(
            tick=tick,
            properties={"position": (current_x, current_y)},
            progress=progress
        )

class ScaleEffect(IEffect):
    """Scaling effect for size animation."""
    
    def __init__(self, start_tick: int, duration_ticks: int,
                 start_scale: Tuple[float, float], end_scale: Tuple[float, float],
                 easing: str = "ease_out"):
        # Implementation similar to TranslateEffect
        pass

class RotateEffect(IEffect):
    """Rotation effect."""
    
    def __init__(self, start_tick: int, duration_ticks: int,
                 start_angle: float, end_angle: float,
                 origin: Tuple[int, int] = (0, 0),
                 easing: str = "linear"):
        # Implementation for rotation around origin point
        pass
```

#### 3.3.2 Visual Effects

```python
class FadeEffect(IEffect):
    """Opacity fade effect."""
    
    def __init__(self, start_tick: int, duration_ticks: int,
                 start_alpha: float, end_alpha: float,
                 easing: str = "ease_in_out"):
        self.start_tick = start_tick
        self.duration_ticks = duration_ticks
        self.start_alpha = start_alpha
        self.end_alpha = end_alpha
        self.easing = easing
        
    def compute_state_at_tick(self, tick: int, base_properties: Dict[str, Any]) -> EffectState:
        if not self.is_active_at_tick(tick):
            return EffectState(tick, {}, active=False)
            
        progress = (tick - self.start_tick) / self.duration_ticks
        eased_progress = apply_easing(progress, self.easing)
        
        current_alpha = interpolate(self.start_alpha, self.end_alpha, eased_progress)
        
        return EffectState(
            tick=tick,
            properties={"alpha": current_alpha},
            progress=progress
        )

class ColorTransitionEffect(IEffect):
    """Color transition effect."""
    
    def __init__(self, start_tick: int, duration_ticks: int,
                 start_color: Tuple[int, int, int], end_color: Tuple[int, int, int],
                 property_name: str = "color",
                 easing: str = "ease_in_out"):
        # Implementation for color interpolation
        pass
```

#### 3.3.3 Physics Effects

```python
class BounceEffect(IEffect):
    """Physics-based bounce effect."""
    
    def __init__(self, start_tick: int, initial_velocity: Tuple[float, float],
                 gravity: float = 0.5, damping: float = 0.8,
                 bounds: Optional[WidgetBounds] = None):
        self.start_tick = start_tick
        self.initial_velocity = initial_velocity
        self.gravity = gravity
        self.damping = damping
        self.bounds = bounds
        self.settled = False
        self.settle_threshold = 0.1
        
    def compute_state_at_tick(self, tick: int, base_properties: Dict[str, Any]) -> EffectState:
        if tick < self.start_tick:
            return EffectState(tick, {}, active=False)
            
        time_delta = tick - self.start_tick
        current_pos = self._simulate_physics(time_delta, base_properties.get("position", (0, 0)))
        
        return EffectState(
            tick=tick,
            properties={"position": current_pos},
            active=not self.settled
        )
    
    def _simulate_physics(self, time_delta: int, start_pos: Tuple[int, int]) -> Tuple[int, int]:
        """Simulate physics for bounce effect."""
        # Physics simulation implementation
        pass

class SpringEffect(IEffect):
    """Spring-based animation effect."""
    
    def __init__(self, start_tick: int, target_value: Any,
                 spring_constant: float = 0.1, damping: float = 0.8):
        # Implementation for spring physics
        pass
```

#### 3.3.4 Procedural Effects

```python
class WaveEffect(IEffect):
    """Wave oscillation effect."""
    
    def __init__(self, start_tick: int, amplitude: float,
                 frequency: float, axis: str = "y",
                 phase_offset: float = 0.0):
        self.start_tick = start_tick
        self.amplitude = amplitude
        self.frequency = frequency
        self.axis = axis
        self.phase_offset = phase_offset
        
    def compute_state_at_tick(self, tick: int, base_properties: Dict[str, Any]) -> EffectState:
        if tick < self.start_tick:
            return EffectState(tick, {}, active=False)
            
        time = tick - self.start_tick
        offset = self.amplitude * math.sin(
            (time * self.frequency + self.phase_offset) * math.pi / 180
        )
        
        current_pos = base_properties.get("position", (0, 0))
        if self.axis == "x":
            new_pos = (current_pos[0] + offset, current_pos[1])
        else:
            new_pos = (current_pos[0], current_pos[1] + offset)
            
        return EffectState(
            tick=tick,
            properties={"position": new_pos},
            active=True
        )

class JitterEffect(IEffect):
    """Random jitter/shake effect."""
    
    def __init__(self, start_tick: int, duration_ticks: int,
                 intensity: float, frequency: int = 1):
        # Implementation for random jitter
        pass
```

## 4. Extended DSL Specification

### 4.1 New DSL Commands for Effects

```ebnf
EffectStmt       ::=  
      FadeStmt
    | ScaleStmt  
    | RotateStmt
    | ColorStmt
    | BounceStmt
    | SpringStmt
    | WaveStmt
    | JitterStmt
    | CompositeStmt
    | ParallelBlock
    | SequentialBlock
    ;

FadeStmt         ::=  
      "FADE" "(" Direction "," Expr ")" [ Options ] ";"
    | "FADE" "(" Expr "," Expr ")" [ Options ] ";"
    ;

ScaleStmt        ::=  
      "SCALE" "(" Expr [ "," Expr ] ")" [ Options ] ";"
    ;

RotateStmt       ::=  
      "ROTATE" "(" Expr [ "," Expr "," Expr ] ")" [ Options ] ";"
    ;

ColorStmt        ::=  
      "COLOR_TRANSITION" "(" ColorValue "," ColorValue ")" [ Options ] ";"
    ;

BounceStmt       ::=  
      "BOUNCE" "(" [ Options ] ")" ";"
    ;

SpringStmt       ::=  
      "SPRING" "(" Expr [ "," Options ] ")" ";"
    ;

WaveStmt         ::=  
      "WAVE" "(" Expr "," Expr [ "," Direction ] ")" [ Options ] ";"
    ;

JitterStmt       ::=  
      "JITTER" "(" Expr [ "," Options ] ")" ";"
    ;

CompositeStmt    ::=  
      "COMPOSITE" [ "(" IDENT ")" ] "{" EffectList "}" [ Options ] ";"
    ;

ParallelBlock    ::=  
      "PARALLEL" "{" EffectList "}" ";"
    ;

SequentialBlock  ::=  
      "SEQUENTIAL" "{" EffectList "}" ";"
    ;

EffectList       ::=  EffectStmt { EffectStmt } ;
ColorValue       ::=  "rgb(" NUMBER "," NUMBER "," NUMBER ")" | IDENT ;
Direction        ::=  "IN" | "OUT" | "LEFT" | "RIGHT" | "UP" | "DOWN" ;
```

### 4.2 DSL Examples

#### 4.2.1 Basic Effects

```dsl
# Fade in over 30 ticks
FADE(IN, 1.0) { duration=30, easing=ease_in };

# Scale up from 50% to 100%
SCALE(0.5, 1.0) { duration=45, easing=ease_out };

# Rotate 360 degrees around center
ROTATE(360) { duration=60, origin=center };

# Color transition from red to blue
COLOR_TRANSITION(rgb(255,0,0), rgb(0,0,255)) { duration=40, property=background };
```

#### 4.2.2 Physics Effects

```dsl
# Bounce effect with gravity
BOUNCE() { gravity=0.8, damping=0.7, bounds=container };

# Spring to target position
SPRING(target_position) { spring_constant=0.15, damping=0.9 };
```

#### 4.2.3 Procedural Effects

```dsl
# Vertical wave oscillation
WAVE(10, 0.1, UP) { duration=INFINITE };

# Jitter effect for 2 seconds
JITTER(3.0) { duration=120, frequency=2 };
```

#### 4.2.4 Composite Effects

```dsl
# PARALLEL EXECUTION (Default)
# All effects start simultaneously, can use delays for staggering
COMPOSITE(entrance) {
    MOVE(LEFT, 100) { duration=40, easing=ease_out };
    FADE(IN, 1.0) { duration=30, delay=10 };  # Starts 10 ticks after MOVE
} { execution=parallel };

# SEQUENTIAL EXECUTION  
# Effects run one after another
COMPOSITE(entrance) {
    MOVE(LEFT, 100) { duration=40, easing=ease_out };
    FADE(IN, 1.0) { duration=30 };  # Starts after MOVE completes
} { execution=sequential };

# MIXED EXECUTION
# Use PARALLEL and SEQUENTIAL blocks for complex timing
COMPOSITE(complex_entrance) {
    PARALLEL {
        MOVE(LEFT, 100) { duration=40 };
        SCALE(0.8, 1.0) { duration=40 };
    }
    SEQUENTIAL {
        PAUSE(10);  # Wait 10 ticks
        FADE(IN, 1.0) { duration=20 };
        COLOR_TRANSITION(rgb(255,0,0), rgb(0,255,0)) { duration=30 };
    }
} { trigger=on_visible };
```

#### 4.2.5 Timing Control Examples

```dsl
# Example 1: Move THEN fade (sequential)
COMPOSITE(slide_then_fade) {
    MOVE(RIGHT, 100) { duration=30 };
    FADE(IN, 1.0) { duration=20 };  # Starts at tick 30
} { execution=sequential };

# Example 2: Move AND fade simultaneously (parallel)
COMPOSITE(slide_and_fade) {
    MOVE(RIGHT, 100) { duration=30 };
    FADE(IN, 1.0) { duration=30 };  # Both start at tick 0
} { execution=parallel };

# Example 3: Move, pause, then fade
COMPOSITE(slide_pause_fade) {
    MOVE(RIGHT, 100) { duration=30 };
    PAUSE(15);  # 15 tick pause
    FADE(IN, 1.0) { duration=20 };  # Starts at tick 45
} { execution=sequential };

# Example 4: Complex mixed timing
COMPOSITE(complex_effect) {
    # These run in parallel
    PARALLEL {
        MOVE(LEFT, 50) { duration=25 };
        WAVE(5, 0.1, UP) { duration=50 };
    }
    # Then these run sequentially
    SEQUENTIAL {
        SCALE(1.0, 1.2) { duration=15 };
        FADE(OUT, 0.0) { duration=20 };
    }
} { priority=high };

# Example 5: Staggered parallel effects
COMPOSITE(staggered_entrance) {
    MOVE(LEFT, 100) { duration=40 };
    FADE(IN, 1.0) { duration=30, delay=10 };    # Starts at tick 10
    SCALE(0.5, 1.0) { duration=25, delay=20 };  # Starts at tick 20
} { execution=parallel };
```

#### 4.2.6 Composite Effect Execution Rules

#### Default Execution Mode
When no `execution` option is specified, **parallel execution is the default**:

```dsl
# These are equivalent:
COMPOSITE(effect1) {
    MOVE(LEFT, 100) { duration=30 };
    FADE(IN, 1.0) { duration=30 };
}

COMPOSITE(effect2) {
    MOVE(LEFT, 100) { duration=30 };
    FADE(IN, 1.0) { duration=30 };
} { execution=parallel };
```

#### Mixed Block Execution Order
When both PARALLEL and SEQUENTIAL blocks appear in the same COMPOSITE, **the blocks themselves execute sequentially** in the order they appear:

```dsl
COMPOSITE(mixed_effect) {
    # Block 1: PARALLEL block executes first (ticks 0-40)
    PARALLEL {
        MOVE(LEFT, 100) { duration=40 };
        SCALE(0.8, 1.0) { duration=40 };
    }
    # Block 2: SEQUENTIAL block executes after Block 1 completes (starts at tick 40)
    SEQUENTIAL {
        PAUSE(10);  # Ticks 40-50
        FADE(IN, 1.0) { duration=20 };  # Ticks 50-70
        COLOR_TRANSITION(rgb(255,0,0), rgb(0,255,0)) { duration=30 };  # Ticks 70-100
    }
} { trigger=on_visible };
```

#### Multiple Block Timeline:
```
Tick:  0    10    20    30    40    50    60    70    80    90   100
Block1: [---PARALLEL BLOCK (MOVE+SCALE)---]
Block2:                                     [-PAUSE-][--FADE--][COLOR_TRANS]
```

#### Explicit Block Ordering
For clarity, you can also explicitly specify execution mode for mixed blocks:

```dsl
# Explicit sequential execution of blocks
COMPOSITE(explicit_mixed) {
    PARALLEL {
        MOVE(LEFT, 50) { duration=25 };
        WAVE(5, 0.1) { duration=25 };
    }
    SEQUENTIAL {
        SCALE(1.0, 1.2) { duration=15 };
        FADE(OUT, 0.0) { duration=20 };
    }
} { execution=sequential };  # Blocks run sequentially (default for mixed)

# Force parallel execution of blocks (unusual but possible)
COMPOSITE(parallel_blocks) {
    PARALLEL {
        MOVE(LEFT, 50) { duration=25 };
        WAVE(5, 0.1) { duration=50 };  # Longer duration
    }
    SEQUENTIAL {
        PAUSE(10);
        FADE(OUT, 0.0) { duration=20 };
    }
} { execution=parallel };  # Both blocks start simultaneously
```

#### Execution Mode Priority Rules
1. **Individual effects** within a COMPOSITE without blocks → **Default: parallel**
2. **Effects within PARALLEL block** → **Always parallel**
3. **Effects within SEQUENTIAL block** → **Always sequential**  
4. **Multiple blocks** (PARALLEL + SEQUENTIAL) → **Default: sequential between blocks**
5. **Explicit execution option** → **Overrides defaults**

### 4.3 DSL Integration Points

```python
class EffectDSLCompiler:
    """Compiles DSL effect definitions into effect objects."""
    
    def __init__(self, effect_registry: EffectRegistry):
        self.effect_registry = effect_registry
        self.parser = EffectParser()
        
    def compile_effects(self, dsl_source: str) -> List[IEffect]:
        """Compile DSL source into effect objects."""
        
    def compile_effect_statement(self, stmt: EffectStatement) -> IEffect:
        """Compile single effect statement."""
        
    def validate_effect_composition(self, effects: List[IEffect]) -> bool:
        """Validate that effects can be composed together."""
```

## 5. Widget Integration Strategy

### 5.1 Making Widgets Animation-Ready

#### 5.1.1 IAnimatable Implementation

```python
# Example: TextWidget implementing IAnimatable
class TextWidget(Widget, IAnimatable):
    
    def get_animation_properties(self) -> Dict[str, Any]:
        """Get current animatable properties."""
        return {
            "position": self.position,
            "size": self.size,
            "alpha": self.alpha,
            "color": self._font_style.color,
            "font_size": self._font_style.size,
            "rotation": getattr(self, '_rotation', 0.0),
            "scale": getattr(self, '_scale', (1.0, 1.0))
        }
    
    def apply_animation_state(self, properties: Dict[str, Any]) -> None:
        """Apply animation state to widget."""
        if "position" in properties:
            self.position = properties["position"]
        if "alpha" in properties:
            self.alpha = properties["alpha"]
        if "color" in properties:
            self._font_style.color = properties["color"]
        if "font_size" in properties:
            self._font_style.size = properties["font_size"]
        if "rotation" in properties:
            self._rotation = properties["rotation"]
        if "scale" in properties:
            self._scale = properties["scale"]
            
        self._mark_dirty()
    
    def get_bounds_at_tick(self, tick: int) -> WidgetBounds:
        """Get widget bounds at specific tick."""
        # Create temporary clone with animation state applied
        clone = self.clone_for_prediction()
        
        # Get animation engine and compute state
        if hasattr(self, '_effect_engine'):
            animated_state = self._effect_engine.compute_widget_state_at_tick(
                self.widget_id, tick
            )
            clone.apply_animation_state(animated_state)
        
        return clone.bounds
    
    def clone_for_prediction(self) -> 'TextWidget':
        """Create a clone for future state prediction."""
        clone = TextWidget(
            text=self.text,
            font_style=copy.deepcopy(self._font_style),
            layout=copy.deepcopy(self._layout)
        )
        clone.position = self.position
        clone.size = self.size
        clone.alpha = self.alpha
        return clone
```

#### 5.1.2 AnimationProxy

```python
class AnimationProxy:
    """Proxy that wraps widgets to provide animation capabilities."""
    
    def __init__(self, widget: Widget, effect_engine: EffectEngine):
        self.widget = widget
        self.effect_engine = effect_engine
        self.last_widget_state_hash = None
        
        # Ensure widget implements IAnimatable
        if not isinstance(widget, IAnimatable):
            raise ValueError(f"Widget {widget.widget_id} must implement IAnimatable")
            
    def attach_effect(self, effect: IEffect, priority: int = 0) -> str:
        """Attach effect to the wrapped widget."""
        return self.effect_engine.attach_effect(
            self.widget.widget_id, effect, priority
        )
        
    def render_at_tick(self, canvas: 'Canvas', tick: int) -> None:
        """Render widget at specific tick with all effects applied."""
        # Check if widget state changed
        current_state_hash = self._compute_widget_state_hash()
        if current_state_hash != self.last_widget_state_hash:
            self.effect_engine.invalidate_cache_for_widget(self.widget.widget_id)
            self.last_widget_state_hash = current_state_hash
            
        # Get animated state
        animated_state = self.effect_engine.compute_widget_state_at_tick(
            self.widget.widget_id, tick
        )
        
        # Create rendering clone
        render_widget = self.widget.clone_for_prediction()
        render_widget.apply_animation_state(animated_state)
        
        # Render the animated widget
        render_widget.render(canvas)
        
    def _compute_widget_state_hash(self) -> int:
        """Compute hash of widget's visual state."""
        # Hash relevant widget properties that affect visual appearance
        pass
```

## 6. Performance Optimization

### 6.1 Caching Strategy

```python
class EffectStateCache:
    """LRU cache for effect states to optimize repeated calculations."""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[Tuple[str, int], EffectState] = {}
        self.access_times: Dict[Tuple[str, int], float] = {}
        self.max_size = max_size
        
    def get(self, widget_id: str, tick: int) -> Optional[EffectState]:
        """Get cached effect state."""
        
    def put(self, widget_id: str, tick: int, state: EffectState) -> None:
        """Cache effect state with LRU eviction."""
        
    def invalidate_widget(self, widget_id: str) -> None:
        """Invalidate all cached states for widget."""
```

### 6.2 Batch Processing

```python
class BatchEffectProcessor:
    """Process multiple effects efficiently in batch operations."""
    
    def compute_batch_states(self, 
                           requests: List[Tuple[str, int]]) -> Dict[Tuple[str, int], EffectState]:
        """Compute multiple effect states in optimized batch."""
        
    def predict_batch_futures(self, 
                            widget_id: str, tick_range: range) -> Dict[int, EffectState]:
        """Predict future states for a range of ticks."""
```

## 7. Implementation Plan

### 7.1 Epic Breakdown

#### Phase 1: Core Infrastructure (2-3 Sprints)
- **Story 1.1**: Implement IAnimatable interface and base effect classes
- **Story 1.2**: Create EffectEngine and EffectStack core classes
- **Story 1.3**: Implement AnimationProxy wrapper system
- **Story 1.4**: Basic effect state caching system

#### Phase 2: Basic Effects (2-3 Sprints)
- **Story 2.1**: Implement Transform effects (Translate, Scale, Rotate)
- **Story 2.2**: Implement Visual effects (Fade, ColorTransition)
- **Story 2.3**: Update TextWidget to implement IAnimatable
- **Story 2.4**: Integration testing with existing tick animation system

#### Phase 3: Advanced Effects (2-3 Sprints)
- **Story 3.1**: Implement Physics effects (Bounce, Spring)
- **Story 3.2**: Implement Procedural effects (Wave, Jitter)
- **Story 3.3**: Composite effect system and effect stacking
- **Story 3.4**: Performance optimization and batch processing

#### Phase 4: DSL Extension (2 Sprints)
- **Story 4.1**: Extend DSL parser for effect commands
- **Story 4.2**: Effect DSL compiler and validation
- **Story 4.3**: DSL integration with effect engine
- **Story 4.4**: Comprehensive testing and documentation

#### Phase 5: Widget Ecosystem (1-2 Sprints)
- **Story 5.1**: Update remaining widgets (Image, Canvas) for IAnimatable
- **Story 5.2**: Widget factory integration with animation system
- **Story 5.3**: Performance benchmarking and optimization
- **Story 5.4**: Final integration testing and performance validation

### 7.2 Testing Strategy

#### 7.2.1 Unit Tests
- Effect computation determinism validation
- State caching correctness
- Widget cloning and prediction accuracy
- DSL compilation and parsing

#### 7.2.2 Integration Tests
- Multi-effect composition testing
- Performance under resource constraints
- Memory usage validation
- Tick-based determinism across widget types

#### 7.2.3 Performance Tests
- Animation frame rate benchmarks
- Memory usage under various effect loads
- Cache efficiency measurements
- Multi-core prediction performance

### 7.3 Acceptance Criteria

1. **Deterministic Behavior**: Same tick always produces same visual result
2. **Universal Application**: All core widgets support animation effects
3. **Performance Targets**: 60fps with up to 10 simultaneous animated widgets
4. **Memory Efficiency**: <1MB additional memory usage for typical animations
5. **DSL Completeness**: All documented effects available through DSL
6. **Future State Queries**: Widgets can render any future tick accurately

## 8. Risk Mitigation

### 8.1 Technical Risks

#### Risk: Performance degradation with multiple effects
**Mitigation**: Implement aggressive caching and batch processing, profile early

#### Risk: Memory usage growth with long-running animations
**Mitigation**: LRU cache with size limits, periodic cache cleanup

#### Risk: DSL complexity affecting maintainability
**Mitigation**: Comprehensive parsing tests, clear documentation

### 8.2 Integration Risks

#### Risk: Breaking existing widget functionality
**Mitigation**: Phased rollout, extensive regression testing

#### Risk: Animation system conflicts with existing tick engine
**Mitigation**: Close coordination with existing animation APIs, unified interfaces

## 9. Future Extensions

### 9.1 Advanced Effect Types
- **Particle Systems**: For complex visual effects
- **Shader-like Effects**: For visual filters and transformations
- **Constraint-based Animation**: For physics-based layouts

### 9.2 Performance Enhancements
- **GPU Acceleration**: For computationally intensive effects
- **WebAssembly Compilation**: For DSL performance optimization
- **Predictive Caching**: Machine learning for cache optimization

This architecture provides a solid foundation for implementing comprehensive animation effects while maintaining the deterministic, resource-efficient characteristics required for the tinyDisplay framework. 