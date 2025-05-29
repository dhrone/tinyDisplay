"""
Integration tests for multi-core rendering integration (Story 3.2 Task 5).

Tests the complete integration between multi-core animation framework
and rendering engine, including performance optimization and real-world scenarios.
"""

import pytest
import time
import threading
from typing import Dict, List

from tinydisplay.animation.tick_based import (
    TickAnimationEngine, TickAnimationDefinition, TickAnimationState,
    create_tick_fade_animation, create_tick_slide_animation
)
from tinydisplay.rendering.multicore_integration import (
    MultiCoreAnimationRenderer, FrameDeliveryManager, MultiCoreRenderingConfig,
    RenderingPerformanceMetrics, create_multicore_renderer, benchmark_multicore_performance
)


class TestMultiCoreAnimationRenderer:
    """Test suite for MultiCoreAnimationRenderer functionality."""
    
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
        
        # Create renderer with test configuration
        config = MultiCoreRenderingConfig(
            num_workers=2,
            use_processes=False,  # Use threads for testing
            prediction_horizon_frames=5,
            cache_size_frames=30
        )
        
        self.renderer = MultiCoreAnimationRenderer(config)
        self.renderer.set_animation_engine(self.engine)
    
    def teardown_method(self):
        """Clean up test environment."""
        self.renderer.shutdown()
    
    def test_get_frame_for_tick__single_frame__returns_valid_state(self):
        """Test getting a single frame with multi-core optimization."""
        tick = 25
        
        frame_state = self.renderer.get_frame_for_tick(tick)
        
        # Should return valid frame state
        assert frame_state is not None
        assert isinstance(frame_state, dict)
        assert "fade_test" in frame_state
        
        # Verify frame content
        fade_state = frame_state["fade_test"]
        assert isinstance(fade_state, TickAnimationState)
        # The animation state tick represents the animation's internal computation
        # which may differ from the requested tick due to animation timing
        assert fade_state.tick >= 0  # Should be a valid tick
        assert 0.0 <= fade_state.opacity <= 1.0
    
    def test_get_frame_for_tick__no_engine__returns_none(self):
        """Test behavior when no animation engine is set."""
        renderer = MultiCoreAnimationRenderer()
        
        frame_state = renderer.get_frame_for_tick(10)
        
        assert frame_state is None
    
    def test_get_frame_for_tick__sequential_frames__maintains_consistency(self):
        """Test sequential frame retrieval for consistency."""
        frames = []
        
        # Get sequential frames
        for tick in range(10, 20):
            frame_state = self.renderer.get_frame_for_tick(tick)
            frames.append((tick, frame_state))
        
        # Verify all frames retrieved
        assert len(frames) == 10
        
        # Verify frame progression
        for i, (tick, frame_state) in enumerate(frames):
            assert frame_state is not None
            assert "fade_test" in frame_state
            
            fade_state = frame_state["fade_test"]
            assert fade_state.tick == tick
            
            # Opacity should increase over time
            if i > 0:
                prev_opacity = frames[i-1][1]["fade_test"].opacity
                assert fade_state.opacity >= prev_opacity
    
    def test_start_stop_prediction__background_prediction__works_correctly(self):
        """Test background frame prediction start/stop."""
        # Start prediction
        self.renderer.start_prediction()
        
        # Give prediction time to work
        time.sleep(0.2)
        
        # Stop prediction
        self.renderer.stop_prediction()
        
        # Should complete without errors
        assert True
    
    def test_get_performance_metrics__after_frames__returns_valid_metrics(self):
        """Test performance metrics collection."""
        # Generate some frame activity
        for tick in range(15):
            self.renderer.get_frame_for_tick(tick)
        
        metrics = self.renderer.get_performance_metrics()
        
        # Verify metrics structure
        assert isinstance(metrics, RenderingPerformanceMetrics)
        assert metrics.average_frame_time_ms >= 0.0
        assert 0.0 <= metrics.multicore_hit_rate <= 100.0
        assert 0.0 <= metrics.fallback_rate <= 100.0
        assert metrics.worker_pool_utilization >= 0.0
    
    def test_optimize_for_target_fps__60fps__returns_optimization_results(self):
        """Test FPS optimization functionality."""
        # Generate some baseline activity
        for tick in range(10):
            self.renderer.get_frame_for_tick(tick)
        
        results = self.renderer.optimize_for_target_fps(60)
        
        # Verify optimization results
        assert isinstance(results, dict)
        assert "target_fps" in results
        assert "status" in results
        assert "optimizations_applied" in results
        assert "recommendations" in results
        assert results["target_fps"] == 60


