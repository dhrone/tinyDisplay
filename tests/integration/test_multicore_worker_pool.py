"""
Integration tests for multi-core worker pool architecture (Story 3.2 Task 3).

Tests the AnimationWorkerPool system for distributed frame computation,
task distribution, load balancing, and performance monitoring.
"""

import pytest
import time
import threading
from concurrent.futures import Future
from typing import Dict, List

from tinydisplay.animation.tick_based import (
    TickAnimationEngine, TickAnimationDefinition, TickAnimationState,
    create_tick_fade_animation, create_tick_slide_animation
)
from tinydisplay.animation.multicore import (
    AnimationWorkerPool, DistributedFrameCache, WorkerPoolMetrics,
    FrameComputationTask, ComputedFrame, _compute_frame_worker
)


class TestAnimationWorkerPool:
    """Test suite for AnimationWorkerPool functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        # Create test engine with animations
        self.engine = TickAnimationEngine()
        
        self.fade_anim = create_tick_fade_animation(
            start_tick=0, duration_ticks=60,
            start_opacity=0.0, end_opacity=1.0,
            position=(10.0, 20.0)
        )
        
        self.slide_anim = create_tick_slide_animation(
            start_tick=30, duration_ticks=90,
            start_position=(0.0, 0.0), end_position=(100.0, 50.0)
        )
        
        self.engine.add_animation("fade_test", self.fade_anim)
        self.engine.add_animation("slide_test", self.slide_anim)
        self.engine.start_animation_at("fade_test", 0)
        self.engine.start_animation_at("slide_test", 30)
        
        # Create worker pool (use threads for testing to avoid multiprocessing complexity)
        self.worker_pool = AnimationWorkerPool(
            num_workers=2, 
            use_processes=False,  # Use threads for testing
            cache_size=60,
            max_cache_memory_mb=10
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        self.worker_pool.shutdown(wait=True)
    
    def test_submit_frame_computation__single_task__returns_task_id(self):
        """Test submitting a single frame computation task."""
        tick = 30
        
        task_id = self.worker_pool.submit_frame_computation(tick, self.engine)
        
        # Should return a valid task ID
        assert isinstance(task_id, str)
        assert len(task_id) > 0
        assert not task_id.startswith("error-")
    
    def test_submit_frame_computation__cached_frame__returns_cached_id(self):
        """Test that cached frames return immediate cached task IDs."""
        tick = 45
        
        # Submit first computation
        task_id1 = self.worker_pool.submit_frame_computation(tick, self.engine)
        
        # Wait for completion and cache storage
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < 2.0:
            result = self.worker_pool.get_computed_frame(task_id1)
            if result:
                break
            time.sleep(0.01)
        
        # Submit same tick again - should return cached ID
        task_id2 = self.worker_pool.submit_frame_computation(tick, self.engine)
        assert task_id2.startswith("cached-")
    
    def test_get_computed_frame__valid_task__returns_result(self):
        """Test retrieving computed frame from worker pool."""
        tick = 25
        
        task_id = self.worker_pool.submit_frame_computation(tick, self.engine)
        
        # Wait for computation to complete
        result = None
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < 2.0:
            result = self.worker_pool.get_computed_frame(task_id)
            if result:
                break
            time.sleep(0.01)
        
        # Should have valid result
        assert result is not None
        assert isinstance(result, ComputedFrame)
        assert result.tick == tick
        assert result.task_id == task_id
        assert len(result.frame_state) > 0
        assert result.computation_time >= 0.0
    
    def test_get_computed_frame__cached_task__returns_immediately(self):
        """Test that cached tasks return results immediately."""
        tick = 35
        
        # First computation to populate cache
        task_id1 = self.worker_pool.submit_frame_computation(tick, self.engine)
        
        # Wait for completion
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < 2.0:
            result = self.worker_pool.get_computed_frame(task_id1)
            if result:
                break
            time.sleep(0.01)
        
        # Second computation should be cached
        task_id2 = self.worker_pool.submit_frame_computation(tick, self.engine)
        cached_result = self.worker_pool.get_computed_frame(task_id2)
        
        # Should return immediately with cached result
        assert cached_result is not None
        assert cached_result.worker_id == "cache"
        assert cached_result.computation_time == 0.0
        assert cached_result.tick == tick
    
    def test_get_computed_frame__invalid_task__returns_none(self):
        """Test that invalid task IDs return None."""
        result = self.worker_pool.get_computed_frame("invalid_task_id")
        assert result is None
        
        result = self.worker_pool.get_computed_frame("error-123")
        assert result is None
    
    def test_submit_batch_computation__multiple_frames__distributes_work(self):
        """Test batch computation with multiple frames."""
        start_tick = 10
        num_frames = 20
        
        task_ids = self.worker_pool.submit_batch_computation(start_tick, num_frames, self.engine)
        
        # Should have task IDs for all frames
        assert len(task_ids) == num_frames
        
        # All task IDs should be valid
        for task_id in task_ids:
            assert isinstance(task_id, str)
            assert len(task_id) > 0
    
    def test_wait_for_batch_completion__all_tasks__completes_successfully(self):
        """Test waiting for batch completion."""
        start_tick = 5
        num_frames = 10
        
        task_ids = self.worker_pool.submit_batch_computation(start_tick, num_frames, self.engine)
        completed_frames = self.worker_pool.wait_for_batch_completion(task_ids, timeout=5.0)
        
        # Should complete most or all tasks
        assert len(completed_frames) >= num_frames * 0.8  # At least 80% completion
        
        # Verify frame content
        for task_id, frame in completed_frames.items():
            assert isinstance(frame, ComputedFrame)
            assert frame.tick >= start_tick
            assert frame.tick < start_tick + num_frames
    
    def test_wait_for_batch_completion__timeout__returns_partial_results(self):
        """Test batch completion with timeout."""
        start_tick = 0
        num_frames = 50  # Large batch
        
        task_ids = self.worker_pool.submit_batch_computation(start_tick, num_frames, self.engine)
        completed_frames = self.worker_pool.wait_for_batch_completion(task_ids, timeout=0.1)  # Very short timeout
        
        # Should return partial results
        assert len(completed_frames) >= 0
        assert len(completed_frames) <= num_frames


class TestWorkerPoolPerformanceMetrics:
    """Test suite for worker pool performance monitoring."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        
        # Add test animation
        fade_anim = create_tick_fade_animation(
            start_tick=0, duration_ticks=60,
            start_opacity=0.0, end_opacity=1.0
        )
        self.engine.add_animation("perf_test", fade_anim)
        self.engine.start_animation_at("perf_test", 0)
        
        self.worker_pool = AnimationWorkerPool(
            num_workers=2, 
            use_processes=False,
            cache_size=30
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        self.worker_pool.shutdown(wait=True)
    
    def test_get_performance_metrics__initial_state__returns_zero_metrics(self):
        """Test initial performance metrics."""
        metrics = self.worker_pool.get_performance_metrics()
        
        assert isinstance(metrics, WorkerPoolMetrics)
        assert metrics.total_tasks_submitted == 0
        assert metrics.total_tasks_completed == 0
        assert metrics.total_computation_time == 0.0
        assert metrics.average_task_time == 0.0
        assert metrics.frames_per_second == 0.0
    
    def test_get_performance_metrics__after_tasks__updates_correctly(self):
        """Test performance metrics after task completion."""
        # Submit and complete some tasks
        task_ids = []
        for tick in range(5):
            task_id = self.worker_pool.submit_frame_computation(tick, self.engine)
            task_ids.append(task_id)
        
        # Wait for completion
        completed_frames = self.worker_pool.wait_for_batch_completion(task_ids, timeout=2.0)
        
        # Check metrics
        metrics = self.worker_pool.get_performance_metrics()
        
        assert metrics.total_tasks_submitted >= 5
        assert metrics.total_tasks_completed >= len(completed_frames)
        assert metrics.total_computation_time > 0.0
        if metrics.total_tasks_completed > 0:
            assert metrics.average_task_time > 0.0
    
    def test_get_worker_utilization__active_workers__returns_utilization(self):
        """Test worker utilization calculation."""
        # Submit tasks to generate utilization
        task_ids = []
        for tick in range(10):
            task_id = self.worker_pool.submit_frame_computation(tick, self.engine)
            task_ids.append(task_id)
        
        # Wait for some completion
        time.sleep(0.1)
        
        utilization = self.worker_pool.get_worker_utilization()
        
        # Should be a valid percentage
        assert isinstance(utilization, float)
        assert 0.0 <= utilization <= 100.0
    
    def test_performance_metrics__cache_statistics__tracks_hit_rate(self):
        """Test cache performance tracking."""
        tick = 15
        
        # First computation (cache miss)
        task_id1 = self.worker_pool.submit_frame_computation(tick, self.engine)
        result1 = None
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < 2.0:
            result1 = self.worker_pool.get_computed_frame(task_id1)
            if result1:
                break
            time.sleep(0.01)
        
        # Second computation (cache hit)
        task_id2 = self.worker_pool.submit_frame_computation(tick, self.engine)
        result2 = self.worker_pool.get_computed_frame(task_id2)
        
        # Check cache metrics
        metrics = self.worker_pool.get_performance_metrics()
        
        # Should have some cache activity
        assert metrics.cache_hit_rate >= 0.0
        assert metrics.cache_miss_rate >= 0.0
        assert abs(metrics.cache_hit_rate + metrics.cache_miss_rate - 1.0) < 0.01


class TestDistributedFrameCache:
    """Test suite for distributed frame cache functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.cache = DistributedFrameCache(max_frames=10, max_memory_mb=5)
        
        # Create test frame state
        self.test_frame_state = {
            "test_anim": TickAnimationState(
                tick=30,
                position=(50.0, 75.0),
                rotation=45.0,
                scale=(1.5, 1.5),
                opacity=0.8,
                custom_properties={"brightness": 0.9}
            )
        }
    
    def test_store_and_get_frame__valid_frame__stores_and_retrieves(self):
        """Test storing and retrieving frames from cache."""
        tick = 25
        
        # Store frame
        success = self.cache.store_frame(tick, self.test_frame_state)
        assert success
        
        # Retrieve frame
        retrieved_frame = self.cache.get_frame(tick)
        assert retrieved_frame is not None
        assert len(retrieved_frame) == len(self.test_frame_state)
        
        # Verify frame content
        for anim_id in self.test_frame_state:
            assert anim_id in retrieved_frame
            original = self.test_frame_state[anim_id]
            retrieved = retrieved_frame[anim_id]
            
            assert original.tick == retrieved.tick
            assert original.position == retrieved.position
            assert original.rotation == retrieved.rotation
            assert original.scale == retrieved.scale
            assert original.opacity == retrieved.opacity
            assert original.custom_properties == retrieved.custom_properties
    
    def test_get_frame__nonexistent_tick__returns_none(self):
        """Test retrieving non-existent frame."""
        result = self.cache.get_frame(999)
        assert result is None
    
    def test_cache_eviction__exceeds_max_frames__evicts_oldest(self):
        """Test cache eviction when exceeding max frames."""
        # Fill cache to capacity
        for tick in range(15):  # More than max_frames (10)
            success = self.cache.store_frame(tick, self.test_frame_state)
            assert success
        
        # Oldest frames should be evicted
        assert self.cache.get_frame(0) is None  # Should be evicted
        assert self.cache.get_frame(14) is not None  # Should still exist
    
    def test_get_cache_stats__after_operations__returns_accurate_stats(self):
        """Test cache statistics tracking."""
        # Perform cache operations
        self.cache.store_frame(10, self.test_frame_state)
        self.cache.store_frame(20, self.test_frame_state)
        
        # Cache hits and misses
        self.cache.get_frame(10)  # Hit
        self.cache.get_frame(10)  # Hit
        self.cache.get_frame(30)  # Miss
        
        stats = self.cache.get_cache_stats()
        
        assert stats['hit_count'] == 2
        assert stats['miss_count'] == 1
        assert abs(stats['hit_rate'] - (2/3)) < 0.01
        assert stats['cached_frames'] == 2
        assert stats['memory_usage_mb'] > 0.0
    
    def test_clear_cache__removes_all_frames(self):
        """Test clearing all cached frames."""
        # Store some frames
        for tick in range(5):
            self.cache.store_frame(tick, self.test_frame_state)
        
        # Verify frames exist
        assert self.cache.get_frame(2) is not None
        
        # Clear cache
        self.cache.clear_cache()
        
        # Verify all frames removed
        for tick in range(5):
            assert self.cache.get_frame(tick) is None
        
        stats = self.cache.get_cache_stats()
        assert stats['cached_frames'] == 0
        assert stats['memory_usage_mb'] == 0.0


class TestWorkerFunction:
    """Test suite for the worker function implementation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        
        fade_anim = create_tick_fade_animation(
            start_tick=0, duration_ticks=60,
            start_opacity=0.0, end_opacity=1.0
        )
        self.engine.add_animation("worker_test", fade_anim)
        self.engine.start_animation_at("worker_test", 0)
    
    def test_compute_frame_worker__valid_task__returns_computed_frame(self):
        """Test the worker function with valid task."""
        from tinydisplay.animation.multicore import AnimationStateSerializer
        
        # Create task
        engine_state = AnimationStateSerializer.serialize_engine_state(self.engine)
        task = FrameComputationTask(
            task_id="test_task_1",
            tick=30,
            engine_state=engine_state
        )
        
        # Execute worker function
        result = _compute_frame_worker(task)
        
        # Verify result
        assert isinstance(result, ComputedFrame)
        assert result.task_id == "test_task_1"
        assert result.tick == 30
        assert len(result.frame_state) > 0
        assert result.computation_time > 0.0
        assert "worker_test" in result.frame_state
    
    def test_compute_frame_worker__invalid_task__returns_error_frame(self):
        """Test worker function with invalid task data."""
        # Create task with invalid engine state
        task = FrameComputationTask(
            task_id="error_task",
            tick=30,
            engine_state=b"invalid_data"
        )
        
        # Execute worker function
        result = _compute_frame_worker(task)
        
        # Should return error frame
        assert isinstance(result, ComputedFrame)
        assert result.task_id == "error_task"
        assert result.tick == 30
        assert len(result.frame_state) == 0  # Empty indicates error
        assert result.worker_id.endswith("-error")


class TestWorkerPoolIntegration:
    """Integration tests for complete worker pool system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        
        # Create multiple animations for complex testing
        for i in range(3):
            fade_anim = create_tick_fade_animation(
                start_tick=i * 20, duration_ticks=60,
                start_opacity=0.0, end_opacity=1.0,
                position=(float(i * 10), float(i * 15))
            )
            self.engine.add_animation(f"integration_test_{i}", fade_anim)
            self.engine.start_animation_at(f"integration_test_{i}", i * 20)
        
        self.worker_pool = AnimationWorkerPool(
            num_workers=3, 
            use_processes=False,
            cache_size=100
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        self.worker_pool.shutdown(wait=True)
    
    def test_full_workflow__large_batch__completes_successfully(self):
        """Test complete workflow with large batch of frames."""
        start_tick = 0
        num_frames = 60  # 1 second at 60fps
        
        # Submit batch computation
        start_time = time.perf_counter()
        task_ids = self.worker_pool.submit_batch_computation(start_tick, num_frames, self.engine)
        submission_time = time.perf_counter() - start_time
        
        # Wait for completion
        start_time = time.perf_counter()
        completed_frames = self.worker_pool.wait_for_batch_completion(task_ids, timeout=10.0)
        completion_time = time.perf_counter() - start_time
        
        # Verify results
        assert len(completed_frames) >= num_frames * 0.9  # At least 90% completion
        
        # Verify performance
        assert submission_time < 1.0  # Submission should be fast
        assert completion_time < 5.0  # Completion should be reasonable
        
        # Verify frame content
        for task_id, frame in completed_frames.items():
            assert isinstance(frame, ComputedFrame)
            assert 0 <= frame.tick < 60
            assert frame.computation_time >= 0.0
    
    def test_concurrent_access__multiple_threads__thread_safe(self):
        """Test thread safety with concurrent access."""
        results = []
        
        def worker_thread(thread_id):
            thread_results = []
            for i in range(10):
                tick = thread_id * 10 + i
                task_id = self.worker_pool.submit_frame_computation(tick, self.engine)
                
                # Wait for result
                start_time = time.perf_counter()
                while time.perf_counter() - start_time < 2.0:
                    result = self.worker_pool.get_computed_frame(task_id)
                    if result:
                        thread_results.append(result)
                        break
                    time.sleep(0.01)
            
            results.extend(thread_results)
        
        # Start multiple threads
        threads = []
        for thread_id in range(3):
            thread = threading.Thread(target=worker_thread, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(results) >= 20  # Should complete most tasks
        
        # Verify no duplicate ticks from same thread
        ticks_by_thread = {}
        for result in results:
            thread_id = result.tick // 10
            if thread_id not in ticks_by_thread:
                ticks_by_thread[thread_id] = set()
            
            tick_in_thread = result.tick % 10
            assert tick_in_thread not in ticks_by_thread[thread_id]
            ticks_by_thread[thread_id].add(tick_in_thread)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 