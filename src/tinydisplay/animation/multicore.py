"""
Multi-Core Animation Framework for Deterministic Frame Pre-Computation

This module provides a multi-core worker pool system for pre-computing animation
frames ahead of display time. It leverages the deterministic nature of the
tick-based animation system to enable safe distributed computation across CPU cores.

Key Features:
1. Worker Pool Architecture: Distributes frame computation across available cores
2. Frame Cache System: Intelligent caching with tick-based indexing
3. Serialization Support: Efficient cross-core communication
4. Performance Monitoring: Real-time metrics and optimization
5. Pi Zero 2W Optimization: Tuned for 4-core ARM Cortex-A53 architecture
"""

import pickle
import zlib
import time
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from queue import Queue, Empty
from collections import OrderedDict
import multiprocessing as mp

from .tick_based import TickAnimationEngine, TickAnimationState, TickAnimationDefinition


@dataclass
class FrameComputationTask:
    """Task definition for frame computation on worker cores."""
    task_id: str
    tick: int
    engine_state: bytes
    priority: int = 0
    created_at: float = field(default_factory=time.perf_counter)


@dataclass
class ComputedFrame:
    """Result of frame computation from worker core."""
    task_id: str
    tick: int
    frame_state: Dict[str, TickAnimationState]
    computation_time: float
    worker_id: str
    completed_at: float = field(default_factory=time.perf_counter)


@dataclass
class WorkerPoolMetrics:
    """Performance metrics for worker pool operations."""
    total_tasks_submitted: int = 0
    total_tasks_completed: int = 0
    total_computation_time: float = 0.0
    average_task_time: float = 0.0
    worker_utilization: Dict[str, float] = field(default_factory=dict)
    cache_hit_rate: float = 0.0
    cache_miss_rate: float = 0.0
    frames_per_second: float = 0.0
    
    def update_completion(self, computation_time: float, worker_id: str) -> None:
        """Update metrics when a task completes."""
        self.total_tasks_completed += 1
        self.total_computation_time += computation_time
        self.average_task_time = self.total_computation_time / max(1, self.total_tasks_completed)
        
        # Update worker utilization
        if worker_id not in self.worker_utilization:
            self.worker_utilization[worker_id] = 0.0
        self.worker_utilization[worker_id] += computation_time


class AnimationStateSerializer:
    """Handles serialization/deserialization of animation state for cross-core communication."""
    
    @staticmethod
    def serialize_engine_state(engine: TickAnimationEngine) -> bytes:
        """Serialize engine state for cross-core communication.
        
        Args:
            engine: TickAnimationEngine to serialize
            
        Returns:
            Compressed serialized state data
        """
        state_data = engine.serialize_engine_state()
        # Compress for efficient transfer between cores
        return zlib.compress(pickle.dumps(state_data), level=6)
    
    @staticmethod
    def deserialize_engine_state(state_data: bytes) -> TickAnimationEngine:
        """Recreate engine from serialized state.
        
        Args:
            state_data: Compressed serialized state
            
        Returns:
            Reconstructed TickAnimationEngine
        """
        decompressed = pickle.loads(zlib.decompress(state_data))
        return TickAnimationEngine.deserialize_engine_state(decompressed)
    
    @staticmethod
    def serialize_frame_state(frame_state: Dict[str, TickAnimationState]) -> bytes:
        """Serialize frame state for caching.
        
        Args:
            frame_state: Frame state to serialize
            
        Returns:
            Compressed serialized frame state
        """
        serializable_state = {
            animation_id: state.serialize()
            for animation_id, state in frame_state.items()
        }
        return zlib.compress(pickle.dumps(serializable_state), level=6)
    
    @staticmethod
    def deserialize_frame_state(state_data: bytes) -> Dict[str, TickAnimationState]:
        """Deserialize frame state from cache.
        
        Args:
            state_data: Compressed serialized frame state
            
        Returns:
            Reconstructed frame state
        """
        decompressed = pickle.loads(zlib.decompress(state_data))
        return {
            animation_id: TickAnimationState.deserialize(state_data)
            for animation_id, state_data in decompressed.items()
        }


