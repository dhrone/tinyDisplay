#!/usr/bin/env python3
"""
Widget Performance Optimization System

Provides performance optimization strategies for widget rendering, memory management,
and reactive binding performance for high-frequency updates.
"""

import time
import threading
import weakref
from typing import Dict, List, Optional, Set, Any, Callable, Type, TypeVar, Generic
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import gc
import psutil
import os
from contextlib import contextmanager

from ..widgets.base import Widget, ReactiveValue
from ..core.reactive import ReactiveDataManager

__slots__ = ['PerformanceMetrics', 'WidgetPool', 'RenderOptimizer', 'MemoryManager', 
             'PerformanceMonitor', 'ReactiveOptimizer', 'PerformanceBenchmark']

T = TypeVar('T', bound=Widget)


class OptimizationLevel(Enum):
    """Performance optimization levels."""
    NONE = 0
    BASIC = 1
    AGGRESSIVE = 2
    MAXIMUM = 3


@dataclass
class PerformanceMetrics:
    """Performance metrics tracking."""
    
    # Rendering metrics
    frame_count: int = 0
    total_render_time: float = 0.0
    average_frame_time: float = 0.0
    min_frame_time: float = float('inf')
    max_frame_time: float = 0.0
    dropped_frames: int = 0
    target_frame_time: float = 1.0 / 60.0  # 60fps
    
    # Memory metrics
    peak_memory_mb: float = 0.0
    current_memory_mb: float = 0.0
    widget_count: int = 0
    pooled_widgets: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Reactive metrics
    reactive_updates: int = 0
    batched_updates: int = 0
    update_time: float = 0.0
    
    # Performance scores (0-100)
    render_score: float = 100.0
    memory_score: float = 100.0
    reactive_score: float = 100.0
    overall_score: float = 100.0
    
    def update_frame_metrics(self, frame_time: float) -> None:
        """Update frame rendering metrics."""
        self.frame_count += 1
        self.total_render_time += frame_time
        self.average_frame_time = self.total_render_time / self.frame_count
        self.min_frame_time = min(self.min_frame_time, frame_time)
        self.max_frame_time = max(self.max_frame_time, frame_time)
        
        if frame_time > self.target_frame_time:
            self.dropped_frames += 1
        
        # Calculate render score (0-100)
        if self.frame_count > 0:
            fps = 1.0 / self.average_frame_time if self.average_frame_time > 0 else 60.0
            target_fps = 1.0 / self.target_frame_time
            self.render_score = min(100.0, (fps / target_fps) * 100.0)
    
    def update_memory_metrics(self, memory_mb: float, widget_count: int, pooled_count: int) -> None:
        """Update memory usage metrics."""
        self.current_memory_mb = memory_mb
        self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)
        self.widget_count = widget_count
        self.pooled_widgets = pooled_count
        
        # Calculate memory score (0-100, target <100MB)
        target_memory = 100.0
        if memory_mb <= target_memory:
            self.memory_score = 100.0
        else:
            self.memory_score = max(0.0, 100.0 - ((memory_mb - target_memory) / target_memory) * 50.0)
    
    def update_reactive_metrics(self, update_time: float, batched: bool) -> None:
        """Update reactive system metrics."""
        self.reactive_updates += 1
        self.update_time += update_time
        if batched:
            self.batched_updates += 1
        
        # Calculate reactive score (0-100, target <50ms average)
        if self.reactive_updates > 0:
            avg_update_time = self.update_time / self.reactive_updates
            target_time = 0.050  # 50ms
            if avg_update_time <= target_time:
                self.reactive_score = 100.0
            else:
                self.reactive_score = max(0.0, 100.0 - ((avg_update_time - target_time) / target_time) * 100.0)
    
    def calculate_overall_score(self) -> None:
        """Calculate overall performance score."""
        self.overall_score = (self.render_score + self.memory_score + self.reactive_score) / 3.0


