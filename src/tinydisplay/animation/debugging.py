"""
Timeline Debugging and Visualization Tools for Advanced Animation Coordination

This module provides comprehensive debugging and visualization tools for the
timeline management system, enabling developers to inspect, analyze, and debug
complex animation sequences with tick-level precision.

Key Features:
1. Timeline inspection API for debugging
2. Tick-level animation state visualization
3. Coordination event logging and analysis
4. Timeline replay and step-through debugging
5. Performance profiling for coordination overhead
6. Timeline validation and consistency checking
"""

import time
import json
import threading
from typing import Dict, List, Optional, Set, Any, Tuple, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
from pathlib import Path

from .tick_based import TickAnimationEngine, TickAnimationDefinition, TickAnimationState
from .coordination import (
    CoordinationPrimitive, CoordinationEngine, CoordinationEvent, CoordinationEventType,
    CoordinationState
)
from .timeline import TickTimeline, CoordinationPlan, TimelineEvent, TimelineEventType


class DebugLevel(Enum):
    """Debug logging levels."""
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DebugLogEntry:
    """Debug log entry for timeline events."""
    timestamp: float
    tick: int
    level: DebugLevel
    category: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'timestamp': self.timestamp,
            'tick': self.tick,
            'level': self.level.value,  # Convert enum to string
            'category': self.category,
            'message': self.message,
            'data': self.data,
            'source': self.source
        }


@dataclass
class ValidationIssue:
    """Timeline validation issue."""
    severity: ValidationSeverity
    category: str
    message: str
    tick: Optional[int] = None
    plan_id: Optional[str] = None
    primitive_id: Optional[str] = None
    animation_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'severity': self.severity.value,  # Convert enum to string
            'category': self.category,
            'message': self.message,
            'tick': self.tick,
            'plan_id': self.plan_id,
            'primitive_id': self.primitive_id,
            'animation_id': self.animation_id,
            'data': self.data
        }


@dataclass
class AnimationStateSnapshot:
    """Snapshot of animation state at specific tick."""
    tick: int
    animation_id: str
    state: TickAnimationState
    is_active: bool
    is_completed: bool
    local_progress: float
    global_progress: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for visualization."""
        return {
            'tick': self.tick,
            'animation_id': self.animation_id,
            'state': self.state.serialize() if self.state else None,
            'is_active': self.is_active,
            'is_completed': self.is_completed,
            'local_progress': self.local_progress,
            'global_progress': self.global_progress
        }


@dataclass
class CoordinationSnapshot:
    """Snapshot of coordination state at specific tick."""
    tick: int
    primitive_id: str
    primitive_type: str
    state: CoordinationState
    dependencies: Set[str]
    events: List[CoordinationEvent]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for visualization."""
        return {
            'tick': self.tick,
            'primitive_id': self.primitive_id,
            'primitive_type': self.primitive_type,
            'state': self.state.value,
            'dependencies': list(self.dependencies),
            'events': [
                {
                    'event_type': event.event_type.value,
                    'tick': event.tick,
                    'coordination_id': event.coordination_id,
                    'data': event.data
                }
                for event in self.events
            ]
        }


