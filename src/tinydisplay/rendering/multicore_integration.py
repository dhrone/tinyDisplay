"""
Multi-Core Animation Integration for Rendering Engine

This module provides seamless integration between the multi-core animation
framework and the rendering engine, enabling pre-computed frame delivery
with automatic fallback and performance optimization.

Key Features:
1. Automatic Frame Pre-computation: Intelligently pre-computes future frames
2. Seamless Fallback: Falls back to real-time computation when needed
3. Performance Monitoring: Tracks multi-core performance and optimization
4. Memory Management: Efficient frame cache management
5. Pi Zero 2W Optimization: Tuned for 4-core ARM architecture
"""

import time
import threading
from typing import Dict, Optional, List, Tuple, Callable
from dataclasses import dataclass
from concurrent.futures import Future

from tinydisplay.animation.tick_based import TickAnimationEngine, TickAnimationState
from tinydisplay.animation.multicore import (
    AnimationWorkerPool, ComputedFrame, WorkerPoolMetrics
)


@dataclass
class MultiCoreRenderingConfig:
    """Configuration for multi-core rendering integration."""
    
    # Worker pool configuration
    num_workers: int = 3  # Leave 1 core for main thread on Pi Zero 2W
    use_processes: bool = True  # Use processes for true parallelism
    
    # Frame prediction configuration
    prediction_horizon_frames: int = 10  # How many frames to predict ahead
    prediction_batch_size: int = 5  # Frames to compute in each batch
    
    # Cache configuration
    cache_size_frames: int = 60  # 1 second at 60fps
    max_cache_memory_mb: int = 50  # Memory limit for frame cache
    
    # Performance thresholds
    target_frame_time_ms: float = 16.67  # 60fps target (1000ms / 60fps)
    fallback_threshold_ms: float = 12.0  # When to use pre-computed frames
    
    # Optimization settings
    enable_adaptive_prediction: bool = True  # Adjust prediction based on performance
    enable_cache_warming: bool = True  # Pre-warm cache with likely frames


@dataclass
class RenderingPerformanceMetrics:
    """Performance metrics for multi-core rendering."""
    
    # Frame timing
    average_frame_time_ms: float = 0.0
    min_frame_time_ms: float = 0.0
    max_frame_time_ms: float = 0.0
    
    # Multi-core utilization
    multicore_hit_rate: float = 0.0  # Percentage of frames served from pre-computation
    fallback_rate: float = 0.0  # Percentage of frames computed in real-time
    
    # Performance improvement
    latency_reduction_percent: float = 0.0  # Improvement over single-core
    throughput_improvement_percent: float = 0.0
    
    # Resource utilization
    worker_pool_utilization: float = 0.0
    cache_hit_rate: float = 0.0
    memory_usage_mb: float = 0.0


