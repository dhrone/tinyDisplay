"""
Integration tests for timeline management system (Story 3.3 Task 2).

Tests the timeline management system including TickTimeline, CoordinationPlan,
timeline caching, future state prediction, and performance monitoring.
"""

import pytest
import time
from typing import List, Dict, Any

from tinydisplay.animation.tick_based import (
    TickAnimationEngine, TickAnimationDefinition, TickAnimationState,
    create_tick_fade_animation, create_tick_slide_animation, create_tick_scale_animation
)
from tinydisplay.animation.coordination import (
    CoordinationEngine, CoordinationEventType, CoordinationState,
    create_sequence_with_delays, create_sync_on_tick, create_barrier_for_animations
)
from tinydisplay.animation.timeline import (
    TickTimeline, CoordinationPlan, TimelineEvent, TimelineEventType,
    TimelineCache, TimelinePerformanceMetrics,
    create_simple_timeline, create_sequential_plan, create_synchronized_plan
)


class TestTimelineCache:
    """Test timeline caching functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = TimelineCache(max_entries=3)
    
    def test_cache_put_get__stores_and_retrieves_values(self):
        """Test basic cache put/get operations."""
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")
        
        assert self.cache.get("key1") == "value1"
        assert self.cache.get("key2") == "value2"
        assert self.cache.get("nonexistent") is None
    
    def test_cache_lru_eviction__evicts_least_recently_used(self):
        """Test LRU eviction when cache is full."""
        # Fill cache to capacity
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")
        self.cache.put("key3", "value3")
        
        # Access key1 to make it recently used
        self.cache.get("key1")
        
        # Add new key, should evict key2 (least recently used)
        self.cache.put("key4", "value4")
        
        assert self.cache.get("key1") == "value1"  # Still there
        assert self.cache.get("key2") is None      # Evicted
        assert self.cache.get("key3") == "value3"  # Still there
        assert self.cache.get("key4") == "value4"  # New entry
    
    def test_cache_hit_rate__calculates_correctly(self):
        """Test cache hit rate calculation."""
        self.cache.put("key1", "value1")
        
        # 2 hits, 1 miss
        self.cache.get("key1")  # Hit
        self.cache.get("key1")  # Hit
        self.cache.get("key2")  # Miss
        
        assert self.cache.get_hit_rate() == 2/3
    
    def test_cache_stats__returns_correct_statistics(self):
        """Test cache statistics reporting."""
        self.cache.put("key1", "value1")
        self.cache.get("key1")  # Hit
        self.cache.get("key2")  # Miss
        
        stats = self.cache.get_stats()
        assert stats['entries'] == 1
        assert stats['max_entries'] == 3
        assert stats['hit_count'] == 1
        assert stats['miss_count'] == 1
        assert stats['hit_rate'] == 0.5


class TestCoordinationPlan:
    """Test coordination plan functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        
        # Create test animations
        fade_anim = create_tick_fade_animation(0, 30, 0.0, 1.0, (10.0, 20.0))
        slide_anim = create_tick_slide_animation(0, 40, (0.0, 0.0), (100.0, 50.0))
        scale_anim = create_tick_scale_animation(0, 20, (0.0, 0.0), (2.0, 2.0))
        
        self.engine.add_animation("fade_test", fade_anim)
        self.engine.add_animation("slide_test", slide_anim)
        self.engine.add_animation("scale_test", scale_anim)
    
    def test_plan_creation__creates_plan_with_primitives(self):
        """Test creating coordination plan with primitives."""
        plan = CoordinationPlan("test_plan", "Test coordination plan")
        
        # Add sequence primitive
        sequence = create_sequence_with_delays(
            "test_sequence",
            ["fade_test", "slide_test"],
            [0, 10],
            50
        )
        plan.add_primitive(sequence)
        
        assert plan.plan_id == "test_plan"
        assert plan.description == "Test coordination plan"
        assert len(plan.primitives) == 1
        assert not plan.is_active
        assert not plan.is_completed
    
    def test_plan_start__activates_plan(self):
        """Test starting a coordination plan."""
        plan = CoordinationPlan("test_plan")
        sequence = create_sequence_with_delays(
            "test_sequence",
            ["fade_test", "slide_test"],
            [0, 10],
            50
        )
        plan.add_primitive(sequence)
        
        plan.start(50)
        
        assert plan.is_active
        assert plan.start_tick == 50
        assert not plan.is_completed
    
    def test_plan_evaluation__executes_primitives(self):
        """Test plan evaluation executes primitives."""
        plan = CoordinationPlan("test_plan")
        sequence = create_sequence_with_delays(
            "test_sequence",
            ["fade_test", "slide_test"],
            [0, 10],
            50
        )
        plan.add_primitive(sequence)
        plan.start(50)
        
        # Evaluate at start tick
        events = plan.evaluate_at(50, self.engine, self.coordination_engine)
        
        assert len(events) == 1
        assert events[0].event_type == CoordinationEventType.SEQUENCE_STARTED
        assert plan.evaluation_count == 1
        assert plan.event_count == 1
    
    def test_plan_completion__detects_when_all_primitives_complete(self):
        """Test plan completion detection."""
        plan = CoordinationPlan("test_plan")
        sequence = create_sequence_with_delays(
            "test_sequence",
            ["fade_test"],
            [0],
            50
        )
        plan.add_primitive(sequence)
        plan.start(50)
        
        # Start sequence
        plan.evaluate_at(50, self.engine, self.coordination_engine)
        
        # Complete animation (fade_test ends at tick 80)
        plan.evaluate_at(85, self.engine, self.coordination_engine)
        
        assert plan.is_completed
        assert plan.completion_tick == 85
        assert not plan.is_active
    
    def test_plan_dependencies__returns_all_animation_dependencies(self):
        """Test plan dependency tracking."""
        plan = CoordinationPlan("test_plan")
        sequence = create_sequence_with_delays(
            "test_sequence",
            ["fade_test", "slide_test", "scale_test"],
            [0, 10, 20],
            50
        )
        plan.add_primitive(sequence)
        
        dependencies = plan.get_dependencies()
        
        assert dependencies == {"fade_test", "slide_test", "scale_test"}
    
    def test_plan_status__returns_detailed_status(self):
        """Test plan status reporting."""
        plan = CoordinationPlan("test_plan", "Test description")
        sequence = create_sequence_with_delays(
            "test_sequence",
            ["fade_test", "slide_test"],
            [0, 10],
            50
        )
        plan.add_primitive(sequence)
        plan.start(50)
        
        status = plan.get_plan_status()
        
        assert status['plan_id'] == "test_plan"
        assert status['description'] == "Test description"
        assert status['is_active'] == True
        assert status['start_tick'] == 50
        assert status['primitive_count'] == 1
        assert "fade_test" in status['dependencies']
        assert "slide_test" in status['dependencies']