@dataclass
class TimelineSnapshot:
    """Complete timeline state snapshot at specific tick."""
    tick: int
    timestamp: float
    animation_snapshots: List[AnimationStateSnapshot]
    coordination_snapshots: List[CoordinationSnapshot]
    active_plans: List[str]
    completed_plans: List[str]
    failed_plans: List[str]
    performance_metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for visualization."""
        return {
            'tick': self.tick,
            'timestamp': self.timestamp,
            'animation_snapshots': [snap.to_dict() for snap in self.animation_snapshots],
            'coordination_snapshots': [snap.to_dict() for snap in self.coordination_snapshots],
            'active_plans': self.active_plans,
            'completed_plans': self.completed_plans,
            'failed_plans': self.failed_plans,
            'performance_metrics': self.performance_metrics
        }


class TimelineDebugLogger:
    """Advanced logging system for timeline debugging."""
    
    def __init__(self, max_entries: int = 10000, enable_file_logging: bool = False,
                 log_file_path: Optional[str] = None):
        """Initialize timeline debug logger.
        
        Args:
            max_entries: Maximum number of log entries to keep in memory
            enable_file_logging: Whether to write logs to file
            log_file_path: Path to log file (auto-generated if None)
        """
        self.max_entries = max_entries
        self.enable_file_logging = enable_file_logging
        self.log_entries: deque[DebugLogEntry] = deque(maxlen=max_entries)
        self.logger_lock = threading.RLock()
        
        # File logging setup
        if enable_file_logging:
            if log_file_path is None:
                timestamp = int(time.time())
                log_file_path = f"timeline_debug_{timestamp}.log"
            self.log_file_path = Path(log_file_path)
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.log_file_path = None
        
        # Category filtering
        self.enabled_categories: Set[str] = set()
        self.min_level = DebugLevel.DEBUG
    
    def set_min_level(self, level: DebugLevel) -> None:
        """Set minimum logging level."""
        self.min_level = level
    
    def enable_category(self, category: str) -> None:
        """Enable logging for specific category."""
        with self.logger_lock:
            self.enabled_categories.add(category)
    
    def disable_category(self, category: str) -> None:
        """Disable logging for specific category."""
        with self.logger_lock:
            self.enabled_categories.discard(category)
    
    def log(self, level: DebugLevel, category: str, message: str, tick: int = 0,
            data: Dict[str, Any] = None, source: str = "") -> None:
        """Log debug message.
        
        Args:
            level: Debug level
            category: Log category
            message: Log message
            tick: Current tick
            data: Additional data
            source: Source of the log message
        """
        # Check if logging is enabled for this level and category
        level_values = {
            DebugLevel.TRACE: 0,
            DebugLevel.DEBUG: 1,
            DebugLevel.INFO: 2,
            DebugLevel.WARNING: 3,
            DebugLevel.ERROR: 4
        }
        
        if level_values[level] < level_values[self.min_level]:
            return
        
        if self.enabled_categories and category not in self.enabled_categories:
            return
        
        entry = DebugLogEntry(
            timestamp=time.perf_counter(),
            tick=tick,
            level=level,
            category=category,
            message=message,
            data=data or {},
            source=source
        )
        
        with self.logger_lock:
            self.log_entries.append(entry)
            
            # Write to file if enabled
            if self.enable_file_logging and self.log_file_path:
                try:
                    with open(self.log_file_path, 'a') as f:
                        f.write(f"{entry.timestamp:.6f} [{entry.level.value.upper()}] "
                               f"T{entry.tick:06d} {entry.category}: {entry.message}")
                        if entry.data:
                            f.write(f" | Data: {json.dumps(entry.data)}")
                        f.write("\n")
                except Exception:
                    pass  # Ignore file logging errors
    
    def get_logs(self, category: Optional[str] = None, min_level: Optional[DebugLevel] = None,
                 start_tick: Optional[int] = None, end_tick: Optional[int] = None,
                 max_entries: Optional[int] = None) -> List[DebugLogEntry]:
        """Get filtered log entries.
        
        Args:
            category: Filter by category
            min_level: Minimum log level
            start_tick: Start tick filter
            end_tick: End tick filter
            max_entries: Maximum number of entries to return
            
        Returns:
            Filtered log entries
        """
        with self.logger_lock:
            entries = list(self.log_entries)
        
        # Apply filters
        if category:
            entries = [e for e in entries if e.category == category]
        
        if min_level:
            level_values = {
                DebugLevel.TRACE: 0,
                DebugLevel.DEBUG: 1,
                DebugLevel.INFO: 2,
                DebugLevel.WARNING: 3,
                DebugLevel.ERROR: 4
            }
            min_value = level_values[min_level]
            entries = [e for e in entries if level_values[e.level] >= min_value]
        
        if start_tick is not None:
            entries = [e for e in entries if e.tick >= start_tick]
        
        if end_tick is not None:
            entries = [e for e in entries if e.tick <= end_tick]
        
        # Sort by timestamp and limit
        entries.sort(key=lambda e: e.timestamp)
        if max_entries:
            entries = entries[-max_entries:]
        
        return entries
    
    def clear_logs(self) -> None:
        """Clear all log entries."""
        with self.logger_lock:
            self.log_entries.clear()
    
    def export_logs(self, file_path: str, format: str = "json") -> bool:
        """Export logs to file.
        
        Args:
            file_path: Output file path
            format: Export format ("json" or "csv")
            
        Returns:
            True if export successful
        """
        try:
            with self.logger_lock:
                entries = list(self.log_entries)
            
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            if format.lower() == "json":
                with open(file_path, 'w') as f:
                    json.dump([entry.to_dict() for entry in entries], f, indent=2)
            elif format.lower() == "csv":
                import csv
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['timestamp', 'tick', 'level', 'category', 'message', 'source', 'data'])
                    for entry in entries:
                        writer.writerow([
                            entry.timestamp, entry.tick, entry.level.value,
                            entry.category, entry.message, entry.source,
                            json.dumps(entry.data) if entry.data else ""
                        ])
            else:
                return False
            
            return True
        except Exception as e:
            # Log the error but don't raise it
            print(f"Export failed: {e}")
            return False


class TimelineInspector:
    """Timeline inspection API for debugging."""
    
    def __init__(self, timeline: TickTimeline, engine: TickAnimationEngine,
                 coordination_engine: CoordinationEngine):
        """Initialize timeline inspector.
        
        Args:
            timeline: Timeline to inspect
            engine: Animation engine
            coordination_engine: Coordination engine
        """
        self.timeline = timeline
        self.engine = engine
        self.coordination_engine = coordination_engine
        self.logger = TimelineDebugLogger()
        self.snapshots: Dict[int, TimelineSnapshot] = {}
        self.inspector_lock = threading.RLock()
    
    def capture_snapshot(self, tick: int) -> TimelineSnapshot:
        """Capture complete timeline state snapshot at specific tick.
        
        Args:
            tick: Tick to capture snapshot at
            
        Returns:
            Timeline snapshot
        """
        with self.inspector_lock:
            # Capture animation states
            animation_snapshots = []
            for animation_id, animation in self.engine.animations.items():
                state = animation.state_at(tick)  # Use correct method name
                snapshot = AnimationStateSnapshot(
                    tick=tick,
                    animation_id=animation_id,
                    state=state,
                    is_active=animation.is_active_at(tick),
                    is_completed=animation.is_completed_at(tick),
                    local_progress=animation.get_local_progress(tick),
                    global_progress=animation.get_local_progress(tick)  # Use local progress for now
                )
                animation_snapshots.append(snapshot)
            
            # Capture coordination states
            coordination_snapshots = []
            for primitive_id, primitive in self.coordination_engine.primitives.items():
                snapshot = CoordinationSnapshot(
                    tick=tick,
                    primitive_id=primitive_id,
                    primitive_type=type(primitive).__name__,
                    state=primitive.state,
                    dependencies=primitive.get_dependencies(),
                    events=primitive.events.copy()
                )
                coordination_snapshots.append(snapshot)
            
            # Capture timeline state
            timeline_state = self.timeline.get_timeline_state(tick)
            
            snapshot = TimelineSnapshot(
                tick=tick,
                timestamp=time.perf_counter(),
                animation_snapshots=animation_snapshots,
                coordination_snapshots=coordination_snapshots,
                active_plans=[],  # Timeline state returns counts, not lists
                completed_plans=[],  # Timeline state returns counts, not lists
                failed_plans=[],  # Timeline state returns counts, not lists
                performance_metrics=timeline_state.get('performance_metrics', {})
            )
            
            # Store snapshot
            self.snapshots[tick] = snapshot
            
            # Log snapshot capture
            self.logger.log(
                DebugLevel.DEBUG,
                "inspector",
                f"Captured timeline snapshot at tick {tick}",
                tick=tick,
                data={
                    'animation_count': len(animation_snapshots),
                    'coordination_count': len(coordination_snapshots),
                    'active_plans': timeline_state.get('active_plans', 0),  # These are counts
                    'completed_plans': timeline_state.get('completed_plans', 0)  # These are counts
                },
                source="TimelineInspector"
            )
            
            return snapshot
    
    def get_snapshot(self, tick: int) -> Optional[TimelineSnapshot]:
        """Get previously captured snapshot.
        
        Args:
            tick: Tick to get snapshot for
            
        Returns:
            Timeline snapshot if available
        """
        return self.snapshots.get(tick)
    
    def get_animation_state_at_tick(self, animation_id: str, tick: int) -> Optional[AnimationStateSnapshot]:
        """Get animation state at specific tick.
        
        Args:
            animation_id: Animation ID
            tick: Tick to inspect
            
        Returns:
            Animation state snapshot
        """
        animation = self.engine.get_animation(animation_id)
        if not animation:
            return None
        
        state = animation.state_at(tick)  # Use correct method name
        return AnimationStateSnapshot(
            tick=tick,
            animation_id=animation_id,
            state=state,
            is_active=animation.is_active_at(tick),
            is_completed=animation.is_completed_at(tick),
            local_progress=animation.get_local_progress(tick),
            global_progress=animation.get_local_progress(tick)  # Use local progress for now
        )
    
    def get_coordination_state_at_tick(self, primitive_id: str, tick: int) -> Optional[CoordinationSnapshot]:
        """Get coordination primitive state at specific tick.
        
        Args:
            primitive_id: Coordination primitive ID
            tick: Tick to inspect
            
        Returns:
            Coordination state snapshot
        """
        primitive = self.coordination_engine.get_primitive(primitive_id)
        if not primitive:
            return None
        
        return CoordinationSnapshot(
            tick=tick,
            primitive_id=primitive_id,
            primitive_type=type(primitive).__name__,
            state=primitive.state,
            dependencies=primitive.get_dependencies(),
            events=primitive.events.copy()
        )
    
    def get_plan_timeline(self, plan_id: str, start_tick: int, end_tick: int) -> Dict[str, Any]:
        """Get detailed timeline for specific coordination plan.
        
        Args:
            plan_id: Plan ID to analyze
            start_tick: Start tick for analysis
            end_tick: End tick for analysis
            
        Returns:
            Plan timeline analysis
        """
        plan = self.timeline.coordination_plans.get(plan_id)
        if not plan:
            return {}
        
        timeline_data = {
            'plan_id': plan_id,
            'start_tick': start_tick,
            'end_tick': end_tick,
            'plan_status': plan.get_plan_status(),
            'tick_analysis': {}
        }
        
        # Analyze each tick in range
        for tick in range(start_tick, end_tick + 1):
            tick_data = {
                'tick': tick,
                'primitive_states': {},
                'events': [],
                'dependencies_met': True
            }
            
            # Check primitive states
            for primitive in plan.primitives:
                primitive_data = {
                    'state': primitive.state.value,
                    'dependencies': list(primitive.get_dependencies()),
                    'dependencies_met': True
                }
                
                # Check if dependencies are met
                for dep_id in primitive.get_dependencies():
                    animation = self.engine.get_animation(dep_id)
                    if animation and not animation.is_active_at(tick):
                        primitive_data['dependencies_met'] = False
                        tick_data['dependencies_met'] = False
                
                tick_data['primitive_states'][primitive.coordination_id] = primitive_data
            
            # Get events at this tick
            events = plan.evaluate_at(tick, self.engine, self.coordination_engine)
            tick_data['events'] = [
                {
                    'event_type': event.event_type.value,
                    'coordination_id': event.coordination_id,
                    'data': event.data
                }
                for event in events
            ]
            
            timeline_data['tick_analysis'][tick] = tick_data
        
        return timeline_data
    
    def analyze_performance_bottlenecks(self, start_tick: int, end_tick: int) -> Dict[str, Any]:
        """Analyze performance bottlenecks in timeline execution.
        
        Args:
            start_tick: Start tick for analysis
            end_tick: End tick for analysis
            
        Returns:
            Performance bottleneck analysis
        """
        analysis = {
            'analysis_range': {'start_tick': start_tick, 'end_tick': end_tick},
            'bottlenecks': [],
            'recommendations': [],
            'metrics_summary': {}
        }
        
        # Analyze snapshots in range
        relevant_snapshots = [
            snapshot for tick, snapshot in self.snapshots.items()
            if start_tick <= tick <= end_tick
        ]
        
        if not relevant_snapshots:
            return analysis
        
        # Calculate metrics
        total_animations = sum(len(s.animation_snapshots) for s in relevant_snapshots)
        total_coordination = sum(len(s.coordination_snapshots) for s in relevant_snapshots)
        avg_animations = total_animations / len(relevant_snapshots)
        avg_coordination = total_coordination / len(relevant_snapshots)
        
        analysis['metrics_summary'] = {
            'total_snapshots': len(relevant_snapshots),
            'average_animations_per_tick': avg_animations,
            'average_coordination_per_tick': avg_coordination,
            'peak_animations': max(len(s.animation_snapshots) for s in relevant_snapshots),
            'peak_coordination': max(len(s.coordination_snapshots) for s in relevant_snapshots)
        }
        
        # Identify bottlenecks
        if avg_animations > 50:
            analysis['bottlenecks'].append({
                'type': 'high_animation_count',
                'severity': 'warning',
                'description': f'High average animation count: {avg_animations:.1f}',
                'recommendation': 'Consider batching or reducing concurrent animations'
            })
        
        if avg_coordination > 20:
            analysis['bottlenecks'].append({
                'type': 'high_coordination_count',
                'severity': 'warning',
                'description': f'High average coordination count: {avg_coordination:.1f}',
                'recommendation': 'Consider simplifying coordination logic'
            })
        
        # Check for failed plans
        failed_plans = set()
        for snapshot in relevant_snapshots:
            failed_plans.update(snapshot.failed_plans)
        
        if failed_plans:
            analysis['bottlenecks'].append({
                'type': 'failed_plans',
                'severity': 'error',
                'description': f'Failed coordination plans: {list(failed_plans)}',
                'recommendation': 'Review plan dependencies and timing'
            })
        
        return analysis
    
    def clear_snapshots(self) -> None:
        """Clear all captured snapshots."""
        with self.inspector_lock:
            self.snapshots.clear()


class TimelineReplayDebugger:
    """Timeline replay and step-through debugging system."""
    
    def __init__(self, timeline: TickTimeline, engine: TickAnimationEngine,
                 coordination_engine: CoordinationEngine):
        """Initialize timeline replay debugger.
        
        Args:
            timeline: Timeline to debug
            engine: Animation engine
            coordination_engine: Coordination engine
        """
        self.timeline = timeline
        self.engine = engine
        self.coordination_engine = coordination_engine
        self.inspector = TimelineInspector(timeline, engine, coordination_engine)
        
        # Replay state
        self.replay_snapshots: List[TimelineSnapshot] = []
        self.current_replay_index = 0
        self.is_replaying = False
        self.replay_lock = threading.RLock()
        
        # Breakpoints
        self.breakpoints: Set[int] = set()
        self.conditional_breakpoints: Dict[int, Callable[[TimelineSnapshot], bool]] = {}
    
    def record_execution(self, start_tick: int, end_tick: int, step_size: int = 1) -> None:
        """Record timeline execution for replay.
        
        Args:
            start_tick: Start tick for recording
            end_tick: End tick for recording
            step_size: Tick step size for recording
        """
        with self.replay_lock:
            self.replay_snapshots.clear()
            
            for tick in range(start_tick, end_tick + 1, step_size):
                # Evaluate timeline at this tick
                self.timeline.evaluate_at_tick(tick, self.engine, self.coordination_engine)
                
                # Capture snapshot
                snapshot = self.inspector.capture_snapshot(tick)
                self.replay_snapshots.append(snapshot)
            
            self.current_replay_index = 0
            
            self.inspector.logger.log(
                DebugLevel.INFO,
                "replay",
                f"Recorded execution from tick {start_tick} to {end_tick}",
                tick=start_tick,
                data={
                    'start_tick': start_tick,
                    'end_tick': end_tick,
                    'step_size': step_size,
                    'snapshot_count': len(self.replay_snapshots)
                },
                source="TimelineReplayDebugger"
            )
    
    def start_replay(self) -> bool:
        """Start replay from beginning.
        
        Returns:
            True if replay started successfully
        """
        with self.replay_lock:
            if not self.replay_snapshots:
                return False
            
            self.current_replay_index = 0
            self.is_replaying = True
            return True
    
    def step_forward(self) -> Optional[TimelineSnapshot]:
        """Step forward one tick in replay.
        
        Returns:
            Current snapshot or None if at end
        """
        with self.replay_lock:
            if not self.is_replaying or self.current_replay_index >= len(self.replay_snapshots):
                return None
            
            snapshot = self.replay_snapshots[self.current_replay_index]
            self.current_replay_index += 1
            
            # Check breakpoints
            if self._check_breakpoints(snapshot):
                self.inspector.logger.log(
                    DebugLevel.INFO,
                    "replay",
                    f"Breakpoint hit at tick {snapshot.tick}",
                    tick=snapshot.tick,
                    source="TimelineReplayDebugger"
                )
            
            return snapshot
    
    def step_backward(self) -> Optional[TimelineSnapshot]:
        """Step backward one tick in replay.
        
        Returns:
            Previous snapshot or None if at beginning
        """
        with self.replay_lock:
            if not self.is_replaying or self.current_replay_index <= 1:
                return None
            
            # Go back 2 positions: undo the increment from last step_forward
            # and then go to the previous snapshot
            self.current_replay_index -= 2
            return self.replay_snapshots[self.current_replay_index]
    
    def jump_to_tick(self, tick: int) -> Optional[TimelineSnapshot]:
        """Jump to specific tick in replay.
        
        Args:
            tick: Tick to jump to
            
        Returns:
            Snapshot at tick or None if not found
        """
        with self.replay_lock:
            for i, snapshot in enumerate(self.replay_snapshots):
                if snapshot.tick == tick:
                    self.current_replay_index = i
                    return snapshot
            return None
    
    def add_breakpoint(self, tick: int) -> None:
        """Add breakpoint at specific tick.
        
        Args:
            tick: Tick to break at
        """
        self.breakpoints.add(tick)
    
    def remove_breakpoint(self, tick: int) -> None:
        """Remove breakpoint at specific tick.
        
        Args:
            tick: Tick to remove breakpoint from
        """
        self.breakpoints.discard(tick)
    
    def add_conditional_breakpoint(self, tick: int, condition: Callable[[TimelineSnapshot], bool]) -> None:
        """Add conditional breakpoint.
        
        Args:
            tick: Tick to check condition at
            condition: Function that returns True to break
        """
        self.conditional_breakpoints[tick] = condition
    
    def remove_conditional_breakpoint(self, tick: int) -> None:
        """Remove conditional breakpoint.
        
        Args:
            tick: Tick to remove conditional breakpoint from
        """
        self.conditional_breakpoints.pop(tick, None)
    
    def _check_breakpoints(self, snapshot: TimelineSnapshot) -> bool:
        """Check if any breakpoints are hit.
        
        Args:
            snapshot: Current snapshot
            
        Returns:
            True if breakpoint hit
        """
        # Check regular breakpoints
        if snapshot.tick in self.breakpoints:
            return True
        
        # Check conditional breakpoints
        if snapshot.tick in self.conditional_breakpoints:
            try:
                condition = self.conditional_breakpoints[snapshot.tick]
                if condition(snapshot):
                    return True
            except Exception:
                pass  # Ignore condition evaluation errors
        
        return False
    
    def get_current_snapshot(self) -> Optional[TimelineSnapshot]:
        """Get current replay snapshot.
        
        Returns:
            Current snapshot or None
        """
        with self.replay_lock:
            if (not self.is_replaying or 
                self.current_replay_index < 0 or 
                self.current_replay_index >= len(self.replay_snapshots)):
                return None
            
            return self.replay_snapshots[self.current_replay_index]
    
    def get_replay_progress(self) -> Dict[str, Any]:
        """Get replay progress information.
        
        Returns:
            Replay progress data
        """
        with self.replay_lock:
            # The current tick should be the tick of the last snapshot returned
            # After step_forward(), current_replay_index points to the next snapshot
            # So we need to look at the previous snapshot (index - 1)
            current_tick = None
            if self.is_replaying and len(self.replay_snapshots) > 0:
                if self.current_replay_index > 0:
                    # We've stepped forward, so current tick is the previous snapshot
                    current_tick = self.replay_snapshots[self.current_replay_index - 1].tick
                elif self.current_replay_index == 0:
                    # We're at the beginning, no snapshot has been returned yet
                    current_tick = None
            
            return {
                'is_replaying': self.is_replaying,
                'current_index': self.current_replay_index,
                'total_snapshots': len(self.replay_snapshots),
                'current_tick': current_tick,
                'progress_percent': (self.current_replay_index / max(1, len(self.replay_snapshots))) * 100,
                'breakpoints': list(self.breakpoints),
                'conditional_breakpoints': list(self.conditional_breakpoints.keys())
            }


class TimelineValidator:
    """Timeline validation and consistency checking system."""
    
    def __init__(self, timeline: TickTimeline, engine: TickAnimationEngine,
                 coordination_engine: CoordinationEngine):
        """Initialize timeline validator.
        
        Args:
            timeline: Timeline to validate
            engine: Animation engine
            coordination_engine: Coordination engine
        """
        self.timeline = timeline
        self.engine = engine
        self.coordination_engine = coordination_engine
        self.validation_issues: List[ValidationIssue] = []
    
    def validate_timeline_consistency(self, start_tick: int, end_tick: int) -> List[ValidationIssue]:
        """Validate timeline consistency across tick range.
        
        Args:
            start_tick: Start tick for validation
            end_tick: End tick for validation
            
        Returns:
            List of validation issues found
        """
        self.validation_issues.clear()
        
        # Validate each plan
        for plan_id, plan in self.timeline.coordination_plans.items():
            self._validate_plan_consistency(plan, start_tick, end_tick)
        
        # Validate animation dependencies
        self._validate_animation_dependencies(start_tick, end_tick)
        
        # Validate timing constraints
        self._validate_timing_constraints(start_tick, end_tick)
        
        # Validate resource usage
        self._validate_resource_usage(start_tick, end_tick)
        
        return self.validation_issues.copy()
    
    def _validate_plan_consistency(self, plan: CoordinationPlan, start_tick: int, end_tick: int) -> None:
        """Validate individual plan consistency."""
        # Check for circular dependencies
        dependencies = plan.get_dependencies()
        for dep_id in dependencies:
            if self._has_circular_dependency(dep_id, dependencies):
                self.validation_issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="circular_dependency",
                    message=f"Circular dependency detected in plan {plan.plan_id}",
                    plan_id=plan.plan_id,
                    animation_id=dep_id
                ))
        
        # Check primitive states
        for primitive in plan.primitives:
            if primitive.state == CoordinationState.FAILED:
                self.validation_issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="primitive_failure",
                    message=f"Primitive {primitive.coordination_id} failed",
                    plan_id=plan.plan_id,
                    primitive_id=primitive.coordination_id
                ))
    
    def _validate_animation_dependencies(self, start_tick: int, end_tick: int) -> None:
        """Validate animation dependencies."""
        for animation_id, animation in self.engine.animations.items():
            # Check if animation is properly defined
            if not animation.start_state or not animation.end_state:
                self.validation_issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="invalid_animation",
                    message=f"Animation {animation_id} missing start or end state",
                    animation_id=animation_id
                ))
            
            # Check timing validity
            if animation.duration_ticks <= 0:
                self.validation_issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="invalid_timing",
                    message=f"Animation {animation_id} has invalid duration: {animation.duration_ticks}",
                    animation_id=animation_id
                ))
    
    def _validate_timing_constraints(self, start_tick: int, end_tick: int) -> None:
        """Validate timing constraints."""
        # Check for overlapping critical sections
        critical_sections = []
        
        for plan in self.timeline.coordination_plans.values():
            if plan.start_tick is not None:
                critical_sections.append((plan.start_tick, plan.completion_tick or end_tick, plan.plan_id))
        
        # Sort by start tick
        critical_sections.sort(key=lambda x: x[0])
        
        # Check for problematic overlaps
        for i in range(len(critical_sections) - 1):
            current = critical_sections[i]
            next_section = critical_sections[i + 1]
            
            if current[1] > next_section[0]:  # Overlap detected
                overlap_duration = current[1] - next_section[0]
                if overlap_duration > 30:  # More than 0.5 seconds at 60fps
                    self.validation_issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="timing_overlap",
                        message=f"Significant timing overlap between plans {current[2]} and {next_section[2]}",
                        data={'overlap_ticks': overlap_duration}
                    ))
    
    def _validate_resource_usage(self, start_tick: int, end_tick: int) -> None:
        """Validate resource usage patterns."""
        # Check for excessive concurrent animations
        for tick in range(start_tick, end_tick + 1, 10):  # Sample every 10 ticks
            active_animations = sum(
                1 for animation in self.engine.animations.values()
                if animation.is_active_at(tick)
            )
            
            if active_animations > 100:  # Threshold for concern
                self.validation_issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="high_resource_usage",
                    message=f"High concurrent animation count at tick {tick}: {active_animations}",
                    tick=tick,
                    data={'active_animations': active_animations}
                ))
    
    def _has_circular_dependency(self, animation_id: str, all_dependencies: Set[str]) -> bool:
        """Check for circular dependencies (simplified check)."""
        # This is a simplified implementation
        # In practice, you'd want a more sophisticated graph traversal
        return animation_id in all_dependencies and len(all_dependencies) > 1
    
    def generate_validation_report(self, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Generate comprehensive validation report.
        
        Args:
            issues: List of validation issues
            
        Returns:
            Validation report
        """
        # Group issues by severity
        by_severity = defaultdict(list)
        for issue in issues:
            by_severity[issue.severity].append(issue)
        
        # Group issues by category
        by_category = defaultdict(list)
        for issue in issues:
            by_category[issue.category].append(issue)
        
        return {
            'total_issues': len(issues),
            'by_severity': {
                severity.value: len(issues_list)
                for severity, issues_list in by_severity.items()
            },
            'by_category': {
                category: len(issues_list)
                for category, issues_list in by_category.items()
            },
            'critical_issues': [
                issue.to_dict() for issue in issues
                if issue.severity == ValidationSeverity.CRITICAL
            ],
            'error_issues': [
                issue.to_dict() for issue in issues
                if issue.severity == ValidationSeverity.ERROR
            ],
            'warning_issues': [
                issue.to_dict() for issue in issues
                if issue.severity == ValidationSeverity.WARNING
            ],
            'recommendations': self._generate_recommendations(issues)
        }
    
    def _generate_recommendations(self, issues: List[ValidationIssue]) -> List[str]:
        """Generate recommendations based on validation issues."""
        recommendations = []
        
        # Count issue types
        error_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.WARNING)
        
        if error_count > 0:
            recommendations.append(f"Fix {error_count} critical errors before proceeding")
        
        if warning_count > 5:
            recommendations.append("Consider simplifying timeline complexity to reduce warnings")
        
        # Category-specific recommendations
        categories = defaultdict(int)
        for issue in issues:
            categories[issue.category] += 1
        
        if categories.get('timing_overlap', 0) > 2:
            recommendations.append("Review plan timing to reduce overlaps")
        
        if categories.get('high_resource_usage', 0) > 0:
            recommendations.append("Consider batching animations to reduce resource usage")
        
        if categories.get('circular_dependency', 0) > 0:
            recommendations.append("Restructure dependencies to eliminate circular references")
        
        return recommendations


