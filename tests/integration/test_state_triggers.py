"""
Integration tests for state-based trigger system (Story 3.3 Task 3).

Tests the trigger system including TriggerConditions, StateTrigger,
trigger chaining, performance optimization, and system integration.
"""

import pytest
import time
from typing import List, Dict, Any

from tinydisplay.animation.tick_based import (
    TickAnimationEngine, TickAnimationDefinition, TickAnimationState,
    create_tick_fade_animation, create_tick_slide_animation, create_tick_scale_animation
)
from tinydisplay.animation.coordination import CoordinationEngine
from tinydisplay.animation.timeline import TickTimeline, CoordinationPlan
from tinydisplay.animation.triggers import (
    StateTriggerSystem, StateTrigger, TriggerCondition, TriggerEvent,
    TriggerPriority, TriggerState, LogicalOperator,
    AnimationStateCondition, TimelineStateCondition, CompositeCondition,
    TriggerConditionCache, TriggerPerformanceMetrics,
    create_animation_property_trigger, create_timeline_state_trigger,
    create_composite_trigger, create_trigger_chain
)


class TestTriggerConditions:
    """Test trigger condition functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        self.timeline = TickTimeline(fps=60)
        
        # Create test animations
        fade_anim = create_tick_fade_animation(0, 60, 0.0, 1.0, (10.0, 20.0))
        slide_anim = create_tick_slide_animation(0, 80, (0.0, 0.0), (100.0, 50.0))
        
        self.engine.add_animation("fade_test", fade_anim)
        self.engine.add_animation("slide_test", slide_anim)
    
    def test_animation_state_condition__evaluates_opacity_correctly(self):
        """Test animation state condition for opacity property."""
        condition = AnimationStateCondition(
            "opacity_condition",
            "fade_test",
            "opacity",
            ">=",
            0.5
        )
        
        # At tick 0, opacity should be 0.0
        result_0 = condition.evaluate(0, self.engine, self.coordination_engine, self.timeline)
        assert result_0 == False
        
        # At tick 30, opacity should be ~0.5
        result_30 = condition.evaluate(30, self.engine, self.coordination_engine, self.timeline)
        assert result_30 == True
        
        # At tick 60, opacity should be 1.0
        result_60 = condition.evaluate(60, self.engine, self.coordination_engine, self.timeline)
        assert result_60 == True
    
    def test_animation_state_condition__evaluates_position_correctly(self):
        """Test animation state condition for position property."""
        condition = AnimationStateCondition(
            "position_condition",
            "slide_test",
            "position",
            "!=",
            (0.0, 0.0)
        )
        
        # At tick 0, position should be (0.0, 0.0)
        result_0 = condition.evaluate(0, self.engine, self.coordination_engine, self.timeline)
        assert result_0 == False
        
        # At tick 40, position should be different
        result_40 = condition.evaluate(40, self.engine, self.coordination_engine, self.timeline)
        assert result_40 == True
    
    def test_animation_state_condition__handles_nonexistent_animation(self):
        """Test condition with non-existent animation."""
        condition = AnimationStateCondition(
            "missing_condition",
            "nonexistent",
            "opacity",
            "==",
            1.0
        )
        
        result = condition.evaluate(30, self.engine, self.coordination_engine, self.timeline)
        assert result == False
    
    def test_timeline_state_condition__evaluates_timeline_properties(self):
        """Test timeline state condition."""
        condition = TimelineStateCondition(
            "timeline_condition",
            "current_tick",
            ">=",
            50
        )
        
        # At tick 30, should be false
        result_30 = condition.evaluate(30, self.engine, self.coordination_engine, self.timeline)
        assert result_30 == False
        
        # At tick 60, should be true
        result_60 = condition.evaluate(60, self.engine, self.coordination_engine, self.timeline)
        assert result_60 == True
    
    def test_composite_condition__and_operator(self):
        """Test composite condition with AND operator."""
        condition1 = AnimationStateCondition("cond1", "fade_test", "opacity", ">=", 0.3)
        condition2 = AnimationStateCondition("cond2", "slide_test", "position", "!=", (0.0, 0.0))
        
        composite = CompositeCondition(
            "and_condition",
            [condition1, condition2],
            LogicalOperator.AND
        )
        
        # At tick 0, both should be false
        result_0 = composite.evaluate(0, self.engine, self.coordination_engine, self.timeline)
        assert result_0 == False
        
        # At tick 40, both should be true
        result_40 = composite.evaluate(40, self.engine, self.coordination_engine, self.timeline)
        assert result_40 == True
    
    def test_composite_condition__or_operator(self):
        """Test composite condition with OR operator."""
        condition1 = AnimationStateCondition("cond1", "fade_test", "opacity", ">=", 0.8)
        condition2 = AnimationStateCondition("cond2", "slide_test", "position", "!=", (0.0, 0.0))
        
        composite = CompositeCondition(
            "or_condition",
            [condition1, condition2],
            LogicalOperator.OR
        )
        
        # At tick 20, first false, second true -> true
        result_20 = composite.evaluate(20, self.engine, self.coordination_engine, self.timeline)
        assert result_20 == True
        
        # At tick 0, both false -> false
        result_0 = composite.evaluate(0, self.engine, self.coordination_engine, self.timeline)
        assert result_0 == False
    
    def test_condition_dependencies__returns_correct_dependencies(self):
        """Test condition dependency tracking."""
        condition1 = AnimationStateCondition("cond1", "fade_test", "opacity", ">=", 0.5)
        condition2 = AnimationStateCondition("cond2", "slide_test", "position", "!=", (0.0, 0.0))
        
        composite = CompositeCondition(
            "composite",
            [condition1, condition2],
            LogicalOperator.AND
        )
        
        dependencies = composite.get_dependencies()
        assert dependencies == {"fade_test", "slide_test"}


class TestTriggerConditionCache:
    """Test trigger condition caching."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = TriggerConditionCache(max_entries=3, ttl_ticks=10)
    
    def test_cache_stores_and_retrieves_results(self):
        """Test basic cache operations."""
        self.cache.put("key1", True, 10)
        self.cache.put("key2", False, 15)
        
        # Within TTL
        assert self.cache.get("key1", 15) == True
        assert self.cache.get("key2", 20) == False
        
        # Outside TTL
        assert self.cache.get("key1", 25) is None
    
    def test_cache_eviction__removes_lru_entries(self):
        """Test LRU eviction."""
        self.cache.put("key1", True, 10)
        self.cache.put("key2", False, 10)
        self.cache.put("key3", True, 10)
        
        # Access key1 to make it recently used
        self.cache.get("key1", 15)
        
        # Add new entry, should evict key2
        self.cache.put("key4", False, 15)
        
        assert self.cache.get("key1", 20) == True   # Still there
        assert self.cache.get("key2", 20) is None   # Evicted
        assert self.cache.get("key3", 20) == True   # Still there
        assert self.cache.get("key4", 20) == False  # New entry


