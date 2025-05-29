"""
Integration tests for multi-core frame prediction API (Story 3.2 Task 1).

Tests the enhanced future frame prediction capabilities of TickAnimationEngine
and validates deterministic behavior across execution contexts.
"""

import pytest
import time
import threading
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Dict, List

from tinydisplay.animation.tick_based import (
    TickAnimationEngine, TickAnimationDefinition, TickAnimationState,
    create_tick_fade_animation, create_tick_slide_animation
)
from tinydisplay.animation.multicore import (
    AnimationStateSerializer, DistributedFrameCache, AnimationWorkerPool,
    _compute_frame_worker, FrameComputationTask
)


class TestFutureFramePredictionAPI:
    """Test suite for future frame prediction API."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        
        # Create test animations
        self.fade_anim = create_tick_fade_animation(
            start_tick=0, duration_ticks=60,
            start_opacity=0.0, end_opacity=1.0,
            position=(10.0, 20.0)
        )
        
        self.slide_anim = create_tick_slide_animation(
            start_tick=30, duration_ticks=90,
            start_position=(0.0, 0.0), end_position=(100.0, 50.0)
        )
        
        # Add animations to engine
        self.engine.add_animation("fade_test", self.fade_anim)
        self.engine.add_animation("slide_test", self.slide_anim)
        
        # Start animations
        self.engine.start_animation_at("fade_test", 0)
        self.engine.start_animation_at("slide_test", 30)
    
    def test_predict_frame_at_tick__single_animation__returns_correct_state(self):
        """Test predicting frame state for single animation."""
        # Test at animation start
        frame_state = self.engine.predict_frame_at_tick(0)
        assert "fade_test" in frame_state
        assert frame_state["fade_test"].opacity == 0.0
        assert frame_state["fade_test"].position == (10.0, 20.0)
        
        # Test at animation middle (tick 30 of 60, with ease_out easing)
        frame_state = self.engine.predict_frame_at_tick(30)
        assert "fade_test" in frame_state
        assert abs(frame_state["fade_test"].opacity - 0.75) < 0.01  # ease_out gives 0.75 at halfway
        
        # Test at animation end
        frame_state = self.engine.predict_frame_at_tick(60)
        assert "fade_test" in frame_state
        assert frame_state["fade_test"].opacity == 1.0
    
    def test_predict_frame_at_tick__multiple_animations__returns_all_active(self):
        """Test predicting frame state with multiple active animations."""
        # Test when both animations are active (tick 60)
        frame_state = self.engine.predict_frame_at_tick(60)
        
        assert "fade_test" in frame_state
        assert "slide_test" in frame_state
        
        # Fade animation should be complete
        assert frame_state["fade_test"].opacity == 1.0
        
        # Slide animation should be in progress
        slide_state = frame_state["slide_test"]
        assert 0.0 < slide_state.position[0] < 100.0
        assert 0.0 < slide_state.position[1] < 50.0
    
    def test_predict_frame_at_tick__future_tick__returns_predicted_state(self):
        """Test predicting far future frame states."""
        # Predict 5 seconds into future (300 ticks at 60fps)
        future_tick = 300
        frame_state = self.engine.predict_frame_at_tick(future_tick)
        
        # Both animations should be complete
        assert "fade_test" not in frame_state  # Animation ended at tick 60
        assert "slide_test" not in frame_state  # Animation ended at tick 120
    
    def test_predict_frame_range__sequential_ticks__returns_all_frames(self):
        """Test batch prediction for range of ticks."""
        start_tick = 25
        end_tick = 35
        
        frame_range = self.engine.predict_frame_range(start_tick, end_tick)
        
        # Should have predictions for all ticks in range
        assert len(frame_range) == 11  # 25-35 inclusive
        
        for tick in range(start_tick, end_tick + 1):
            assert tick in frame_range
            
            # Verify frame state consistency
            frame_state = frame_range[tick]
            if tick < 30:
                # Only fade animation active
                assert "fade_test" in frame_state
                assert "slide_test" not in frame_state
            else:
                # Both animations active
                assert "fade_test" in frame_state
                assert "slide_test" in frame_state
    
    def test_predict_frame_range__large_range__performance_acceptable(self):
        """Test performance of large range predictions."""
        start_tick = 0
        end_tick = 120  # 2 seconds at 60fps
        
        start_time = time.perf_counter()
        frame_range = self.engine.predict_frame_range(start_tick, end_tick)
        computation_time = time.perf_counter() - start_time
        
        # Should complete in reasonable time (< 100ms for 121 frames)
        assert computation_time < 0.1
        assert len(frame_range) == 121
        
        # Verify all frames are present
        for tick in range(start_tick, end_tick + 1):
            assert tick in frame_range
    
    def test_get_prediction_workload__balanced_distribution__correct_chunks(self):
        """Test workload distribution for multi-core processing."""
        start_tick = 0
        num_frames = 120
        num_workers = 3
        
        workload = self.engine.get_prediction_workload(start_tick, num_frames, num_workers)
        
        # Should have chunks for each worker
        assert len(workload) == num_workers
        
        # Verify workload coverage
        total_frames = 0
        for start, end in workload:
            total_frames += (end - start + 1)
            assert start >= 0
            assert end < start_tick + num_frames
        
        assert total_frames == num_frames
    
    def test_get_prediction_workload__uneven_distribution__handles_remainder(self):
        """Test workload distribution with uneven frame counts."""
        start_tick = 10
        num_frames = 100  # Not evenly divisible by 3
        num_workers = 3
        
        workload = self.engine.get_prediction_workload(start_tick, num_frames, num_workers)
        
        # Should still distribute all frames
        total_frames = sum(end - start + 1 for start, end in workload)
        assert total_frames == num_frames
        
        # Last worker should get the remainder
        last_chunk_size = workload[-1][1] - workload[-1][0] + 1
        first_chunk_size = workload[0][1] - workload[0][0] + 1
        
        # Difference should be at most the remainder
        assert abs(last_chunk_size - first_chunk_size) <= (num_frames % num_workers)
    
    def test_get_prediction_workload__edge_cases__handles_correctly(self):
        """Test workload distribution edge cases."""
        # Zero frames
        workload = self.engine.get_prediction_workload(0, 0, 3)
        assert workload == []
        
        # Zero workers
        workload = self.engine.get_prediction_workload(0, 100, 0)
        assert workload == []
        
        # More workers than frames
        workload = self.engine.get_prediction_workload(0, 2, 5)
        assert len(workload) == 2  # Only 2 chunks for 2 frames
        
        total_frames = sum(end - start + 1 for start, end in workload)
        assert total_frames == 2


class TestDeterministicValidation:
    """Test suite for deterministic behavior validation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        
        # Create complex animation with multiple properties
        self.complex_anim = TickAnimationDefinition(
            start_tick=0,
            duration_ticks=100,
            start_state=TickAnimationState(
                tick=0,
                position=(0.0, 0.0),
                rotation=0.0,
                scale=(0.5, 0.5),
                opacity=0.0,
                custom_properties={"brightness": 0.0, "contrast": 1.0}
            ),
            end_state=TickAnimationState(
                tick=100,
                position=(200.0, 150.0),
                rotation=360.0,
                scale=(2.0, 2.0),
                opacity=1.0,
                custom_properties={"brightness": 1.0, "contrast": 2.0}
            ),
            easing="ease_in_out"
        )
        
        self.engine.add_animation("complex_test", self.complex_anim)
        self.engine.start_animation_at("complex_test", 0)
    
    def test_deterministic_prediction__multiple_calls__identical_results(self):
        """Test that multiple prediction calls return identical results."""
        test_tick = 50
        
        # Make multiple predictions
        results = []
        for _ in range(10):
            frame_state = self.engine.predict_frame_at_tick(test_tick)
            results.append(frame_state)
        
        # All results should be identical
        reference = results[0]
        for result in results[1:]:
            assert len(result) == len(reference)
            for anim_id in reference:
                assert anim_id in result
                ref_state = reference[anim_id]
                test_state = result[anim_id]
                
                assert ref_state.tick == test_state.tick
                assert ref_state.position == test_state.position
                assert ref_state.rotation == test_state.rotation
                assert ref_state.scale == test_state.scale
                assert ref_state.opacity == test_state.opacity
                assert ref_state.custom_properties == test_state.custom_properties
    
    def test_deterministic_prediction__different_threads__identical_results(self):
        """Test deterministic behavior across multiple threads."""
        test_tick = 75
        results = []
        
        def predict_frame():
            frame_state = self.engine.predict_frame_at_tick(test_tick)
            results.append(frame_state)
        
        # Run predictions in multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=predict_frame)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All results should be identical
        assert len(results) == 5
        reference = results[0]
        for result in results[1:]:
            self._assert_frame_states_equal(reference, result)
    
    def test_deterministic_prediction__serialization_roundtrip__preserves_state(self):
        """Test that serialization/deserialization preserves deterministic behavior."""
        test_tick = 60
        
        # Get original prediction
        original_frame = self.engine.predict_frame_at_tick(test_tick)
        
        # Serialize and deserialize engine
        serialized = self.engine.serialize_engine_state()
        restored_engine = TickAnimationEngine.deserialize_engine_state(serialized)
        
        # Get prediction from restored engine
        restored_frame = restored_engine.predict_frame_at_tick(test_tick)
        
        # Results should be identical
        self._assert_frame_states_equal(original_frame, restored_frame)
    
    def test_deterministic_prediction__complex_easing__consistent_values(self):
        """Test deterministic behavior with complex easing functions."""
        # Test various easing functions
        easing_functions = ["linear", "ease_in", "ease_out", "ease_in_out", "bounce", "elastic"]
        
        for easing in easing_functions:
            # Create animation with specific easing
            anim = TickAnimationDefinition(
                start_tick=0,
                duration_ticks=60,
                start_state=TickAnimationState(tick=0, position=(0.0, 0.0), opacity=0.0),
                end_state=TickAnimationState(tick=60, position=(100.0, 100.0), opacity=1.0),
                easing=easing
            )
            
            engine = TickAnimationEngine()
            engine.add_animation(f"test_{easing}", anim)
            engine.start_animation_at(f"test_{easing}", 0)
            
            # Test determinism at multiple points
            for test_tick in [15, 30, 45]:
                results = []
                for _ in range(5):
                    frame_state = engine.predict_frame_at_tick(test_tick)
                    results.append(frame_state)
                
                # All results should be identical
                reference = results[0]
                for result in results[1:]:
                    self._assert_frame_states_equal(reference, result)
    
    def _assert_frame_states_equal(self, state1: Dict[str, TickAnimationState], 
                                 state2: Dict[str, TickAnimationState]) -> None:
        """Assert that two frame states are identical."""
        assert len(state1) == len(state2)
        
        for anim_id in state1:
            assert anim_id in state2
            s1 = state1[anim_id]
            s2 = state2[anim_id]
            
            assert s1.tick == s2.tick
            assert s1.position == s2.position
            assert s1.rotation == s2.rotation
            assert s1.scale == s2.scale
            assert s1.opacity == s2.opacity
            assert s1.custom_properties == s2.custom_properties


