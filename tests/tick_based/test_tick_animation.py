"""
Test Suite for Tick-Based Animation System

This test suite validates the tick-based animation framework, ensuring
deterministic behavior and correct animation calculations.
"""

import unittest
import math
from typing import Dict, List

# Import the tick-based animation system
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.tinydisplay.animation.tick_based import (
    TickAnimationState,
    TickEasing,
    TickAnimationDefinition,
    TickAnimationEngine,
    TickFramePredictor,
    create_tick_fade_animation,
    create_tick_slide_animation,
    create_tick_scale_animation
)


class TestTickAnimationState(unittest.TestCase):
    """Test TickAnimationState functionality."""
    
    def test_state_creation(self):
        """Test creating animation states."""
        state = TickAnimationState(
            tick=10,
            position=(100.0, 50.0),
            rotation=45.0,
            scale=(2.0, 1.5),
            opacity=0.8
        )
        
        self.assertEqual(state.tick, 10)
        self.assertEqual(state.position, (100.0, 50.0))
        self.assertEqual(state.rotation, 45.0)
        self.assertEqual(state.scale, (2.0, 1.5))
        self.assertEqual(state.opacity, 0.8)
    
    def test_state_validation(self):
        """Test state parameter validation."""
        # Test negative tick
        with self.assertRaises(ValueError):
            TickAnimationState(tick=-1, position=(0.0, 0.0))
        
        # Test invalid opacity
        with self.assertRaises(ValueError):
            TickAnimationState(tick=0, position=(0.0, 0.0), opacity=1.5)
        
        # Test negative scale
        with self.assertRaises(ValueError):
            TickAnimationState(tick=0, position=(0.0, 0.0), scale=(-1.0, 1.0))
    
    def test_state_interpolation(self):
        """Test state interpolation."""
        start_state = TickAnimationState(
            tick=0,
            position=(0.0, 0.0),
            opacity=0.0
        )
        
        end_state = TickAnimationState(
            tick=10,
            position=(100.0, 50.0),
            opacity=1.0
        )
        
        # Test 50% interpolation
        mid_state = start_state.interpolate_to(end_state, 0.5)
        self.assertEqual(mid_state.position, (50.0, 25.0))
        self.assertEqual(mid_state.opacity, 0.5)
    
    def test_state_serialization(self):
        """Test state serialization and deserialization."""
        original = TickAnimationState(
            tick=5,
            position=(10.0, 20.0),
            rotation=30.0,
            scale=(1.5, 2.0),
            opacity=0.7,
            custom_properties={'test': 42}
        )
        
        # Serialize and deserialize
        data = original.serialize()
        restored = TickAnimationState.deserialize(data)
        
        self.assertEqual(original.tick, restored.tick)
        self.assertEqual(original.position, restored.position)
        self.assertEqual(original.rotation, restored.rotation)
        self.assertEqual(original.scale, restored.scale)
        self.assertEqual(original.opacity, restored.opacity)
        self.assertEqual(original.custom_properties, restored.custom_properties)


class TestTickEasing(unittest.TestCase):
    """Test TickEasing functions."""
    
    def test_linear_easing(self):
        """Test linear easing function."""
        self.assertEqual(TickEasing.linear(0.0), 0.0)
        self.assertEqual(TickEasing.linear(0.5), 0.5)
        self.assertEqual(TickEasing.linear(1.0), 1.0)
    
    def test_ease_in_easing(self):
        """Test ease-in easing function."""
        self.assertEqual(TickEasing.ease_in(0.0), 0.0)
        self.assertEqual(TickEasing.ease_in(0.5), 0.25)
        self.assertEqual(TickEasing.ease_in(1.0), 1.0)
    
    def test_ease_out_easing(self):
        """Test ease-out easing function."""
        self.assertEqual(TickEasing.ease_out(0.0), 0.0)
        self.assertEqual(TickEasing.ease_out(1.0), 1.0)
        # ease_out(0.5) should be > 0.5 (faster start)
        self.assertGreater(TickEasing.ease_out(0.5), 0.5)
    
    def test_bounce_easing(self):
        """Test bounce easing function."""
        self.assertEqual(TickEasing.bounce(0.0), 0.0)
        self.assertEqual(TickEasing.bounce(1.0), 1.0)
        # Bounce should have values in valid range
        for t in [0.1, 0.3, 0.5, 0.7, 0.9]:
            result = TickEasing.bounce(t)
            self.assertGreaterEqual(result, 0.0)
            self.assertLessEqual(result, 1.2)  # Bounce can overshoot slightly
    
    def test_easing_determinism(self):
        """Test that easing functions are deterministic."""
        test_values = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
        easing_functions = [
            TickEasing.linear,
            TickEasing.ease_in,
            TickEasing.ease_out,
            TickEasing.ease_in_out,
            TickEasing.bounce,
            TickEasing.elastic
        ]
        
        for func in easing_functions:
            for t in test_values:
                # Run multiple times to ensure determinism
                results = [func(t) for _ in range(10)]
                # All results should be identical
                self.assertTrue(all(r == results[0] for r in results))


