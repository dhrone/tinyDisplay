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
from .coordination import CoordinationEngine, CoordinationEvent, CoordinationPrimitive
from .timeline import TickTimeline, CoordinationPlan


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
class CoordinationComputationTask:
    """Task definition for coordination event computation on worker cores."""
    task_id: str
    start_tick: int
    end_tick: int
    engine_state: bytes
    coordination_state: bytes
    timeline_state: bytes
    priority: int = 0
    created_at: float = field(default_factory=time.perf_counter)


@dataclass
class ComputedCoordinationEvents:
    """Result of coordination event computation from worker core."""
    task_id: str
    start_tick: int
    end_tick: int
    coordination_events: List[CoordinationEvent]
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
    average_evaluation_time: float = 0.0
    worker_utilization: Dict[str, float] = field(default_factory=dict)
    cache_hit_rate: float = 0.0
    cache_miss_rate: float = 0.0
    frames_per_second: float = 0.0
    
    def update_completion(self, computation_time: float, worker_id: str) -> None:
        """Update metrics when a task completes."""
        self.total_tasks_completed += 1
        self.total_computation_time += computation_time
        self.average_task_time = self.total_computation_time / max(1, self.total_tasks_completed)
        self.average_evaluation_time = self.average_task_time
        
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
    
    @staticmethod
    def serialize_coordination_state(coordination_engine: CoordinationEngine) -> bytes:
        """Serialize coordination engine state for cross-core communication.
        
        Args:
            coordination_engine: CoordinationEngine to serialize
            
        Returns:
            Compressed serialized coordination state
        """
        state_data = {
            'current_tick': coordination_engine.current_tick,
            'primitives': {
                pid: {
                    'type': type(primitive).__name__,
                    'state': primitive.serialize_state() if hasattr(primitive, 'serialize_state') else {},
                    'coordination_id': primitive.coordination_id,
                    'state_enum': primitive.state.value,
                    'created_tick': primitive.created_tick,
                    'activated_tick': primitive.activated_tick,
                    'completed_tick': primitive.completed_tick
                }
                for pid, primitive in coordination_engine.primitives.items()
            },
            'event_history': [
                {
                    'event_type': event.event_type.value,
                    'tick': event.tick,
                    'coordination_id': event.coordination_id,
                    'data': event.data,
                    'timestamp': event.timestamp
                }
                for event in coordination_engine.event_history[-100:]  # Last 100 events
            ]
        }
        return zlib.compress(pickle.dumps(state_data), level=6)
    
    @staticmethod
    def serialize_timeline_state(timeline: TickTimeline) -> bytes:
        """Serialize timeline state for cross-core communication.
        
        Args:
            timeline: TickTimeline to serialize
            
        Returns:
            Compressed serialized timeline state
        """
        return timeline.serialize_timeline_state()
    
    @staticmethod
    def serialize_coordination_events(events: List[CoordinationEvent]) -> bytes:
        """Serialize coordination events for caching.
        
        Args:
            events: List of coordination events to serialize
            
        Returns:
            Compressed serialized events
        """
        serializable_events = [
            {
                'event_type': event.event_type.value,
                'tick': event.tick,
                'coordination_id': event.coordination_id,
                'data': event.data,
                'timestamp': event.timestamp
            }
            for event in events
        ]
        return zlib.compress(pickle.dumps(serializable_events), level=6)
    
    @staticmethod
    def deserialize_coordination_events(state_data: bytes) -> List[CoordinationEvent]:
        """Deserialize coordination events from cache.
        
        Args:
            state_data: Compressed serialized events
            
        Returns:
            Reconstructed coordination events
        """
        from .coordination import CoordinationEventType
        
        decompressed = pickle.loads(zlib.decompress(state_data))
        events = []
        
        for event_data in decompressed:
            event = CoordinationEvent(
                event_type=CoordinationEventType(event_data['event_type']),
                tick=event_data['tick'],
                coordination_id=event_data['coordination_id'],
                data=event_data['data']
            )
            event.timestamp = event_data['timestamp']
            events.append(event)
        
        return events


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