class TestAnimationStateSerialization:
    """Test suite for animation state serialization system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        
        # Create test animation
        self.test_anim = create_tick_fade_animation(
            start_tick=0, duration_ticks=60,
            start_opacity=0.0, end_opacity=1.0,
            position=(50.0, 75.0)
        )
        
        self.engine.add_animation("serialize_test", self.test_anim)
        self.engine.start_animation_at("serialize_test", 0)
    
    def test_serialize_engine_state__complete_engine__preserves_all_data(self):
        """Test serialization of complete engine state."""
        # Advance engine to specific state
        self.engine.set_current_tick(25)
        
        # Serialize engine state
        serialized = AnimationStateSerializer.serialize_engine_state(self.engine)
        
        # Should produce compressed bytes
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0
        
        # Deserialize and verify
        restored_engine = AnimationStateSerializer.deserialize_engine_state(serialized)
        
        assert restored_engine.current_tick == 25
        assert "serialize_test" in restored_engine.animations
        
        # Verify animation definition is preserved
        original_def = self.engine.get_animation("serialize_test")
        restored_def = restored_engine.get_animation("serialize_test")
        
        assert original_def.start_tick == restored_def.start_tick
        assert original_def.duration_ticks == restored_def.duration_ticks
        assert original_def.easing == restored_def.easing
    
    def test_serialize_frame_state__complex_frame__preserves_all_properties(self):
        """Test serialization of complex frame state."""
        # Create frame state with multiple animations
        frame_state = {
            "anim1": TickAnimationState(
                tick=30,
                position=(100.0, 200.0),
                rotation=45.0,
                scale=(1.5, 2.0),
                opacity=0.75,
                custom_properties={"brightness": 0.8, "contrast": 1.2}
            ),
            "anim2": TickAnimationState(
                tick=30,
                position=(50.0, 150.0),
                rotation=90.0,
                scale=(0.5, 0.5),
                opacity=0.25,
                custom_properties={"volume": 0.6}
            )
        }
        
        # Serialize frame state
        serialized = AnimationStateSerializer.serialize_frame_state(frame_state)
        
        # Should produce compressed bytes
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0
        
        # Deserialize and verify
        restored_frame = AnimationStateSerializer.deserialize_frame_state(serialized)
        
        assert len(restored_frame) == 2
        assert "anim1" in restored_frame
        assert "anim2" in restored_frame
        
        # Verify all properties preserved
        for anim_id in frame_state:
            original = frame_state[anim_id]
            restored = restored_frame[anim_id]
            
            assert original.tick == restored.tick
            assert original.position == restored.position
            assert original.rotation == restored.rotation
            assert original.scale == restored.scale
            assert original.opacity == restored.opacity
            assert original.custom_properties == restored.custom_properties
    
    def test_serialization_compression__large_state__reduces_size(self):
        """Test that compression reduces serialized state size."""
        # Create large frame state
        large_frame_state = {}
        for i in range(100):
            large_frame_state[f"anim_{i}"] = TickAnimationState(
                tick=i,
                position=(float(i), float(i * 2)),
                rotation=float(i * 3),
                scale=(1.0 + i * 0.01, 1.0 + i * 0.01),
                opacity=min(1.0, i * 0.01),
                custom_properties={f"prop_{j}": float(i + j) for j in range(10)}
            )
        
        # Serialize with compression
        compressed = AnimationStateSerializer.serialize_frame_state(large_frame_state)
        
        # Estimate uncompressed size (rough calculation)
        estimated_uncompressed = len(str(large_frame_state).encode())
        
        # Compressed should be significantly smaller
        compression_ratio = len(compressed) / estimated_uncompressed
        assert compression_ratio < 0.5  # At least 50% compression
    
    def test_serialization_roundtrip__multiple_iterations__maintains_integrity(self):
        """Test that multiple serialization roundtrips maintain data integrity."""
        original_frame = self.engine.predict_frame_at_tick(40)
        
        current_frame = original_frame
        
        # Perform multiple roundtrips
        for _ in range(5):
            serialized = AnimationStateSerializer.serialize_frame_state(current_frame)
            current_frame = AnimationStateSerializer.deserialize_frame_state(serialized)
        
        # Final result should match original
        assert len(current_frame) == len(original_frame)
        for anim_id in original_frame:
            assert anim_id in current_frame
            original_state = original_frame[anim_id]
            final_state = current_frame[anim_id]
            
            assert original_state.tick == final_state.tick
            assert original_state.position == final_state.position
            assert original_state.rotation == final_state.rotation
            assert original_state.scale == final_state.scale
            assert original_state.opacity == final_state.opacity
            assert original_state.custom_properties == final_state.custom_properties


class TestPerformanceOptimization:
    """Test suite for performance optimization of prediction API."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        
        # Create multiple animations for performance testing
        for i in range(10):
            fade_anim = create_tick_fade_animation(
                start_tick=i * 10, duration_ticks=60,
                start_opacity=0.0, end_opacity=1.0,
                position=(float(i * 10), float(i * 20))
            )
            self.engine.add_animation(f"perf_test_{i}", fade_anim)
            self.engine.start_animation_at(f"perf_test_{i}", i * 10)
    
    def test_prediction_performance__single_frame__meets_target(self):
        """Test that single frame prediction meets performance targets."""
        test_tick = 50
        
        # Measure prediction time
        start_time = time.perf_counter()
        for _ in range(1000):
            self.engine.predict_frame_at_tick(test_tick)
        end_time = time.perf_counter()
        
        # Calculate average time per prediction
        avg_time = (end_time - start_time) / 1000
        
        # Should be much faster than 16.67ms (60fps requirement)
        assert avg_time < 0.001  # Less than 1ms per prediction
    
    def test_batch_prediction_performance__large_range__acceptable_throughput(self):
        """Test performance of batch prediction operations."""
        start_tick = 0
        end_tick = 300  # 5 seconds at 60fps
        
        # Measure batch prediction time
        start_time = time.perf_counter()
        frame_range = self.engine.predict_frame_range(start_tick, end_tick)
        end_time = time.perf_counter()
        
        computation_time = end_time - start_time
        frames_per_second = len(frame_range) / computation_time
        
        # Should achieve high throughput (>1000 fps computation)
        assert frames_per_second > 1000
        assert len(frame_range) == 301  # 0-300 inclusive
    
    def test_workload_distribution_performance__balanced_load__efficient_distribution(self):
        """Test performance of workload distribution calculation."""
        start_time = time.perf_counter()
        
        # Test multiple workload distributions
        for num_frames in [60, 120, 300, 600]:
            for num_workers in [2, 3, 4, 8]:
                workload = self.engine.get_prediction_workload(0, num_frames, num_workers)
                
                # Verify workload is balanced
                chunk_sizes = [end - start + 1 for start, end in workload]
                if chunk_sizes:
                    max_chunk = max(chunk_sizes)
                    min_chunk = min(chunk_sizes)
                    balance_ratio = min_chunk / max_chunk if max_chunk > 0 else 1.0
                    
                    # Chunks should be reasonably balanced (>80% efficiency)
                    assert balance_ratio > 0.8
        
        end_time = time.perf_counter()
        
        # Distribution calculation should be very fast
        assert (end_time - start_time) < 0.01  # Less than 10ms for all tests
    
    @pytest.mark.performance
    def test_memory_usage__large_predictions__bounded_memory(self):
        """Test that large predictions don't cause excessive memory usage."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform large batch predictions
        for _ in range(10):
            frame_range = self.engine.predict_frame_range(0, 600)  # 10 seconds
            
            # Clear reference to allow garbage collection
            del frame_range
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (<50MB)
        assert memory_increase < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 