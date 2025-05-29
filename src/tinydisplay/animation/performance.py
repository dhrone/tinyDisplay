#!/usr/bin/env python3
"""
Performance Monitoring and Optimization for Tick-Based Animation System

Provides comprehensive performance monitoring, optimization utilities, and benchmarking
tools for ensuring tick-based animations meet 60fps targets on target hardware.
"""

import time
import statistics
import threading
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import contextmanager
import psutil
import gc

from .tick_based import TickAnimationEngine, TickAnimationDefinition, TickEasing


@dataclass
class PerformanceMetrics:
    """Performance metrics for animation operations."""
    operation_name: str
    execution_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    @property
    def average_time(self) -> float:
        """Get average execution time."""
        return self.total_time / self.execution_count if self.execution_count > 0 else 0.0
    
    @property
    def recent_average(self) -> float:
        """Get average of recent executions."""
        return statistics.mean(self.recent_times) if self.recent_times else 0.0
    
    @property
    def operations_per_second(self) -> float:
        """Get operations per second based on average time."""
        return 1.0 / self.average_time if self.average_time > 0 else 0.0
    
    @property
    def recent_ops_per_second(self) -> float:
        """Get recent operations per second."""
        return 1.0 / self.recent_average if self.recent_average > 0 else 0.0
    
    def add_measurement(self, execution_time: float) -> None:
        """Add a new performance measurement."""
        self.execution_count += 1
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.recent_times.append(execution_time)
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.execution_count = 0
        self.total_time = 0.0
        self.min_time = float('inf')
        self.max_time = 0.0
        self.recent_times.clear()


@dataclass
class FramePerformanceStats:
    """Performance statistics for a single frame."""
    frame_number: int
    tick: int
    total_frame_time: float
    tick_advancement_time: float
    state_computation_time: float
    state_application_time: float
    easing_computation_time: float
    active_animations: int
    memory_usage_mb: float
    cpu_usage_percent: float
    
    @property
    def fps(self) -> float:
        """Calculate FPS from total frame time."""
        return 1.0 / self.total_frame_time if self.total_frame_time > 0 else 0.0
    
    @property
    def animation_overhead_percent(self) -> float:
        """Calculate animation overhead as percentage of total frame time."""
        animation_time = (self.tick_advancement_time + 
                         self.state_computation_time + 
                         self.state_application_time + 
                         self.easing_computation_time)
        return (animation_time / self.total_frame_time * 100) if self.total_frame_time > 0 else 0.0