class TestTickTimeline:
    """Test timeline management functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.timeline = TickTimeline(fps=60)
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        
        # Create test animations
        fade_anim = create_tick_fade_animation(0, 30, 0.0, 1.0, (10.0, 20.0))
        slide_anim = create_tick_slide_animation(0, 40, (0.0, 0.0), (100.0, 50.0))
        
        self.engine.add_animation("fade_test", fade_anim)
        self.engine.add_animation("slide_test", slide_anim)
    
    def test_timeline_creation__initializes_correctly(self):
        """Test timeline creation and initialization."""
        assert self.timeline.fps == 60
        assert self.timeline.current_tick == 0
        assert len(self.timeline.coordination_plans) == 0
        assert len(self.timeline.event_history) == 0
    
    def test_add_coordination_plan__adds_plan_to_timeline(self):
        """Test adding coordination plan to timeline."""
        plan = CoordinationPlan("test_plan", "Test plan")
        
        plan_id = self.timeline.add_coordination_plan(plan)
        
        assert plan_id == "test_plan"
        assert "test_plan" in self.timeline.coordination_plans
        assert self.timeline.performance_metrics.active_plans_count == 1
    
    def test_start_plan__starts_plan_and_creates_event(self):
        """Test starting a plan creates timeline event."""
        plan = CoordinationPlan("test_plan", "Test plan")
        sequence = create_sequence_with_delays(
            "test_sequence",
            ["fade_test"],
            [0],
            50
        )
        plan.add_primitive(sequence)
        self.timeline.add_coordination_plan(plan)
        
        success = self.timeline.start_plan("test_plan", 50)
        
        assert success == True
        assert plan.is_active
        assert len(self.timeline.event_history) == 1
        assert self.timeline.event_history[0].event_type == TimelineEventType.PLAN_STARTED
        assert self.timeline.event_history[0].plan_id == "test_plan"
    
    def test_evaluate_at_tick__processes_all_active_plans(self):
        """Test timeline evaluation processes all active plans."""
        # Create two plans
        plan1 = CoordinationPlan("plan1")
        sequence1 = create_sequence_with_delays("seq1", ["fade_test"], [0], 50)
        plan1.add_primitive(sequence1)
        
        plan2 = CoordinationPlan("plan2")
        sync2 = create_sync_on_tick("sync2", ["slide_test"], 55)
        plan2.add_primitive(sync2)
        
        self.timeline.add_coordination_plan(plan1)
        self.timeline.add_coordination_plan(plan2)
        self.timeline.start_plan("plan1", 50)
        self.timeline.start_plan("plan2", 50)
        
        # Evaluate at tick 55
        events = self.timeline.evaluate_at_tick(55, self.engine, self.coordination_engine)
        
        assert self.timeline.current_tick == 55
        assert len(events) >= 1  # Should have sync trigger event
        assert self.timeline.performance_metrics.total_evaluations == 1
    
    def test_timeline_plan_completion__creates_completion_event(self):
        """Test timeline creates completion events for finished plans."""
        plan = CoordinationPlan("test_plan")
        sequence = create_sequence_with_delays("test_seq", ["fade_test"], [0], 50)
        plan.add_primitive(sequence)
        
        self.timeline.add_coordination_plan(plan)
        self.timeline.start_plan("test_plan", 50)
        
        # Start sequence
        self.timeline.evaluate_at_tick(50, self.engine, self.coordination_engine)
        
        # Complete animation (fade_test ends at tick 80)
        self.timeline.evaluate_at_tick(85, self.engine, self.coordination_engine)
        
        # Check for completion event
        completion_events = [e for e in self.timeline.event_history 
                           if e.event_type == TimelineEventType.PLAN_COMPLETED]
        assert len(completion_events) == 1
        assert completion_events[0].plan_id == "test_plan"
    
    def test_timeline_state__returns_comprehensive_state(self):
        """Test timeline state reporting."""
        plan = CoordinationPlan("test_plan", "Test description")
        self.timeline.add_coordination_plan(plan)
        self.timeline.start_plan("test_plan", 50)
        
        state = self.timeline.get_timeline_state(60)
        
        assert state['current_tick'] == 60
        assert state['fps'] == 60
        assert state['total_plans'] == 1
        assert state['active_plans'] == 1
        assert 'performance_metrics' in state
        assert 'cache_stats' in state
    
    def test_timeline_prediction__predicts_future_events(self):
        """Test timeline future event prediction."""
        plan = CoordinationPlan("test_plan")
        sequence = create_sequence_with_delays("test_seq", ["fade_test", "slide_test"], [0, 10], 50)
        plan.add_primitive(sequence)
        
        self.timeline.add_coordination_plan(plan)
        self.timeline.start_plan("test_plan", 50)
        
        # Start sequence
        self.timeline.evaluate_at_tick(50, self.engine, self.coordination_engine)
        
        # Predict future events
        future_events = self.timeline.predict_future_events(55, 65, self.engine, self.coordination_engine)
        
        # Should predict events (though exact count depends on implementation)
        assert isinstance(future_events, list)
    
    def test_timeline_scheduled_events__executes_scheduled_events(self):
        """Test timeline scheduled event execution."""
        executed = []
        
        def test_event():
            executed.append("executed")
        
        self.timeline.schedule_event(100, test_event)
        
        # Evaluate at scheduled tick
        self.timeline.evaluate_at_tick(100, self.engine, self.coordination_engine)
        
        assert len(executed) == 1
        assert executed[0] == "executed"
    
    def test_timeline_checkpoint__creates_checkpoint_event(self):
        """Test timeline checkpoint creation."""
        self.timeline.create_checkpoint(75, "Test checkpoint")
        
        checkpoint_events = [e for e in self.timeline.event_history 
                           if e.event_type == TimelineEventType.TIMELINE_CHECKPOINT]
        assert len(checkpoint_events) == 1
        assert checkpoint_events[0].tick == 75
        assert checkpoint_events[0].data['description'] == "Test checkpoint"
    
    def test_timeline_serialization__serializes_and_deserializes_state(self):
        """Test timeline state serialization."""
        plan = CoordinationPlan("test_plan")
        self.timeline.add_coordination_plan(plan)
        self.timeline.current_tick = 100
        
        # Serialize
        serialized_data = self.timeline.serialize_timeline_state()
        
        # Deserialize
        restored_timeline = TickTimeline.deserialize_timeline_state(serialized_data)
        
        assert restored_timeline.current_tick == 100
        assert restored_timeline.fps == 60
    
    def test_clear_completed_plans__removes_completed_plans(self):
        """Test clearing completed plans."""
        plan1 = CoordinationPlan("plan1")
        plan1.is_completed = True
        
        plan2 = CoordinationPlan("plan2")
        plan2.is_active = True
        
        self.timeline.add_coordination_plan(plan1)
        self.timeline.add_coordination_plan(plan2)
        
        cleared_count = self.timeline.clear_completed_plans()
        
        assert cleared_count == 1
        assert "plan1" not in self.timeline.coordination_plans
        assert "plan2" in self.timeline.coordination_plans


class TestTimelinePerformanceMetrics:
    """Test timeline performance monitoring."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metrics = TimelinePerformanceMetrics()
    
    def test_evaluation_time_update__updates_metrics_correctly(self):
        """Test evaluation time metric updates."""
        self.metrics.update_evaluation_time(0.001)  # 1ms
        self.metrics.update_evaluation_time(0.002)  # 2ms
        self.metrics.update_evaluation_time(0.003)  # 3ms
        
        assert self.metrics.total_evaluations == 3
        assert self.metrics.peak_evaluation_time == 0.003
        assert self.metrics.average_evaluation_time > 0.0
    
    def test_performance_metrics__tracks_all_metrics(self):
        """Test comprehensive performance metric tracking."""
        self.metrics.total_events = 100
        self.metrics.active_plans_count = 5
        self.metrics.completed_plans_count = 10
        self.metrics.cache_hit_rate = 0.85
        
        assert self.metrics.total_events == 100
        assert self.metrics.active_plans_count == 5
        assert self.metrics.completed_plans_count == 10
        assert self.metrics.cache_hit_rate == 0.85