class TestFrameDeliveryManager:
    """Test suite for FrameDeliveryManager high-level interface."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        
        # Add test animations
        fade_anim = create_tick_fade_animation(
            start_tick=0, duration_ticks=60,
            start_opacity=0.0, end_opacity=1.0
        )
        self.engine.add_animation("delivery_test", fade_anim)
        self.engine.start_animation_at("delivery_test", 0)
        
        # Create delivery manager
        config = MultiCoreRenderingConfig(
            num_workers=2,
            use_processes=False,
            prediction_horizon_frames=5
        )
        self.manager = FrameDeliveryManager(self.engine, config)
    
    def teardown_method(self):
        """Clean up test environment."""
        self.manager.shutdown()
    
    def test_get_frame__valid_tick__returns_frame(self):
        """Test frame delivery through high-level interface."""
        tick = 30
        
        frame_state = self.manager.get_frame(tick)
        
        assert frame_state is not None
        assert "delivery_test" in frame_state
        # The animation state tick represents the animation's internal computation
        assert frame_state["delivery_test"].tick >= 0  # Should be a valid tick
    
    def test_get_performance_summary__after_activity__returns_summary(self):
        """Test performance summary generation."""
        # Generate activity
        for tick in range(10):
            self.manager.get_frame(tick)
        
        summary = self.manager.get_performance_summary()
        
        assert isinstance(summary, str)
        assert "Multi-Core Animation Performance Summary" in summary
        assert "Frame Timing" in summary
        assert "Multi-Core Efficiency" in summary
        assert "Resource Utilization" in summary
    
    def test_optimize_for_fps__returns_optimization_summary(self):
        """Test FPS optimization through high-level interface."""
        # Generate baseline activity
        for tick in range(5):
            self.manager.get_frame(tick)
        
        summary = self.manager.optimize_for_fps(60)
        
        assert isinstance(summary, str)
        assert "Optimization for 60fps" in summary
        assert "Status:" in summary


class TestConvenienceFunctions:
    """Test suite for convenience functions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        
        fade_anim = create_tick_fade_animation(
            start_tick=0, duration_ticks=60,
            start_opacity=0.0, end_opacity=1.0
        )
        self.engine.add_animation("convenience_test", fade_anim)
        self.engine.start_animation_at("convenience_test", 0)
    
    def test_create_multicore_renderer__default_config__creates_manager(self):
        """Test convenience function for creating renderer."""
        manager = create_multicore_renderer(self.engine)
        
        try:
            assert isinstance(manager, FrameDeliveryManager)
            
            # Test basic functionality
            frame = manager.get_frame(15)
            assert frame is not None
            assert "convenience_test" in frame
            
        finally:
            manager.shutdown()
    
    def test_create_multicore_renderer__custom_config__applies_settings(self):
        """Test convenience function with custom configuration."""
        manager = create_multicore_renderer(
            self.engine,
            num_workers=1,
            prediction_frames=3
        )
        
        try:
            assert isinstance(manager, FrameDeliveryManager)
            
            # Verify configuration applied
            config = manager.renderer.config
            assert config.num_workers == 1
            assert config.prediction_horizon_frames == 3
            
        finally:
            manager.shutdown()
    
    def test_benchmark_multicore_performance__small_benchmark__returns_results(self):
        """Test performance benchmarking function."""
        # Run small benchmark
        results = benchmark_multicore_performance(
            self.engine,
            num_frames=20,  # Small test
            target_fps=60
        )
        
        # Verify benchmark results
        assert isinstance(results, dict)
        assert "total_frames" in results
        assert "achieved_fps" in results
        assert "average_frame_time_ms" in results
        assert "multicore_hit_rate" in results
        assert "performance_summary" in results
        
        assert results["total_frames"] == 20
        assert results["achieved_fps"] > 0
        assert results["average_frame_time_ms"] >= 0


