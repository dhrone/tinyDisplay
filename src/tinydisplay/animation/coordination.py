"""
Animation Coordination Primitives for tinyDisplay Epic 3

This module implements deterministic coordination mechanisms for complex multi-animation
sequences, enabling precise timing control and state-based triggers across distributed
worker cores.

Key Coordination Primitives:
- AnimationSync: Synchronize multiple animations to start at exact timestamp
- AnimationBarrier: Wait for multiple animations to complete before proceeding
- AnimationSequence: Execute animations in deterministic sequence with timing offsets
- AnimationTrigger: Trigger animations based on state conditions
- CoordinationPlan: Orchestrate complex multi-phase animation scenarios

All primitives operate on absolute timestamps for deterministic behavior across cores.
"""

import time
import math
from typing import Dict, List, Optional, Tuple, Callable, Any, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

from .deterministic import AnimationState, AnimationDefinition, DeterministicAnimationEngine
from .multicore import CoordinationEventType


# ============================================================================
# Core Coordination Data Structures
# ============================================================================

@dataclass
class CoordinationEvent:
    """Base class for coordination events."""
    event_id: str
    event_type: CoordinationEventType
    timestamp: float
    priority: int = 0
    is_completed: bool = False
    completion_time: Optional[float] = None


@dataclass
class AnimationReference:
    """Reference to an animation with timing information."""
    animation_id: str
    start_time: float
    duration: float
    priority: int = 0
    
    @property
    def end_time(self) -> float:
        """Calculate animation end time."""
        return self.start_time + self.duration