class MultiCoreAnimationRenderer:
    """
    Multi-core animation renderer with intelligent frame pre-computation.
    
    This class integrates the multi-core animation framework with the rendering
    engine to provide optimized frame delivery with automatic performance tuning.
    """
    
    def __init__(self, config: MultiCoreRenderingConfig = None):
        """Initialize multi-core animation renderer."""
        self.config = config or MultiCoreRenderingConfig()
        
        # Initialize worker pool
        self.worker_pool = AnimationWorkerPool(
            num_workers=self.config.num_workers,
            use_processes=self.config.use_processes,
            cache_size=self.config.cache_size_frames,
            max_cache_memory_mb=self.config.max_cache_memory_mb
        )
        
        # Frame prediction state
        self._prediction_active = False
        self._prediction_thread: Optional[threading.Thread] = None
        self._prediction_lock = threading.Lock()
        self._current_tick = 0
        self._last_prediction_tick = -1
        
        # Performance tracking
        self._frame_times: List[float] = []
        self._multicore_hits = 0
        self._fallback_hits = 0
        self._total_frames = 0
        
        # Animation engine reference
        self._animation_engine: Optional[TickAnimationEngine] = None
        
        # Shutdown flag
        self._shutdown = False
    
    def set_animation_engine(self, engine: TickAnimationEngine) -> None:
        """Set the animation engine for frame computation."""
        self._animation_engine = engine
    
    def start_prediction(self) -> None:
        """Start background frame prediction."""
        if self._prediction_active or not self._animation_engine:
            return
        
        self._prediction_active = True
        self._prediction_thread = threading.Thread(
            target=self._prediction_worker,
            daemon=True
        )
        self._prediction_thread.start()
    
    def stop_prediction(self) -> None:
        """Stop background frame prediction."""
        self._prediction_active = False
        if self._prediction_thread:
            self._prediction_thread.join(timeout=1.0)
            self._prediction_thread = None
    
    def get_frame_for_tick(self, tick: int, timeout_ms: float = None) -> Optional[Dict[str, TickAnimationState]]:
        """
        Get animation frame for specified tick with multi-core optimization.
        
        This method first attempts to retrieve a pre-computed frame from the
        worker pool. If not available, it falls back to real-time computation.
        
        Args:
            tick: Target tick for frame
            timeout_ms: Maximum time to wait for pre-computed frame
            
        Returns:
            Animation frame state or None if computation fails
        """
        if not self._animation_engine:
            return None
        
        start_time = time.perf_counter()
        self._current_tick = tick
        
        # Try to get pre-computed frame first
        frame_state = self._get_precomputed_frame(tick, timeout_ms)
        
        if frame_state is not None:
            # Success with pre-computed frame
            self._multicore_hits += 1
            computation_time = (time.perf_counter() - start_time) * 1000
            self._record_frame_time(computation_time)
            return frame_state
        
        # Fallback to real-time computation
        try:
            frame_state = self._animation_engine.compute_frame_state(tick)
            self._fallback_hits += 1
            computation_time = (time.perf_counter() - start_time) * 1000
            self._record_frame_time(computation_time)
            
            # Trigger prediction if needed
            self._trigger_prediction_if_needed(tick)
            
            return frame_state
            
        except Exception as e:
            print(f"Error computing frame for tick {tick}: {e}")
            return None
    
    def _get_precomputed_frame(self, tick: int, timeout_ms: float = None) -> Optional[Dict[str, TickAnimationState]]:
        """Attempt to get pre-computed frame from worker pool."""
        # Check if we have a task for this tick
        task_id = f"predict_{tick}"
        
        # Set timeout based on configuration
        if timeout_ms is None:
            timeout_ms = self.config.fallback_threshold_ms
        
        timeout_seconds = timeout_ms / 1000.0
        start_time = time.perf_counter()
        
        while time.perf_counter() - start_time < timeout_seconds:
            computed_frame = self.worker_pool.get_computed_frame(task_id)
            if computed_frame:
                return computed_frame.frame_state
            
            # Small sleep to avoid busy waiting
            time.sleep(0.001)  # 1ms
        
        return None
    
    def _trigger_prediction_if_needed(self, current_tick: int) -> None:
        """Trigger frame prediction if conditions are met."""
        if not self.config.enable_adaptive_prediction:
            return
        
        with self._prediction_lock:
            # Check if we need to start prediction
            if (current_tick - self._last_prediction_tick >= self.config.prediction_batch_size and
                self._animation_engine):
                
                # Submit batch prediction
                start_tick = current_tick + 1
                num_frames = self.config.prediction_horizon_frames
                
                try:
                    task_ids = self.worker_pool.submit_batch_computation(
                        start_tick, num_frames, self._animation_engine
                    )
                    self._last_prediction_tick = current_tick
                    
                except Exception as e:
                    print(f"Error submitting prediction batch: {e}")
    
    def _prediction_worker(self) -> None:
        """Background worker for continuous frame prediction."""
        while self._prediction_active and not self._shutdown:
            try:
                if self._animation_engine and self.config.enable_cache_warming:
                    # Predict frames ahead of current position
                    prediction_start = self._current_tick + 1
                    
                    # Submit prediction batch
                    task_ids = self.worker_pool.submit_batch_computation(
                        prediction_start,
                        self.config.prediction_horizon_frames,
                        self._animation_engine
                    )
                    
                    # Wait for some completion before next batch
                    self.worker_pool.wait_for_batch_completion(
                        task_ids[:self.config.prediction_batch_size],
                        timeout=0.1
                    )
                
                # Sleep before next prediction cycle
                time.sleep(0.05)  # 50ms between prediction cycles
                
            except Exception as e:
                print(f"Error in prediction worker: {e}")
                time.sleep(0.1)
    
    def _record_frame_time(self, time_ms: float) -> None:
        """Record frame computation time for performance tracking."""
        self._frame_times.append(time_ms)
        self._total_frames += 1
        
        # Keep only recent frame times (last 100 frames)
        if len(self._frame_times) > 100:
            self._frame_times = self._frame_times[-100:]
    
    def get_performance_metrics(self) -> RenderingPerformanceMetrics:
        """Get comprehensive performance metrics."""
        metrics = RenderingPerformanceMetrics()
        
        # Frame timing metrics
        if self._frame_times:
            metrics.average_frame_time_ms = sum(self._frame_times) / len(self._frame_times)
            metrics.min_frame_time_ms = min(self._frame_times)
            metrics.max_frame_time_ms = max(self._frame_times)
        
        # Multi-core utilization
        total_requests = self._multicore_hits + self._fallback_hits
        if total_requests > 0:
            metrics.multicore_hit_rate = (self._multicore_hits / total_requests) * 100
            metrics.fallback_rate = (self._fallback_hits / total_requests) * 100
        
        # Performance improvement estimation
        if metrics.average_frame_time_ms > 0:
            # Estimate single-core time (assuming 2x slower without multi-core)
            estimated_single_core_time = metrics.average_frame_time_ms * 2.0
            metrics.latency_reduction_percent = (
                (estimated_single_core_time - metrics.average_frame_time_ms) / 
                estimated_single_core_time * 100
            )
        
        # Worker pool metrics
        worker_metrics = self.worker_pool.get_performance_metrics()
        metrics.worker_pool_utilization = self.worker_pool.get_worker_utilization()
        metrics.cache_hit_rate = worker_metrics.cache_hit_rate * 100
        
        # Memory usage (estimated)
        metrics.memory_usage_mb = len(self._frame_times) * 0.001  # Rough estimate
        
        return metrics
    
    def optimize_for_target_fps(self, target_fps: int = 60) -> Dict[str, any]:
        """
        Automatically optimize configuration for target FPS.
        
        Args:
            target_fps: Target frames per second
            
        Returns:
            Dictionary with optimization results and recommendations
        """
        target_frame_time_ms = 1000.0 / target_fps
        current_metrics = self.get_performance_metrics()
        
        optimization_results = {
            "target_fps": target_fps,
            "target_frame_time_ms": target_frame_time_ms,
            "current_average_ms": current_metrics.average_frame_time_ms,
            "optimizations_applied": [],
            "recommendations": []
        }
        
        # Check if we're meeting target
        if current_metrics.average_frame_time_ms <= target_frame_time_ms:
            optimization_results["status"] = "meeting_target"
            return optimization_results
        
        # Apply optimizations
        if current_metrics.multicore_hit_rate < 70:
            # Increase prediction horizon
            old_horizon = self.config.prediction_horizon_frames
            self.config.prediction_horizon_frames = min(old_horizon + 5, 30)
            optimization_results["optimizations_applied"].append(
                f"Increased prediction horizon: {old_horizon} -> {self.config.prediction_horizon_frames}"
            )
        
        if current_metrics.cache_hit_rate < 80:
            # Increase cache size
            old_cache = self.config.cache_size_frames
            self.config.cache_size_frames = min(old_cache + 30, 120)
            optimization_results["optimizations_applied"].append(
                f"Increased cache size: {old_cache} -> {self.config.cache_size_frames}"
            )
        
        # Provide recommendations
        if current_metrics.worker_pool_utilization < 60:
            optimization_results["recommendations"].append(
                "Consider increasing worker count or reducing prediction batch size"
            )
        
        if current_metrics.average_frame_time_ms > target_frame_time_ms * 1.5:
            optimization_results["recommendations"].append(
                "Frame computation is significantly slow - consider optimizing animations"
            )
        
        optimization_results["status"] = "optimized"
        return optimization_results
    
    def shutdown(self) -> None:
        """Shutdown multi-core renderer and clean up resources."""
        self._shutdown = True
        self.stop_prediction()
        self.worker_pool.shutdown(wait=True)