class TestTickAnimationDefinition(unittest.TestCase):
    """Test TickAnimationDefinition functionality."""
    
    def setUp(self):
        """Set up test animation definition."""
        self.start_state = TickAnimationState(
            tick=0,
            position=(0.0, 0.0),
            opacity=0.0
        )
        
        self.end_state = TickAnimationState(
            tick=60,  # 1 second at 60fps
            position=(100.0, 50.0),
            opacity=1.0
        )
        
        self.animation = TickAnimationDefinition(
            start_tick=0,
            duration_ticks=60,
            start_state=self.start_state,
            end_state=self.end_state,
            easing="linear"
        )
    
    def test_animation_creation(self):
        """Test creating animation definitions."""
        self.assertEqual(self.animation.start_tick, 0)
        self.assertEqual(self.animation.duration_ticks, 60)
        self.assertEqual(self.animation.end_tick, 60)
        self.assertEqual(self.animation.easing, "linear")
    
    def test_animation_validation(self):
        """Test animation parameter validation."""
        # Test negative start tick
        with self.assertRaises(ValueError):
            TickAnimationDefinition(
                start_tick=-1,
                duration_ticks=60,
                start_state=self.start_state,
                end_state=self.end_state
            )
        
        # Test zero duration
        with self.assertRaises(ValueError):
            TickAnimationDefinition(
                start_tick=0,
                duration_ticks=0,
                start_state=self.start_state,
                end_state=self.end_state
            )
    
    def test_animation_timing(self):
        """Test animation timing calculations."""
        # Before start
        self.assertFalse(self.animation.is_active_at(-1))
        self.assertFalse(self.animation.is_completed_at(-1))
        
        # At start
        self.assertTrue(self.animation.is_active_at(0))
        self.assertFalse(self.animation.is_completed_at(0))
        
        # During animation
        self.assertTrue(self.animation.is_active_at(30))
        self.assertFalse(self.animation.is_completed_at(30))
        
        # At end
        self.assertTrue(self.animation.is_active_at(60))
        self.assertFalse(self.animation.is_completed_at(60))
        
        # After end
        self.assertFalse(self.animation.is_active_at(61))
        self.assertTrue(self.animation.is_completed_at(61))
    
    def test_animation_progress(self):
        """Test animation progress calculations."""
        # Test progress at various points
        self.assertEqual(self.animation.get_local_progress(0), 0.0)
        self.assertEqual(self.animation.get_local_progress(30), 0.5)
        self.assertEqual(self.animation.get_local_progress(60), 1.0)
        
        # Test before and after bounds
        self.assertEqual(self.animation.get_local_progress(-10), 0.0)
        self.assertEqual(self.animation.get_local_progress(70), 1.0)
    
    def test_animation_state_computation(self):
        """Test animation state computation at various ticks."""
        # At start
        start_computed = self.animation.state_at(0)
        self.assertEqual(start_computed.position, (0.0, 0.0))
        self.assertEqual(start_computed.opacity, 0.0)
        
        # At middle (linear interpolation)
        mid_computed = self.animation.state_at(30)
        self.assertEqual(mid_computed.position, (50.0, 25.0))
        self.assertEqual(mid_computed.opacity, 0.5)
        
        # At end
        end_computed = self.animation.state_at(60)
        self.assertEqual(end_computed.position, (100.0, 50.0))
        self.assertEqual(end_computed.opacity, 1.0)
    
    def test_animation_repeat_modes(self):
        """Test animation repeat modes."""
        # Create repeating animation
        repeat_animation = TickAnimationDefinition(
            start_tick=0,
            duration_ticks=30,
            start_state=self.start_state,
            end_state=self.end_state,
            repeat_count=2,
            repeat_mode="restart"
        )
        
        # Test that animation runs for correct total duration
        self.assertEqual(repeat_animation.end_tick, 60)
        self.assertTrue(repeat_animation.is_active_at(45))
        self.assertFalse(repeat_animation.is_active_at(61))
    
    def test_animation_serialization(self):
        """Test animation serialization and deserialization."""
        # Serialize and deserialize
        data = self.animation.serialize()
        restored = TickAnimationDefinition.deserialize(data)
        
        self.assertEqual(self.animation.start_tick, restored.start_tick)
        self.assertEqual(self.animation.duration_ticks, restored.duration_ticks)
        self.assertEqual(self.animation.easing, restored.easing)
        self.assertEqual(self.animation.repeat_count, restored.repeat_count)
        self.assertEqual(self.animation.repeat_mode, restored.repeat_mode)


