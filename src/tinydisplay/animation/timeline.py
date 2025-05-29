"""
Timeline Management System for Advanced Animation Coordination

This module provides sophisticated timeline management capabilities that enable
complex animation sequence orchestration with tick-based precision and future
state prediction for multi-core pre-computation.

Key Features:
1. TickTimeline: Central timeline management with tick precision
2. CoordinationPlan: Complex sequence orchestration container
3. Timeline event scheduling and execution
4. Future timeline state prediction API
5. Timeline serialization for multi-core compatibility
6. Performance monitoring and metrics
"""

import time
import threading
import pickle
import zlib
from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

from .tick_based import TickAnimationEngine, TickAnimationDefinition, TickAnimationState
from .coordination import (
    CoordinationPrimitive, CoordinationEngine, CoordinationEvent, CoordinationEventType,
    CoordinationState
)


class TimelineEventType(Enum):
    """Types of timeline events."""
    PLAN_STARTED = "plan_started"
    PLAN_COMPLETED = "plan_completed"
    PLAN_FAILED = "plan_failed"
    COORDINATION_TRIGGERED = "coordination_triggered"
    TIMELINE_CHECKPOINT = "timeline_checkpoint"


@dataclass
class TimelineEvent:
    """Event in the timeline system."""
    event_type: TimelineEventType
    tick: int
    plan_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.perf_counter)


@dataclass
class TimelinePerformanceMetrics:
    """Performance metrics for timeline operations."""
    total_evaluations: int = 0
    total_events: int = 0
    average_evaluation_time: float = 0.0
    peak_evaluation_time: float = 0.0
    active_plans_count: int = 0
    completed_plans_count: int = 0
    failed_plans_count: int = 0
    memory_usage_bytes: int = 0
    cache_hit_rate: float = 0.0
    
    def update_evaluation_time(self, evaluation_time: float) -> None:
        """Update evaluation time metrics."""
        self.total_evaluations += 1
        self.peak_evaluation_time = max(self.peak_evaluation_time, evaluation_time)
        
        # Update rolling average
        alpha = 0.1  # Smoothing factor
        if self.average_evaluation_time == 0.0:
            self.average_evaluation_time = evaluation_time
        else:
            self.average_evaluation_time = (
                alpha * evaluation_time + (1 - alpha) * self.average_evaluation_time
            )


class CoordinationPlan:
    """Container for coordinated animation sequence."""
    
    def __init__(self, plan_id: str, description: str = ""):
        """Initialize coordination plan.
        
        Args:
            plan_id: Unique identifier for this plan
            description: Optional description of the plan
        """
        self.plan_id = plan_id
        self.description = description
        self.primitives: List[CoordinationPrimitive] = []
        self.is_active = False
        self.is_completed = False
        self.is_failed = False
        self.start_tick: Optional[int] = None
        self.completion_tick: Optional[int] = None
        self.failure_tick: Optional[int] = None
        self.failure_reason: Optional[str] = None
        self.created_at = time.perf_counter()
        
        # Performance tracking
        self.evaluation_count = 0
        self.event_count = 0
    
    def add_primitive(self, primitive: CoordinationPrimitive) -> None:
        """Add coordination primitive to plan."""
        self.primitives.append(primitive)
    
    def evaluate_at(self, tick: int, engine: TickAnimationEngine, 
                   coordination_engine: CoordinationEngine) -> List[CoordinationEvent]:
        """Evaluate all primitives in plan at current tick."""
        if not self.is_active or self.is_completed or self.is_failed:
            return []
        
        self.evaluation_count += 1
        all_events = []
        
        try:
            for primitive in self.primitives:
                if primitive.state != CoordinationState.COMPLETED:
                    events = primitive.evaluate(tick, engine, coordination_engine)
                    all_events.extend(events)
                    self.event_count += len(events)
            
            # Check if plan is complete
            if all(p.is_completed() for p in self.primitives):
                self.is_completed = True
                self.completion_tick = tick
                self.is_active = False
        
        except Exception as e:
            self.is_failed = True
            self.failure_tick = tick
            self.failure_reason = str(e)
            self.is_active = False
        
        return all_events
    
    def predict_events_at(self, tick: int, engine: TickAnimationEngine,
                         coordination_engine: CoordinationEngine) -> List[CoordinationEvent]:
        """Predict coordination events at future tick."""
        if not self.is_active:
            return []
        
        predicted_events = []
        
        # Create temporary copies of primitives for prediction
        for primitive in self.primitives:
            if not primitive.is_completed():
                try:
                    # For prediction, we create a temporary state
                    temp_events = primitive.evaluate(tick, engine, coordination_engine)
                    predicted_events.extend(temp_events)
                except Exception:
                    # Prediction failures are non-fatal
                    pass
        
        return predicted_events
    
    def start(self, tick: int) -> None:
        """Start the coordination plan."""
        if not self.is_active:
            self.is_active = True
            self.start_tick = tick
    
    def get_dependencies(self) -> Set[str]:
        """Get all animation dependencies for this plan."""
        dependencies = set()
        for primitive in self.primitives:
            dependencies.update(primitive.get_dependencies())
        return dependencies
    
    def get_plan_status(self) -> Dict[str, Any]:
        """Get detailed plan status information."""
        return {
            'plan_id': self.plan_id,
            'description': self.description,
            'is_active': self.is_active,
            'is_completed': self.is_completed,
            'is_failed': self.is_failed,
            'start_tick': self.start_tick,
            'completion_tick': self.completion_tick,
            'failure_tick': self.failure_tick,
            'failure_reason': self.failure_reason,
            'primitive_count': len(self.primitives),
            'completed_primitives': sum(1 for p in self.primitives if p.is_completed()),
            'evaluation_count': self.evaluation_count,
            'event_count': self.event_count,
            'dependencies': list(self.get_dependencies())
        }
    
    def serialize_state(self) -> Dict[str, Any]:
        """Serialize plan state for cross-core computation."""
        return {
            'plan_id': self.plan_id,
            'description': self.description,
            'is_active': self.is_active,
            'is_completed': self.is_completed,
            'is_failed': self.is_failed,
            'start_tick': self.start_tick,
            'completion_tick': self.completion_tick,
            'failure_tick': self.failure_tick,
            'failure_reason': self.failure_reason,
            'primitives': [p.serialize_state() if hasattr(p, 'serialize_state') else {} 
                          for p in self.primitives],
            'evaluation_count': self.evaluation_count,
            'event_count': self.event_count
        }