class WidgetPool(Generic[T]):
    """Memory pool for frequently created/destroyed widgets."""
    
    def __init__(self, widget_class: Type[T], max_size: int = 50):
        self._widget_class = widget_class
        self._max_size = max_size
        self._available: deque[T] = deque()
        self._in_use: Set[T] = set()
        self._lock = threading.RLock()
        self._created_count = 0
        self._reused_count = 0
    
    def acquire(self, *args, **kwargs) -> T:
        """Acquire a widget from the pool or create new one."""
        with self._lock:
            if self._available:
                widget = self._available.popleft()
                self._in_use.add(widget)
                self._reused_count += 1
                
                # Reset widget state
                widget._reset_for_reuse(*args, **kwargs)
                return widget
            else:
                # Create new widget
                widget = self._widget_class(*args, **kwargs)
                self._in_use.add(widget)
                self._created_count += 1
                return widget
    
    def release(self, widget: T) -> None:
        """Release a widget back to the pool."""
        with self._lock:
            if widget in self._in_use:
                self._in_use.remove(widget)
                
                # Clean up widget for reuse
                widget._cleanup_for_pooling()
                
                # Add back to pool if not full
                if len(self._available) < self._max_size:
                    self._available.append(widget)
    
    def clear(self) -> None:
        """Clear the pool and destroy all widgets."""
        with self._lock:
            for widget in self._available:
                widget.destroy()
            self._available.clear()
            
            for widget in self._in_use.copy():
                widget.destroy()
            self._in_use.clear()
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get pool statistics."""
        return {
            'available': len(self._available),
            'in_use': len(self._in_use),
            'created': self._created_count,
            'reused': self._reused_count,
            'reuse_ratio': self._reused_count / max(1, self._created_count + self._reused_count)
        }


class RenderOptimizer:
    """Optimizes widget rendering performance."""
    
    def __init__(self, optimization_level: OptimizationLevel = OptimizationLevel.BASIC):
        self._optimization_level = optimization_level
        self._dirty_regions: Set[tuple] = set()
        self._render_cache: Dict[str, Any] = {}
        self._last_render_time = 0.0
        self._frame_skip_threshold = 1.0 / 30.0  # Skip frames if slower than 30fps
        self._lock = threading.RLock()
    
    def should_render_widget(self, widget: Widget) -> bool:
        """Determine if widget should be rendered this frame."""
        if not widget.visible or widget.alpha <= 0:
            return False
        
        if self._optimization_level == OptimizationLevel.NONE:
            return True
        
        # Basic optimization: skip if not dirty
        if self._optimization_level.value >= OptimizationLevel.BASIC.value:
            if not widget.needs_render():
                return False
        
        # Aggressive optimization: frame skipping
        if self._optimization_level.value >= OptimizationLevel.AGGRESSIVE.value:
            current_time = time.time()
            if current_time - self._last_render_time < self._frame_skip_threshold:
                return False
        
        return True
    
    def optimize_render_order(self, widgets: List[Widget]) -> List[Widget]:
        """Optimize widget rendering order for performance."""
        if self._optimization_level == OptimizationLevel.NONE:
            return widgets
        
        # Sort by render complexity (simple widgets first)
        def render_complexity(widget: Widget) -> int:
            complexity = 0
            if hasattr(widget, '_image_source'):  # ImageWidget
                complexity += 3
            if hasattr(widget, '_style') and widget._style:  # Styled widgets
                complexity += 2
            if hasattr(widget, '_text'):  # TextWidget
                complexity += 1
            return complexity
        
        return sorted(widgets, key=render_complexity)
    
    def cache_render_result(self, widget: Widget, result: Any) -> None:
        """Cache widget render result for reuse."""
        if self._optimization_level.value >= OptimizationLevel.BASIC.value:
            cache_key = f"{widget.widget_id}_{widget._last_modified}"
            self._render_cache[cache_key] = result
    
    def get_cached_render(self, widget: Widget) -> Optional[Any]:
        """Get cached render result if available."""
        if self._optimization_level.value >= OptimizationLevel.BASIC.value:
            cache_key = f"{widget.widget_id}_{widget._last_modified}"
            return self._render_cache.get(cache_key)
        return None
    
    def clear_cache(self) -> None:
        """Clear render cache."""
        with self._lock:
            self._render_cache.clear()


class MemoryManager:
    """Manages memory usage and optimization."""
    
    def __init__(self, target_memory_mb: float = 100.0):
        self._target_memory_mb = target_memory_mb
        self._widget_pools: Dict[Type, WidgetPool] = {}
        self._weak_refs: Set[weakref.ref] = set()
        self._gc_threshold = 0.8  # Trigger GC at 80% of target
        self._last_gc_time = 0.0
        self._gc_interval = 5.0  # GC every 5 seconds max
    
    def get_pool(self, widget_class: Type[T]) -> WidgetPool[T]:
        """Get or create widget pool for class."""
        if widget_class not in self._widget_pools:
            self._widget_pools[widget_class] = WidgetPool(widget_class)
        return self._widget_pools[widget_class]
    
    def track_widget(self, widget: Widget) -> None:
        """Track widget for memory management."""
        def cleanup_callback(ref):
            self._weak_refs.discard(ref)
        
        weak_ref = weakref.ref(widget, cleanup_callback)
        self._weak_refs.add(weak_ref)
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def should_trigger_gc(self) -> bool:
        """Check if garbage collection should be triggered."""
        current_memory = self.get_memory_usage()
        current_time = time.time()
        
        memory_pressure = current_memory >= (self._target_memory_mb * self._gc_threshold)
        time_elapsed = current_time - self._last_gc_time >= self._gc_interval
        
        return memory_pressure or time_elapsed
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Perform memory optimization."""
        start_memory = self.get_memory_usage()
        
        # Clean up dead weak references
        dead_refs = [ref for ref in self._weak_refs if ref() is None]
        for ref in dead_refs:
            self._weak_refs.discard(ref)
        
        # Trigger garbage collection
        if self.should_trigger_gc():
            collected = gc.collect()
            self._last_gc_time = time.time()
        else:
            collected = 0
        
        end_memory = self.get_memory_usage()
        
        return {
            'memory_before_mb': start_memory,
            'memory_after_mb': end_memory,
            'memory_freed_mb': start_memory - end_memory,
            'objects_collected': collected,
            'tracked_widgets': len([ref for ref in self._weak_refs if ref() is not None])
        }


