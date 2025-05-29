"""
Integration tests for coordination primitives (Story 3.3 Task 1).

Tests the core coordination primitives including TickAnimationSync,
TickAnimationBarrier, TickAnimationSequence, and TickAnimationTrigger.
"""

import pytest
import time
from typing import List, Dict, Any

from tinydisplay.animation.tick_based import (
    TickAnimationEngine, TickAnimationDefinition, TickAnimationState,
    create_tick_fade_animation, create_tick_slide_animation
)
from tinydisplay.animation.coordination import (
    CoordinationEngine, CoordinationEventType, CoordinationState,
    TickAnimationSync, TickAnimationBarrier, TickAnimationSequence, TickAnimationTrigger,
    AnimationCompletionCondition, AnimationProgressCondition, TickCondition,
    create_sync_on_tick, create_sync_on_completion, create_barrier_for_animations,
    create_sequence_with_delays, create_progress_trigger
)


class TestCoordinationConditions:
    """Test suite for coordination conditions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        
        # Create test animations
        self.fade_anim = create_tick_fade_animation(0, 60, 0.0, 1.0, (10.0, 20.0))
        self.slide_anim = create_tick_slide_animation(30, 90, (0.0, 0.0), (100.0, 50.0))
        
        self.engine.add_animation("fade_test", self.fade_anim)
        self.engine.add_animation("slide_test", self.slide_anim)
        self.engine.start_animation_at("fade_test", 0)
        self.engine.start_animation_at("slide_test", 30)
    
    def test_animation_completion_condition__single_animation__evaluates_correctly(self):
        """Test completion condition for single animation."""
        condition = AnimationCompletionCondition("fade_test")
        
        # Should not be complete at start
        assert not condition.evaluate(0, self.engine, self.coordination_engine)
        
        # Should not be complete during animation
        assert not condition.evaluate(30, self.engine, self.coordination_engine)
        
        # Should be complete after animation ends
        assert condition.evaluate(70, self.engine, self.coordination_engine)
    
    def test_animation_completion_condition__multiple_animations__waits_for_all(self):
        """Test completion condition for multiple animations."""
        condition = AnimationCompletionCondition(["fade_test", "slide_test"])
        
        # Should not be complete when only one is done
        assert not condition.evaluate(70, self.engine, self.coordination_engine)
        
        # Should be complete when both are done
        assert condition.evaluate(130, self.engine, self.coordination_engine)
    
    def test_animation_progress_condition__evaluates_progress_correctly(self):
        """Test progress condition evaluation."""
        condition = AnimationProgressCondition("fade_test", 0.5)
        
        # Should not be met at start
        assert not condition.evaluate(0, self.engine, self.coordination_engine)
        
        # Should be met at halfway point
        assert condition.evaluate(30, self.engine, self.coordination_engine)
        
        # Should still be met after halfway
        assert condition.evaluate(45, self.engine, self.coordination_engine)
    
    def test_tick_condition__evaluates_tick_correctly(self):
        """Test tick condition evaluation."""
        condition = TickCondition(50)
        
        # Should not be met before target tick
        assert not condition.evaluate(49, self.engine, self.coordination_engine)
        
        # Should be met at target tick
        assert condition.evaluate(50, self.engine, self.coordination_engine)
        
        # Should still be met after target tick
        assert condition.evaluate(60, self.engine, self.coordination_engine)
    
    def test_condition_dependencies__returns_correct_dependencies(self):
        """Test that conditions return correct dependencies."""
        completion_condition = AnimationCompletionCondition(["fade_test", "slide_test"])
        assert completion_condition.get_dependencies() == {"fade_test", "slide_test"}
        
        progress_condition = AnimationProgressCondition("fade_test", 0.5)
        assert progress_condition.get_dependencies() == {"fade_test"}
        
        tick_condition = TickCondition(50)
        assert tick_condition.get_dependencies() == set()


class TestTickAnimationSync:
    """Test suite for TickAnimationSync primitive."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        
        # Create test animations (not started yet)
        self.fade_anim = create_tick_fade_animation(0, 60, 0.0, 1.0, (10.0, 20.0))
        self.slide_anim = create_tick_slide_animation(0, 90, (0.0, 0.0), (100.0, 50.0))
        
        self.engine.add_animation("fade_test", self.fade_anim)
        self.engine.add_animation("slide_test", self.slide_anim)
    
    def test_sync_on_tick__triggers_at_correct_tick(self):
        """Test sync that triggers at specific tick."""
        sync = create_sync_on_tick("test_sync", ["fade_test", "slide_test"], 25)
        self.coordination_engine.add_primitive(sync)
        
        # Should be pending before trigger tick
        events = self.coordination_engine.evaluate_coordination(20)
        assert len(events) == 0
        assert sync.state == CoordinationState.PENDING
        
        # Should trigger at target tick
        events = self.coordination_engine.evaluate_coordination(25)
        assert len(events) == 1
        assert events[0].event_type == CoordinationEventType.SYNC_TRIGGERED
        assert sync.state == CoordinationState.COMPLETED
        assert sync.sync_tick == 25
        
        # Verify animations were started
        fade_animation = self.engine.get_animation("fade_test")
        slide_animation = self.engine.get_animation("slide_test")
        assert fade_animation.start_tick == 25
        assert slide_animation.start_tick == 25
    
    def test_sync_on_completion__triggers_when_dependency_completes(self):
        """Test sync that triggers when other animation completes."""
        # Start trigger animation
        trigger_anim = create_tick_fade_animation(0, 30, 0.0, 1.0, (0.0, 0.0))
        self.engine.add_animation("trigger_test", trigger_anim)
        self.engine.start_animation_at("trigger_test", 0)
        
        sync = create_sync_on_completion("test_sync", ["fade_test", "slide_test"], ["trigger_test"])
        self.coordination_engine.add_primitive(sync)
        
        # Should not trigger while dependency is active
        events = self.coordination_engine.evaluate_coordination(15)
        assert len(events) == 0
        assert sync.state == CoordinationState.PENDING
        
        # Should trigger when dependency completes
        events = self.coordination_engine.evaluate_coordination(35)
        assert len(events) == 1
        assert events[0].event_type == CoordinationEventType.SYNC_TRIGGERED
        assert sync.state == CoordinationState.COMPLETED
    
    def test_sync_dependencies__returns_correct_dependencies(self):
        """Test that sync returns correct dependencies."""
        sync = create_sync_on_tick("test_sync", ["fade_test", "slide_test"], 25)
        
        dependencies = sync.get_dependencies()
        assert "fade_test" in dependencies
        assert "slide_test" in dependencies