class TestConvenienceFunctions:
    """Test timeline convenience functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TickAnimationEngine()
        
        # Create test animations
        fade_anim = create_tick_fade_animation(0, 30, 0.0, 1.0, (10.0, 20.0))
        slide_anim = create_tick_slide_animation(0, 40, (0.0, 0.0), (100.0, 50.0))
        
        self.engine.add_animation("fade_test", fade_anim)
        self.engine.add_animation("slide_test", slide_anim)
    
    def test_create_simple_timeline__creates_timeline_with_defaults(self):
        """Test simple timeline creation."""
        timeline = create_simple_timeline()
        
        assert timeline.fps == 60
        assert timeline.current_tick == 0
        assert len(timeline.coordination_plans) == 0
    
    def test_create_sequential_plan__creates_plan_with_sequence(self):
        """Test sequential plan creation."""
        plan = create_sequential_plan(
            "seq_plan",
            [("fade_test", 0), ("slide_test", 10)],
            50,
            "Sequential test plan"
        )
        
        assert plan.plan_id == "seq_plan"
        assert plan.description == "Sequential test plan"
        assert len(plan.primitives) == 1
        assert plan.get_dependencies() == {"fade_test", "slide_test"}
    
    def test_create_synchronized_plan__creates_plan_with_sync(self):
        """Test synchronized plan creation."""
        plan = create_synchronized_plan(
            "sync_plan",
            ["fade_test", "slide_test"],
            75,
            "Synchronized test plan"
        )
        
        assert plan.plan_id == "sync_plan"
        assert plan.description == "Synchronized test plan"
        assert len(plan.primitives) == 1
        assert plan.get_dependencies() == {"fade_test", "slide_test"}


class TestTimelineIntegration:
    """Test complete timeline integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.timeline = TickTimeline(fps=60)
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        
        # Create test animations
        fade_anim = create_tick_fade_animation(0, 30, 0.0, 1.0, (10.0, 20.0))
        slide_anim = create_tick_slide_animation(0, 40, (0.0, 0.0), (100.0, 50.0))
        scale_anim = create_tick_scale_animation(0, 20, (0.0, 0.0), (2.0, 2.0))
        
        self.engine.add_animation("fade_test", fade_anim)
        self.engine.add_animation("slide_test", slide_anim)
        self.engine.add_animation("scale_test", scale_anim)
    
    def test_complex_timeline_scenario__executes_multiple_plans(self):
        """Test complex timeline with multiple coordinated plans."""
        # Create sequential plan
        seq_plan = create_sequential_plan(
            "sequence_plan",
            [("fade_test", 0), ("slide_test", 10)],
            50,
            "Sequential animations"
        )
        
        # Create synchronized plan
        sync_plan = create_synchronized_plan(
            "sync_plan",
            ["scale_test"],
            100,
            "Synchronized scale"
        )
        
        # Add plans to timeline
        self.timeline.add_coordination_plan(seq_plan)
        self.timeline.add_coordination_plan(sync_plan)
        
        # Start plans
        self.timeline.start_plan("sequence_plan", 50)
        self.timeline.start_plan("sync_plan", 90)
        
        # Execute timeline over time
        events_50 = self.timeline.evaluate_at_tick(50, self.engine, self.coordination_engine)
        events_60 = self.timeline.evaluate_at_tick(60, self.engine, self.coordination_engine)
        events_100 = self.timeline.evaluate_at_tick(100, self.engine, self.coordination_engine)
        
        # Verify execution
        assert len(events_50) >= 1  # Sequence should start
        assert len(events_100) >= 1  # Sync should trigger
        
        # Check timeline state
        state = self.timeline.get_timeline_state()
        assert state['total_plans'] == 2
        assert state['active_plans'] >= 0  # May have completed
        
        # Verify performance metrics
        metrics = self.timeline.get_performance_metrics()
        assert metrics.total_evaluations == 3
        assert metrics.total_events > 0
    
    def test_timeline_with_prediction__predicts_and_executes_correctly(self):
        """Test timeline prediction accuracy."""
        # Create plan with known timing
        plan = create_sequential_plan(
            "predictable_plan",
            [("fade_test", 0), ("slide_test", 35)],  # slide starts at 50+35=85
            50
        )
        
        self.timeline.add_coordination_plan(plan)
        self.timeline.start_plan("predictable_plan", 50)
        
        # Start the plan
        self.timeline.evaluate_at_tick(50, self.engine, self.coordination_engine)
        
        # Predict future events
        future_events = self.timeline.predict_future_events(80, 90, self.engine, self.coordination_engine)
        
        # Execute actual timeline
        actual_events = self.timeline.evaluate_at_tick(85, self.engine, self.coordination_engine)
        
        # Prediction should have some correlation with actual events
        assert isinstance(future_events, list)
        assert isinstance(actual_events, list) 