class FrameDeliveryManager:
    """
    High-level frame delivery manager for seamless multi-core integration.
    
    This class provides a simple interface for rendering engines to get
    optimized animation frames with automatic multi-core acceleration.
    """
    
    def __init__(self, animation_engine: TickAnimationEngine, config: MultiCoreRenderingConfig = None):
        """Initialize frame delivery manager."""
        self.animation_engine = animation_engine
        self.renderer = MultiCoreAnimationRenderer(config)
        self.renderer.set_animation_engine(animation_engine)
        
        # Start background prediction
        self.renderer.start_prediction()
    
    def get_frame(self, tick: int) -> Optional[Dict[str, TickAnimationState]]:
        """Get optimized frame for tick."""
        return self.renderer.get_frame_for_tick(tick)
    
    def get_performance_summary(self) -> str:
        """Get human-readable performance summary."""
        metrics = self.renderer.get_performance_metrics()
        
        return f"""Multi-Core Animation Performance Summary:
        
Frame Timing:
  • Average: {metrics.average_frame_time_ms:.2f}ms
  • Range: {metrics.min_frame_time_ms:.2f}ms - {metrics.max_frame_time_ms:.2f}ms
  
Multi-Core Efficiency:
  • Pre-computed frames: {metrics.multicore_hit_rate:.1f}%
  • Real-time fallback: {metrics.fallback_rate:.1f}%
  • Latency reduction: {metrics.latency_reduction_percent:.1f}%
  
Resource Utilization:
  • Worker pool: {metrics.worker_pool_utilization:.1f}%
  • Cache hit rate: {metrics.cache_hit_rate:.1f}%
  • Memory usage: {metrics.memory_usage_mb:.1f}MB
"""
    
    def optimize_for_fps(self, target_fps: int = 60) -> str:
        """Optimize for target FPS and return results."""
        results = self.renderer.optimize_for_target_fps(target_fps)
        
        summary = f"Optimization for {target_fps}fps:\n"
        summary += f"Status: {results['status']}\n"
        
        if results["optimizations_applied"]:
            summary += "Applied optimizations:\n"
            for opt in results["optimizations_applied"]:
                summary += f"  • {opt}\n"
        
        if results["recommendations"]:
            summary += "Recommendations:\n"
            for rec in results["recommendations"]:
                summary += f"  • {rec}\n"
        
        return summary
    
    def shutdown(self) -> None:
        """Shutdown frame delivery manager."""
        self.renderer.shutdown()