class DistributedFrameCache:
    """Intelligent frame cache with tick-based indexing and memory management."""
    
    def __init__(self, max_frames: int = 120, max_memory_mb: int = 50):
        """Initialize distributed frame cache.
        
        Args:
            max_frames: Maximum number of frames to cache (default: 2 seconds at 60fps)
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_frames = max_frames
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict[int, bytes] = OrderedDict()
        self.cache_lock = threading.RLock()
        self.hit_count = 0
        self.miss_count = 0
        self.current_memory_usage = 0
    
    def get_frame(self, tick: int) -> Optional[Dict[str, TickAnimationState]]:
        """Retrieve frame from cache if available.
        
        Args:
            tick: Tick to retrieve
            
        Returns:
            Frame state if cached, None otherwise
        """
        with self.cache_lock:
            if tick in self.cache:
                # Move to end (most recently used)
                serialized_frame = self.cache.pop(tick)
                self.cache[tick] = serialized_frame
                self.hit_count += 1
                
                try:
                    return AnimationStateSerializer.deserialize_frame_state(serialized_frame)
                except Exception:
                    # Remove corrupted cache entry
                    del self.cache[tick]
                    self.miss_count += 1
                    return None
            else:
                self.miss_count += 1
                return None
    
    def store_frame(self, tick: int, frame_state: Dict[str, TickAnimationState]) -> bool:
        """Store frame in cache.
        
        Args:
            tick: Tick to store
            frame_state: Frame state to cache
            
        Returns:
            True if stored successfully, False if cache is full
        """
        try:
            serialized_frame = AnimationStateSerializer.serialize_frame_state(frame_state)
            frame_size = len(serialized_frame)
            
            with self.cache_lock:
                # Check memory limits
                if self.current_memory_usage + frame_size > self.max_memory_bytes:
                    self._evict_frames(frame_size)
                
                # Check frame count limits
                while len(self.cache) >= self.max_frames:
                    self._evict_oldest_frame()
                
                # Store frame
                self.cache[tick] = serialized_frame
                self.current_memory_usage += frame_size
                return True
                
        except Exception:
            return False
    
    def _evict_frames(self, required_space: int) -> None:
        """Evict frames to free required space."""
        while (self.current_memory_usage + required_space > self.max_memory_bytes and 
               self.cache):
            self._evict_oldest_frame()
    
    def _evict_oldest_frame(self) -> None:
        """Evict the oldest frame from cache."""
        if self.cache:
            tick, serialized_frame = self.cache.popitem(last=False)
            self.current_memory_usage -= len(serialized_frame)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / max(1, total_requests)
        
        with self.cache_lock:
            return {
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate': hit_rate,
                'cached_frames': len(self.cache),
                'memory_usage_mb': self.current_memory_usage / (1024 * 1024),
                'memory_usage_percent': (self.current_memory_usage / self.max_memory_bytes) * 100
            }
    
    def clear_cache(self) -> None:
        """Clear all cached frames."""
        with self.cache_lock:
            self.cache.clear()
            self.current_memory_usage = 0


def _compute_frame_worker(task: FrameComputationTask) -> ComputedFrame:
    """Worker function for frame computation (module-level for pickling).
    
    This function runs on worker processes and must be at module level
    for proper serialization by multiprocessing.
    
    Args:
        task: Frame computation task
        
    Returns:
        Computed frame result
    """
    start_time = time.perf_counter()
    worker_id = f"worker-{mp.current_process().pid}"
    
    try:
        # Deserialize engine state
        engine = AnimationStateSerializer.deserialize_engine_state(task.engine_state)
        
        # Compute frame state at target tick
        frame_state = engine.predict_frame_at_tick(task.tick)
        
        computation_time = time.perf_counter() - start_time
        
        return ComputedFrame(
            task_id=task.task_id,
            tick=task.tick,
            frame_state=frame_state,
            computation_time=computation_time,
            worker_id=worker_id
        )
        
    except Exception as e:
        # Return error frame
        computation_time = time.perf_counter() - start_time
        return ComputedFrame(
            task_id=task.task_id,
            tick=task.tick,
            frame_state={},  # Empty frame indicates error
            computation_time=computation_time,
            worker_id=f"{worker_id}-error",
        )


class AnimationWorkerPool:
    """Multi-core worker pool for distributed frame computation.
    
    Optimized for Pi Zero 2W (4 cores) with intelligent task distribution
    and performance monitoring.
    """
    
    def __init__(self, num_workers: int = 3, use_processes: bool = True, 
                 cache_size: int = 120, max_cache_memory_mb: int = 50):
        """Initialize animation worker pool.
        
        Args:
            num_workers: Number of worker cores (default 3, leaving 1 for main thread)
            use_processes: Use processes vs threads for true parallelism
            cache_size: Maximum frames to cache
            max_cache_memory_mb: Maximum cache memory in MB
        """
        self.num_workers = num_workers
        self.use_processes = use_processes
        
        # Initialize executor
        if use_processes:
            self.executor = ProcessPoolExecutor(max_workers=num_workers)
        else:
            self.executor = ThreadPoolExecutor(max_workers=num_workers)
        
        # Initialize components
        self.frame_cache = DistributedFrameCache(cache_size, max_cache_memory_mb)
        self.metrics = WorkerPoolMetrics()
        self.active_tasks: Dict[str, Future] = {}
        self.task_counter = 0
        self.shutdown_requested = False
        
        # Performance monitoring
        self._last_metrics_update = time.perf_counter()
        self._completed_tasks_since_update = 0
    
    def submit_frame_computation(self, tick: int, engine: TickAnimationEngine, 
                               priority: int = 0) -> str:
        """Submit frame computation task to worker pool.
        
        Args:
            tick: Tick to compute
            engine: Animation engine state
            priority: Task priority (higher = more important)
            
        Returns:
            Task ID for tracking completion
        """
        # Check cache first
        cached_frame = self.frame_cache.get_frame(tick)
        if cached_frame is not None:
            # Return synthetic task ID for cached result
            return f"cached-{tick}"
        
        # Create computation task
        self.task_counter += 1
        task_id = f"task-{self.task_counter}-{tick}"
        
        try:
            engine_state = AnimationStateSerializer.serialize_engine_state(engine)
            task = FrameComputationTask(
                task_id=task_id,
                tick=tick,
                engine_state=engine_state,
                priority=priority
            )
            
            # Submit to worker pool
            future = self.executor.submit(_compute_frame_worker, task)
            self.active_tasks[task_id] = future
            self.metrics.total_tasks_submitted += 1
            
            return task_id
            
        except Exception:
            return f"error-{tick}"
    
    def get_computed_frame(self, task_id: str, timeout: float = 0.001) -> Optional[ComputedFrame]:
        """Retrieve computed frame if ready (non-blocking).
        
        Args:
            task_id: Task ID from submit_frame_computation
            timeout: Maximum time to wait for result
            
        Returns:
            ComputedFrame if ready, None if still computing
        """
        # Handle cached results
        if task_id.startswith("cached-"):
            tick = int(task_id.split("-")[1])
            cached_frame = self.frame_cache.get_frame(tick)
            if cached_frame:
                return ComputedFrame(
                    task_id=task_id,
                    tick=tick,
                    frame_state=cached_frame,
                    computation_time=0.0,
                    worker_id="cache"
                )
            return None
        
        # Handle error tasks
        if task_id.startswith("error-"):
            return None
        
        # Check active tasks
        if task_id not in self.active_tasks:
            return None
        
        future = self.active_tasks[task_id]
        if future.done():
            try:
                result = future.result(timeout=timeout)
                del self.active_tasks[task_id]
                
                # Update metrics
                self.metrics.update_completion(result.computation_time, result.worker_id)
                self._completed_tasks_since_update += 1
                
                # Cache successful results
                if result.frame_state:  # Non-empty indicates success
                    self.frame_cache.store_frame(result.tick, result.frame_state)
                
                return result
                
            except Exception:
                del self.active_tasks[task_id]
                return None
        
        return None
    
    def submit_batch_computation(self, start_tick: int, num_frames: int, 
                               engine: TickAnimationEngine) -> List[str]:
        """Submit batch of frame computations optimized for worker distribution.
        
        Args:
            start_tick: Starting tick for batch
            num_frames: Number of frames to compute
            engine: Animation engine state
            
        Returns:
            List of task IDs for tracking completion
        """
        # Get workload distribution
        workload = engine.get_prediction_workload(start_tick, num_frames, self.num_workers)
        task_ids = []
        
        # Submit tasks for each worker chunk
        for worker_start, worker_end in workload:
            for tick in range(worker_start, worker_end + 1):
                task_id = self.submit_frame_computation(tick, engine)
                task_ids.append(task_id)
        
        return task_ids
    
    def wait_for_batch_completion(self, task_ids: List[str], 
                                timeout: float = 5.0) -> Dict[str, ComputedFrame]:
        """Wait for batch of tasks to complete.
        
        Args:
            task_ids: List of task IDs to wait for
            timeout: Maximum time to wait for all tasks
            
        Returns:
            Dictionary mapping task IDs to completed frames
        """
        completed_frames = {}
        start_time = time.perf_counter()
        
        while (len(completed_frames) < len(task_ids) and 
               time.perf_counter() - start_time < timeout):
            
            for task_id in task_ids:
                if task_id not in completed_frames:
                    frame = self.get_computed_frame(task_id, timeout=0.01)
                    if frame:
                        completed_frames[task_id] = frame
            
            # Small sleep to prevent busy waiting
            time.sleep(0.001)
        
        return completed_frames
    
    def get_performance_metrics(self) -> WorkerPoolMetrics:
        """Get current performance metrics."""
        # Update frames per second calculation
        current_time = time.perf_counter()
        time_delta = current_time - self._last_metrics_update
        
        if time_delta > 1.0:  # Update every second
            self.metrics.frames_per_second = self._completed_tasks_since_update / time_delta
            self._last_metrics_update = current_time
            self._completed_tasks_since_update = 0
        
        # Update cache metrics
        cache_stats = self.frame_cache.get_cache_stats()
        self.metrics.cache_hit_rate = cache_stats['hit_rate']
        self.metrics.cache_miss_rate = 1.0 - cache_stats['hit_rate']
        
        return self.metrics
    
    def get_worker_utilization(self) -> float:
        """Calculate overall worker utilization percentage.
        
        Returns:
            Worker utilization as percentage (0-100)
        """
        if not self.metrics.worker_utilization:
            return 0.0
        
        total_time = sum(self.metrics.worker_utilization.values())
        elapsed_time = time.perf_counter() - self._last_metrics_update
        max_possible_time = self.num_workers * elapsed_time
        
        if max_possible_time > 0:
            return min(100.0, (total_time / max_possible_time) * 100.0)
        return 0.0
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown worker pool and cleanup resources.
        
        Args:
            wait: Whether to wait for active tasks to complete
        """
        self.shutdown_requested = True
        
        if wait:
            # Wait for active tasks to complete
            for task_id, future in list(self.active_tasks.items()):
                try:
                    future.result(timeout=1.0)
                except Exception:
                    pass
        
        # Shutdown executor
        self.executor.shutdown(wait=wait)
        
        # Clear cache
        self.frame_cache.clear_cache()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown(wait=True) 