class TimelineCache:
    """Cache for timeline state and predictions."""
    
    def __init__(self, max_entries: int = 1000):
        """Initialize timeline cache.
        
        Args:
            max_entries: Maximum number of cache entries
        """
        self.max_entries = max_entries
        self.cache: Dict[str, Any] = {}
        self.access_order: deque = deque()
        self.hit_count = 0
        self.miss_count = 0
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)
                self.hit_count += 1
                return self.cache[key]
            else:
                self.miss_count += 1
                return None
    
    def put(self, key: str, value: Any) -> None:
        """Put value in cache."""
        with self.lock:
            if key in self.cache:
                # Update existing entry
                self.access_order.remove(key)
            elif len(self.cache) >= self.max_entries:
                # Evict least recently used
                lru_key = self.access_order.popleft()
                del self.cache[lru_key]
            
            self.cache[key] = value
            self.access_order.append(key)
    
    def clear(self) -> None:
        """Clear cache."""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'entries': len(self.cache),
            'max_entries': self.max_entries,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': self.get_hit_rate()
        }


class TickTimeline:
    """Timeline management system with tick-based precision."""
    
    def __init__(self, fps: int = 60):
        """Initialize timeline.
        
        Args:
            fps: Frames per second for tick conversion
        """
        self.fps = fps
        self.coordination_plans: Dict[str, CoordinationPlan] = {}
        self.event_history: List[TimelineEvent] = []
        self.current_tick = 0
        self.timeline_lock = threading.RLock()
        
        # Performance monitoring
        self.performance_metrics = TimelinePerformanceMetrics()
        
        # Caching for predictions
        self.prediction_cache = TimelineCache(max_entries=500)
        
        # Event scheduling
        self.scheduled_events: Dict[int, List[Callable]] = defaultdict(list)
    
    def add_coordination_plan(self, plan: CoordinationPlan) -> str:
        """Add coordination plan to timeline."""
        with self.timeline_lock:
            self.coordination_plans[plan.plan_id] = plan
            self.performance_metrics.active_plans_count += 1
            return plan.plan_id
    
    def remove_coordination_plan(self, plan_id: str) -> bool:
        """Remove coordination plan from timeline."""
        with self.timeline_lock:
            if plan_id in self.coordination_plans:
                plan = self.coordination_plans.pop(plan_id)
                if plan.is_completed:
                    self.performance_metrics.completed_plans_count += 1
                elif plan.is_failed:
                    self.performance_metrics.failed_plans_count += 1
                self.performance_metrics.active_plans_count -= 1
                return True
            return False
    
    def start_plan(self, plan_id: str, start_tick: Optional[int] = None) -> bool:
        """Start a coordination plan."""
        with self.timeline_lock:
            if plan_id not in self.coordination_plans:
                return False
            
            plan = self.coordination_plans[plan_id]
            start_tick = start_tick if start_tick is not None else self.current_tick
            plan.start(start_tick)
            
            # Create timeline event
            event = TimelineEvent(
                event_type=TimelineEventType.PLAN_STARTED,
                tick=start_tick,
                plan_id=plan_id,
                data={'description': plan.description}
            )
            self.event_history.append(event)
            self.performance_metrics.total_events += 1
            
            return True
    
    def evaluate_at_tick(self, tick: int, engine: TickAnimationEngine,
                        coordination_engine: CoordinationEngine) -> List[CoordinationEvent]:
        """Evaluate all coordination plans at specific tick."""
        start_time = time.perf_counter()
        
        with self.timeline_lock:
            self.current_tick = tick
            all_events = []
            completed_plans = []
            failed_plans = []
            
            # Execute scheduled events
            if tick in self.scheduled_events:
                for event_func in self.scheduled_events[tick]:
                    try:
                        event_func()
                    except Exception as e:
                        print(f"Error executing scheduled event at tick {tick}: {e}")
                del self.scheduled_events[tick]
            
            # Evaluate all active plans
            for plan_id, plan in self.coordination_plans.items():
                if plan.is_active and not plan.is_completed and not plan.is_failed:
                    try:
                        events = plan.evaluate_at(tick, engine, coordination_engine)
                        all_events.extend(events)
                        
                        # Check for plan completion or failure
                        if plan.is_completed:
                            completed_plans.append(plan_id)
                        elif plan.is_failed:
                            failed_plans.append(plan_id)
                    
                    except Exception as e:
                        plan.is_failed = True
                        plan.failure_tick = tick
                        plan.failure_reason = str(e)
                        failed_plans.append(plan_id)
            
            # Create timeline events for completed/failed plans
            for plan_id in completed_plans:
                event = TimelineEvent(
                    event_type=TimelineEventType.PLAN_COMPLETED,
                    tick=tick,
                    plan_id=plan_id
                )
                self.event_history.append(event)
                self.performance_metrics.total_events += 1
            
            for plan_id in failed_plans:
                plan = self.coordination_plans[plan_id]
                event = TimelineEvent(
                    event_type=TimelineEventType.PLAN_FAILED,
                    tick=tick,
                    plan_id=plan_id,
                    data={'failure_reason': plan.failure_reason}
                )
                self.event_history.append(event)
                self.performance_metrics.total_events += 1
            
            # Limit event history size
            if len(self.event_history) > 10000:
                self.event_history = self.event_history[-5000:]
            
            # Update performance metrics
            evaluation_time = time.perf_counter() - start_time
            self.performance_metrics.update_evaluation_time(evaluation_time)
            self.performance_metrics.cache_hit_rate = self.prediction_cache.get_hit_rate()
            
            return all_events
    
    def predict_future_events(self, start_tick: int, end_tick: int, 
                             engine: TickAnimationEngine,
                             coordination_engine: CoordinationEngine) -> List[CoordinationEvent]:
        """Predict coordination events in future tick range."""
        cache_key = f"predict_{start_tick}_{end_tick}_{hash(tuple(self.coordination_plans.keys()))}"
        
        # Check cache first
        cached_result = self.prediction_cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        future_events = []
        
        with self.timeline_lock:
            for tick in range(start_tick, end_tick + 1):
                for plan in self.coordination_plans.values():
                    if plan.is_active:
                        try:
                            predicted_events = plan.predict_events_at(tick, engine, coordination_engine)
                            future_events.extend(predicted_events)
                        except Exception:
                            # Prediction failures are non-fatal
                            pass
        
        # Cache the result
        self.prediction_cache.put(cache_key, future_events)
        
        return future_events
    
    def schedule_event(self, tick: int, event_func: Callable) -> None:
        """Schedule an event to execute at specific tick."""
        with self.timeline_lock:
            self.scheduled_events[tick].append(event_func)
    
    def create_checkpoint(self, tick: int, description: str = "") -> None:
        """Create a timeline checkpoint for debugging."""
        with self.timeline_lock:
            event = TimelineEvent(
                event_type=TimelineEventType.TIMELINE_CHECKPOINT,
                tick=tick,
                plan_id="system",
                data={
                    'description': description,
                    'active_plans': len([p for p in self.coordination_plans.values() if p.is_active]),
                    'total_plans': len(self.coordination_plans)
                }
            )
            self.event_history.append(event)
            self.performance_metrics.total_events += 1
    
    def get_timeline_state(self, tick: Optional[int] = None) -> Dict[str, Any]:
        """Get complete timeline state for debugging/inspection."""
        target_tick = tick if tick is not None else self.current_tick
        
        with self.timeline_lock:
            active_plans = [p for p in self.coordination_plans.values() if p.is_active]
            completed_plans = [p for p in self.coordination_plans.values() if p.is_completed]
            failed_plans = [p for p in self.coordination_plans.values() if p.is_failed]
            
            return {
                'current_tick': target_tick,
                'fps': self.fps,
                'total_plans': len(self.coordination_plans),
                'active_plans': len(active_plans),
                'completed_plans': len(completed_plans),
                'failed_plans': len(failed_plans),
                'recent_events': [
                    {
                        'event_type': e.event_type.value,
                        'tick': e.tick,
                        'plan_id': e.plan_id,
                        'data': e.data
                    }
                    for e in self.event_history if e.tick >= target_tick - 60  # Last second
                ],
                'performance_metrics': {
                    'total_evaluations': self.performance_metrics.total_evaluations,
                    'total_events': self.performance_metrics.total_events,
                    'average_evaluation_time': self.performance_metrics.average_evaluation_time,
                    'peak_evaluation_time': self.performance_metrics.peak_evaluation_time,
                    'cache_hit_rate': self.performance_metrics.cache_hit_rate
                },
                'cache_stats': self.prediction_cache.get_stats(),
                'scheduled_events_count': sum(len(events) for events in self.scheduled_events.values())
            }
    
    def serialize_timeline_state(self) -> bytes:
        """Serialize timeline state for cross-core computation."""
        with self.timeline_lock:
            state_data = {
                'current_tick': self.current_tick,
                'fps': self.fps,
                'coordination_plans': {
                    pid: plan.serialize_state() 
                    for pid, plan in self.coordination_plans.items()
                },
                'performance_metrics': {
                    'total_evaluations': self.performance_metrics.total_evaluations,
                    'total_events': self.performance_metrics.total_events,
                    'average_evaluation_time': self.performance_metrics.average_evaluation_time
                }
            }
            return zlib.compress(pickle.dumps(state_data))
    
    @classmethod
    def deserialize_timeline_state(cls, data: bytes) -> 'TickTimeline':
        """Deserialize timeline state from bytes."""
        state_data = pickle.loads(zlib.decompress(data))
        
        timeline = cls(fps=state_data['fps'])
        timeline.current_tick = state_data['current_tick']
        
        # Restore performance metrics
        timeline.performance_metrics.total_evaluations = state_data['performance_metrics']['total_evaluations']
        timeline.performance_metrics.total_events = state_data['performance_metrics']['total_events']
        timeline.performance_metrics.average_evaluation_time = state_data['performance_metrics']['average_evaluation_time']
        
        # Note: Coordination plans would need to be reconstructed from primitives
        # This is a simplified version for basic state transfer
        
        return timeline
    
    def clear_completed_plans(self) -> int:
        """Remove all completed and failed plans."""
        with self.timeline_lock:
            completed_ids = [
                pid for pid, plan in self.coordination_plans.items()
                if plan.is_completed or plan.is_failed
            ]
            
            for pid in completed_ids:
                self.remove_coordination_plan(pid)
            
            return len(completed_ids)
    
    def get_performance_metrics(self) -> TimelinePerformanceMetrics:
        """Get current performance metrics."""
        return self.performance_metrics