class TestTickAnimationEngine(unittest.TestCase):
    """Test TickAnimationEngine functionality."""
    
    def setUp(self):
        """Set up test engine and animations."""
        self.engine = TickAnimationEngine()
        
        # Create test animations
        self.fade_anim = create_tick_fade_animation(
            start_tick=0,
            duration_ticks=30,
            start_opacity=0.0,
            end_opacity=1.0,
            easing="linear"  # Use linear for predictable test results
        )
        
        self.slide_anim = create_tick_slide_animation(
            start_tick=10,
            duration_ticks=20,
            start_position=(0.0, 0.0),
            end_position=(100.0, 50.0),
            easing="linear"  # Use linear for predictable test results
        )
        
        # Add animations to engine
        self.engine.add_animation("fade", self.fade_anim)
        self.engine.add_animation("slide", self.slide_anim)
    
    def test_engine_animation_management(self):
        """Test adding, removing, and querying animations."""
        # Test has_animation
        self.assertTrue(self.engine.has_animation("fade"))
        self.assertTrue(self.engine.has_animation("slide"))
        self.assertFalse(self.engine.has_animation("nonexistent"))
        
        # Test get_animation
        retrieved_fade = self.engine.get_animation("fade")
        self.assertIsNotNone(retrieved_fade)
        self.assertEqual(retrieved_fade.start_tick, 0)
        
        # Test remove_animation
        self.engine.remove_animation("fade")
        self.assertFalse(self.engine.has_animation("fade"))
    
    def test_engine_tick_management(self):
        """Test tick advancement and setting."""
        # Initial tick
        self.assertEqual(self.engine.current_tick, 0)
        
        # Advance tick
        self.engine.advance_tick()
        self.assertEqual(self.engine.current_tick, 1)
        
        # Set specific tick
        self.engine.set_current_tick(50)
        self.assertEqual(self.engine.current_tick, 50)
        
        # Test invalid tick
        with self.assertRaises(ValueError):
            self.engine.set_current_tick(-1)
    
    def test_engine_active_animations(self):
        """Test getting active animations at different ticks."""
        # At tick 0: only fade is active
        active_at_0 = self.engine.get_active_animations_at(0)
        self.assertEqual(set(active_at_0), {"fade"})
        
        # At tick 15: both animations are active
        active_at_15 = self.engine.get_active_animations_at(15)
        self.assertEqual(set(active_at_15), {"fade", "slide"})
        
        # At tick 35: no animations are active
        active_at_35 = self.engine.get_active_animations_at(35)
        self.assertEqual(len(active_at_35), 0)
    
    def test_engine_frame_computation(self):
        """Test computing complete frame states."""
        # Compute frame at tick 15 (both animations active)
        frame_state = self.engine.compute_frame_state(15)
        
        self.assertIn("fade", frame_state)
        self.assertIn("slide", frame_state)
        
        # Check fade animation state (50% through)
        fade_state = frame_state["fade"]
        self.assertEqual(fade_state.opacity, 0.5)
        
        # Check slide animation state (25% through, started at tick 10)
        slide_state = frame_state["slide"]
        self.assertEqual(slide_state.position, (25.0, 12.5))
    
    def test_engine_determinism(self):
        """Test that engine produces deterministic results."""
        test_ticks = [0, 5, 15, 25, 35]
        
        for tick in test_ticks:
            # Compute frame multiple times
            frames = [self.engine.compute_frame_state(tick) for _ in range(10)]
            
            # All frames should be identical
            reference_frame = frames[0]
            for frame in frames[1:]:
                self.assertEqual(len(frame), len(reference_frame))
                for animation_id in reference_frame:
                    self.assertIn(animation_id, frame)
                    ref_state = reference_frame[animation_id]
                    test_state = frame[animation_id]
                    
                    # Compare all state properties
                    self.assertEqual(ref_state.tick, test_state.tick)
                    self.assertEqual(ref_state.position, test_state.position)
                    self.assertEqual(ref_state.rotation, test_state.rotation)
                    self.assertEqual(ref_state.scale, test_state.scale)
                    self.assertEqual(ref_state.opacity, test_state.opacity)
                    self.assertEqual(ref_state.custom_properties, test_state.custom_properties)
    
    def test_engine_serialization(self):
        """Test engine state serialization and deserialization."""
        # Set engine to specific state
        self.engine.set_current_tick(25)
        
        # Serialize and deserialize
        data = self.engine.serialize_engine_state()
        restored_engine = TickAnimationEngine.deserialize_engine_state(data)
        
        # Compare engines
        self.assertEqual(self.engine.current_tick, restored_engine.current_tick)
        self.assertEqual(len(self.engine.animations), len(restored_engine.animations))
        
        for animation_id in self.engine.animations:
            self.assertTrue(restored_engine.has_animation(animation_id))


