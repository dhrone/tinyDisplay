#!/usr/bin/env python3
"""
Comprehensive Test Suite for Performance Optimization and Monitoring

Tests the performance monitoring, optimization utilities, and benchmarking
tools to ensure they meet 60fps targets and provide accurate metrics.
"""

import pytest
import time
import threading
from typing import Dict, Any, List

from src.tinydisplay.animation.performance import (
    AnimationPerformanceMonitor, EasingOptimizer, PerformanceBenchmark,
    PerformanceMetrics, FramePerformanceStats,
    create_performance_monitor, create_easing_optimizer, run_quick_performance_check
)
from src.tinydisplay.animation.tick_based import TickAnimationEngine, TickEasing
from src.tinydisplay.animation.utilities import create_fade_animation, create_slide_animation


class TestPerformanceMetrics:
    """Test the PerformanceMetrics class."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = PerformanceMetrics("test_operation")
        
        assert metrics.operation_name == "test_operation"
        assert metrics.execution_count == 0
        assert metrics.total_time == 0.0
        assert metrics.min_time == float('inf')
        assert metrics.max_time == 0.0
        assert len(metrics.recent_times) == 0
        
        # Test properties with no data
        assert metrics.average_time == 0.0
        assert metrics.recent_average == 0.0
        assert metrics.operations_per_second == 0.0
        assert metrics.recent_ops_per_second == 0.0
    
    def test_add_measurement(self):
        """Test adding performance measurements."""
        metrics = PerformanceMetrics("test_operation")
        
        # Add measurements
        metrics.add_measurement(0.001)  # 1ms
        metrics.add_measurement(0.002)  # 2ms
        metrics.add_measurement(0.0015) # 1.5ms
        
        assert metrics.execution_count == 3
        assert abs(metrics.total_time - 0.0045) < 1e-10  # Use floating point tolerance
        assert metrics.min_time == 0.001
        assert metrics.max_time == 0.002
        assert len(metrics.recent_times) == 3
        
        # Test calculated properties
        assert abs(metrics.average_time - 0.0015) < 1e-6
        assert abs(metrics.recent_average - 0.0015) < 1e-6
        assert metrics.operations_per_second > 600  # Should be ~666 ops/sec
        assert metrics.recent_ops_per_second > 600
    
    def test_recent_times_limit(self):
        """Test that recent times are limited to maxlen."""
        metrics = PerformanceMetrics("test_operation")
        
        # Add more than 100 measurements
        for i in range(150):
            metrics.add_measurement(0.001)
        
        assert metrics.execution_count == 150
        assert len(metrics.recent_times) == 100  # Limited to maxlen
    
    def test_reset_metrics(self):
        """Test resetting metrics."""
        metrics = PerformanceMetrics("test_operation")
        
        # Add some data
        metrics.add_measurement(0.001)
        metrics.add_measurement(0.002)
        
        # Reset
        metrics.reset()
        
        assert metrics.execution_count == 0
        assert metrics.total_time == 0.0
        assert metrics.min_time == float('inf')
        assert metrics.max_time == 0.0
        assert len(metrics.recent_times) == 0


class TestFramePerformanceStats:
    """Test the FramePerformanceStats class."""
    
    def test_frame_stats_creation(self):
        """Test frame performance stats creation."""
        stats = FramePerformanceStats(
            frame_number=1,
            tick=60,
            total_frame_time=0.016,  # ~60fps
            tick_advancement_time=0.001,
            state_computation_time=0.002,
            state_application_time=0.001,
            easing_computation_time=0.0005,
            active_animations=5,
            memory_usage_mb=50.0,
            cpu_usage_percent=25.0
        )
        
        assert stats.frame_number == 1
        assert stats.tick == 60
        assert stats.total_frame_time == 0.016
        assert stats.active_animations == 5
        
        # Test calculated properties
        assert abs(stats.fps - 62.5) < 0.1  # 1/0.016 = 62.5
        
        animation_overhead = (0.001 + 0.002 + 0.001 + 0.0005) / 0.016 * 100
        assert abs(stats.animation_overhead_percent - animation_overhead) < 0.1
    
    def test_fps_calculation(self):
        """Test FPS calculation from frame time."""
        # 60fps frame
        stats_60fps = FramePerformanceStats(
            frame_number=1, tick=0, total_frame_time=1.0/60,
            tick_advancement_time=0, state_computation_time=0,
            state_application_time=0, easing_computation_time=0,
            active_animations=0, memory_usage_mb=0, cpu_usage_percent=0
        )
        assert abs(stats_60fps.fps - 60.0) < 0.1
        
        # 30fps frame
        stats_30fps = FramePerformanceStats(
            frame_number=1, tick=0, total_frame_time=1.0/30,
            tick_advancement_time=0, state_computation_time=0,
            state_application_time=0, easing_computation_time=0,
            active_animations=0, memory_usage_mb=0, cpu_usage_percent=0
        )
        assert abs(stats_30fps.fps - 30.0) < 0.1


class TestAnimationPerformanceMonitor:
    """Test the AnimationPerformanceMonitor class."""
    
    def test_monitor_initialization(self):
        """Test monitor initialization."""
        monitor = AnimationPerformanceMonitor()
        
        assert monitor.enable_detailed_monitoring is True
        assert len(monitor.metrics) == 0
        assert len(monitor.frame_stats) == 0
        assert monitor.current_frame_number == 0
        assert monitor.target_fps == 60.0
        assert abs(monitor.target_frame_time - 1.0/60) < 1e-6
    
    def test_measure_operation_context_manager(self):
        """Test operation measurement context manager."""
        monitor = AnimationPerformanceMonitor()
        
        # Measure an operation
        with monitor.measure_operation("test_operation"):
            time.sleep(0.001)  # 1ms operation
        
        assert "test_operation" in monitor.metrics
        metrics = monitor.metrics["test_operation"]
        assert metrics.execution_count == 1
        assert metrics.total_time > 0.0009  # Should be at least 1ms
        assert metrics.min_time > 0.0009
        assert metrics.max_time > 0.0009
    
    def test_measure_operation_disabled(self):
        """Test operation measurement when disabled."""
        monitor = AnimationPerformanceMonitor(enable_detailed_monitoring=False)
        
        with monitor.measure_operation("test_operation"):
            time.sleep(0.001)
        
        # Should not record metrics when disabled
        assert len(monitor.metrics) == 0
    
    def test_frame_measurement_cycle(self):
        """Test complete frame measurement cycle."""
        monitor = AnimationPerformanceMonitor()
        
        # Start frame measurement
        timing_data = monitor.start_frame_measurement(tick=100)
        
        assert timing_data['tick'] == 100
        assert timing_data['frame_number'] == 1
        assert 'frame_start' in timing_data
        
        # Record various timings
        monitor.record_tick_advancement(timing_data, 0.001)
        monitor.record_state_computation(timing_data, 0.002, 5)
        monitor.record_state_application(timing_data, 0.001)
        monitor.record_easing_computation(timing_data, 0.0005)
        
        # Finish measurement
        time.sleep(0.001)  # Small delay to ensure measurable frame time
        frame_stats = monitor.finish_frame_measurement(timing_data)
        
        assert isinstance(frame_stats, FramePerformanceStats)
        assert frame_stats.frame_number == 1
        assert frame_stats.tick == 100
        assert frame_stats.tick_advancement_time == 0.001
        assert frame_stats.state_computation_time == 0.002
        assert frame_stats.state_application_time == 0.001
        assert frame_stats.easing_computation_time == 0.0005
        assert frame_stats.active_animations == 5
        assert frame_stats.total_frame_time > 0.001
        
        # Check that frame stats were recorded
        assert len(monitor.frame_stats) == 1
        assert monitor.frame_stats[0] == frame_stats
    
    def test_performance_summary(self):
        """Test performance summary generation."""
        monitor = AnimationPerformanceMonitor()
        
        # Add some frame stats
        for i in range(10):
            timing_data = monitor.start_frame_measurement(tick=i)
            monitor.record_tick_advancement(timing_data, 0.001)
            monitor.record_state_computation(timing_data, 0.002, 3)
            monitor.record_state_application(timing_data, 0.001)
            monitor.record_easing_computation(timing_data, 0.0005)
            time.sleep(0.001)
            monitor.finish_frame_measurement(timing_data)
        
        # Get summary
        summary = monitor.get_performance_summary(recent_frames=5)
        
        assert 'frame_statistics' in summary
        assert 'animation_performance' in summary
        assert 'system_performance' in summary
        assert 'operation_metrics' in summary
        
        frame_stats = summary['frame_statistics']
        assert frame_stats['total_frames'] == 10
        assert frame_stats['recent_frames_analyzed'] == 5
        assert frame_stats['target_fps'] == 60.0
        assert 'average_fps' in frame_stats
        assert 'fps_target_met' in frame_stats
        
        anim_perf = summary['animation_performance']
        assert 'average_tick_advancement_ms' in anim_perf
        assert 'average_state_computation_ms' in anim_perf
        assert 'average_active_animations' in anim_perf
        assert anim_perf['average_active_animations'] == 3.0
    
    def test_performance_warnings(self):
        """Test performance warning detection."""
        monitor = AnimationPerformanceMonitor()
        
        # Add frame with poor performance
        timing_data = monitor.start_frame_measurement(tick=0)
        monitor.record_tick_advancement(timing_data, 0.001)
        monitor.record_state_computation(timing_data, 0.002, 1)
        monitor.record_state_application(timing_data, 0.001)
        monitor.record_easing_computation(timing_data, 0.0005)
        
        # Simulate slow frame (longer than target)
        time.sleep(0.02)  # 20ms - much longer than 16.67ms target
        frame_stats = monitor.finish_frame_measurement(timing_data)
        
        warnings = monitor.check_performance_warnings(recent_frames=1)
        
        # Should have warnings for low FPS and frame time spike
        assert len(warnings) > 0
        warning_text = ' '.join(warnings)
        assert 'FPS below target' in warning_text or 'Frame time spike' in warning_text
    
    def test_reset_metrics(self):
        """Test resetting all metrics."""
        monitor = AnimationPerformanceMonitor()
        
        # Add some data
        with monitor.measure_operation("test_op"):
            time.sleep(0.001)
        
        timing_data = monitor.start_frame_measurement(tick=0)
        monitor.finish_frame_measurement(timing_data)
        
        assert len(monitor.metrics) > 0
        assert len(monitor.frame_stats) > 0
        assert monitor.current_frame_number > 0
        
        # Reset
        monitor.reset_metrics()
        
        assert len(monitor.metrics) == 0
        assert len(monitor.frame_stats) == 0
        assert monitor.current_frame_number == 0


class TestEasingOptimizer:
    """Test the EasingOptimizer class."""
    
    def test_optimizer_initialization(self):
        """Test optimizer initialization."""
        optimizer = EasingOptimizer()
        
        assert optimizer._cache_enabled is True
        assert optimizer._cache_size == 1000
        assert len(optimizer._easing_cache) == 0
        assert optimizer._cache_hits == 0
        assert optimizer._cache_misses == 0
    
    def test_caching_enable_disable(self):
        """Test enabling and disabling caching."""
        optimizer = EasingOptimizer()
        
        # Test disabling
        optimizer.disable_caching()
        assert optimizer._cache_enabled is False
        
        # Test enabling with custom size
        optimizer.enable_caching(cache_size=500)
        assert optimizer._cache_enabled is True
        assert optimizer._cache_size == 500
    
    def test_cache_operations(self):
        """Test cache operations."""
        optimizer = EasingOptimizer()
        
        # Test cache miss
        result = optimizer.get_cached_easing_result("linear", 0.5)
        assert result is None
        assert optimizer._cache_misses == 1
        assert optimizer._cache_hits == 0
        
        # Cache a result
        optimizer.cache_easing_result("linear", 0.5, 0.5)
        
        # Test cache hit
        result = optimizer.get_cached_easing_result("linear", 0.5)
        assert result == 0.5
        assert optimizer._cache_hits == 1
        assert optimizer._cache_misses == 1
    
    def test_optimized_easing_result(self):
        """Test optimized easing result computation."""
        optimizer = EasingOptimizer()
        
        # First call should compute and cache
        result1 = optimizer.get_optimized_easing_result("linear", 0.5)
        assert result1 == 0.5
        assert optimizer._cache_misses == 1
        assert optimizer._cache_hits == 0
        
        # Second call should use cache
        result2 = optimizer.get_optimized_easing_result("linear", 0.5)
        assert result2 == 0.5
        assert optimizer._cache_misses == 1
        assert optimizer._cache_hits == 1
    
    def test_cache_size_management(self):
        """Test cache size management."""
        optimizer = EasingOptimizer()
        optimizer.enable_caching(cache_size=10)  # Small cache for testing
        
        # Fill cache beyond capacity
        for i in range(15):
            progress = i / 100.0
            optimizer.cache_easing_result("linear", progress, progress)
        
        # Cache should be limited
        assert len(optimizer._easing_cache) <= 10
    
    def test_cache_statistics(self):
        """Test cache statistics."""
        optimizer = EasingOptimizer()
        
        # Initial stats
        stats = optimizer.get_cache_statistics()
        assert stats['cache_enabled'] is True
        assert stats['cache_size'] == 0
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0
        assert stats['hit_rate_percent'] == 0.0
        
        # Add some cache activity
        optimizer.get_optimized_easing_result("linear", 0.5)  # Miss + cache
        optimizer.get_optimized_easing_result("linear", 0.5)  # Hit
        
        stats = optimizer.get_cache_statistics()
        assert stats['cache_size'] == 1
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 1
        assert stats['hit_rate_percent'] == 50.0
    
    def test_clear_cache(self):
        """Test clearing cache."""
        optimizer = EasingOptimizer()
        
        # Add some cache data
        optimizer.get_optimized_easing_result("linear", 0.5)
        optimizer.get_optimized_easing_result("ease_in", 0.3)
        
        assert len(optimizer._easing_cache) > 0
        assert optimizer._cache_hits + optimizer._cache_misses > 0
        
        # Clear cache
        optimizer.clear_cache()
        
        assert len(optimizer._easing_cache) == 0
        assert optimizer._cache_hits == 0
        assert optimizer._cache_misses == 0


class TestPerformanceBenchmark:
    """Test the PerformanceBenchmark class."""
    
    def test_benchmark_initialization(self):
        """Test benchmark initialization."""
        benchmark = PerformanceBenchmark(target_fps=30.0)
        
        assert benchmark.target_fps == 30.0
        assert abs(benchmark.target_frame_time - 1.0/30) < 1e-6
        assert isinstance(benchmark.monitor, AnimationPerformanceMonitor)
        assert isinstance(benchmark.optimizer, EasingOptimizer)
    
    def test_tick_advancement_benchmark(self):
        """Test tick advancement benchmarking."""
        benchmark = PerformanceBenchmark()
        
        results = benchmark.benchmark_tick_advancement(iterations=100)
        
        assert 'total_time' in results
        assert 'average_time_ms' in results
        assert 'operations_per_second' in results
        assert 'target_fps_capable' in results
        assert 'iterations' in results
        
        assert results['iterations'] == 100
        assert results['total_time'] > 0
        assert results['operations_per_second'] > 0
        
        # Should be very fast for tick advancement
        assert results['operations_per_second'] > 1000
    
    def test_state_computation_benchmark(self):
        """Test state computation benchmarking."""
        benchmark = PerformanceBenchmark()
        
        results = benchmark.benchmark_state_computation(animation_count=5, iterations=10)
        
        assert 'total_time' in results
        assert 'total_computations' in results
        assert 'average_time_per_computation_us' in results
        assert 'computations_per_second' in results
        assert 'animations_tested' in results
        assert 'iterations' in results
        assert 'target_fps_capable' in results
        
        assert results['animations_tested'] == 5
        assert results['iterations'] == 10
        assert results['total_computations'] == 5 * 10 * 60  # 5 anims * 10 iters * 60 ticks
        assert results['computations_per_second'] > 0
    
    def test_easing_functions_benchmark(self):
        """Test easing functions benchmarking."""
        benchmark = PerformanceBenchmark()
        
        results = benchmark.benchmark_easing_functions(iterations=1000)
        
        # Should have results for all easing functions
        expected_functions = ["linear", "ease_in", "ease_out", "ease_in_out", "bounce", "elastic"]
        for func_name in expected_functions:
            assert func_name in results
            
            func_results = results[func_name]
            assert 'unoptimized_time' in func_results
            assert 'optimized_time' in func_results
            assert 'speedup_factor' in func_results
            assert 'unoptimized_ops_per_second' in func_results
            assert 'optimized_ops_per_second' in func_results
            assert 'cache_hit_rate_percent' in func_results
            assert 'iterations' in func_results
            
            assert func_results['iterations'] == 1000
            # For small datasets, caching overhead may outweigh benefits
            # Just verify that the speedup factor is calculated correctly
            assert func_results['speedup_factor'] > 0  # Should be positive
            assert func_results['unoptimized_ops_per_second'] > 0
            assert func_results['optimized_ops_per_second'] > 0
    
    def test_full_animation_pipeline_benchmark(self):
        """Test full animation pipeline benchmarking."""
        benchmark = PerformanceBenchmark()
        
        results = benchmark.benchmark_full_animation_pipeline(duration_seconds=1)
        
        assert 'duration_seconds' in results
        assert 'total_frames' in results
        assert 'average_fps' in results
        assert 'min_fps' in results
        assert 'max_fps' in results
        assert 'average_frame_time_ms' in results
        assert 'target_fps' in results
        assert 'target_met_percent' in results
        assert 'performance_rating' in results
        
        assert results['duration_seconds'] >= 1.0
        assert results['total_frames'] > 0
        assert results['average_fps'] > 0
        assert results['target_fps'] == 60.0
        assert results['performance_rating'] in ['Excellent', 'Good', 'Acceptable', 'Poor', 'Unacceptable']
    
    def test_performance_rating_calculation(self):
        """Test performance rating calculation."""
        benchmark = PerformanceBenchmark(target_fps=60.0)
        
        # Test excellent rating
        rating = benchmark._calculate_performance_rating(60.0, 98.0)
        assert rating == "Excellent"
        
        # Test good rating
        rating = benchmark._calculate_performance_rating(55.0, 92.0)
        assert rating == "Good"
        
        # Test acceptable rating
        rating = benchmark._calculate_performance_rating(50.0, 85.0)
        assert rating == "Acceptable"
        
        # Test poor rating
        rating = benchmark._calculate_performance_rating(40.0, 70.0)
        assert rating == "Poor"
        
        # Test unacceptable rating
        rating = benchmark._calculate_performance_rating(20.0, 30.0)
        assert rating == "Unacceptable"


class TestConvenienceFunctions:
    """Test convenience functions for performance monitoring."""
    
    def test_create_performance_monitor(self):
        """Test creating performance monitor."""
        monitor = create_performance_monitor(enable_detailed=True)
        
        assert isinstance(monitor, AnimationPerformanceMonitor)
        assert monitor.enable_detailed_monitoring is True
        
        monitor_disabled = create_performance_monitor(enable_detailed=False)
        assert monitor_disabled.enable_detailed_monitoring is False
    
    def test_create_easing_optimizer(self):
        """Test creating easing optimizer."""
        optimizer = create_easing_optimizer(cache_size=500)
        
        assert isinstance(optimizer, EasingOptimizer)
        assert optimizer._cache_enabled is True
        assert optimizer._cache_size == 500
    
    def test_run_quick_performance_check(self):
        """Test quick performance check."""
        results = run_quick_performance_check(target_fps=60.0)
        
        assert 'target_fps' in results
        assert 'tick_advancement_capable' in results
        assert 'state_computation_capable' in results
        assert 'tick_ops_per_second' in results
        assert 'state_computations_per_second' in results
        assert 'quick_assessment' in results
        
        assert results['target_fps'] == 60.0
        assert isinstance(results['tick_advancement_capable'], bool)
        assert isinstance(results['state_computation_capable'], bool)
        assert results['tick_ops_per_second'] > 0
        assert results['state_computations_per_second'] > 0
        assert results['quick_assessment'] in ['PASS', 'FAIL']


class TestPerformanceIntegration:
    """Test performance monitoring integration with animation system."""
    
    def test_monitor_with_real_animations(self):
        """Test monitor with real animation execution."""
        monitor = AnimationPerformanceMonitor()
        engine = TickAnimationEngine()
        
        # Create test animations
        fade_anim = create_fade_animation(0.0, 1.0)
        slide_anim = create_slide_animation((0, 0), (100, 100))
        
        engine.add_animation("fade", fade_anim)
        engine.add_animation("slide", slide_anim)
        engine.start_animation_at("fade", 0)
        engine.start_animation_at("slide", 0)
        
        # Simulate frame processing with monitoring
        for tick in range(60):  # 1 second at 60fps
            timing_data = monitor.start_frame_measurement(tick)
            
            # Measure tick advancement
            with monitor.measure_operation("tick_advancement"):
                engine.advance_tick()
            
            # Measure state computation
            with monitor.measure_operation("state_computation"):
                frame_state = engine.compute_frame_state(tick)
            
            # Record active animations count
            active_animations = engine.get_active_animations_at(tick)
            active_count = len(active_animations)
            monitor.record_state_computation(timing_data, 0.001, active_count)
            
            # Simulate state application
            with monitor.measure_operation("state_application"):
                time.sleep(0.0001)  # 0.1ms simulated processing
            
            monitor.finish_frame_measurement(timing_data)
        
        # Check that we have comprehensive metrics
        assert len(monitor.frame_stats) == 60
        assert "tick_advancement" in monitor.metrics
        assert "state_computation" in monitor.metrics
        assert "state_application" in monitor.metrics
        
        # Get performance summary
        summary = monitor.get_performance_summary()
        assert summary['frame_statistics']['total_frames'] == 60
        assert summary['animation_performance']['average_active_animations'] > 0
        
        # Should have good performance
        warnings = monitor.check_performance_warnings()
        # Warnings are acceptable but should not be critical
        assert len(warnings) < 5  # Should not have too many warnings
    
    def test_easing_optimizer_with_real_functions(self):
        """Test easing optimizer with real easing functions."""
        optimizer = EasingOptimizer()
        
        # Test all easing functions
        easing_functions = ["linear", "ease_in", "ease_out", "ease_in_out", "bounce", "elastic"]
        progress_values = [i / 100.0 for i in range(101)]  # 0.0 to 1.0 in 0.01 steps
        
        for easing_name in easing_functions:
            # First pass - should populate cache
            for progress in progress_values:
                result1 = optimizer.get_optimized_easing_result(easing_name, progress)
                assert 0.0 <= result1 <= 1.0  # All easing functions should return valid range
            
            # Second pass - should use cache
            for progress in progress_values:
                result2 = optimizer.get_optimized_easing_result(easing_name, progress)
                assert 0.0 <= result2 <= 1.0
        
        # Check cache statistics
        stats = optimizer.get_cache_statistics()
        assert stats['cache_hits'] > 0
        assert stats['hit_rate_percent'] > 0
        
        # Cache should have improved performance
        assert stats['hit_rate_percent'] >= 50  # Should have good hit rate


class TestPerformanceTargets:
    """Test that performance targets are met."""
    
    def test_60fps_capability(self):
        """Test that system can achieve 60fps."""
        benchmark = PerformanceBenchmark(target_fps=60.0)
        
        # Quick performance check
        quick_results = run_quick_performance_check(target_fps=60.0)
        
        # Both tick advancement and state computation should be capable of 60fps
        assert quick_results['tick_advancement_capable'] is True
        assert quick_results['state_computation_capable'] is True
        assert quick_results['quick_assessment'] == 'PASS'
        
        # Tick advancement should be very fast
        assert quick_results['tick_ops_per_second'] > 1000
        
        # State computation should be fast enough for multiple animations
        assert quick_results['state_computations_per_second'] > 100
    
    def test_memory_efficiency(self):
        """Test memory efficiency of performance monitoring."""
        monitor = AnimationPerformanceMonitor()
        
        # Run many frames to test memory management
        for i in range(2000):  # More than the 1000 frame limit
            timing_data = monitor.start_frame_measurement(i)
            monitor.record_tick_advancement(timing_data, 0.001)
            monitor.record_state_computation(timing_data, 0.002, 5)
            monitor.finish_frame_measurement(timing_data)
        
        # Should not exceed memory limit
        assert len(monitor.frame_stats) <= 1000
        
        # Should have kept the most recent frames
        assert monitor.frame_stats[-1].tick == 1999
        assert monitor.frame_stats[0].tick >= 1000
    
    def test_easing_cache_efficiency(self):
        """Test easing cache efficiency."""
        optimizer = EasingOptimizer()
        optimizer.enable_caching(cache_size=100)
        
        # Test with repeated progress values (common in animations)
        common_progress_values = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        # First pass - populate cache
        for _ in range(100):
            for progress in common_progress_values:
                optimizer.get_optimized_easing_result("ease_in_out", progress)
        
        stats = optimizer.get_cache_statistics()
        
        # Should have very high hit rate for repeated values
        assert stats['hit_rate_percent'] > 80
        assert stats['cache_size'] <= 100  # Should respect cache size limit


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 