class AnimationPerformanceMonitor:
    """Comprehensive performance monitoring for animation system."""
    
    def __init__(self, enable_detailed_monitoring: bool = True):
        """Initialize performance monitor.
        
        Args:
            enable_detailed_monitoring: Enable detailed per-operation monitoring
        """
        self.enable_detailed_monitoring = enable_detailed_monitoring
        self.metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self.frame_stats: List[FramePerformanceStats] = []
        self.frame_stats_lock = threading.Lock()
        self.current_frame_number = 0
        
        # Performance thresholds
        self.target_fps = 60.0
        self.target_frame_time = 1.0 / self.target_fps  # ~16.67ms
        self.warning_threshold = self.target_frame_time * 0.8  # 80% of target
        self.critical_threshold = self.target_frame_time * 0.95  # 95% of target
        
        # System monitoring
        self.process = psutil.Process()
        
    @contextmanager
    def measure_operation(self, operation_name: str):
        """Context manager for measuring operation performance."""
        if not self.enable_detailed_monitoring:
            yield
            return
            
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            if operation_name not in self.metrics:
                self.metrics[operation_name] = PerformanceMetrics(operation_name)
            
            self.metrics[operation_name].add_measurement(execution_time)
    
    def start_frame_measurement(self, tick: int) -> Dict[str, float]:
        """Start measuring frame performance.
        
        Args:
            tick: Current animation tick
            
        Returns:
            Dictionary with timing markers for frame measurement
        """
        self.current_frame_number += 1
        return {
            'frame_start': time.perf_counter(),
            'tick': tick,
            'frame_number': self.current_frame_number,
            'tick_advancement_time': 0.0,
            'state_computation_time': 0.0,
            'state_application_time': 0.0,
            'easing_computation_time': 0.0,
            'active_animations': 0
        }
    
    def record_tick_advancement(self, timing_data: Dict[str, float], execution_time: float) -> None:
        """Record tick advancement timing."""
        timing_data['tick_advancement_time'] = execution_time
    
    def record_state_computation(self, timing_data: Dict[str, float], execution_time: float, active_count: int) -> None:
        """Record state computation timing."""
        timing_data['state_computation_time'] = execution_time
        timing_data['active_animations'] = active_count
    
    def record_state_application(self, timing_data: Dict[str, float], execution_time: float) -> None:
        """Record state application timing."""
        timing_data['state_application_time'] = execution_time
    
    def record_easing_computation(self, timing_data: Dict[str, float], execution_time: float) -> None:
        """Record easing computation timing."""
        timing_data['easing_computation_time'] = execution_time
    
    def finish_frame_measurement(self, timing_data: Dict[str, float]) -> FramePerformanceStats:
        """Finish frame measurement and record statistics.
        
        Args:
            timing_data: Timing data from start_frame_measurement
            
        Returns:
            FramePerformanceStats for the completed frame
        """
        frame_end = time.perf_counter()
        total_frame_time = frame_end - timing_data['frame_start']
        
        # Get system metrics
        memory_info = self.process.memory_info()
        memory_usage_mb = memory_info.rss / 1024 / 1024
        cpu_usage = self.process.cpu_percent()
        
        frame_stats = FramePerformanceStats(
            frame_number=timing_data['frame_number'],
            tick=timing_data['tick'],
            total_frame_time=total_frame_time,
            tick_advancement_time=timing_data['tick_advancement_time'],
            state_computation_time=timing_data['state_computation_time'],
            state_application_time=timing_data['state_application_time'],
            easing_computation_time=timing_data['easing_computation_time'],
            active_animations=timing_data['active_animations'],
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage
        )
        
        with self.frame_stats_lock:
            self.frame_stats.append(frame_stats)
            
            # Keep only recent frame stats (last 1000 frames)
            if len(self.frame_stats) > 1000:
                self.frame_stats = self.frame_stats[-1000:]
        
        return frame_stats
    
    def get_performance_summary(self, recent_frames: int = 60) -> Dict[str, Any]:
        """Get comprehensive performance summary.
        
        Args:
            recent_frames: Number of recent frames to analyze
            
        Returns:
            Dictionary with performance summary
        """
        with self.frame_stats_lock:
            recent_stats = self.frame_stats[-recent_frames:] if self.frame_stats else []
        
        if not recent_stats:
            return {'error': 'No frame statistics available'}
        
        # Calculate frame timing statistics
        frame_times = [stat.total_frame_time for stat in recent_stats]
        fps_values = [stat.fps for stat in recent_stats]
        
        summary = {
            'frame_statistics': {
                'total_frames': len(self.frame_stats),
                'recent_frames_analyzed': len(recent_stats),
                'average_fps': statistics.mean(fps_values),
                'min_fps': min(fps_values),
                'max_fps': max(fps_values),
                'fps_std_dev': statistics.stdev(fps_values) if len(fps_values) > 1 else 0.0,
                'average_frame_time_ms': statistics.mean(frame_times) * 1000,
                'min_frame_time_ms': min(frame_times) * 1000,
                'max_frame_time_ms': max(frame_times) * 1000,
                'target_fps': self.target_fps,
                'target_frame_time_ms': self.target_frame_time * 1000,
                'fps_target_met': statistics.mean(fps_values) >= self.target_fps * 0.95
            },
            'animation_performance': {
                'average_tick_advancement_ms': statistics.mean([s.tick_advancement_time for s in recent_stats]) * 1000,
                'average_state_computation_ms': statistics.mean([s.state_computation_time for s in recent_stats]) * 1000,
                'average_state_application_ms': statistics.mean([s.state_application_time for s in recent_stats]) * 1000,
                'average_easing_computation_ms': statistics.mean([s.easing_computation_time for s in recent_stats]) * 1000,
                'average_animation_overhead_percent': statistics.mean([s.animation_overhead_percent for s in recent_stats]),
                'average_active_animations': statistics.mean([s.active_animations for s in recent_stats])
            },
            'system_performance': {
                'average_memory_usage_mb': statistics.mean([s.memory_usage_mb for s in recent_stats]),
                'max_memory_usage_mb': max([s.memory_usage_mb for s in recent_stats]),
                'average_cpu_usage_percent': statistics.mean([s.cpu_usage_percent for s in recent_stats]),
                'max_cpu_usage_percent': max([s.cpu_usage_percent for s in recent_stats])
            },
            'operation_metrics': {
                name: {
                    'total_executions': metrics.execution_count,
                    'average_time_ms': metrics.average_time * 1000,
                    'recent_average_ms': metrics.recent_average * 1000,
                    'min_time_ms': metrics.min_time * 1000,
                    'max_time_ms': metrics.max_time * 1000,
                    'operations_per_second': metrics.operations_per_second,
                    'recent_ops_per_second': metrics.recent_ops_per_second
                }
                for name, metrics in self.metrics.items()
            }
        }
        
        return summary
    
    def check_performance_warnings(self, recent_frames: int = 10) -> List[str]:
        """Check for performance warnings based on recent frames.
        
        Args:
            recent_frames: Number of recent frames to check
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        with self.frame_stats_lock:
            recent_stats = self.frame_stats[-recent_frames:] if self.frame_stats else []
        
        if not recent_stats:
            return warnings
        
        # Check FPS performance
        avg_fps = statistics.mean([stat.fps for stat in recent_stats])
        if avg_fps < self.target_fps * 0.9:
            warnings.append(f"FPS below target: {avg_fps:.1f} < {self.target_fps}")
        
        # Check frame time consistency
        frame_times = [stat.total_frame_time for stat in recent_stats]
        if max(frame_times) > self.critical_threshold:
            warnings.append(f"Frame time spike detected: {max(frame_times)*1000:.2f}ms > {self.critical_threshold*1000:.2f}ms")
        
        # Check memory usage
        memory_usage = [stat.memory_usage_mb for stat in recent_stats]
        if max(memory_usage) > 100:  # 100MB threshold
            warnings.append(f"High memory usage: {max(memory_usage):.1f}MB")
        
        # Check animation overhead
        overhead_percent = [stat.animation_overhead_percent for stat in recent_stats]
        if statistics.mean(overhead_percent) > 50:  # 50% of frame time
            warnings.append(f"High animation overhead: {statistics.mean(overhead_percent):.1f}% of frame time")
        
        return warnings
    
    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        self.metrics.clear()
        with self.frame_stats_lock:
            self.frame_stats.clear()
        self.current_frame_number = 0


class EasingOptimizer:
    """Optimized easing function calculations for performance."""
    
    def __init__(self):
        """Initialize easing optimizer with caching."""
        self._cache_enabled = True
        self._cache_size = 1000
        self._easing_cache: Dict[Tuple[str, float], float] = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def enable_caching(self, cache_size: int = 1000) -> None:
        """Enable easing function result caching.
        
        Args:
            cache_size: Maximum number of cached results
        """
        self._cache_enabled = True
        self._cache_size = cache_size
        self._easing_cache.clear()
    
    def disable_caching(self) -> None:
        """Disable easing function caching."""
        self._cache_enabled = False
        self._easing_cache.clear()
    
    def get_cached_easing_result(self, easing_name: str, progress: float, precision: int = 4) -> Optional[float]:
        """Get cached easing result if available.
        
        Args:
            easing_name: Name of easing function
            progress: Progress value (0.0 to 1.0)
            precision: Decimal precision for caching key
            
        Returns:
            Cached result or None if not cached
        """
        if not self._cache_enabled:
            return None
        
        # Round progress for cache key to reduce cache size
        rounded_progress = round(progress, precision)
        cache_key = (easing_name, rounded_progress)
        
        if cache_key in self._easing_cache:
            self._cache_hits += 1
            return self._easing_cache[cache_key]
        
        self._cache_misses += 1
        return None
    
    def cache_easing_result(self, easing_name: str, progress: float, result: float, precision: int = 4) -> None:
        """Cache easing function result.
        
        Args:
            easing_name: Name of easing function
            progress: Progress value (0.0 to 1.0)
            result: Computed easing result
            precision: Decimal precision for caching key
        """
        if not self._cache_enabled:
            return
        
        # Manage cache size
        if len(self._easing_cache) >= self._cache_size:
            # Remove oldest entries (simple FIFO)
            keys_to_remove = list(self._easing_cache.keys())[:self._cache_size // 4]
            for key in keys_to_remove:
                del self._easing_cache[key]
        
        rounded_progress = round(progress, precision)
        cache_key = (easing_name, rounded_progress)
        self._easing_cache[cache_key] = result
    
    def get_optimized_easing_result(self, easing_name: str, progress: float) -> float:
        """Get easing result with optimization.
        
        Args:
            easing_name: Name of easing function
            progress: Progress value (0.0 to 1.0)
            
        Returns:
            Easing function result
        """
        # Check cache first
        cached_result = self.get_cached_easing_result(easing_name, progress)
        if cached_result is not None:
            return cached_result
        
        # Compute result
        easing_func = TickEasing.get_easing_function(easing_name)
        result = easing_func(progress)
        
        # Cache result
        self.cache_easing_result(easing_name, progress, result)
        
        return result
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get easing cache performance statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            'cache_enabled': self._cache_enabled,
            'cache_size': len(self._easing_cache),
            'max_cache_size': self._cache_size,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': hit_rate,
            'total_requests': total_requests
        }
    
    def clear_cache(self) -> None:
        """Clear easing function cache."""
        self._easing_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0


class PerformanceBenchmark:
    """Comprehensive performance benchmarking for animation system."""
    
    def __init__(self, target_fps: float = 60.0):
        """Initialize performance benchmark.
        
        Args:
            target_fps: Target frames per second
        """
        self.target_fps = target_fps
        self.target_frame_time = 1.0 / target_fps
        self.monitor = AnimationPerformanceMonitor()
        self.optimizer = EasingOptimizer()
    
    def benchmark_tick_advancement(self, iterations: int = 1000) -> Dict[str, float]:
        """Benchmark tick advancement performance.
        
        Args:
            iterations: Number of iterations to run
            
        Returns:
            Performance statistics
        """
        engine = TickAnimationEngine()
        
        # Warm up
        for _ in range(10):
            engine.advance_tick()
        
        start_time = time.perf_counter()
        for _ in range(iterations):
            engine.advance_tick()
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        return {
            'total_time': total_time,
            'average_time_ms': avg_time * 1000,
            'operations_per_second': iterations / total_time,
            'target_fps_capable': avg_time < self.target_frame_time,
            'iterations': iterations
        }
    
    def benchmark_state_computation(self, animation_count: int = 10, iterations: int = 100) -> Dict[str, float]:
        """Benchmark animation state computation.
        
        Args:
            animation_count: Number of concurrent animations
            iterations: Number of iterations to run
            
        Returns:
            Performance statistics
        """
        from .utilities import create_fade_animation, create_slide_animation, create_scale_animation
        
        engine = TickAnimationEngine()
        
        # Add test animations
        animations = []
        for i in range(animation_count):
            if i % 3 == 0:
                anim = create_fade_animation(0.0, 1.0)
            elif i % 3 == 1:
                anim = create_slide_animation((0, 0), (100, 100))
            else:
                anim = create_scale_animation((0.5, 0.5), (2.0, 2.0))
            
            engine.add_animation(f"test_anim_{i}", anim)
            engine.start_animation_at(f"test_anim_{i}", 0)
            animations.append(anim)
        
        # Warm up
        for tick in range(10):
            engine.compute_frame_state(tick)
        
        start_time = time.perf_counter()
        for iteration in range(iterations):
            for tick in range(60):  # 1 second of animation at 60fps
                frame_state = engine.compute_frame_state(tick)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        total_computations = iterations * 60 * animation_count
        avg_time_per_computation = total_time / total_computations
        
        return {
            'total_time': total_time,
            'total_computations': total_computations,
            'average_time_per_computation_us': avg_time_per_computation * 1_000_000,
            'computations_per_second': total_computations / total_time,
            'animations_tested': animation_count,
            'iterations': iterations,
            'target_fps_capable': avg_time_per_computation < (self.target_frame_time / animation_count)
        }
    
    def benchmark_easing_functions(self, iterations: int = 10000) -> Dict[str, Dict[str, float]]:
        """Benchmark all easing functions.
        
        Args:
            iterations: Number of iterations per easing function
            
        Returns:
            Performance statistics for each easing function
        """
        easing_functions = ["linear", "ease_in", "ease_out", "ease_in_out", "bounce", "elastic"]
        results = {}
        
        for easing_name in easing_functions:
            easing_func = TickEasing.get_easing_function(easing_name)
            
            # Test with and without optimization
            progress_values = [i / iterations for i in range(iterations)]
            
            # Unoptimized benchmark
            start_time = time.perf_counter()
            for progress in progress_values:
                result = easing_func(progress)
            unoptimized_time = time.perf_counter() - start_time
            
            # Optimized benchmark (with caching)
            self.optimizer.clear_cache()
            start_time = time.perf_counter()
            for progress in progress_values:
                result = self.optimizer.get_optimized_easing_result(easing_name, progress)
            optimized_time = time.perf_counter() - start_time
            
            cache_stats = self.optimizer.get_cache_statistics()
            
            results[easing_name] = {
                'unoptimized_time': unoptimized_time,
                'optimized_time': optimized_time,
                'speedup_factor': unoptimized_time / optimized_time if optimized_time > 0 else 1.0,
                'unoptimized_ops_per_second': iterations / unoptimized_time,
                'optimized_ops_per_second': iterations / optimized_time,
                'cache_hit_rate_percent': cache_stats['hit_rate_percent'],
                'iterations': iterations
            }
        
        return results
    
    def benchmark_full_animation_pipeline(self, duration_seconds: int = 5) -> Dict[str, Any]:
        """Benchmark complete animation pipeline for sustained performance.
        
        Args:
            duration_seconds: Duration to run benchmark
            
        Returns:
            Comprehensive performance statistics
        """
        from .utilities import create_fade_animation, create_slide_animation
        
        engine = TickAnimationEngine()
        
        # Create multiple animations
        animations = [
            create_fade_animation(0.0, 1.0),
            create_slide_animation((0, 0), (200, 150)),
            create_fade_animation(1.0, 0.0),
            create_slide_animation((200, 150), (0, 0))
        ]
        
        for i, anim in enumerate(animations):
            engine.add_animation(f"benchmark_anim_{i}", anim)
            engine.start_animation_at(f"benchmark_anim_{i}", 0)
        
        # Run benchmark
        start_time = time.perf_counter()
        frame_count = 0
        frame_times = []
        
        while time.perf_counter() - start_time < duration_seconds:
            frame_start = time.perf_counter()
            
            # Simulate full frame processing
            engine.advance_tick()
            frame_state = engine.compute_frame_state(engine.current_tick)
            
            # Simulate some processing time
            time.sleep(0.001)  # 1ms simulated processing
            
            frame_end = time.perf_counter()
            frame_time = frame_end - frame_start
            frame_times.append(frame_time)
            frame_count += 1
        
        total_time = time.perf_counter() - start_time
        
        # Calculate statistics
        avg_frame_time = statistics.mean(frame_times)
        min_frame_time = min(frame_times)
        max_frame_time = max(frame_times)
        avg_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
        
        # Count frames meeting target
        target_frames = sum(1 for ft in frame_times if ft <= self.target_frame_time)
        target_met_percent = (target_frames / frame_count * 100) if frame_count > 0 else 0.0
        
        return {
            'duration_seconds': total_time,
            'total_frames': frame_count,
            'average_fps': avg_fps,
            'min_fps': 1.0 / max_frame_time if max_frame_time > 0 else 0.0,
            'max_fps': 1.0 / min_frame_time if min_frame_time > 0 else 0.0,
            'average_frame_time_ms': avg_frame_time * 1000,
            'min_frame_time_ms': min_frame_time * 1000,
            'max_frame_time_ms': max_frame_time * 1000,
            'target_fps': self.target_fps,
            'target_frame_time_ms': self.target_frame_time * 1000,
            'target_met_percent': target_met_percent,
            'frames_meeting_target': target_frames,
            'performance_rating': self._calculate_performance_rating(avg_fps, target_met_percent)
        }
    
    def _calculate_performance_rating(self, avg_fps: float, target_met_percent: float) -> str:
        """Calculate performance rating based on metrics.
        
        Args:
            avg_fps: Average FPS achieved
            target_met_percent: Percentage of frames meeting target
            
        Returns:
            Performance rating string
        """
        if avg_fps >= self.target_fps * 0.95 and target_met_percent >= 95:
            return "Excellent"
        elif avg_fps >= self.target_fps * 0.9 and target_met_percent >= 90:
            return "Good"
        elif avg_fps >= self.target_fps * 0.8 and target_met_percent >= 80:
            return "Acceptable"
        elif avg_fps >= self.target_fps * 0.6 and target_met_percent >= 60:
            return "Poor"
        else:
            return "Unacceptable"
    
    def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive performance benchmark suite.
        
        Returns:
            Complete benchmark results
        """
        print("Running comprehensive animation performance benchmark...")
        
        results = {
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'python_version': f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}"
            },
            'target_performance': {
                'target_fps': self.target_fps,
                'target_frame_time_ms': self.target_frame_time * 1000
            }
        }
        
        # Tick advancement benchmark
        print("  Benchmarking tick advancement...")
        results['tick_advancement'] = self.benchmark_tick_advancement()
        
        # State computation benchmark
        print("  Benchmarking state computation...")
        results['state_computation'] = self.benchmark_state_computation()
        
        # Easing functions benchmark
        print("  Benchmarking easing functions...")
        results['easing_functions'] = self.benchmark_easing_functions()
        
        # Full pipeline benchmark
        print("  Benchmarking full animation pipeline...")
        results['full_pipeline'] = self.benchmark_full_animation_pipeline()
        
        # Overall assessment
        pipeline_rating = results['full_pipeline']['performance_rating']
        results['overall_assessment'] = {
            'performance_rating': pipeline_rating,
            'target_fps_capable': results['full_pipeline']['average_fps'] >= self.target_fps * 0.95,
            'recommended_for_production': pipeline_rating in ['Excellent', 'Good'],
            'optimization_needed': pipeline_rating in ['Poor', 'Unacceptable']
        }
        
        print(f"  Benchmark complete. Overall rating: {pipeline_rating}")
        return results