class DistributedCoordinationCache:
    """Cache for coordination events and timeline states with tick-based indexing."""
    
    def __init__(self, max_entries: int = 200, max_memory_mb: int = 20):
        """Initialize coordination cache.
        
        Args:
            max_entries: Maximum number of cache entries
            max_memory_mb: Maximum memory usage in MB
        """
        self.max_entries = max_entries
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.event_cache: OrderedDict[Tuple[int, int], bytes] = OrderedDict()  # (start_tick, end_tick) -> events
        self.timeline_cache: OrderedDict[int, bytes] = OrderedDict()  # tick -> timeline_state
        self.cache_lock = threading.RLock()
        self.hit_count = 0
        self.miss_count = 0
        self.current_memory_usage = 0
    
    def get_coordination_events(self, start_tick: int, end_tick: int) -> Optional[List[CoordinationEvent]]:
        """Retrieve coordination events from cache if available.
        
        Args:
            start_tick: Start tick for event range
            end_tick: End tick for event range
            
        Returns:
            Coordination events if cached, None otherwise
        """
        cache_key = (start_tick, end_tick)
        
        with self.cache_lock:
            if cache_key in self.event_cache:
                # Move to end (most recently used)
                serialized_events = self.event_cache.pop(cache_key)
                self.event_cache[cache_key] = serialized_events
                self.hit_count += 1
                
                try:
                    return AnimationStateSerializer.deserialize_coordination_events(serialized_events)
                except Exception:
                    # Remove corrupted cache entry
                    del self.event_cache[cache_key]
                    self.miss_count += 1
                    return None
            else:
                self.miss_count += 1
                return None
    
    def store_coordination_events(self, start_tick: int, end_tick: int, 
                                 events: List[CoordinationEvent]) -> bool:
        """Store coordination events in cache.
        
        Args:
            start_tick: Start tick for event range
            end_tick: End tick for event range
            events: Coordination events to cache
            
        Returns:
            True if stored successfully, False if cache is full
        """
        try:
            serialized_events = AnimationStateSerializer.serialize_coordination_events(events)
            event_size = len(serialized_events)
            cache_key = (start_tick, end_tick)
            
            with self.cache_lock:
                # Check memory limits
                if self.current_memory_usage + event_size > self.max_memory_bytes:
                    self._evict_coordination_entries(event_size)
                
                # Check entry limits
                if len(self.event_cache) >= self.max_entries:
                    self._evict_oldest_coordination_entry()
                
                self.event_cache[cache_key] = serialized_events
                self.current_memory_usage += event_size
                return True
                
        except Exception:
            return False
    
    def get_timeline_state(self, tick: int) -> Optional[bytes]:
        """Retrieve timeline state from cache.
        
        Args:
            tick: Tick to retrieve timeline state for
            
        Returns:
            Serialized timeline state if cached, None otherwise
        """
        with self.cache_lock:
            if tick in self.timeline_cache:
                # Move to end (most recently used)
                timeline_state = self.timeline_cache.pop(tick)
                self.timeline_cache[tick] = timeline_state
                self.hit_count += 1
                return timeline_state
            else:
                self.miss_count += 1
                return None
    
    def store_timeline_state(self, tick: int, timeline_state: bytes) -> bool:
        """Store timeline state in cache.
        
        Args:
            tick: Tick for timeline state
            timeline_state: Serialized timeline state
            
        Returns:
            True if stored successfully, False if cache is full
        """
        state_size = len(timeline_state)
        
        with self.cache_lock:
            # Check memory limits
            if self.current_memory_usage + state_size > self.max_memory_bytes:
                self._evict_timeline_entries(state_size)
            
            # Check entry limits
            if len(self.timeline_cache) >= self.max_entries:
                self._evict_oldest_timeline_entry()
            
            self.timeline_cache[tick] = timeline_state
            self.current_memory_usage += state_size
            return True
    
    def _evict_coordination_entries(self, required_space: int) -> None:
        """Evict coordination entries to free memory."""
        while (self.current_memory_usage + required_space > self.max_memory_bytes and 
               self.event_cache):
            self._evict_oldest_coordination_entry()
    
    def _evict_oldest_coordination_entry(self) -> None:
        """Evict oldest coordination cache entry."""
        if self.event_cache:
            cache_key, serialized_events = self.event_cache.popitem(last=False)
            self.current_memory_usage -= len(serialized_events)
    
    def _evict_timeline_entries(self, required_space: int) -> None:
        """Evict timeline entries to free memory."""
        while (self.current_memory_usage + required_space > self.max_memory_bytes and 
               self.timeline_cache):
            self._evict_oldest_timeline_entry()
    
    def _evict_oldest_timeline_entry(self) -> None:
        """Evict oldest timeline cache entry."""
        if self.timeline_cache:
            tick, timeline_state = self.timeline_cache.popitem(last=False)
            self.current_memory_usage -= len(timeline_state)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get coordination cache statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0.0
        
        return {
            'coordination_entries': len(self.event_cache),
            'timeline_entries': len(self.timeline_cache),
            'total_entries': len(self.event_cache) + len(self.timeline_cache),
            'max_entries': self.max_entries,
            'memory_usage_bytes': self.current_memory_usage,
            'max_memory_bytes': self.max_memory_bytes,
            'memory_usage_percent': (self.current_memory_usage / self.max_memory_bytes) * 100,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': hit_rate
        }
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        with self.cache_lock:
            self.event_cache.clear()
            self.timeline_cache.clear()
            self.current_memory_usage = 0
            self.hit_count = 0
            self.miss_count = 0


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


