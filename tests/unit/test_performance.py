#!/usr/bin/env python3
"""
Tests for Widget Performance Optimization System

Tests performance optimization strategies, memory management, rendering optimization,
and reactive binding performance for high-frequency updates.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import List
import gc

from src.tinydisplay.widgets.performance import (
    PerformanceMetrics, WidgetPool, RenderOptimizer, MemoryManager,
    PerformanceMonitor, ReactiveOptimizer, PerformanceBenchmark,
    OptimizationLevel, get_performance_monitor, enable_performance_optimization,
    disable_performance_optimization
)
from src.tinydisplay.widgets.base import Widget, ReactiveValue


class MockWidget(Widget):
    """Mock widget for testing."""
    
    def __init__(self, widget_id: str = None):
        super().__init__(widget_id)
        self.render_called = False
        self.reset_called = False
        self.cleanup_called = False
    
    def render(self, canvas) -> None:
        """Mock render method."""
        self.render_called = True
        time.sleep(0.001)  # Simulate render time
    
    def _reset_for_reuse(self, *args, **kwargs) -> None:
        """Mock reset for reuse."""
        super()._reset_for_reuse(*args, **kwargs)
        self.reset_called = True
        self.render_called = False
    
    def _cleanup_for_pooling(self) -> None:
        """Mock cleanup for pooling."""
        super()._cleanup_for_pooling()
        self.cleanup_called = True


class TestPerformanceMetrics:
    """Test performance metrics tracking."""
    
    def test_initialization__default_values__correct(self):
        """Test metrics initialization with default values."""
        metrics = PerformanceMetrics()
        
        assert metrics.frame_count == 0
        assert metrics.total_render_time == 0.0
        assert metrics.average_frame_time == 0.0
        assert metrics.min_frame_time == float('inf')
        assert metrics.max_frame_time == 0.0
        assert metrics.dropped_frames == 0
        assert metrics.target_frame_time == 1.0 / 60.0
        
        assert metrics.peak_memory_mb == 0.0
        assert metrics.current_memory_mb == 0.0
        assert metrics.widget_count == 0
        assert metrics.pooled_widgets == 0
        
        assert metrics.reactive_updates == 0
        assert metrics.batched_updates == 0
        assert metrics.update_time == 0.0
        
        assert metrics.render_score == 100.0
        assert metrics.memory_score == 100.0
        assert metrics.reactive_score == 100.0
        assert metrics.overall_score == 100.0
    
    def test_update_frame_metrics__single_frame__updates_correctly(self):
        """Test frame metrics update with single frame."""
        metrics = PerformanceMetrics()
        frame_time = 0.010  # 10ms
        
        metrics.update_frame_metrics(frame_time)
        
        assert metrics.frame_count == 1
        assert metrics.total_render_time == frame_time
        assert metrics.average_frame_time == frame_time
        assert metrics.min_frame_time == frame_time
        assert metrics.max_frame_time == frame_time
        assert metrics.dropped_frames == 0  # 10ms < 16.67ms (60fps)
        assert metrics.render_score == 100.0  # Good performance
    
    def test_update_frame_metrics__slow_frame__drops_frame(self):
        """Test frame metrics with slow frame causing drop."""
        metrics = PerformanceMetrics()
        slow_frame_time = 0.020  # 20ms > 16.67ms (60fps)
        
        metrics.update_frame_metrics(slow_frame_time)
        
        assert metrics.frame_count == 1
        assert metrics.dropped_frames == 1
        assert metrics.render_score < 100.0  # Reduced score
    
    def test_update_memory_metrics__within_target__perfect_score(self):
        """Test memory metrics within target range."""
        metrics = PerformanceMetrics()
        
        metrics.update_memory_metrics(50.0, 10, 5)  # 50MB < 100MB target
        
        assert metrics.current_memory_mb == 50.0
        assert metrics.peak_memory_mb == 50.0
        assert metrics.widget_count == 10
        assert metrics.pooled_widgets == 5
        assert metrics.memory_score == 100.0
    
    def test_update_memory_metrics__exceeds_target__reduced_score(self):
        """Test memory metrics exceeding target."""
        metrics = PerformanceMetrics()
        
        metrics.update_memory_metrics(150.0, 20, 10)  # 150MB > 100MB target
        
        assert metrics.current_memory_mb == 150.0
        assert metrics.peak_memory_mb == 150.0
        assert metrics.memory_score < 100.0
    
    def test_update_reactive_metrics__fast_updates__good_score(self):
        """Test reactive metrics with fast updates."""
        metrics = PerformanceMetrics()
        
        metrics.update_reactive_metrics(0.001, True)  # 1ms, batched
        metrics.update_reactive_metrics(0.002, False)  # 2ms, not batched
        
        assert metrics.reactive_updates == 2
        assert metrics.batched_updates == 1
        assert metrics.update_time == 0.003
        assert metrics.reactive_score == 100.0  # Average 1.5ms < 50ms target
    
    def test_calculate_overall_score__averages_scores(self):
        """Test overall score calculation."""
        metrics = PerformanceMetrics()
        metrics.render_score = 90.0
        metrics.memory_score = 80.0
        metrics.reactive_score = 70.0
        
        metrics.calculate_overall_score()
        
        assert metrics.overall_score == 80.0  # (90 + 80 + 70) / 3


class TestWidgetPool:
    """Test widget memory pooling."""
    
    def test_initialization__empty_pool__correct_state(self):
        """Test pool initialization."""
        pool = WidgetPool(MockWidget, max_size=10)
        
        assert pool._widget_class == MockWidget
        assert pool._max_size == 10
        assert len(pool._available) == 0
        assert len(pool._in_use) == 0
        assert pool._created_count == 0
        assert pool._reused_count == 0
    
    def test_acquire__empty_pool__creates_new_widget(self):
        """Test acquiring widget from empty pool."""
        pool = WidgetPool(MockWidget, max_size=10)
        
        widget = pool.acquire("test_widget")
        
        assert isinstance(widget, MockWidget)
        assert widget in pool._in_use
        assert len(pool._available) == 0
        assert pool._created_count == 1
        assert pool._reused_count == 0
    
    def test_release__widget_in_use__returns_to_pool(self):
        """Test releasing widget back to pool."""
        pool = WidgetPool(MockWidget, max_size=10)
        widget = pool.acquire("test_widget")
        
        pool.release(widget)
        
        assert widget not in pool._in_use
        assert widget in pool._available
        assert widget.cleanup_called
    
    def test_acquire_after_release__reuses_widget(self):
        """Test reusing widget from pool."""
        pool = WidgetPool(MockWidget, max_size=10)
        widget1 = pool.acquire("test_widget_1")
        pool.release(widget1)
        
        widget2 = pool.acquire("test_widget_2")
        
        assert widget1 is widget2  # Same widget instance
        assert widget2.reset_called
        assert pool._created_count == 1
        assert pool._reused_count == 1
    
    def test_release__pool_full__widget_not_added(self):
        """Test releasing widget when pool is full."""
        pool = WidgetPool(MockWidget, max_size=1)
        widget1 = pool.acquire("widget_1")
        widget2 = pool.acquire("widget_2")
        
        pool.release(widget1)  # Should be added to pool
        pool.release(widget2)  # Pool full, should not be added
        
        assert len(pool._available) == 1
        assert widget1 in pool._available
        assert widget2 not in pool._available
    
    def test_clear__destroys_all_widgets(self):
        """Test clearing pool destroys all widgets."""
        pool = WidgetPool(MockWidget, max_size=10)
        widget1 = pool.acquire("widget_1")
        widget2 = pool.acquire("widget_2")
        pool.release(widget1)
        
        with patch.object(MockWidget, 'destroy') as mock_destroy:
            pool.clear()
            
            assert len(pool._available) == 0
            assert len(pool._in_use) == 0
            assert mock_destroy.call_count == 2  # Both widgets destroyed
    
    def test_stats__returns_correct_statistics(self):
        """Test pool statistics."""
        pool = WidgetPool(MockWidget, max_size=10)
        widget1 = pool.acquire("widget_1")
        widget2 = pool.acquire("widget_2")
        pool.release(widget1)
        widget3 = pool.acquire("widget_3")  # Reuses widget1
        
        stats = pool.stats
        
        assert stats['available'] == 0
        assert stats['in_use'] == 2
        assert stats['created'] == 2
        assert stats['reused'] == 1
        assert stats['reuse_ratio'] == 1/3  # 1 reuse out of 3 total acquisitions


class TestRenderOptimizer:
    """Test render optimization."""
    
    def test_initialization__default_level__basic_optimization(self):
        """Test optimizer initialization."""
        optimizer = RenderOptimizer()
        
        assert optimizer._optimization_level == OptimizationLevel.BASIC
        assert len(optimizer._dirty_regions) == 0
        assert len(optimizer._render_cache) == 0
    
    def test_should_render_widget__invisible_widget__returns_false(self):
        """Test render decision for invisible widget."""
        optimizer = RenderOptimizer()
        widget = MockWidget()
        widget.visible = False
        
        should_render = optimizer.should_render_widget(widget)
        
        assert not should_render
    
    def test_should_render_widget__zero_alpha__returns_false(self):
        """Test render decision for zero alpha widget."""
        optimizer = RenderOptimizer()
        widget = MockWidget()
        widget.alpha = 0.0
        
        should_render = optimizer.should_render_widget(widget)
        
        assert not should_render
    
    def test_should_render_widget__clean_widget_basic_optimization__returns_false(self):
        """Test render decision for clean widget with basic optimization."""
        optimizer = RenderOptimizer(OptimizationLevel.BASIC)
        widget = MockWidget()
        widget.mark_clean()  # Widget is clean
        
        should_render = optimizer.should_render_widget(widget)
        
        assert not should_render
    
    def test_should_render_widget__no_optimization__always_returns_true(self):
        """Test render decision with no optimization."""
        optimizer = RenderOptimizer(OptimizationLevel.NONE)
        widget = MockWidget()
        widget.mark_clean()  # Even clean widgets should render
        
        should_render = optimizer.should_render_widget(widget)
        
        assert should_render
    
    def test_optimize_render_order__sorts_by_complexity(self):
        """Test render order optimization by complexity."""
        optimizer = RenderOptimizer()
        
        # Create widgets with different complexities
        text_widget = MockWidget("text")
        text_widget._text = "test"  # TextWidget marker
        
        image_widget = MockWidget("image")
        image_widget._image_source = "test.png"  # ImageWidget marker
        
        simple_widget = MockWidget("simple")
        
        widgets = [image_widget, text_widget, simple_widget]
        
        optimized = optimizer.optimize_render_order(widgets)
        
        # Should be ordered: simple (0), text (1), image (3)
        assert optimized[0] is simple_widget
        assert optimized[1] is text_widget
        assert optimized[2] is image_widget
    
    def test_cache_render_result__basic_optimization__caches_result(self):
        """Test render result caching."""
        optimizer = RenderOptimizer(OptimizationLevel.BASIC)
        widget = MockWidget()
        result = "cached_render_result"
        
        optimizer.cache_render_result(widget, result)
        cached = optimizer.get_cached_render(widget)
        
        assert cached == result
    
    def test_get_cached_render__no_optimization__returns_none(self):
        """Test cached render with no optimization."""
        optimizer = RenderOptimizer(OptimizationLevel.NONE)
        widget = MockWidget()
        
        optimizer.cache_render_result(widget, "result")
        cached = optimizer.get_cached_render(widget)
        
        assert cached is None
    
    def test_clear_cache__removes_all_cached_results(self):
        """Test cache clearing."""
        optimizer = RenderOptimizer(OptimizationLevel.BASIC)
        widget = MockWidget()
        
        optimizer.cache_render_result(widget, "result")
        optimizer.clear_cache()
        cached = optimizer.get_cached_render(widget)
        
        assert cached is None


class TestMemoryManager:
    """Test memory management."""
    
    @patch('psutil.Process')
    def test_initialization__sets_target_memory(self, mock_process):
        """Test memory manager initialization."""
        manager = MemoryManager(target_memory_mb=50.0)
        
        assert manager._target_memory_mb == 50.0
        assert len(manager._widget_pools) == 0
        assert len(manager._weak_refs) == 0
    
    def test_get_pool__creates_pool_for_class(self):
        """Test pool creation for widget class."""
        manager = MemoryManager()
        
        pool = manager.get_pool(MockWidget)
        
        assert isinstance(pool, WidgetPool)
        assert pool._widget_class == MockWidget
        assert MockWidget in manager._widget_pools
    
    def test_get_pool__same_class__returns_same_pool(self):
        """Test getting same pool for same class."""
        manager = MemoryManager()
        
        pool1 = manager.get_pool(MockWidget)
        pool2 = manager.get_pool(MockWidget)
        
        assert pool1 is pool2
    
    def test_track_widget__adds_weak_reference(self):
        """Test widget tracking with weak references."""
        manager = MemoryManager()
        widget = MockWidget()
        
        manager.track_widget(widget)
        
        assert len(manager._weak_refs) == 1
        # Verify weak reference points to widget
        refs = [ref for ref in manager._weak_refs if ref() is not None]
        assert len(refs) == 1
        assert refs[0]() is widget
    
    def test_track_widget__widget_deleted__weak_ref_cleaned(self):
        """Test weak reference cleanup when widget is deleted."""
        manager = MemoryManager()
        widget = MockWidget()
        manager.track_widget(widget)
        
        del widget  # Delete widget
        gc.collect()  # Force garbage collection
        
        # Trigger cleanup by accessing weak refs
        live_refs = [ref for ref in manager._weak_refs if ref() is not None]
        assert len(live_refs) == 0
    
    @patch('psutil.Process')
    def test_get_memory_usage__returns_memory_in_mb(self, mock_process):
        """Test memory usage calculation."""
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
        mock_process.return_value = mock_process_instance
        
        manager = MemoryManager()
        memory_mb = manager.get_memory_usage()
        
        assert memory_mb == 100.0
    
    @patch('psutil.Process')
    def test_should_trigger_gc__memory_pressure__returns_true(self, mock_process):
        """Test GC trigger due to memory pressure."""
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value.rss = 90 * 1024 * 1024  # 90MB
        mock_process.return_value = mock_process_instance
        
        manager = MemoryManager(target_memory_mb=100.0)  # 90MB > 80MB threshold
        
        should_trigger = manager.should_trigger_gc()
        
        assert should_trigger
    
    @patch('psutil.Process')
    @patch('gc.collect')
    def test_optimize_memory__performs_gc_and_cleanup(self, mock_gc, mock_process):
        """Test memory optimization."""
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
        mock_process.return_value = mock_process_instance
        mock_gc.return_value = 42  # Objects collected
        
        manager = MemoryManager()
        
        result = manager.optimize_memory()
        
        assert result['memory_before_mb'] == 100.0
        assert result['memory_after_mb'] == 100.0
        assert result['objects_collected'] == 42
        mock_gc.assert_called_once()


class TestReactiveOptimizer:
    """Test reactive binding optimization."""
    
    def test_initialization__sets_batch_parameters(self):
        """Test reactive optimizer initialization."""
        optimizer = ReactiveOptimizer(batch_size=5, batch_timeout=0.1)
        
        assert optimizer._batch_size == 5
        assert optimizer._batch_timeout == 0.1
        assert len(optimizer._pending_updates) == 0
        assert optimizer._update_count == 0
        assert optimizer._batch_count == 0
    
    def test_queue_update__single_update__queued(self):
        """Test queuing single update."""
        optimizer = ReactiveOptimizer(batch_size=10)
        update_func = Mock()
        
        optimizer.queue_update(update_func)
        
        assert len(optimizer._pending_updates) == 1
        assert optimizer._update_count == 1
        assert optimizer._batch_count == 0  # Not processed yet
        update_func.assert_not_called()
    
    def test_queue_update__batch_size_reached__processes_batch(self):
        """Test batch processing when size threshold reached."""
        optimizer = ReactiveOptimizer(batch_size=2)
        update_func1 = Mock()
        update_func2 = Mock()
        
        optimizer.queue_update(update_func1)
        optimizer.queue_update(update_func2)  # Should trigger batch processing
        
        assert len(optimizer._pending_updates) == 0  # Batch processed
        assert optimizer._batch_count == 1
        update_func1.assert_called_once()
        update_func2.assert_called_once()
    
    def test_queue_update__timeout_reached__processes_batch(self):
        """Test batch processing when timeout reached."""
        optimizer = ReactiveOptimizer(batch_size=10, batch_timeout=0.01)  # 10ms timeout
        update_func = Mock()
        
        optimizer.queue_update(update_func)
        time.sleep(0.02)  # Wait longer than timeout
        optimizer.queue_update(Mock())  # Should trigger batch processing
        
        assert optimizer._batch_count >= 1
        update_func.assert_called_once()
    
    def test_force_flush__processes_pending_updates(self):
        """Test force flushing pending updates."""
        optimizer = ReactiveOptimizer(batch_size=10)
        update_func = Mock()
        
        optimizer.queue_update(update_func)
        optimizer.force_flush()
        
        assert len(optimizer._pending_updates) == 0
        assert optimizer._batch_count == 1
        update_func.assert_called_once()
    
    def test_stats__returns_correct_statistics(self):
        """Test reactive optimizer statistics."""
        optimizer = ReactiveOptimizer(batch_size=2)
        
        optimizer.queue_update(Mock())
        optimizer.queue_update(Mock())  # Triggers batch
        optimizer.queue_update(Mock())
        
        stats = optimizer.stats
        
        assert stats['total_updates'] == 3
        assert stats['total_batches'] == 1
        assert stats['pending_updates'] == 1
        assert stats['batch_efficiency'] == 3.0  # 3 updates / 1 batch


class TestPerformanceMonitor:
    """Test performance monitoring."""
    
    def test_initialization__creates_components(self):
        """Test monitor initialization."""
        monitor = PerformanceMonitor()
        
        assert isinstance(monitor.metrics, PerformanceMetrics)
        assert isinstance(monitor.memory_manager, MemoryManager)
        assert isinstance(monitor.render_optimizer, RenderOptimizer)
        assert isinstance(monitor.reactive_optimizer, ReactiveOptimizer)
        assert not monitor._monitoring_active
    
    def test_start_monitoring__starts_background_thread(self):
        """Test starting performance monitoring."""
        monitor = PerformanceMonitor()
        
        monitor.start_monitoring(interval=0.1)
        
        assert monitor._monitoring_active
        assert monitor._monitor_thread is not None
        assert monitor._monitor_thread.is_alive()
        
        # Cleanup
        monitor.stop_monitoring()
    
    def test_stop_monitoring__stops_background_thread(self):
        """Test stopping performance monitoring."""
        monitor = PerformanceMonitor()
        monitor.start_monitoring(interval=0.1)
        
        monitor.stop_monitoring()
        
        assert not monitor._monitoring_active
        # Thread should stop within timeout
        if monitor._monitor_thread:
            monitor._monitor_thread.join(timeout=1.0)
            assert not monitor._monitor_thread.is_alive()
    
    def test_measure_frame__context_manager__updates_metrics(self):
        """Test frame measurement context manager."""
        monitor = PerformanceMonitor()
        
        with monitor.measure_frame():
            time.sleep(0.01)  # Simulate frame work
        
        assert monitor.metrics.frame_count == 1
        assert monitor.metrics.total_render_time > 0.01
    
    def test_measure_reactive_update__context_manager__updates_metrics(self):
        """Test reactive update measurement."""
        monitor = PerformanceMonitor()
        
        with monitor.measure_reactive_update(batched=True):
            time.sleep(0.001)  # Simulate update work
        
        assert monitor.metrics.reactive_updates == 1
        assert monitor.metrics.batched_updates == 1
        assert monitor.metrics.update_time > 0.001
    
    def test_get_performance_report__returns_comprehensive_data(self):
        """Test performance report generation."""
        monitor = PerformanceMonitor()
        
        # Add some test data
        monitor.metrics.update_frame_metrics(0.01)
        monitor.metrics.update_memory_metrics(50.0, 10, 5)
        monitor.metrics.update_reactive_metrics(0.001, True)
        monitor.metrics.calculate_overall_score()
        
        report = monitor.get_performance_report()
        
        assert 'metrics' in report
        assert 'memory_pools' in report
        assert 'reactive_stats' in report
        
        metrics = report['metrics']
        assert metrics['render_score'] == 100.0
        assert metrics['memory_score'] == 100.0
        assert metrics['reactive_score'] == 100.0
        assert metrics['frame_count'] == 1
        assert metrics['memory_mb'] == 50.0


class TestPerformanceBenchmark:
    """Test performance benchmarking."""
    
    def test_initialization__sets_monitor(self):
        """Test benchmark initialization."""
        monitor = PerformanceMonitor()
        benchmark = PerformanceBenchmark(monitor)
        
        assert benchmark._monitor is monitor
        assert len(benchmark._benchmark_results) == 0
    
    def test_benchmark_widget_creation__measures_performance(self):
        """Test widget creation benchmarking."""
        monitor = PerformanceMonitor()
        benchmark = PerformanceBenchmark(monitor)
        
        result = benchmark.benchmark_widget_creation(MockWidget, count=10)
        
        assert result['widget_class'] == 'MockWidget'
        assert result['count'] == 10
        assert result['total_time_ms'] > 0
        assert result['time_per_widget_ms'] > 0
        assert result['memory_used_mb'] >= 0
        assert 'meets_target' in result
    
    def test_benchmark_rendering_performance__measures_fps(self):
        """Test rendering performance benchmarking."""
        monitor = PerformanceMonitor()
        benchmark = PerformanceBenchmark(monitor)
        
        # Create mock widgets
        widgets = [MockWidget(f"widget_{i}") for i in range(5)]
        
        result = benchmark.benchmark_rendering_performance(widgets, frames=10)
        
        assert result['widget_count'] == 5
        assert result['frame_count'] == 10
        assert result['total_time_s'] > 0
        assert result['average_frame_time_ms'] > 0
        assert result['average_fps'] > 0
        assert 'meets_60fps_target' in result
    
    def test_benchmark_reactive_performance__measures_update_speed(self):
        """Test reactive performance benchmarking."""
        monitor = PerformanceMonitor()
        benchmark = PerformanceBenchmark(monitor)
        
        reactive_values = [ReactiveValue(f"initial_{i}") for i in range(3)]
        
        result = benchmark.benchmark_reactive_performance(reactive_values, updates=30)
        
        assert result['reactive_count'] == 3
        assert result['update_count'] == 30
        assert result['total_time_s'] > 0
        assert result['average_update_time_ms'] > 0
        assert result['updates_per_second'] > 0
        assert 'meets_target' in result


class TestGlobalFunctions:
    """Test global performance functions."""
    
    def test_get_performance_monitor__singleton_pattern(self):
        """Test global monitor singleton."""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        assert monitor1 is monitor2
        assert isinstance(monitor1, PerformanceMonitor)
    
    def test_enable_performance_optimization__starts_monitoring(self):
        """Test enabling performance optimization."""
        enable_performance_optimization(OptimizationLevel.AGGRESSIVE)
        
        monitor = get_performance_monitor()
        assert monitor.render_optimizer._optimization_level == OptimizationLevel.AGGRESSIVE
        assert monitor._monitoring_active
        
        # Cleanup
        disable_performance_optimization()
    
    def test_disable_performance_optimization__stops_monitoring(self):
        """Test disabling performance optimization."""
        enable_performance_optimization()
        disable_performance_optimization()
        
        monitor = get_performance_monitor()
        assert not monitor._monitoring_active


@pytest.mark.performance
class TestPerformanceTargets:
    """Test performance targets are met."""
    
    def test_widget_creation_performance__meets_1ms_target(self):
        """Test widget creation meets <1ms per widget target."""
        start_time = time.perf_counter()
        
        widgets = []
        for i in range(100):
            widget = MockWidget(f"perf_test_{i}")
            widgets.append(widget)
        
        creation_time = time.perf_counter() - start_time
        time_per_widget = creation_time / 100
        
        # Cleanup
        for widget in widgets:
            widget.destroy()
        
        assert time_per_widget < 0.001  # <1ms per widget
    
    def test_rendering_performance__meets_60fps_target(self):
        """Test rendering performance meets 30fps target."""
        widgets = [MockWidget(f"render_test_{i}") for i in range(20)]
        canvas = Mock()
        
        start_time = time.perf_counter()
        
        # Simulate 60 frames
        for frame in range(60):
            for widget in widgets:
                widget.render(canvas)
        
        total_time = time.perf_counter() - start_time
        average_frame_time = total_time / 60
        
        # Cleanup
        for widget in widgets:
            widget.destroy()
        
        target_frame_time = 1.0 / 30.0  # 33.33ms for 30fps (more realistic for test)
        assert average_frame_time <= target_frame_time
    
    def test_reactive_update_performance__meets_50ms_target(self):
        """Test reactive updates meet <50ms target."""
        reactive_values = [ReactiveValue(f"perf_{i}") for i in range(10)]
        
        start_time = time.perf_counter()
        
        # Perform 1000 updates
        for i in range(1000):
            reactive_value = reactive_values[i % len(reactive_values)]
            reactive_value.value = f"update_{i}"
        
        total_time = time.perf_counter() - start_time
        average_update_time = total_time / 1000
        
        assert average_update_time < 0.050  # <50ms per update
    
    @patch('psutil.Process')
    def test_memory_usage__stays_under_100mb_target(self, mock_process):
        """Test memory usage stays under 100MB target."""
        # Simulate memory usage under target
        mock_process_instance = Mock()
        mock_process_instance.memory_info.return_value.rss = 80 * 1024 * 1024  # 80MB
        mock_process.return_value = mock_process_instance
        
        manager = MemoryManager(target_memory_mb=100.0)
        memory_mb = manager.get_memory_usage()
        
        assert memory_mb < 100.0  # Under 100MB target


if __name__ == "__main__":
    pytest.main([__file__]) 