# Convenience functions for performance monitoring

def create_performance_monitor(enable_detailed: bool = True) -> AnimationPerformanceMonitor:
    """Create animation performance monitor.
    
    Args:
        enable_detailed: Enable detailed per-operation monitoring
        
    Returns:
        AnimationPerformanceMonitor instance
    """
    return AnimationPerformanceMonitor(enable_detailed)


def create_easing_optimizer(cache_size: int = 1000) -> EasingOptimizer:
    """Create easing function optimizer.
    
    Args:
        cache_size: Maximum cache size
        
    Returns:
        EasingOptimizer instance
    """
    optimizer = EasingOptimizer()
    optimizer.enable_caching(cache_size)
    return optimizer


def run_quick_performance_check(target_fps: float = 60.0) -> Dict[str, Any]:
    """Run quick performance check for animation system.
    
    Args:
        target_fps: Target frames per second
        
    Returns:
        Quick performance assessment
    """
    benchmark = PerformanceBenchmark(target_fps)
    
    # Quick tests
    tick_perf = benchmark.benchmark_tick_advancement(iterations=100)
    state_perf = benchmark.benchmark_state_computation(animation_count=5, iterations=10)
    
    return {
        'target_fps': target_fps,
        'tick_advancement_capable': tick_perf['target_fps_capable'],
        'state_computation_capable': state_perf['target_fps_capable'],
        'tick_ops_per_second': tick_perf['operations_per_second'],
        'state_computations_per_second': state_perf['computations_per_second'],
        'quick_assessment': 'PASS' if (tick_perf['target_fps_capable'] and state_perf['target_fps_capable']) else 'FAIL'
    } 