class CoordinationState(Enum):
    """States for coordination primitives."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# Base Coordination Primitive
# ============================================================================

class CoordinationPrimitive(ABC):
    """Abstract base class for all coordination primitives."""
    
    def __init__(self, primitive_id: str, timestamp: float):
        """Initialize coordination primitive."""
        self.primitive_id = primitive_id
        self.timestamp = timestamp
        self.state = CoordinationState.PENDING
        self.creation_time = time.time()
        self.activation_time: Optional[float] = None
        self.completion_time: Optional[float] = None
        self.error_message: Optional[str] = None
    
    @abstractmethod
    def evaluate_at(self, current_time: float, engine: DeterministicAnimationEngine) -> bool:
        """Evaluate if coordination condition is met at current time."""
        pass
    
    @abstractmethod
    def get_affected_animations(self) -> List[str]:
        """Get list of animation IDs affected by this primitive."""
        pass
    
    def activate(self, current_time: float):
        """Activate the coordination primitive."""
        if self.state == CoordinationState.PENDING:
            self.state = CoordinationState.ACTIVE
            self.activation_time = current_time
    
    def complete(self, current_time: float):
        """Mark coordination primitive as completed."""
        if self.state == CoordinationState.ACTIVE:
            self.state = CoordinationState.COMPLETED
            self.completion_time = current_time
    
    def fail(self, current_time: float, error_message: str):
        """Mark coordination primitive as failed."""
        self.state = CoordinationState.FAILED
        self.completion_time = current_time
        self.error_message = error_message
    
    def cancel(self, current_time: float):
        """Cancel coordination primitive."""
        self.state = CoordinationState.CANCELLED
        self.completion_time = current_time


# ============================================================================
# Animation Sync Primitive
# ============================================================================

class AnimationSync(CoordinationPrimitive):
    """Synchronize multiple animations to start at exact timestamp."""
    
    def __init__(self, primitive_id: str, sync_time: float, animations: List[str]):
        """Initialize animation sync primitive.
        
        Args:
            primitive_id: Unique identifier for this sync primitive
            sync_time: Absolute timestamp when animations should start
            animations: List of animation IDs to synchronize
        """
        super().__init__(primitive_id, sync_time)
        self.sync_time = sync_time
        self.animation_ids = animations.copy()
        self.synchronized_animations: Set[str] = set()
    
    def evaluate_at(self, current_time: float, engine: DeterministicAnimationEngine) -> bool:
        """Check if sync condition is met at current time."""
        if self.state != CoordinationState.PENDING:
            return self.state == CoordinationState.COMPLETED
        
        # Check if we've reached the sync time
        if current_time >= self.sync_time:
            # Activate the primitive first
            self.activate(current_time)
            
            # Activate all animations at sync time
            for animation_id in self.animation_ids:
                if engine.has_animation(animation_id):
                    # Start animation at sync time
                    animation = engine.get_animation(animation_id)
                    if animation and not animation.is_active_at(self.sync_time):
                        engine.start_animation_at(animation_id, self.sync_time)
                        self.synchronized_animations.add(animation_id)
            
            self.complete(current_time)
            return True
        
        return False
    
    def get_affected_animations(self) -> List[str]:
        """Get list of animation IDs affected by this sync."""
        return self.animation_ids.copy()
    
    def get_sync_status(self) -> Dict[str, bool]:
        """Get synchronization status for each animation."""
        return {anim_id: anim_id in self.synchronized_animations 
                for anim_id in self.animation_ids}


# ============================================================================
# Animation Barrier Primitive
# ============================================================================

class AnimationBarrier(CoordinationPrimitive):
    """Wait for multiple animations to reach completion before proceeding."""
    
    def __init__(self, primitive_id: str, animations: List[str], 
                 barrier_time: Optional[float] = None, timeout: Optional[float] = None):
        """Initialize animation barrier primitive.
        
        Args:
            primitive_id: Unique identifier for this barrier
            animations: List of animation IDs to wait for
            barrier_time: Optional absolute time to wait until
            timeout: Optional timeout in seconds from creation
        """
        super().__init__(primitive_id, barrier_time or time.time())
        self.animation_ids = animations.copy()
        self.barrier_time = barrier_time
        self.timeout = timeout
        self.timeout_time = (self.creation_time + timeout) if timeout else None
        self.completed_animations: Set[str] = set()
    
    def evaluate_at(self, current_time: float, engine: DeterministicAnimationEngine) -> bool:
        """Check if barrier condition is met at current time."""
        if self.state != CoordinationState.PENDING:
            return self.state == CoordinationState.COMPLETED
        
        # Check for timeout
        if self.timeout_time and current_time >= self.timeout_time:
            self.fail(current_time, f"Barrier timeout after {self.timeout}s")
            return False
        
        # Check if barrier time has been reached (if specified)
        if self.barrier_time and current_time < self.barrier_time:
            return False
        
        # Check completion status of all animations
        all_completed = True
        self.completed_animations.clear()
        
        for animation_id in self.animation_ids:
            if engine.has_animation(animation_id):
                animation = engine.get_animation(animation_id)
                if animation and animation.is_completed_at(current_time):
                    self.completed_animations.add(animation_id)
                else:
                    all_completed = False
            else:
                # Animation doesn't exist - consider it completed
                self.completed_animations.add(animation_id)
        
        if all_completed:
            self.complete(current_time)
            return True
        
        return False
    
    def get_affected_animations(self) -> List[str]:
        """Get list of animation IDs affected by this barrier."""
        return self.animation_ids.copy()
    
    def get_completion_status(self) -> Dict[str, bool]:
        """Get completion status for each animation."""
        return {anim_id: anim_id in self.completed_animations 
                for anim_id in self.animation_ids}
    
    def get_progress(self) -> float:
        """Get barrier completion progress (0.0 to 1.0)."""
        if not self.animation_ids:
            return 1.0
        return len(self.completed_animations) / len(self.animation_ids)


# ============================================================================
# Animation Sequence Primitive
# ============================================================================

class AnimationSequence(CoordinationPrimitive):
    """Execute animations in deterministic sequence with timing offsets."""
    
    def __init__(self, primitive_id: str, sequence: List[Tuple[str, float]], 
                 base_time: Optional[float] = None):
        """Initialize animation sequence primitive.
        
        Args:
            primitive_id: Unique identifier for this sequence
            sequence: List of (animation_id, start_offset) tuples
            base_time: Base timestamp for sequence (defaults to current time)
        """
        base_time = base_time or time.time()
        super().__init__(primitive_id, base_time)
        
        self.base_time = base_time
        self.sequence = sequence.copy()
        self.active_animations: Set[str] = set()
        self.completed_animations: Set[str] = set()
        self.current_step = 0
        
        # Calculate absolute start times
        self.animation_schedule: List[Tuple[str, float]] = [
            (anim_id, base_time + offset) for anim_id, offset in sequence
        ]
        
        # Sort by start time for efficient processing
        self.animation_schedule.sort(key=lambda x: x[1])
    
    def evaluate_at(self, current_time: float, engine: DeterministicAnimationEngine) -> bool:
        """Evaluate sequence state at current time."""
        if self.state == CoordinationState.COMPLETED:
            return True
        
        if self.state == CoordinationState.PENDING:
            self.activate(current_time)
        
        # Start animations that should be active at current time
        while (self.current_step < len(self.animation_schedule) and 
               current_time >= self.animation_schedule[self.current_step][1]):
            
            animation_id, start_time = self.animation_schedule[self.current_step]
            
            if engine.has_animation(animation_id):
                engine.start_animation_at(animation_id, start_time)
                self.active_animations.add(animation_id)
            
            self.current_step += 1
        
        # Check for completed animations
        for animation_id in list(self.active_animations):
            if engine.has_animation(animation_id):
                animation = engine.get_animation(animation_id)
                if animation and animation.is_completed_at(current_time):
                    self.active_animations.remove(animation_id)
                    self.completed_animations.add(animation_id)
        
        # Check if sequence is complete
        if (self.current_step >= len(self.animation_schedule) and 
            len(self.active_animations) == 0):
            self.complete(current_time)
            return True
        
        return False
    
    def get_affected_animations(self) -> List[str]:
        """Get list of animation IDs in this sequence."""
        return [anim_id for anim_id, _ in self.sequence]
    
    def get_active_animations_at(self, current_time: float) -> List[str]:
        """Get animations that should be active at current time."""
        active = []
        for animation_id, start_time in self.animation_schedule:
            if start_time <= current_time:
                if animation_id not in self.completed_animations:
                    active.append(animation_id)
        return active
    
    def get_sequence_progress(self) -> float:
        """Get sequence completion progress (0.0 to 1.0)."""
        if not self.sequence:
            return 1.0
        
        total_animations = len(self.sequence)
        completed_count = len(self.completed_animations)
        return completed_count / total_animations
    
    def get_next_animation(self, current_time: float) -> Optional[Tuple[str, float]]:
        """Get next animation to start and its start time."""
        for animation_id, start_time in self.animation_schedule[self.current_step:]:
            if start_time > current_time:
                return (animation_id, start_time)
        return None


# ============================================================================
# Animation Trigger Primitive
# ============================================================================

class AnimationTrigger(CoordinationPrimitive):
    """Trigger animations based on deterministic state conditions."""
    
    def __init__(self, primitive_id: str, condition: Callable[[Dict[str, AnimationState]], bool],
                 triggered_animations: List[str], max_evaluations: int = 1000):
        """Initialize animation trigger primitive.
        
        Args:
            primitive_id: Unique identifier for this trigger
            condition: Function that evaluates frame state and returns bool
            triggered_animations: List of animation IDs to trigger when condition is met
            max_evaluations: Maximum number of condition evaluations to prevent infinite loops
        """
        super().__init__(primitive_id, time.time())
        self.condition = condition
        self.triggered_animations = triggered_animations.copy()
        self.max_evaluations = max_evaluations
        self.evaluation_count = 0
        self.trigger_time: Optional[float] = None
        self.is_triggered = False
    
    def evaluate_at(self, current_time: float, engine: DeterministicAnimationEngine) -> bool:
        """Evaluate trigger condition against current frame state."""
        if self.state == CoordinationState.COMPLETED:
            return True
        
        if self.state == CoordinationState.PENDING:
            self.activate(current_time)
        
        # Check evaluation limit
        if self.evaluation_count >= self.max_evaluations:
            self.fail(current_time, f"Maximum evaluations ({self.max_evaluations}) exceeded")
            return False
        
        # Skip if already triggered
        if self.is_triggered:
            # Check if all triggered animations have started
            all_started = True
            for animation_id in self.triggered_animations:
                if engine.has_animation(animation_id):
                    animation = engine.get_animation(animation_id)
                    if animation and not animation.is_active_at(current_time):
                        all_started = False
                        break
            
            if all_started:
                self.complete(current_time)
                return True
            return False
        
        # Evaluate condition
        try:
            frame_state = engine.get_frame_at(current_time)
            self.evaluation_count += 1
            
            if self.condition(frame_state):
                # Trigger condition met - start animations
                self.is_triggered = True
                self.trigger_time = current_time
                
                for animation_id in self.triggered_animations:
                    if engine.has_animation(animation_id):
                        engine.start_animation_at(animation_id, current_time)
                
                return True
        
        except Exception as e:
            self.fail(current_time, f"Condition evaluation error: {str(e)}")
            return False
        
        return False
    
    def get_affected_animations(self) -> List[str]:
        """Get list of animation IDs affected by this trigger."""
        return self.triggered_animations.copy()
    
    def get_trigger_status(self) -> Dict[str, Any]:
        """Get detailed trigger status information."""
        return {
            "is_triggered": self.is_triggered,
            "trigger_time": self.trigger_time,
            "evaluation_count": self.evaluation_count,
            "max_evaluations": self.max_evaluations,
            "triggered_animations": self.triggered_animations.copy()
        }


# ============================================================================
# Coordination Plan
# ============================================================================

class CoordinationPlan:
    """Orchestrate complex multi-phase animation scenarios."""
    
    def __init__(self, plan_id: str, primitives: List[CoordinationPrimitive]):
        """Initialize coordination plan.
        
        Args:
            plan_id: Unique identifier for this coordination plan
            primitives: List of coordination primitives to execute
        """
        self.plan_id = plan_id
        self.primitives = primitives.copy()
        self.creation_time = time.time()
        self.start_time: Optional[float] = None
        self.completion_time: Optional[float] = None
        self.is_active = False
        self.is_completed = False
        
        # Sort primitives by timestamp for efficient processing
        self.primitives.sort(key=lambda p: p.timestamp)
        
        # Track primitive states
        self.active_primitives: Set[str] = set()
        self.completed_primitives: Set[str] = set()
        self.failed_primitives: Set[str] = set()
    
    def start(self, current_time: float):
        """Start executing the coordination plan."""
        if not self.is_active:
            self.is_active = True
            self.start_time = current_time
    
    def evaluate_at(self, current_time: float, engine: DeterministicAnimationEngine) -> bool:
        """Evaluate coordination plan at current time."""
        if not self.is_active:
            self.start(current_time)
        
        if self.is_completed:
            return True
        
        # Evaluate all primitives
        for primitive in self.primitives:
            if primitive.primitive_id in self.completed_primitives:
                continue
            
            if primitive.primitive_id in self.failed_primitives:
                continue
            
            # Evaluate primitives that are pending or active
            if primitive.state in [CoordinationState.PENDING, CoordinationState.ACTIVE]:
                try:
                    if primitive.evaluate_at(current_time, engine):
                        if primitive.state == CoordinationState.COMPLETED:
                            self.active_primitives.discard(primitive.primitive_id)
                            self.completed_primitives.add(primitive.primitive_id)
                        elif primitive.state == CoordinationState.FAILED:
                            self.active_primitives.discard(primitive.primitive_id)
                            self.failed_primitives.add(primitive.primitive_id)
                    elif primitive.state == CoordinationState.ACTIVE:
                        # Keep track of active primitives
                        self.active_primitives.add(primitive.primitive_id)
                except Exception as e:
                    primitive.fail(current_time, f"Evaluation error: {str(e)}")
                    self.active_primitives.discard(primitive.primitive_id)
                    self.failed_primitives.add(primitive.primitive_id)
        
        # Check if plan is complete
        total_primitives = len(self.primitives)
        finished_primitives = len(self.completed_primitives) + len(self.failed_primitives)
        
        if finished_primitives >= total_primitives:
            self.is_completed = True
            self.completion_time = current_time
            return True
        
        return False
    
    def get_plan_status(self) -> Dict[str, Any]:
        """Get detailed plan status information."""
        total_primitives = len(self.primitives)
        completed_count = len(self.completed_primitives)
        failed_count = len(self.failed_primitives)
        active_count = len(self.active_primitives)
        
        return {
            "plan_id": self.plan_id,
            "is_active": self.is_active,
            "is_completed": self.is_completed,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "total_primitives": total_primitives,
            "completed_primitives": completed_count,
            "failed_primitives": failed_count,
            "active_primitives": active_count,
            "progress": completed_count / total_primitives if total_primitives > 0 else 0.0
        }
    
    def get_affected_animations(self) -> Set[str]:
        """Get all animation IDs affected by this plan."""
        affected = set()
        for primitive in self.primitives:
            affected.update(primitive.get_affected_animations())
        return affected
    
    def cancel(self, current_time: float):
        """Cancel the coordination plan."""
        for primitive in self.primitives:
            if primitive.state in [CoordinationState.PENDING, CoordinationState.ACTIVE]:
                primitive.cancel(current_time)
        
        self.is_completed = True
        self.completion_time = current_time


# ============================================================================
# Coordination Manager
# ============================================================================

class CoordinationManager:
    """Manage multiple coordination plans and primitives."""
    
    def __init__(self):
        """Initialize coordination manager."""
        self.active_plans: Dict[str, CoordinationPlan] = {}
        self.completed_plans: Dict[str, CoordinationPlan] = {}
        self.plan_counter = 0
    
    def add_plan(self, plan: CoordinationPlan):
        """Add coordination plan to manager."""
        self.active_plans[plan.plan_id] = plan
    
    def create_simple_sync(self, animations: List[str], sync_time: float) -> str:
        """Create a simple sync coordination plan."""
        plan_id = f"sync_plan_{self.plan_counter}"
        self.plan_counter += 1
        
        sync_primitive = AnimationSync(f"sync_{plan_id}", sync_time, animations)
        plan = CoordinationPlan(plan_id, [sync_primitive])
        
        self.add_plan(plan)
        return plan_id
    
    def create_sequence_plan(self, sequence: List[Tuple[str, float]], 
                           base_time: Optional[float] = None) -> str:
        """Create a sequence coordination plan."""
        plan_id = f"sequence_plan_{self.plan_counter}"
        self.plan_counter += 1
        
        sequence_primitive = AnimationSequence(f"sequence_{plan_id}", sequence, base_time)
        plan = CoordinationPlan(plan_id, [sequence_primitive])
        
        self.add_plan(plan)
        return plan_id
    
    def create_complex_plan(self, primitives: List[CoordinationPrimitive]) -> str:
        """Create a complex coordination plan with multiple primitives."""
        plan_id = f"complex_plan_{self.plan_counter}"
        self.plan_counter += 1
        
        plan = CoordinationPlan(plan_id, primitives)
        self.add_plan(plan)
        return plan_id
    
    def evaluate_all_plans(self, current_time: float, engine: DeterministicAnimationEngine):
        """Evaluate all active coordination plans."""
        completed_plan_ids = []
        
        for plan_id, plan in self.active_plans.items():
            try:
                if plan.evaluate_at(current_time, engine):
                    if plan.is_completed:
                        completed_plan_ids.append(plan_id)
            except Exception as e:
                print(f"Error evaluating plan {plan_id}: {str(e)}")
                plan.cancel(current_time)
                completed_plan_ids.append(plan_id)
        
        # Move completed plans
        for plan_id in completed_plan_ids:
            plan = self.active_plans.pop(plan_id)
            self.completed_plans[plan_id] = plan
    
    def get_manager_status(self) -> Dict[str, Any]:
        """Get coordination manager status."""
        return {
            "active_plans": len(self.active_plans),
            "completed_plans": len(self.completed_plans),
            "total_plans": len(self.active_plans) + len(self.completed_plans),
            "plan_counter": self.plan_counter
        }
    
    def cancel_plan(self, plan_id: str, current_time: float) -> bool:
        """Cancel a specific coordination plan."""
        if plan_id in self.active_plans:
            plan = self.active_plans.pop(plan_id)
            plan.cancel(current_time)
            self.completed_plans[plan_id] = plan
            return True
        return False
    
    def cancel_all_plans(self, current_time: float):
        """Cancel all active coordination plans."""
        for plan_id in list(self.active_plans.keys()):
            self.cancel_plan(plan_id, current_time) 