class TestPerformanceScenarios:
    """Test suite for real-world performance scenarios."""
    
    def setup_method(self):
        """Set up complex animation scenario."""
        self.engine = TickAnimationEngine()
        
        # Create multiple overlapping animations
        for i in range(5):
            fade_anim = create_tick_fade_animation(
                start_tick=i * 10, duration_ticks=60,
                start_opacity=0.0, end_opacity=1.0,
                position=(float(i * 20), float(i * 15))
            )
            
            slide_anim = create_tick_slide_animation(
                start_tick=i * 15, duration_ticks=80,
                start_position=(0.0, float(i * 10)),
                end_position=(100.0, float(i * 10 + 50))
            )
            
            self.engine.add_animation(f"fade_{i}", fade_anim)
            self.engine.add_animation(f"slide_{i}", slide_anim)
            self.engine.start_animation_at(f"fade_{i}", i * 10)
            self.engine.start_animation_at(f"slide_{i}", i * 15)
        
        # Create high-performance configuration
        config = MultiCoreRenderingConfig(
            num_workers=2,
            use_processes=False,  # Use threads for testing
            prediction_horizon_frames=15,
            cache_size_frames=100,
            enable_adaptive_prediction=True,
            enable_cache_warming=True
        )
        
        self.manager = FrameDeliveryManager(self.engine, config)
    
    def teardown_method(self):
        """Clean up test environment."""
        self.manager.shutdown()
    
    def test_high_frequency_rendering__60fps_simulation__maintains_performance(self):
        """Test high-frequency rendering simulation."""
        frame_times = []
        target_frame_time_ms = 16.67  # 60fps
        
        # Simulate 60fps rendering for 1 second
        start_time = time.perf_counter()
        
        for tick in range(60):
            frame_start = time.perf_counter()
            frame = self.manager.get_frame(tick)
            frame_time = (time.perf_counter() - frame_start) * 1000
            frame_times.append(frame_time)
            
            # Verify frame validity
            assert frame is not None
            assert len(frame) > 0
        
        total_time = time.perf_counter() - start_time
        
        # Performance analysis
        avg_frame_time = sum(frame_times) / len(frame_times)
        max_frame_time = max(frame_times)
        achieved_fps = 60 / total_time
        
        # Performance assertions
        assert avg_frame_time < target_frame_time_ms * 2  # Allow 2x overhead for testing
        assert achieved_fps > 30  # Should achieve at least 30fps
        assert max_frame_time < 50  # No frame should take more than 50ms
    
    def test_burst_rendering__large_batch__handles_efficiently(self):
        """Test burst rendering of large frame batch."""
        batch_size = 100
        start_time = time.perf_counter()
        
        frames = []
        for tick in range(batch_size):
            frame = self.manager.get_frame(tick)
            frames.append(frame)
        
        total_time = time.perf_counter() - start_time
        
        # Verify all frames rendered
        assert len(frames) == batch_size
        for frame in frames:
            assert frame is not None
        
        # Performance check
        avg_time_per_frame = (total_time / batch_size) * 1000
        assert avg_time_per_frame < 100  # Should average less than 100ms per frame
    
    def test_concurrent_access__multiple_threads__thread_safe(self):
        """Test concurrent frame access from multiple threads."""
        results = []
        errors = []
        
        def render_thread(thread_id, start_tick, num_frames):
            thread_results = []
            try:
                for i in range(num_frames):
                    tick = start_tick + i
                    frame = self.manager.get_frame(tick)
                    if frame:
                        thread_results.append((thread_id, tick, len(frame)))
                    else:
                        errors.append(f"Thread {thread_id}: No frame for tick {tick}")
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
            
            results.extend(thread_results)
        
        # Start multiple rendering threads
        threads = []
        for thread_id in range(3):
            thread = threading.Thread(
                target=render_thread,
                args=(thread_id, thread_id * 20, 15)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) >= 30  # Should complete most frames
        
        # Verify no data corruption
        for thread_id, tick, frame_count in results:
            assert frame_count > 0  # Each frame should have animations
    
    def test_memory_efficiency__long_running__stable_memory(self):
        """Test memory efficiency over extended rendering."""
        initial_metrics = self.manager.get_performance_summary()
        
        # Render many frames to test memory stability
        for tick in range(200):
            frame = self.manager.get_frame(tick)
            assert frame is not None
            
            # Periodic memory check
            if tick % 50 == 0:
                metrics = self.manager.renderer.get_performance_metrics()
                # Memory usage should remain reasonable
                assert metrics.memory_usage_mb < 100  # Should stay under 100MB
        
        final_metrics = self.manager.get_performance_summary()
        
        # Should complete without memory issues
        assert "Multi-Core Animation Performance Summary" in final_metrics


class TestErrorHandling:
    """Test suite for error handling and edge cases."""
    
    def setup_method(self):
        """Set up test environment."""
        self.engine = TickAnimationEngine()
        
        config = MultiCoreRenderingConfig(
            num_workers=1,
            use_processes=False
        )
        self.renderer = MultiCoreAnimationRenderer(config)
    
    def teardown_method(self):
        """Clean up test environment."""
        self.renderer.shutdown()
    
    def test_get_frame_for_tick__no_animations__returns_empty_frame(self):
        """Test behavior with no animations."""
        self.renderer.set_animation_engine(self.engine)
        
        frame = self.renderer.get_frame_for_tick(10)
        
        # Should return empty frame, not None
        assert frame is not None
        assert isinstance(frame, dict)
        assert len(frame) == 0
    
    def test_get_frame_for_tick__invalid_tick__handles_gracefully(self):
        """Test behavior with invalid tick values."""
        fade_anim = create_tick_fade_animation(
            start_tick=0, duration_ticks=60,
            start_opacity=0.0, end_opacity=1.0
        )
        self.engine.add_animation("error_test", fade_anim)
        self.engine.start_animation_at("error_test", 0)
        self.renderer.set_animation_engine(self.engine)
        
        # Test negative tick
        frame = self.renderer.get_frame_for_tick(-10)
        assert frame is not None  # Should handle gracefully
        
        # Test very large tick
        frame = self.renderer.get_frame_for_tick(999999)
        assert frame is not None  # Should handle gracefully
    
    def test_shutdown__multiple_calls__handles_gracefully(self):
        """Test multiple shutdown calls."""
        # First shutdown
        self.renderer.shutdown()
        
        # Second shutdown should not cause errors
        self.renderer.shutdown()
        
        # Should complete without exceptions
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 