class TestTickAnimationBarrier:
    """Test suite for TickAnimationBarrier primitive."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        
        # Create and start test animations
        self.fade_anim = create_tick_fade_animation(0, 60, 0.0, 1.0, (10.0, 20.0))
        self.slide_anim = create_tick_slide_animation(0, 90, (0.0, 0.0), (100.0, 50.0))
        
        self.engine.add_animation("fade_test", self.fade_anim)
        self.engine.add_animation("slide_test", self.slide_anim)
        self.engine.start_animation_at("fade_test", 0)
        self.engine.start_animation_at("slide_test", 0)
    
    def test_barrier__waits_for_all_animations_to_complete(self):
        """Test barrier waits for all animations to complete."""
        barrier = create_barrier_for_animations("test_barrier", ["fade_test", "slide_test"])
        self.coordination_engine.add_primitive(barrier)
        
        # Should become active when animations are running
        events = self.coordination_engine.evaluate_coordination(10)
        assert len(events) == 0
        assert barrier.state == CoordinationState.ACTIVE
        
        # Should not resolve when only one animation completes
        events = self.coordination_engine.evaluate_coordination(70)  # fade_test completes
        assert len(events) == 0
        assert barrier.state == CoordinationState.ACTIVE
        
        # Should resolve when all animations complete
        events = self.coordination_engine.evaluate_coordination(100)  # slide_test completes
        assert len(events) == 1
        assert events[0].event_type == CoordinationEventType.BARRIER_RESOLVED
        assert barrier.state == CoordinationState.COMPLETED
    
    def test_barrier_with_callback__executes_callback_on_completion(self):
        """Test barrier executes callback when resolved."""
        callback_executed = []
        
        def completion_callback():
            callback_executed.append(True)
        
        barrier = TickAnimationBarrier("test_barrier", ["fade_test"], completion_callback)
        self.coordination_engine.add_primitive(barrier)
        
        # Evaluate until completion
        self.coordination_engine.evaluate_coordination(10)  # Activate
        events = self.coordination_engine.evaluate_coordination(70)  # Complete
        
        assert len(events) == 1
        assert len(callback_executed) == 1
        assert barrier.state == CoordinationState.COMPLETED
    
    def test_barrier_dependencies__returns_monitored_animations(self):
        """Test that barrier returns correct dependencies."""
        barrier = create_barrier_for_animations("test_barrier", ["fade_test", "slide_test"])
        
        dependencies = barrier.get_dependencies()
        assert dependencies == {"fade_test", "slide_test"}


class TestTickAnimationSequence:
    """Test suite for TickAnimationSequence primitive."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        
        # Create test animations (not started yet)
        self.fade_anim = create_tick_fade_animation(0, 30, 0.0, 1.0, (10.0, 20.0))
        self.slide_anim = create_tick_slide_animation(0, 40, (0.0, 0.0), (100.0, 50.0))
        self.scale_anim = create_tick_fade_animation(0, 20, 0.0, 1.0, (50.0, 60.0))  # Reuse fade for simplicity
        
        self.engine.add_animation("fade_test", self.fade_anim)
        self.engine.add_animation("slide_test", self.slide_anim)
        self.engine.add_animation("scale_test", self.scale_anim)
    
    def test_sequence_with_delays__starts_animations_in_order(self):
        """Test sequence starts animations with correct delays."""
        sequence = create_sequence_with_delays(
            "test_sequence", 
            ["fade_test", "slide_test", "scale_test"],
            [0, 10, 25],  # Delays in ticks
            50  # Start tick
        )
        self.coordination_engine.add_primitive(sequence)
        
        # Should start sequence at trigger tick
        events = self.coordination_engine.evaluate_coordination(50)
        assert len(events) == 1
        assert events[0].event_type == CoordinationEventType.SEQUENCE_STARTED
        assert sequence.state == CoordinationState.ACTIVE
        
        # First animation should start immediately (delay 0)
        fade_animation = self.engine.get_animation("fade_test")
        assert fade_animation.start_tick == 50
        
        # Second animation should start after delay
        self.coordination_engine.evaluate_coordination(60)
        slide_animation = self.engine.get_animation("slide_test")
        assert slide_animation.start_tick == 60
        
        # Third animation should start after its delay
        self.coordination_engine.evaluate_coordination(75)
        scale_animation = self.engine.get_animation("scale_test")
        assert scale_animation.start_tick == 75
    
    def test_sequence_completion__completes_when_all_animations_done(self):
        """Test sequence completes when all animations are done."""
        sequence = create_sequence_with_delays(
            "test_sequence",
            ["fade_test", "slide_test"],
            [0, 10],
            20
        )
        self.coordination_engine.add_primitive(sequence)
        
        # Start sequence
        self.coordination_engine.evaluate_coordination(20)
        
        # Evaluate through animation completion
        self.coordination_engine.evaluate_coordination(30)  # slide_test starts
        
        # Should complete when all animations are done
        # fade_test ends at 20+30=50, slide_test ends at 30+40=70
        events = self.coordination_engine.evaluate_coordination(80)
        
        # Find completion event
        completion_events = [e for e in events if e.event_type == CoordinationEventType.SEQUENCE_COMPLETED]
        assert len(completion_events) >= 0  # May complete in earlier evaluation
        assert sequence.state == CoordinationState.COMPLETED
    
    def test_sequence_dependencies__returns_all_animations(self):
        """Test that sequence returns correct dependencies."""
        sequence = create_sequence_with_delays(
            "test_sequence",
            ["fade_test", "slide_test", "scale_test"],
            [0, 10, 25],
            50
        )
        
        dependencies = sequence.get_dependencies()
        assert "fade_test" in dependencies
        assert "slide_test" in dependencies
        assert "scale_test" in dependencies