class ReactiveOptimizer:
    """Optimizes reactive binding performance."""
    
    def __init__(self, batch_size: int = 10, batch_timeout: float = 0.016):  # ~60fps
        self._batch_size = batch_size
        self._batch_timeout = batch_timeout
        self._pending_updates: List[Callable] = []
        self._last_batch_time = time.time()  # Initialize to current time
        self._lock = threading.RLock()
        self._update_count = 0
        self._batch_count = 0
    
    def queue_update(self, update_func: Callable) -> None:
        """Queue a reactive update for batching."""
        with self._lock:
            self._pending_updates.append(update_func)
            self._update_count += 1
            
            # Process batch if size threshold reached or timeout exceeded
            current_time = time.time()
            should_process = (
                len(self._pending_updates) >= self._batch_size or
                current_time - self._last_batch_time >= self._batch_timeout
            )
            
            if should_process:
                self._process_batch()
    
    def _process_batch(self) -> None:
        """Process batched updates."""
        if not self._pending_updates:
            return
        
        start_time = time.time()
        updates_to_process = self._pending_updates.copy()
        self._pending_updates.clear()
        self._last_batch_time = start_time
        self._batch_count += 1
        
        # Process all updates in batch
        for update_func in updates_to_process:
            try:
                update_func()
            except Exception as e:
                print(f"Error in batched reactive update: {e}")
        
        # Update metrics
        batch_time = time.time() - start_time
        return batch_time
    
    def force_flush(self) -> None:
        """Force process all pending updates."""
        with self._lock:
            if self._pending_updates:
                self._process_batch()
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get reactive optimization statistics."""
        return {
            'total_updates': self._update_count,
            'total_batches': self._batch_count,
            'pending_updates': len(self._pending_updates),
            'batch_efficiency': self._update_count / max(1, self._batch_count)
        }


class PerformanceMonitor:
    """Monitors and tracks widget system performance."""
    
    def __init__(self):
        self._metrics = PerformanceMetrics()
        self._memory_manager = MemoryManager()
        self._render_optimizer = RenderOptimizer()
        self._reactive_optimizer = ReactiveOptimizer()
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    @property
    def metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self._metrics
    
    @property
    def memory_manager(self) -> MemoryManager:
        """Get memory manager."""
        return self._memory_manager
    
    @property
    def render_optimizer(self) -> RenderOptimizer:
        """Get render optimizer."""
        return self._render_optimizer
    
    @property
    def reactive_optimizer(self) -> ReactiveOptimizer:
        """Get reactive optimizer."""
        return self._reactive_optimizer
    
    def start_monitoring(self, interval: float = 1.0) -> None:
        """Start performance monitoring."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
    
    def _monitor_loop(self, interval: float) -> None:
        """Main monitoring loop."""
        while not self._stop_event.wait(interval):
            try:
                # Update memory metrics
                memory_mb = self._memory_manager.get_memory_usage()
                widget_count = len([ref for ref in self._memory_manager._weak_refs if ref() is not None])
                pooled_count = sum(pool.stats['available'] for pool in self._memory_manager._widget_pools.values())
                
                self._metrics.update_memory_metrics(memory_mb, widget_count, pooled_count)
                
                # Trigger memory optimization if needed
                if self._memory_manager.should_trigger_gc():
                    self._memory_manager.optimize_memory()
                
                # Update overall score
                self._metrics.calculate_overall_score()
                
            except Exception as e:
                print(f"Error in performance monitoring: {e}")
    
    @contextmanager
    def measure_frame(self):
        """Context manager to measure frame rendering time."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            frame_time = time.perf_counter() - start_time
            self._metrics.update_frame_metrics(frame_time)
    
    @contextmanager
    def measure_reactive_update(self, batched: bool = False):
        """Context manager to measure reactive update time."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            update_time = time.perf_counter() - start_time
            self._metrics.update_reactive_metrics(update_time, batched)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        return {
            'metrics': {
                'render_score': self._metrics.render_score,
                'memory_score': self._metrics.memory_score,
                'reactive_score': self._metrics.reactive_score,
                'overall_score': self._metrics.overall_score,
                'frame_count': self._metrics.frame_count,
                'average_fps': 1.0 / self._metrics.average_frame_time if self._metrics.average_frame_time > 0 else 0,
                'dropped_frames': self._metrics.dropped_frames,
                'memory_mb': self._metrics.current_memory_mb,
                'peak_memory_mb': self._metrics.peak_memory_mb,
                'widget_count': self._metrics.widget_count
            },
            'memory_pools': {
                cls.__name__: pool.stats 
                for cls, pool in self._memory_manager._widget_pools.items()
            },
            'reactive_stats': self._reactive_optimizer.stats
        }