# Convenience functions for creating common timeline patterns

def create_simple_timeline(fps: int = 60) -> TickTimeline:
    """Create a simple timeline with default settings."""
    return TickTimeline(fps=fps)


def create_sequential_plan(plan_id: str, animation_sequences: List[Tuple[str, int]], 
                          start_tick: int, description: str = "") -> CoordinationPlan:
    """Create a plan with sequential animation execution.
    
    Args:
        plan_id: Unique plan identifier
        animation_sequences: List of (animation_id, delay_ticks) tuples
        start_tick: Tick to start the sequence
        description: Optional plan description
    """
    from .coordination import create_sequence_with_delays
    
    plan = CoordinationPlan(plan_id, description)
    
    animation_ids = [anim_id for anim_id, _ in animation_sequences]
    delays = [delay for _, delay in animation_sequences]
    
    sequence = create_sequence_with_delays(
        f"{plan_id}_sequence",
        animation_ids,
        delays,
        start_tick
    )
    
    plan.add_primitive(sequence)
    return plan


def create_synchronized_plan(plan_id: str, animation_ids: List[str], 
                           sync_tick: int, description: str = "") -> CoordinationPlan:
    """Create a plan with synchronized animation start.
    
    Args:
        plan_id: Unique plan identifier
        animation_ids: List of animations to synchronize
        sync_tick: Tick to start all animations
        description: Optional plan description
    """
    from .coordination import create_sync_on_tick
    
    plan = CoordinationPlan(plan_id, description)
    
    sync = create_sync_on_tick(
        f"{plan_id}_sync",
        animation_ids,
        sync_tick
    )
    
    plan.add_primitive(sync)
    return plan 