def _compute_coordination_worker(task: CoordinationComputationTask) -> ComputedCoordinationEvents:
    """Worker function for coordination event computation.
    
    This function runs on worker cores to compute coordination events
    for a specific tick range using serialized engine and coordination state.
    
    Args:
        task: Coordination computation task
        
    Returns:
        Computed coordination events
    """
    start_time = time.perf_counter()
    worker_id = f"coord_worker_{mp.current_process().pid}"
    
    try:
        # Deserialize engine state
        engine = AnimationStateSerializer.deserialize_engine_state(task.engine_state)
        
        # Deserialize timeline state
        timeline = TickTimeline.deserialize_timeline_state(task.timeline_state)
        
        # Create coordination engine (simplified reconstruction)
        coordination_engine = CoordinationEngine(engine)
        
        # Compute coordination events for tick range
        all_events = []
        for tick in range(task.start_tick, task.end_tick + 1):
            # Evaluate timeline coordination at this tick
            events = timeline.evaluate_at_tick(tick, engine, coordination_engine)
            all_events.extend(events)
        
        computation_time = time.perf_counter() - start_time
        
        return ComputedCoordinationEvents(
            task_id=task.task_id,
            start_tick=task.start_tick,
            end_tick=task.end_tick,
            coordination_events=all_events,
            computation_time=computation_time,
            worker_id=worker_id
        )
        
    except Exception as e:
        # Return empty result on error
        computation_time = time.perf_counter() - start_time
        return ComputedCoordinationEvents(
            task_id=task.task_id,
            start_tick=task.start_tick,
            end_tick=task.end_tick,
            coordination_events=[],
            computation_time=computation_time,
            worker_id=worker_id
        )