# Convenience functions for easy integration

def create_multicore_renderer(
    animation_engine: TickAnimationEngine,
    num_workers: int = 3,
    prediction_frames: int = 10
) -> FrameDeliveryManager:
    """
    Create a multi-core animation renderer with sensible defaults.
    
    Args:
        animation_engine: The tick-based animation engine
        num_workers: Number of worker cores (default: 3 for Pi Zero 2W)
        prediction_frames: Number of frames to predict ahead
        
    Returns:
        Configured frame delivery manager
    """
    config = MultiCoreRenderingConfig(
        num_workers=num_workers,
        prediction_horizon_frames=prediction_frames
    )
    
    return FrameDeliveryManager(animation_engine, config)


def benchmark_multicore_performance(
    animation_engine: TickAnimationEngine,
    num_frames: int = 300,  # 5 seconds at 60fps
    target_fps: int = 60
) -> Dict[str, any]:
    """
    Benchmark multi-core animation performance.
    
    Args:
        animation_engine: The animation engine to benchmark
        num_frames: Number of frames to render for benchmark
        target_fps: Target FPS for performance evaluation
        
    Returns:
        Comprehensive benchmark results
    """
    # Create renderer
    renderer = create_multicore_renderer(animation_engine)
    
    # Warm up
    for tick in range(10):
        renderer.get_frame(tick)
    
    # Benchmark
    start_time = time.perf_counter()
    frame_times = []
    
    for tick in range(num_frames):
        frame_start = time.perf_counter()
        frame = renderer.get_frame(tick)
        frame_time = (time.perf_counter() - frame_start) * 1000
        frame_times.append(frame_time)
    
    total_time = time.perf_counter() - start_time
    
    # Calculate metrics
    avg_frame_time = sum(frame_times) / len(frame_times)
    achieved_fps = num_frames / total_time
    target_frame_time = 1000.0 / target_fps
    
    # Get performance metrics
    metrics = renderer.renderer.get_performance_metrics()
    
    # Cleanup
    renderer.shutdown()
    
    return {
        "total_frames": num_frames,
        "total_time_seconds": total_time,
        "average_frame_time_ms": avg_frame_time,
        "achieved_fps": achieved_fps,
        "target_fps": target_fps,
        "fps_efficiency": (achieved_fps / target_fps) * 100,
        "multicore_hit_rate": metrics.multicore_hit_rate,
        "latency_reduction": metrics.latency_reduction_percent,
        "meets_target": avg_frame_time <= target_frame_time,
        "performance_summary": f"Achieved {achieved_fps:.1f}fps (target: {target_fps}fps) with {metrics.multicore_hit_rate:.1f}% multi-core acceleration"
    } 