class TestStateTrigger:
    """Test state trigger functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        self.timeline = TickTimeline(fps=60)
        
        # Create test animation
        fade_anim = create_tick_fade_animation(0, 60, 0.0, 1.0, (10.0, 20.0))
        self.engine.add_animation("fade_test", fade_anim)
        
        # Track trigger actions
        self.action_calls = []
    
    def test_trigger_creation__initializes_correctly(self):
        """Test trigger creation and initialization."""
        condition = AnimationStateCondition("cond", "fade_test", "opacity", ">=", 0.5)
        
        def test_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(tick)
        
        trigger = StateTrigger(
            "test_trigger",
            condition,
            test_action,
            TriggerPriority.HIGH,
            auto_reset=True,
            cooldown_ticks=5
        )
        
        assert trigger.trigger_id == "test_trigger"
        assert trigger.priority == TriggerPriority.HIGH
        assert trigger.auto_reset == True
        assert trigger.cooldown_ticks == 5
        assert trigger.state == TriggerState.INACTIVE
    
    def test_trigger_evaluation__executes_when_condition_met(self):
        """Test trigger execution when condition is met."""
        condition = AnimationStateCondition("cond", "fade_test", "opacity", ">=", 0.5)
        
        def test_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(tick)
        
        trigger = StateTrigger("test_trigger", condition, test_action)
        trigger.state = TriggerState.ACTIVE
        
        # At tick 30, opacity should be ~0.5, condition should be met
        events = trigger.evaluate(30, self.engine, self.coordination_engine, self.timeline)
        
        assert len(events) == 1
        assert events[0].event_type == "trigger_activated"
        assert events[0].trigger_id == "test_trigger"
        assert len(self.action_calls) == 1
        assert self.action_calls[0] == 30
        assert trigger.trigger_count == 1
    
    def test_trigger_cooldown__prevents_rapid_firing(self):
        """Test trigger cooldown mechanism."""
        condition = AnimationStateCondition("cond", "fade_test", "opacity", ">=", 0.0)  # Always true
        
        def test_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(tick)
        
        trigger = StateTrigger("test_trigger", condition, test_action, cooldown_ticks=10)
        trigger.state = TriggerState.ACTIVE
        
        # First trigger at tick 20
        events1 = trigger.evaluate(20, self.engine, self.coordination_engine, self.timeline)
        assert len(events1) == 1
        assert len(self.action_calls) == 1
        
        # Try to trigger again at tick 25 (within cooldown)
        trigger.state = TriggerState.ACTIVE  # Reset state for test
        events2 = trigger.evaluate(25, self.engine, self.coordination_engine, self.timeline)
        assert len(events2) == 0  # Should not trigger
        assert len(self.action_calls) == 1  # No new action calls
        
        # Trigger again at tick 35 (after cooldown)
        trigger.state = TriggerState.ACTIVE  # Reset state for test
        events3 = trigger.evaluate(35, self.engine, self.coordination_engine, self.timeline)
        assert len(events3) == 1  # Should trigger
        assert len(self.action_calls) == 2  # New action call
    
    def test_trigger_auto_reset__resets_after_execution(self):
        """Test trigger auto-reset functionality."""
        condition = AnimationStateCondition("cond", "fade_test", "opacity", ">=", 0.5)
        
        def test_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(tick)
        
        trigger = StateTrigger("test_trigger", condition, test_action, auto_reset=True)
        trigger.state = TriggerState.ACTIVE
        
        # Trigger at tick 30
        events = trigger.evaluate(30, self.engine, self.coordination_engine, self.timeline)
        
        assert len(events) == 1
        assert trigger.state == TriggerState.INACTIVE  # Should auto-reset
    
    def test_trigger_chaining__executes_chained_triggers(self):
        """Test trigger chaining functionality."""
        condition1 = AnimationStateCondition("cond1", "fade_test", "opacity", ">=", 0.5)
        condition2 = AnimationStateCondition("cond2", "fade_test", "opacity", ">=", 0.0)  # Always true
        
        def action1(tick, engine, coord_engine, timeline):
            self.action_calls.append(f"action1_{tick}")
        
        def action2(tick, engine, coord_engine, timeline):
            self.action_calls.append(f"action2_{tick}")
        
        trigger1 = StateTrigger("trigger1", condition1, action1)
        trigger2 = StateTrigger("trigger2", condition2, action2)
        
        # Chain trigger2 to trigger1 with 5 tick delay
        trigger1.add_chained_trigger(trigger2, 5)
        
        trigger1.state = TriggerState.ACTIVE
        trigger2.state = TriggerState.ACTIVE
        
        # Execute trigger1 at tick 30
        events = trigger1.evaluate(30, self.engine, self.coordination_engine, self.timeline)
        
        # Should have events from both triggers
        assert len(events) == 2
        assert len(self.action_calls) == 2
        assert "action1_30" in self.action_calls
        assert "action2_35" in self.action_calls  # 30 + 5 delay
    
    def test_trigger_dependencies__returns_condition_dependencies(self):
        """Test trigger dependency tracking."""
        condition = AnimationStateCondition("cond", "fade_test", "opacity", ">=", 0.5)
        
        def test_action(tick, engine, coord_engine, timeline):
            pass
        
        trigger = StateTrigger("test_trigger", condition, test_action)
        
        dependencies = trigger.get_dependencies()
        assert dependencies == {"fade_test"}


class TestStateTriggerSystem:
    """Test state trigger system functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.trigger_system = StateTriggerSystem()
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        self.timeline = TickTimeline(fps=60)
        
        # Create test animations
        fade_anim = create_tick_fade_animation(0, 60, 0.0, 1.0, (10.0, 20.0))
        slide_anim = create_tick_slide_animation(0, 80, (0.0, 0.0), (100.0, 50.0))
        
        self.engine.add_animation("fade_test", fade_anim)
        self.engine.add_animation("slide_test", slide_anim)
        
        # Track actions
        self.action_calls = []
    
    def test_system_add_remove_triggers__manages_triggers_correctly(self):
        """Test adding and removing triggers from system."""
        condition = AnimationStateCondition("cond", "fade_test", "opacity", ">=", 0.5)
        
        def test_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(tick)
        
        trigger = StateTrigger("test_trigger", condition, test_action)
        
        # Add trigger
        trigger_id = self.trigger_system.add_trigger(trigger)
        assert trigger_id == "test_trigger"
        assert trigger.state == TriggerState.ACTIVE
        assert len(self.trigger_system.get_active_triggers()) == 1
        
        # Remove trigger
        success = self.trigger_system.remove_trigger("test_trigger")
        assert success == True
        assert len(self.trigger_system.get_active_triggers()) == 0
    
    def test_system_evaluation__processes_triggers_by_priority(self):
        """Test system evaluates triggers in priority order."""
        condition = AnimationStateCondition("cond", "fade_test", "opacity", ">=", 0.0)  # Always true
        
        def high_action(tick, engine, coord_engine, timeline):
            self.action_calls.append("high")
        
        def normal_action(tick, engine, coord_engine, timeline):
            self.action_calls.append("normal")
        
        def low_action(tick, engine, coord_engine, timeline):
            self.action_calls.append("low")
        
        # Create triggers with different priorities
        high_trigger = StateTrigger("high", condition, high_action, TriggerPriority.HIGH)
        normal_trigger = StateTrigger("normal", condition, normal_action, TriggerPriority.NORMAL)
        low_trigger = StateTrigger("low", condition, low_action, TriggerPriority.LOW)
        
        # Add in reverse priority order
        self.trigger_system.add_trigger(low_trigger)
        self.trigger_system.add_trigger(normal_trigger)
        self.trigger_system.add_trigger(high_trigger)
        
        # Evaluate system
        events = self.trigger_system.evaluate_triggers(30, self.engine, self.coordination_engine, self.timeline)
        
        assert len(events) == 3
        # Actions should be called in priority order
        assert self.action_calls == ["high", "normal", "low"]
    
    def test_system_performance_metrics__tracks_performance(self):
        """Test system performance metric tracking."""
        condition = AnimationStateCondition("cond", "fade_test", "opacity", ">=", 0.5)
        
        def test_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(tick)
        
        trigger = StateTrigger("test_trigger", condition, test_action)
        self.trigger_system.add_trigger(trigger)
        
        # Evaluate multiple times
        self.trigger_system.evaluate_triggers(30, self.engine, self.coordination_engine, self.timeline)
        self.trigger_system.evaluate_triggers(40, self.engine, self.coordination_engine, self.timeline)
        
        metrics = self.trigger_system.get_performance_metrics()
        assert metrics.total_evaluations == 2
        assert metrics.total_triggers >= 1  # At least one trigger fired
        assert metrics.average_evaluation_time > 0.0
    
    def test_system_state__returns_comprehensive_state(self):
        """Test system state reporting."""
        condition = AnimationStateCondition("cond", "fade_test", "opacity", ">=", 0.5)
        
        def test_action(tick, engine, coord_engine, timeline):
            pass
        
        trigger = StateTrigger("test_trigger", condition, test_action, TriggerPriority.HIGH)
        self.trigger_system.add_trigger(trigger)
        
        state = self.trigger_system.get_system_state()
        
        assert state["total_triggers"] == 1
        assert state["active_triggers"] == 1
        assert state["triggers_by_priority"]["HIGH"] == 1
        assert "performance_metrics" in state
        assert "recent_events" in state
    
    def test_system_reset_triggers__resets_all_triggers(self):
        """Test resetting all triggers in system."""
        condition = AnimationStateCondition("cond", "fade_test", "opacity", ">=", 0.0)  # Always true
        
        def test_action(tick, engine, coord_engine, timeline):
            pass
        
        trigger1 = StateTrigger("trigger1", condition, test_action)
        trigger2 = StateTrigger("trigger2", condition, test_action)
        
        self.trigger_system.add_trigger(trigger1)
        self.trigger_system.add_trigger(trigger2)
        
        # Trigger both
        self.trigger_system.evaluate_triggers(30, self.engine, self.coordination_engine, self.timeline)
        
        # Both should be triggered/completed
        assert trigger1.state in (TriggerState.TRIGGERED, TriggerState.COMPLETED)
        assert trigger2.state in (TriggerState.TRIGGERED, TriggerState.COMPLETED)
        
        # Reset all
        reset_count = self.trigger_system.reset_all_triggers()
        assert reset_count == 2
        assert trigger1.state == TriggerState.INACTIVE
        assert trigger2.state == TriggerState.INACTIVE