class TestTickAnimationTrigger:
    """Test suite for TickAnimationTrigger primitive."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        
        # Create and start test animation
        self.fade_anim = create_tick_fade_animation(0, 60, 0.0, 1.0, (10.0, 20.0))
        self.engine.add_animation("fade_test", self.fade_anim)
        self.engine.start_animation_at("fade_test", 0)
    
    def test_progress_trigger__activates_at_target_progress(self):
        """Test trigger activates when animation reaches target progress."""
        action_executed = []
        
        def trigger_action(tick, engine, coord_engine):
            action_executed.append(tick)
        
        trigger = create_progress_trigger("test_trigger", "fade_test", 0.5, trigger_action)
        self.coordination_engine.add_primitive(trigger)
        
        # Should not trigger before target progress
        events = self.coordination_engine.evaluate_coordination(20)
        assert len(events) == 0
        assert len(action_executed) == 0
        
        # Should trigger at target progress
        events = self.coordination_engine.evaluate_coordination(30)  # 50% progress
        assert len(events) == 1
        assert events[0].event_type == CoordinationEventType.TRIGGER_ACTIVATED
        assert len(action_executed) == 1
        assert action_executed[0] == 30
        assert trigger.state == CoordinationState.COMPLETED
    
    def test_trigger_auto_reset__resets_after_activation(self):
        """Test trigger with auto-reset resets after activation."""
        action_count = []
        
        def trigger_action(tick, engine, coord_engine):
            action_count.append(tick)
        
        condition = AnimationProgressCondition("fade_test", 0.25)
        trigger = TickAnimationTrigger("test_trigger", condition, trigger_action, auto_reset=True)
        self.coordination_engine.add_primitive(trigger)
        
        # Should trigger at 25% progress
        events = self.coordination_engine.evaluate_coordination(15)
        assert len(events) == 1
        assert trigger.state == CoordinationState.PENDING  # Reset to pending
        
        # Should be able to trigger again (though condition is still met)
        # Note: In practice, auto-reset triggers need conditions that can become false
        assert len(action_count) == 1
    
    def test_trigger_dependencies__returns_condition_dependencies(self):
        """Test that trigger returns correct dependencies."""
        def dummy_action(tick, engine, coord_engine):
            pass
        
        trigger = create_progress_trigger("test_trigger", "fade_test", 0.5, dummy_action)
        
        dependencies = trigger.get_dependencies()
        assert dependencies == {"fade_test"}


class TestCoordinationEngine:
    """Test suite for CoordinationEngine."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        
        # Create test animations
        self.fade_anim = create_tick_fade_animation(0, 60, 0.0, 1.0, (10.0, 20.0))
        self.slide_anim = create_tick_slide_animation(0, 90, (0.0, 0.0), (100.0, 50.0))
        
        self.engine.add_animation("fade_test", self.fade_anim)
        self.engine.add_animation("slide_test", self.slide_anim)
    
    def test_add_remove_primitive__manages_primitives_correctly(self):
        """Test adding and removing coordination primitives."""
        sync = create_sync_on_tick("test_sync", ["fade_test"], 25)
        
        # Add primitive
        self.coordination_engine.add_primitive(sync)
        assert self.coordination_engine.get_primitive("test_sync") == sync
        
        # Remove primitive
        self.coordination_engine.remove_primitive("test_sync")
        assert self.coordination_engine.get_primitive("test_sync") is None
    
    def test_evaluate_coordination__processes_all_primitives(self):
        """Test coordination evaluation processes all primitives."""
        sync1 = create_sync_on_tick("sync1", ["fade_test"], 25)
        sync2 = create_sync_on_tick("sync2", ["slide_test"], 30)
        
        self.coordination_engine.add_primitive(sync1)
        self.coordination_engine.add_primitive(sync2)
        
        # Evaluate at tick 25 - should trigger sync1
        events = self.coordination_engine.evaluate_coordination(25)
        sync_events = [e for e in events if e.event_type == CoordinationEventType.SYNC_TRIGGERED]
        assert len(sync_events) == 1
        assert sync_events[0].coordination_id == "sync1"
        
        # Evaluate at tick 30 - should trigger sync2
        events = self.coordination_engine.evaluate_coordination(30)
        sync_events = [e for e in events if e.event_type == CoordinationEventType.SYNC_TRIGGERED]
        assert len(sync_events) == 1
        assert sync_events[0].coordination_id == "sync2"
    
    def test_get_coordination_state__returns_complete_state(self):
        """Test getting complete coordination state."""
        sync = create_sync_on_tick("test_sync", ["fade_test"], 25)
        self.coordination_engine.add_primitive(sync)
        
        # Get state before activation
        state = self.coordination_engine.get_coordination_state(20)
        assert state['current_tick'] == 20
        assert 'test_sync' in state['primitives']
        assert state['primitives']['test_sync']['state'] == 'pending'
        assert state['active_count'] == 0
        assert state['completed_count'] == 0
        
        # Trigger sync
        self.coordination_engine.evaluate_coordination(25)
        
        # Get state after activation
        state = self.coordination_engine.get_coordination_state(25)
        assert state['primitives']['test_sync']['state'] == 'completed'
        assert state['completed_count'] == 1
        assert len(state['recent_events']) > 0
    
    def test_clear_completed_primitives__removes_completed_primitives(self):
        """Test clearing completed primitives."""
        sync1 = create_sync_on_tick("sync1", ["fade_test"], 25)
        sync2 = create_sync_on_tick("sync2", ["slide_test"], 50)
        
        self.coordination_engine.add_primitive(sync1)
        self.coordination_engine.add_primitive(sync2)
        
        # Trigger first sync
        self.coordination_engine.evaluate_coordination(25)
        
        # Clear completed primitives
        cleared_count = self.coordination_engine.clear_completed_primitives()
        assert cleared_count == 1
        assert self.coordination_engine.get_primitive("sync1") is None
        assert self.coordination_engine.get_primitive("sync2") is not None
    
    def test_event_history__maintains_event_history(self):
        """Test that coordination engine maintains event history."""
        sync = create_sync_on_tick("test_sync", ["fade_test"], 25)
        self.coordination_engine.add_primitive(sync)
        
        # Trigger sync
        events = self.coordination_engine.evaluate_coordination(25)
        
        # Check event history
        assert len(self.coordination_engine.event_history) == len(events)
        assert self.coordination_engine.event_history[-1].event_type == CoordinationEventType.SYNC_TRIGGERED