class TestTickFramePredictor(unittest.TestCase):
    """Test TickFramePredictor functionality."""
    
    def setUp(self):
        """Set up test predictor and engine."""
        self.engine = TickAnimationEngine()
        self.predictor = TickFramePredictor(lookahead_ticks=60)
        self.predictor.set_engine(self.engine)
        
        # Add test animation
        fade_anim = create_tick_fade_animation(
            start_tick=0,
            duration_ticks=30,
            start_opacity=0.0,
            end_opacity=1.0,
            easing="linear"  # Use linear for predictable test results
        )
        self.engine.add_animation("fade", fade_anim)
    
    def test_predictor_frame_prediction(self):
        """Test frame prediction functionality."""
        # Predict frame at tick 15
        predicted_frame = self.predictor.predict_frame_at(15)
        
        self.assertIn("fade", predicted_frame)
        fade_state = predicted_frame["fade"]
        self.assertEqual(fade_state.opacity, 0.5)  # 50% through animation
    
    def test_predictor_tick_generation(self):
        """Test prediction tick generation."""
        prediction_ticks = self.predictor.generate_prediction_ticks(10)
        
        self.assertEqual(len(prediction_ticks), 60)
        self.assertEqual(prediction_ticks[0], 10)
        self.assertEqual(prediction_ticks[-1], 69)
    
    def test_predictor_determinism_validation(self):
        """Test determinism validation."""
        # Test determinism at various ticks
        test_ticks = [0, 10, 15, 25, 35]
        
        for tick in test_ticks:
            is_deterministic = self.predictor.validate_determinism(tick, num_iterations=50)
            self.assertTrue(is_deterministic, f"Determinism failed at tick {tick}")


class TestTickAnimationHelpers(unittest.TestCase):
    """Test helper functions for creating animations."""
    
    def test_create_fade_animation(self):
        """Test fade animation creation."""
        fade_anim = create_tick_fade_animation(
            start_tick=5,
            duration_ticks=20,
            start_opacity=0.2,
            end_opacity=0.8,
            position=(10.0, 20.0)
        )
        
        self.assertEqual(fade_anim.start_tick, 5)
        self.assertEqual(fade_anim.duration_ticks, 20)
        self.assertEqual(fade_anim.start_state.opacity, 0.2)
        self.assertEqual(fade_anim.end_state.opacity, 0.8)
        self.assertEqual(fade_anim.start_state.position, (10.0, 20.0))
    
    def test_create_slide_animation(self):
        """Test slide animation creation."""
        slide_anim = create_tick_slide_animation(
            start_tick=10,
            duration_ticks=30,
            start_position=(0.0, 0.0),
            end_position=(100.0, 50.0)
        )
        
        self.assertEqual(slide_anim.start_tick, 10)
        self.assertEqual(slide_anim.duration_ticks, 30)
        self.assertEqual(slide_anim.start_state.position, (0.0, 0.0))
        self.assertEqual(slide_anim.end_state.position, (100.0, 50.0))
    
    def test_create_scale_animation(self):
        """Test scale animation creation."""
        scale_anim = create_tick_scale_animation(
            start_tick=0,
            duration_ticks=40,
            start_scale=(0.5, 0.5),
            end_scale=(2.0, 1.5),
            position=(50.0, 25.0)
        )
        
        self.assertEqual(scale_anim.start_tick, 0)
        self.assertEqual(scale_anim.duration_ticks, 40)
        self.assertEqual(scale_anim.start_state.scale, (0.5, 0.5))
        self.assertEqual(scale_anim.end_state.scale, (2.0, 1.5))
        self.assertEqual(scale_anim.start_state.position, (50.0, 25.0))


if __name__ == '__main__':
    unittest.main() 