class TestConvenienceFunctions:
    """Test trigger convenience functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        self.timeline = TickTimeline(fps=60)
        
        # Create test animation
        fade_anim = create_tick_fade_animation(0, 60, 0.0, 1.0, (10.0, 20.0))
        self.engine.add_animation("fade_test", fade_anim)
        
        self.action_calls = []
    
    def test_create_animation_property_trigger__creates_correct_trigger(self):
        """Test animation property trigger creation."""
        def test_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(tick)
        
        trigger = create_animation_property_trigger(
            "opacity_trigger",
            "fade_test",
            "opacity",
            ">=",
            0.5,
            test_action,
            TriggerPriority.HIGH
        )
        
        assert trigger.trigger_id == "opacity_trigger"
        assert trigger.priority == TriggerPriority.HIGH
        assert trigger.condition.animation_id == "fade_test"
        assert trigger.condition.property_name == "opacity"
        assert trigger.get_dependencies() == {"fade_test"}
    
    def test_create_timeline_state_trigger__creates_correct_trigger(self):
        """Test timeline state trigger creation."""
        def test_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(tick)
        
        trigger = create_timeline_state_trigger(
            "timeline_trigger",
            "current_tick",
            ">=",
            50,
            test_action
        )
        
        assert trigger.trigger_id == "timeline_trigger"
        assert trigger.condition.property_name == "current_tick"
        assert trigger.condition.operator == ">="
        assert trigger.condition.target_value == 50
    
    def test_create_composite_trigger__creates_correct_trigger(self):
        """Test composite trigger creation."""
        condition1 = AnimationStateCondition("cond1", "fade_test", "opacity", ">=", 0.3)
        condition2 = AnimationStateCondition("cond2", "fade_test", "opacity", "<=", 0.7)
        
        def test_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(tick)
        
        trigger = create_composite_trigger(
            "composite_trigger",
            [condition1, condition2],
            LogicalOperator.AND,
            test_action
        )
        
        assert trigger.trigger_id == "composite_trigger"
        assert isinstance(trigger.condition, CompositeCondition)
        assert trigger.condition.operator == LogicalOperator.AND
        assert len(trigger.condition.conditions) == 2
    
    def test_create_trigger_chain__creates_chained_triggers(self):
        """Test trigger chain creation."""
        condition1 = AnimationStateCondition("cond1", "fade_test", "opacity", ">=", 0.5)
        condition2 = AnimationStateCondition("cond2", "fade_test", "opacity", ">=", 0.0)
        condition3 = AnimationStateCondition("cond3", "fade_test", "opacity", ">=", 0.0)
        
        def action1(tick, engine, coord_engine, timeline):
            self.action_calls.append("action1")
        
        def action2(tick, engine, coord_engine, timeline):
            self.action_calls.append("action2")
        
        def action3(tick, engine, coord_engine, timeline):
            self.action_calls.append("action3")
        
        base_trigger = StateTrigger("base", condition1, action1)
        trigger2 = StateTrigger("trigger2", condition2, action2)
        trigger3 = StateTrigger("trigger3", condition3, action3)
        
        # Create chain: base -> trigger2 (delay 5) -> trigger3 (delay 10)
        chained_trigger = create_trigger_chain(
            base_trigger,
            [(trigger2, 5), (trigger3, 10)]
        )
        
        assert chained_trigger == base_trigger
        assert len(base_trigger.chained_triggers) == 1
        assert base_trigger.chained_triggers[0] == trigger2
        assert len(trigger2.chained_triggers) == 1
        assert trigger2.chained_triggers[0] == trigger3


class TestTriggerIntegration:
    """Test complete trigger system integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.trigger_system = StateTriggerSystem()
        self.engine = TickAnimationEngine()
        self.coordination_engine = CoordinationEngine(self.engine)
        self.timeline = TickTimeline(fps=60)
        
        # Create test animations
        fade_anim = create_tick_fade_animation(0, 60, 0.0, 1.0, (10.0, 20.0))
        slide_anim = create_tick_slide_animation(0, 80, (0.0, 0.0), (100.0, 50.0))
        scale_anim = create_tick_scale_animation(0, 40, (0.0, 0.0), (2.0, 2.0))
        
        self.engine.add_animation("fade_test", fade_anim)
        self.engine.add_animation("slide_test", slide_anim)
        self.engine.add_animation("scale_test", scale_anim)
        
        self.action_calls = []
    
    def test_complex_trigger_scenario__multiple_triggers_and_conditions(self):
        """Test complex scenario with multiple triggers and conditions."""
        # Create triggers for different animation states
        def fade_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(f"fade_trigger_{tick}")
        
        def slide_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(f"slide_trigger_{tick}")
        
        def composite_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(f"composite_trigger_{tick}")
        
        # Fade trigger: when opacity >= 0.5
        fade_trigger = create_animation_property_trigger(
            "fade_trigger",
            "fade_test",
            "opacity",
            ">=",
            0.5,
            fade_action,
            TriggerPriority.HIGH
        )
        
        # Slide trigger: when position changes
        slide_trigger = create_animation_property_trigger(
            "slide_trigger",
            "slide_test",
            "position",
            "!=",
            (0.0, 0.0),
            slide_action,
            TriggerPriority.NORMAL
        )
        
        # Composite trigger: when both fade and slide are active
        fade_condition = AnimationStateCondition("fade_cond", "fade_test", "opacity", ">", 0.0)
        slide_condition = AnimationStateCondition("slide_cond", "slide_test", "position", "!=", (0.0, 0.0))
        
        composite_trigger = create_composite_trigger(
            "composite_trigger",
            [fade_condition, slide_condition],
            LogicalOperator.AND,
            composite_action,
            TriggerPriority.LOW
        )
        
        # Add triggers to system
        self.trigger_system.add_trigger(fade_trigger)
        self.trigger_system.add_trigger(slide_trigger)
        self.trigger_system.add_trigger(composite_trigger)
        
        # Evaluate at different ticks
        events_10 = self.trigger_system.evaluate_triggers(10, self.engine, self.coordination_engine, self.timeline)
        events_30 = self.trigger_system.evaluate_triggers(30, self.engine, self.coordination_engine, self.timeline)
        events_50 = self.trigger_system.evaluate_triggers(50, self.engine, self.coordination_engine, self.timeline)
        
        # Verify trigger execution
        assert len(self.action_calls) >= 2  # At least slide and composite should trigger
        
        # Check system state
        state = self.trigger_system.get_system_state()
        assert state["total_triggers"] == 3
        assert state["triggers_by_priority"]["HIGH"] == 1
        assert state["triggers_by_priority"]["NORMAL"] == 1
        assert state["triggers_by_priority"]["LOW"] == 1
        
        # Verify performance metrics
        metrics = self.trigger_system.get_performance_metrics()
        assert metrics.total_evaluations == 3
        assert metrics.total_triggers > 0
    
    def test_trigger_with_timeline_integration__coordinates_with_timeline(self):
        """Test trigger system integration with timeline."""
        # Create a trigger that activates based on timeline state
        def timeline_action(tick, engine, coord_engine, timeline):
            self.action_calls.append(f"timeline_trigger_{tick}")
            # Add a coordination plan when triggered
            from tinydisplay.animation.timeline import create_sequential_plan
            plan = create_sequential_plan(
                f"triggered_plan_{tick}",
                [("scale_test", 0)],
                tick,
                f"Plan triggered at tick {tick}"
            )
            timeline.add_coordination_plan(plan)
            timeline.start_plan(f"triggered_plan_{tick}", tick)
        
        timeline_trigger = create_timeline_state_trigger(
            "timeline_trigger",
            "current_tick",
            ">=",
            40,
            timeline_action
        )
        
        self.trigger_system.add_trigger(timeline_trigger)
        
        # Evaluate trigger system with timeline
        events = self.trigger_system.evaluate_triggers(45, self.engine, self.coordination_engine, self.timeline)
        
        # Verify trigger executed and plan was added
        assert len(self.action_calls) == 1
        assert "timeline_trigger_45" in self.action_calls
        
        # Check that plan was added to timeline
        timeline_state = self.timeline.get_timeline_state()
        assert timeline_state["total_plans"] == 1 