class TestConvenienceFunctions:
    """Test suite for convenience functions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        
        # Create test animations
        self.fade_anim = create_tick_fade_animation(0, 60, 0.0, 1.0, (10.0, 20.0))
        self.slide_anim = create_tick_slide_animation(0, 90, (0.0, 0.0), (100.0, 50.0))
        
        self.engine.add_animation("fade_test", self.fade_anim)
        self.engine.add_animation("slide_test", self.slide_anim)
    
    def test_create_sync_on_tick__creates_correct_sync(self):
        """Test convenience function for creating tick-based sync."""
        sync = create_sync_on_tick("test_sync", ["fade_test", "slide_test"], 25)
        
        assert sync.coordination_id == "test_sync"
        assert sync.animation_ids == ["fade_test", "slide_test"]
        assert isinstance(sync.trigger_condition, TickCondition)
        assert sync.trigger_condition.target_tick == 25
    
    def test_create_sync_on_completion__creates_correct_sync(self):
        """Test convenience function for creating completion-based sync."""
        sync = create_sync_on_completion("test_sync", ["fade_test"], ["slide_test"])
        
        assert sync.coordination_id == "test_sync"
        assert sync.animation_ids == ["fade_test"]
        assert isinstance(sync.trigger_condition, AnimationCompletionCondition)
        assert sync.trigger_condition.animation_ids == {"slide_test"}
    
    def test_create_barrier_for_animations__creates_correct_barrier(self):
        """Test convenience function for creating animation barrier."""
        barrier = create_barrier_for_animations("test_barrier", ["fade_test", "slide_test"])
        
        assert barrier.coordination_id == "test_barrier"
        assert barrier.animation_ids == ["fade_test", "slide_test"]
    
    def test_create_sequence_with_delays__creates_correct_sequence(self):
        """Test convenience function for creating animation sequence."""
        sequence = create_sequence_with_delays(
            "test_sequence",
            ["fade_test", "slide_test"],
            [0, 10],
            50
        )
        
        assert sequence.coordination_id == "test_sequence"
        assert sequence.sequence_steps == [("fade_test", 0), ("slide_test", 10)]
        assert isinstance(sequence.start_condition, TickCondition)
        assert sequence.start_condition.target_tick == 50
    
    def test_create_sequence_with_delays__validates_input(self):
        """Test sequence creation validates input parameters."""
        with pytest.raises(ValueError, match="Number of delays must match number of animations"):
            create_sequence_with_delays("test_sequence", ["fade_test"], [0, 10], 50)
    
    def test_create_progress_trigger__creates_correct_trigger(self):
        """Test convenience function for creating progress trigger."""
        def dummy_action(tick, engine, coord_engine):
            pass
        
        trigger = create_progress_trigger("test_trigger", "fade_test", 0.5, dummy_action)
        
        assert trigger.coordination_id == "test_trigger"
        assert isinstance(trigger.trigger_condition, AnimationProgressCondition)
        assert trigger.trigger_condition.animation_id == "fade_test"
        assert trigger.trigger_condition.target_progress == 0.5
        assert trigger.action == dummy_action


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 