class PerformanceBenchmark:
    """Performance benchmarking suite for widgets."""
    
    def __init__(self, monitor: PerformanceMonitor):
        self._monitor = monitor
        self._benchmark_results: Dict[str, Dict[str, Any]] = {}
    
    def benchmark_widget_creation(self, widget_class: Type[Widget], count: int = 100) -> Dict[str, Any]:
        """Benchmark widget creation performance."""
        start_time = time.perf_counter()
        start_memory = self._monitor.memory_manager.get_memory_usage()
        
        widgets = []
        for i in range(count):
            # Create widgets with appropriate parameters based on type
            if widget_class.__name__ == 'TextWidget':
                widget = widget_class(text=f"Benchmark {i}", widget_id=f"benchmark_{i}")
            elif widget_class.__name__ == 'RectangleWidget':
                widget = widget_class(width=50, height=30, widget_id=f"benchmark_{i}")
            elif widget_class.__name__ == 'CircleWidget':
                widget = widget_class(radius=25, widget_id=f"benchmark_{i}")
            elif widget_class.__name__ == 'ProgressBarWidget':
                widget = widget_class(progress=0.5, widget_id=f"benchmark_{i}")
            elif widget_class.__name__ == 'ImageWidget':
                widget = widget_class(image_source=b"mock_data", widget_id=f"benchmark_{i}")
            else:
                # Default case - try with just widget_id
                widget = widget_class(widget_id=f"benchmark_{i}")
            widgets.append(widget)
        
        creation_time = time.perf_counter() - start_time
        end_memory = self._monitor.memory_manager.get_memory_usage()
        
        # Cleanup
        for widget in widgets:
            widget.destroy()
        
        result = {
            'widget_class': widget_class.__name__,
            'count': count,
            'total_time_ms': creation_time * 1000,
            'time_per_widget_ms': (creation_time / count) * 1000,
            'memory_used_mb': end_memory - start_memory,
            'memory_per_widget_kb': ((end_memory - start_memory) * 1024) / count,
            'meets_target': (creation_time / count) < 0.001  # <1ms per widget
        }
        
        self._benchmark_results[f"creation_{widget_class.__name__}"] = result
        return result
    
    def benchmark_rendering_performance(self, widgets: List[Widget], frames: int = 60) -> Dict[str, Any]:
        """Benchmark rendering performance."""
        from unittest.mock import Mock
        
        canvas = Mock()
        start_time = time.perf_counter()
        
        frame_times = []
        for frame in range(frames):
            frame_start = time.perf_counter()
            
            for widget in widgets:
                if self._monitor.render_optimizer.should_render_widget(widget):
                    widget.render(canvas)
            
            frame_time = time.perf_counter() - frame_start
            frame_times.append(frame_time)
        
        total_time = time.perf_counter() - start_time
        average_frame_time = sum(frame_times) / len(frame_times)
        max_frame_time = max(frame_times)
        min_frame_time = min(frame_times)
        
        target_frame_time = 1.0 / 60.0  # 60fps
        dropped_frames = sum(1 for ft in frame_times if ft > target_frame_time)
        
        result = {
            'widget_count': len(widgets),
            'frame_count': frames,
            'total_time_s': total_time,
            'average_frame_time_ms': average_frame_time * 1000,
            'min_frame_time_ms': min_frame_time * 1000,
            'max_frame_time_ms': max_frame_time * 1000,
            'average_fps': 1.0 / average_frame_time,
            'dropped_frames': dropped_frames,
            'frame_drop_rate': dropped_frames / frames,
            'meets_60fps_target': average_frame_time <= target_frame_time
        }
        
        self._benchmark_results[f"rendering_{len(widgets)}_widgets"] = result
        return result
    
    def benchmark_reactive_performance(self, reactive_values: List[ReactiveValue], updates: int = 1000) -> Dict[str, Any]:
        """Benchmark reactive system performance."""
        start_time = time.perf_counter()
        
        update_times = []
        for i in range(updates):
            update_start = time.perf_counter()
            
            # Update random reactive value
            reactive_value = reactive_values[i % len(reactive_values)]
            reactive_value.value = f"update_{i}"
            
            update_time = time.perf_counter() - update_start
            update_times.append(update_time)
        
        total_time = time.perf_counter() - start_time
        average_update_time = sum(update_times) / len(update_times)
        
        result = {
            'reactive_count': len(reactive_values),
            'update_count': updates,
            'total_time_s': total_time,
            'average_update_time_ms': average_update_time * 1000,
            'updates_per_second': updates / total_time,
            'meets_target': average_update_time < 0.050  # <50ms target
        }
        
        self._benchmark_results[f"reactive_{len(reactive_values)}_values"] = result
        return result
    
    def run_full_benchmark_suite(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        from ..widgets.text import TextWidget
        from ..widgets.image import ImageWidget
        from ..widgets.progress import ProgressBarWidget
        from ..widgets.shapes import RectangleWidget
        
        results = {}
        
        # Widget creation benchmarks
        for widget_class in [TextWidget, ImageWidget, ProgressBarWidget, RectangleWidget]:
            try:
                result = self.benchmark_widget_creation(widget_class, 100)
                results[f"creation_{widget_class.__name__}"] = result
            except Exception as e:
                print(f"Benchmark failed for {widget_class.__name__}: {e}")
        
        # Rendering performance benchmark
        try:
            test_widgets = [
                TextWidget(text="Test", widget_id=f"text_{i}") for i in range(5)
            ] + [
                RectangleWidget(width=50, height=50, widget_id=f"rect_{i}") for i in range(15)
            ]
            
            result = self.benchmark_rendering_performance(test_widgets, 60)
            results["rendering_20_widgets"] = result
            
            # Cleanup
            for widget in test_widgets:
                widget.destroy()
                
        except Exception as e:
            print(f"Rendering benchmark failed: {e}")
        
        # Reactive performance benchmark
        try:
            reactive_values = [ReactiveValue(f"initial_{i}") for i in range(10)]
            result = self.benchmark_reactive_performance(reactive_values, 1000)
            results["reactive_10_values"] = result
        except Exception as e:
            print(f"Reactive benchmark failed: {e}")
        
        # Overall assessment
        results["summary"] = self._assess_benchmark_results(results)
        
        return results
    
    def _assess_benchmark_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall benchmark performance."""
        creation_passed = 0
        creation_total = 0
        rendering_passed = 0
        rendering_total = 0
        reactive_passed = 0
        reactive_total = 0
        
        for key, result in results.items():
            if key.startswith("creation_"):
                creation_total += 1
                if result.get("meets_target", False):
                    creation_passed += 1
            elif key.startswith("rendering_"):
                rendering_total += 1
                if result.get("meets_60fps_target", False):
                    rendering_passed += 1
            elif key.startswith("reactive_"):
                reactive_total += 1
                if result.get("meets_target", False):
                    reactive_passed += 1
        
        return {
            "creation_score": (creation_passed / max(1, creation_total)) * 100,
            "rendering_score": (rendering_passed / max(1, rendering_total)) * 100,
            "reactive_score": (reactive_passed / max(1, reactive_total)) * 100,
            "overall_pass": all([
                creation_passed == creation_total,
                rendering_passed == rendering_total,
                reactive_passed == reactive_total
            ]),
            "pi_zero_ready": all([
                creation_passed == creation_total,
                rendering_passed == rendering_total,
                reactive_passed == reactive_total
            ])
        }


# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def enable_performance_optimization(level: OptimizationLevel = OptimizationLevel.BASIC) -> None:
    """Enable performance optimization globally."""
    monitor = get_performance_monitor()
    monitor.render_optimizer._optimization_level = level
    monitor.start_monitoring()


def disable_performance_optimization() -> None:
    """Disable performance optimization globally."""
    monitor = get_performance_monitor()
    monitor.stop_monitoring() 