# Convenience functions for creating debugging tools

def create_timeline_debugger(timeline: TickTimeline, engine: TickAnimationEngine,
                           coordination_engine: CoordinationEngine) -> Tuple[TimelineInspector, TimelineReplayDebugger, TimelineValidator]:
    """Create complete timeline debugging toolkit.
    
    Args:
        timeline: Timeline to debug
        engine: Animation engine
        coordination_engine: Coordination engine
        
    Returns:
        Tuple of (inspector, replay_debugger, validator)
    """
    inspector = TimelineInspector(timeline, engine, coordination_engine)
    replay_debugger = TimelineReplayDebugger(timeline, engine, coordination_engine)
    validator = TimelineValidator(timeline, engine, coordination_engine)
    
    return inspector, replay_debugger, validator


def create_debug_logger(enable_file_logging: bool = True, log_file_path: Optional[str] = None) -> TimelineDebugLogger:
    """Create timeline debug logger with common settings.
    
    Args:
        enable_file_logging: Whether to enable file logging
        log_file_path: Path to log file
        
    Returns:
        Configured debug logger
    """
    logger = TimelineDebugLogger(
        max_entries=10000,
        enable_file_logging=enable_file_logging,
        log_file_path=log_file_path
    )
    
    # Enable common categories
    logger.enable_category("timeline")
    logger.enable_category("coordination")
    logger.enable_category("animation")
    logger.enable_category("performance")
    logger.enable_category("validation")
    
    return logger 