class AnimationWorkerPool:
    """Multi-core worker pool for distributed animation frame computation.
    
    This class manages a pool of worker processes/threads that can compute
    animation frames in parallel, leveraging the deterministic nature of
    the tick-based animation system for safe distributed computation.
    """
    
    def __init__(self, num_workers: int = 3, use_processes: bool = True, 
                 cache_size: int = 120, max_cache_memory_mb: int = 50,
                 coordination_cache_size: int = 200, coordination_cache_memory_mb: int = 20):
        """Initialize animation worker pool.
        
        Args:
            num_workers: Number of worker processes/threads
            use_processes: Use processes (True) or threads (False)
            cache_size: Maximum frames to cache
            max_cache_memory_mb: Maximum cache memory in MB
            coordination_cache_size: Maximum coordination cache entries
            coordination_cache_memory_mb: Maximum coordination cache memory in MB
        """
        self.num_workers = num_workers
        self.use_processes = use_processes
        
        # Initialize executor
        if use_processes:
            self.executor = ProcessPoolExecutor(max_workers=num_workers)
        else:
            self.executor = ThreadPoolExecutor(max_workers=num_workers)
        
        # Initialize caches
        self.frame_cache = DistributedFrameCache(cache_size, max_cache_memory_mb)
        self.coordination_cache = DistributedCoordinationCache(
            coordination_cache_size, coordination_cache_memory_mb
        )
        
        # Task management
        self.active_tasks: Dict[str, Future] = {}
        self.active_coordination_tasks: Dict[str, Future] = {}
        self.task_counter = 0
        self.coordination_task_counter = 0
        self.pool_lock = threading.RLock()
        
        # Performance metrics
        self.metrics = WorkerPoolMetrics()
        self.coordination_metrics = WorkerPoolMetrics()  # Separate metrics for coordination
        
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
        """Get current performance metrics for frame computation."""
        # Update cache hit rates
        frame_cache_stats = self.frame_cache.get_cache_stats()
        total_requests = frame_cache_stats['hit_count'] + frame_cache_stats['miss_count']
        
        if total_requests > 0:
            self.metrics.cache_hit_rate = frame_cache_stats['hit_count'] / total_requests
            self.metrics.cache_miss_rate = frame_cache_stats['miss_count'] / total_requests
        
        # Calculate frames per second
        if self.metrics.total_computation_time > 0:
            self.metrics.frames_per_second = self.metrics.total_tasks_completed / self.metrics.total_computation_time
        
        return self.metrics
    
    def get_coordination_performance_metrics(self) -> WorkerPoolMetrics:
        """Get current performance metrics for coordination computation."""
        # Update coordination cache hit rates
        coord_cache_stats = self.coordination_cache.get_cache_stats()
        total_requests = coord_cache_stats['hit_count'] + coord_cache_stats['miss_count']
        
        if total_requests > 0:
            self.coordination_metrics.cache_hit_rate = coord_cache_stats['hit_count'] / total_requests
            self.coordination_metrics.cache_miss_rate = coord_cache_stats['miss_count'] / total_requests
        
        # Calculate coordination events per second
        if self.coordination_metrics.total_computation_time > 0:
            self.coordination_metrics.frames_per_second = (
                self.coordination_metrics.total_tasks_completed / 
                self.coordination_metrics.total_computation_time
            )
        
        return self.coordination_metrics
    
    def get_combined_performance_metrics(self) -> Dict[str, Any]:
        """Get combined performance metrics for both frame and coordination computation."""
        frame_metrics = self.get_performance_metrics()
        coord_metrics = self.get_coordination_performance_metrics()
        frame_cache_stats = self.frame_cache.get_cache_stats()
        coord_cache_stats = self.coordination_cache.get_cache_stats()
        
        return {
            'frame_computation': {
                'total_tasks_submitted': frame_metrics.total_tasks_submitted,
                'total_tasks_completed': frame_metrics.total_tasks_completed,
                'average_task_time': frame_metrics.average_task_time,
                'frames_per_second': frame_metrics.frames_per_second,
                'cache_hit_rate': frame_metrics.cache_hit_rate,
                'cache_stats': frame_cache_stats
            },
            'coordination_computation': {
                'total_tasks_submitted': coord_metrics.total_tasks_submitted,
                'total_tasks_completed': coord_metrics.total_tasks_completed,
                'average_task_time': coord_metrics.average_task_time,
                'events_per_second': coord_metrics.frames_per_second,  # Reusing field for events
                'cache_hit_rate': coord_metrics.cache_hit_rate,
                'cache_stats': coord_cache_stats
            },
            'worker_pool': {
                'num_workers': self.num_workers,
                'use_processes': self.use_processes,
                'active_frame_tasks': len(self.active_tasks),
                'active_coordination_tasks': len(self.active_coordination_tasks),
                'worker_utilization': frame_metrics.worker_utilization
            }
        }
    
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
    
    def submit_coordination_computation(self, start_tick: int, end_tick: int,
                                      engine: TickAnimationEngine,
                                      coordination_engine: CoordinationEngine,
                                      timeline: TickTimeline,
                                      priority: int = 0) -> str:
        """Submit coordination event computation task to worker pool.
        
        Args:
            start_tick: Start tick for coordination computation
            end_tick: End tick for coordination computation
            engine: Current animation engine state
            coordination_engine: Current coordination engine state
            timeline: Current timeline state
            priority: Task priority (higher = more urgent)
            
        Returns:
            Task ID for tracking completion
        """
        with self.pool_lock:
            # Check cache first
            cached_events = self.coordination_cache.get_coordination_events(start_tick, end_tick)
            if cached_events is not None:
                # Return a completed "task" with cached results
                task_id = f"cached_coord_{self.coordination_task_counter}"
                self.coordination_task_counter += 1
                return task_id
            
            task_id = f"coord_task_{self.coordination_task_counter}"
            self.coordination_task_counter += 1
            
            # Serialize states for cross-core communication
            engine_state = AnimationStateSerializer.serialize_engine_state(engine)
            coordination_state = AnimationStateSerializer.serialize_coordination_state(coordination_engine)
            timeline_state = AnimationStateSerializer.serialize_timeline_state(timeline)
            
            # Create coordination computation task
            task = CoordinationComputationTask(
                task_id=task_id,
                start_tick=start_tick,
                end_tick=end_tick,
                engine_state=engine_state,
                coordination_state=coordination_state,
                timeline_state=timeline_state,
                priority=priority
            )
            
            # Submit to worker pool
            future = self.executor.submit(_compute_coordination_worker, task)
            self.active_coordination_tasks[task_id] = future
            self.coordination_metrics.total_tasks_submitted += 1
            
            return task_id
    
    def get_computed_coordination_events(self, task_id: str, 
                                       timeout: float = 0.001) -> Optional[ComputedCoordinationEvents]:
        """Get computed coordination events if ready.
        
        Args:
            task_id: Task ID from submit_coordination_computation
            timeout: Maximum time to wait for completion
            
        Returns:
            Computed coordination events if ready, None otherwise
        """
        # Handle cached results
        if task_id.startswith("cached_coord_"):
            return None  # Cached results handled separately
        
        with self.pool_lock:
            if task_id not in self.active_coordination_tasks:
                return None
            
            future = self.active_coordination_tasks[task_id]
            
            try:
                result = future.result(timeout=timeout)
                
                # Task completed, clean up and update metrics
                del self.active_coordination_tasks[task_id]
                self.coordination_metrics.update_completion(
                    result.computation_time, 
                    result.worker_id
                )
                
                # Cache the computed events
                self.coordination_cache.store_coordination_events(
                    result.start_tick,
                    result.end_tick,
                    result.coordination_events
                )
                
                return result
                
            except Exception:
                # Task not ready or failed
                return None
    
    def submit_batch_coordination_computation(self, start_tick: int, num_tick_ranges: int,
                                            range_size: int, engine: TickAnimationEngine,
                                            coordination_engine: CoordinationEngine,
                                            timeline: TickTimeline) -> List[str]:
        """Submit batch coordination computation for multiple tick ranges.
        
        Args:
            start_tick: Starting tick for batch computation
            num_tick_ranges: Number of tick ranges to compute
            range_size: Size of each tick range
            engine: Current animation engine state
            coordination_engine: Current coordination engine state
            timeline: Current timeline state
            
        Returns:
            List of task IDs for tracking completion
        """
        task_ids = []
        
        for i in range(num_tick_ranges):
            range_start = start_tick + (i * range_size)
            range_end = range_start + range_size - 1
            
            task_id = self.submit_coordination_computation(
                range_start, range_end, engine, coordination_engine, timeline
            )
            task_ids.append(task_id)
        
        return task_ids
    
    def wait_for_coordination_batch_completion(self, task_ids: List[str],
                                             timeout: float = 5.0) -> Dict[str, ComputedCoordinationEvents]:
        """Wait for batch coordination computation to complete.
        
        Args:
            task_ids: List of task IDs to wait for
            timeout: Maximum time to wait for all tasks
            
        Returns:
            Dictionary mapping task IDs to computed coordination events
        """
        results = {}
        start_time = time.perf_counter()
        
        while task_ids and (time.perf_counter() - start_time) < timeout:
            completed_tasks = []
            
            for task_id in task_ids:
                result = self.get_computed_coordination_events(task_id, timeout=0.001)
                if result:
                    results[task_id] = result
                    completed_tasks.append(task_id)
            
            # Remove completed tasks
            for task_id in completed_tasks:
                task_ids.remove(task_id)
            
            if task_ids:
                time.sleep(0.001)  # Small delay before checking again
        
        return results 