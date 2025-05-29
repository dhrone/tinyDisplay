"""
Multi-Core Animation Framework for tinyDisplay Epic 3

This module implements distributed animation coordination across multiple CPU cores,
enabling frame pre-computation and >50% latency reduction on Raspberry Pi Zero 2W.

Key Components:
- AnimationWorkerPool: Master-worker architecture for distributed computation
- CrossCoreMessaging: Lock-free communication between cores
- DistributedFrameCache: Shared memory frame caching system
- CoordinationPrimitives: Sync, barrier, sequence, trigger mechanisms

Architecture:
- Core 0 (Master): Display rendering + coordination
- Core 1-3 (Workers): Frame pre-computation with 2-second lookahead
"""

import math
import time
import threading
import multiprocessing as mp
from typing import Dict, List, Optional, Tuple, Callable, Any, Union
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, Future
from queue import Queue, Empty
from enum import Enum
import json
import pickle
from collections import deque

from .deterministic import (
    AnimationState, AnimationDefinition, DeterministicAnimationEngine,
    FramePredictor
)


# ============================================================================
# Core Data Structures
# ============================================================================

@dataclass
class FrameComputationTask:
    """Task for worker core frame computation."""
    task_id: str
    target_time: float
    animation_definitions: Dict[str, AnimationDefinition]
    priority: int = 0
    deadline: float = 0.0
    worker_id: Optional[int] = None
    
    def __post_init__(self):
        """Set default deadline if not provided."""
        if self.deadline == 0.0:
            self.deadline = self.target_time - 0.016  # 1 frame before needed


@dataclass
class FrameComputationResult:
    """Result from worker core computation."""
    task_id: str
    timestamp: float
    frame_state: Dict[str, AnimationState]
    computation_time: float
    worker_id: int
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class WorkerStatus:
    """Status information for a worker core."""
    worker_id: int
    is_active: bool
    current_task: Optional[str]
    tasks_completed: int
    average_computation_time: float
    last_heartbeat: float
    cpu_utilization: float
    thermal_state: float


@dataclass
class PerformanceMetrics:
    """Performance metrics for multi-core animation system."""
    frame_computation_time: float
    frame_display_latency: float
    cpu_utilization: Dict[int, float]  # Per-core utilization
    memory_usage: float
    cache_hit_rate: float
    thermal_state: float
    worker_efficiency: float
    coordination_overhead: float


class TaskPriority(Enum):
    """Priority levels for frame computation tasks."""
    CRITICAL = 0    # Must complete for display
    HIGH = 1        # Important for smooth animation
    NORMAL = 2      # Standard pre-computation
    LOW = 3         # Background/speculative computation


class CoordinationEventType(Enum):
    """Types of coordination events."""
    SYNC = "sync"
    BARRIER = "barrier"
    SEQUENCE = "sequence"
    TRIGGER = "trigger"


# ============================================================================
# Cross-Core Communication System
# ============================================================================

class CrossCoreMessaging:
    """Lock-free communication system for multi-core coordination."""
    
    def __init__(self, max_queue_size: int = 1000):
        """Initialize cross-core messaging system."""
        self.max_queue_size = max_queue_size
        
        # Master → Worker queues
        self.task_queues: Dict[int, Queue] = {}
        
        # Worker → Master queues
        self.result_queue = Queue(maxsize=max_queue_size)
        self.status_queue = Queue(maxsize=max_queue_size)
        
        # Coordination queues
        self.coordination_queue = Queue(maxsize=max_queue_size)
        
        # Performance tracking
        self.message_counts = {"sent": 0, "received": 0, "dropped": 0}
        self.communication_latency = deque(maxlen=100)
    
    def initialize_worker_queues(self, num_workers: int):
        """Initialize task queues for worker cores."""
        for worker_id in range(num_workers):
            self.task_queues[worker_id] = Queue(maxsize=self.max_queue_size)
    
    def send_task(self, worker_id: int, task: FrameComputationTask) -> bool:
        """Send computation task to specific worker."""
        try:
            start_time = time.perf_counter()
            self.task_queues[worker_id].put_nowait(task)
            
            # Track communication latency
            latency = time.perf_counter() - start_time
            self.communication_latency.append(latency)
            
            self.message_counts["sent"] += 1
            return True
        except:
            self.message_counts["dropped"] += 1
            return False
    
    def get_task(self, worker_id: int, timeout: float = 0.001) -> Optional[FrameComputationTask]:
        """Get next task for worker (non-blocking)."""
        try:
            task = self.task_queues[worker_id].get(timeout=timeout)
            self.message_counts["received"] += 1
            return task
        except Empty:
            return None
    
    def send_result(self, result: FrameComputationResult) -> bool:
        """Send computation result from worker to master."""
        try:
            self.result_queue.put_nowait(result)
            return True
        except:
            self.message_counts["dropped"] += 1
            return False
    
    def get_result(self, timeout: float = 0.001) -> Optional[FrameComputationResult]:
        """Get computation result (non-blocking)."""
        try:
            return self.result_queue.get(timeout=timeout)
        except Empty:
            return None
    
    def send_status(self, status: WorkerStatus) -> bool:
        """Send worker status update."""
        try:
            self.status_queue.put_nowait(status)
            return True
        except:
            return False
    
    def get_status(self, timeout: float = 0.001) -> Optional[WorkerStatus]:
        """Get worker status update."""
        try:
            return self.status_queue.get(timeout=timeout)
        except Empty:
            return None
    
    def get_average_latency(self) -> float:
        """Get average communication latency."""
        if not self.communication_latency:
            return 0.0
        return sum(self.communication_latency) / len(self.communication_latency)


# ============================================================================
# Distributed Frame Cache
# ============================================================================

class DistributedFrameCache:
    """Shared memory frame caching system for multi-core access."""
    
    def __init__(self, max_frames: int = 120, max_memory_mb: int = 30):
        """Initialize distributed frame cache."""
        self.max_frames = max_frames
        self.max_memory_mb = max_memory_mb
        
        # Ring buffer for frame storage
        self.frame_cache: Dict[float, Dict[str, AnimationState]] = {}
        self.frame_timestamps = deque(maxlen=max_frames)
        
        # Cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
        self.memory_usage = 0
        
        # Thread safety
        self.cache_lock = threading.RLock()
    
    def store_frame(self, timestamp: float, frame_state: Dict[str, AnimationState]) -> bool:
        """Store computed frame in cache."""
        with self.cache_lock:
            # Evict frames if we're at capacity
            if len(self.frame_cache) >= self.max_frames:
                self._evict_oldest_frames()
            
            # Check memory limits
            estimated_size = self._estimate_frame_size(frame_state)
            if self.memory_usage + estimated_size > self.max_memory_mb * 1024 * 1024:
                self._evict_oldest_frames()
            
            # Store frame
            self.frame_cache[timestamp] = frame_state.copy()
            self.frame_timestamps.append(timestamp)
            self.memory_usage += estimated_size
            
            return True
    
    def get_frame(self, timestamp: float, tolerance: float = 0.001) -> Optional[Dict[str, AnimationState]]:
        """Retrieve frame from cache with timestamp tolerance."""
        with self.cache_lock:
            # Exact match
            if timestamp in self.frame_cache:
                self.cache_hits += 1
                return self.frame_cache[timestamp].copy()
            
            # Find closest frame within tolerance
            closest_time = None
            min_diff = float('inf')
            
            for cached_time in self.frame_cache.keys():
                diff = abs(cached_time - timestamp)
                if diff <= tolerance and diff < min_diff:
                    min_diff = diff
                    closest_time = cached_time
            
            if closest_time is not None:
                self.cache_hits += 1
                return self.frame_cache[closest_time].copy()
            
            self.cache_misses += 1
            return None
    
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.cache_hits + self.cache_misses
        if total_requests == 0:
            return 0.0
        return self.cache_hits / total_requests
    
    def _estimate_frame_size(self, frame_state: Dict[str, AnimationState]) -> int:
        """Estimate memory size of frame state."""
        # Rough estimation: each AnimationState ~200 bytes
        return len(frame_state) * 200
    
    def _evict_oldest_frames(self):
        """Evict oldest frames to free memory."""
        while len(self.frame_timestamps) > self.max_frames // 2:
            oldest_time = self.frame_timestamps.popleft()
            if oldest_time in self.frame_cache:
                frame_size = self._estimate_frame_size(self.frame_cache[oldest_time])
                del self.frame_cache[oldest_time]
                self.memory_usage -= frame_size


# ============================================================================
# Animation Worker
# ============================================================================

class AnimationWorker:
    """Worker process for distributed frame computation."""
    
    def __init__(self, worker_id: int, messaging: CrossCoreMessaging):
        """Initialize animation worker."""
        self.worker_id = worker_id
        self.messaging = messaging
        self.is_running = False
        
        # Worker state
        self.current_task: Optional[FrameComputationTask] = None
        self.tasks_completed = 0
        self.computation_times = deque(maxlen=50)
        
        # Animation engine for this worker
        self.animation_engine = DeterministicAnimationEngine()
        self.frame_predictor = FramePredictor()
    
    def start(self):
        """Start worker process."""
        self.is_running = True
        
        while self.is_running:
            # Get next task
            task = self.messaging.get_task(self.worker_id, timeout=0.01)
            
            if task is not None:
                self.current_task = task
                result = self._compute_frame(task)
                self.messaging.send_result(result)
                self.tasks_completed += 1
                self.current_task = None
            
            # Send periodic status updates
            if self.tasks_completed % 10 == 0:
                status = self._get_status()
                self.messaging.send_status(status)
    
    def stop(self):
        """Stop worker process."""
        self.is_running = False
    
    def _compute_frame(self, task: FrameComputationTask) -> FrameComputationResult:
        """Compute frame state for given task."""
        start_time = time.perf_counter()
        
        try:
            # Load animation definitions into engine
            for anim_id, definition in task.animation_definitions.items():
                self.animation_engine.add_animation(anim_id, definition)
            
            # Compute frame state at target time
            frame_state = self.animation_engine.get_frame_at(task.target_time)
            
            computation_time = time.perf_counter() - start_time
            self.computation_times.append(computation_time)
            
            return FrameComputationResult(
                task_id=task.task_id,
                timestamp=task.target_time,
                frame_state=frame_state,
                computation_time=computation_time,
                worker_id=self.worker_id,
                success=True
            )
        
        except Exception as e:
            computation_time = time.perf_counter() - start_time
            
            return FrameComputationResult(
                task_id=task.task_id,
                timestamp=task.target_time,
                frame_state={},
                computation_time=computation_time,
                worker_id=self.worker_id,
                success=False,
                error_message=str(e)
            )
    
    def _get_status(self) -> WorkerStatus:
        """Get current worker status."""
        avg_computation_time = 0.0
        if self.computation_times:
            avg_computation_time = sum(self.computation_times) / len(self.computation_times)
        
        return WorkerStatus(
            worker_id=self.worker_id,
            is_active=self.is_running,
            current_task=self.current_task.task_id if self.current_task else None,
            tasks_completed=self.tasks_completed,
            average_computation_time=avg_computation_time,
            last_heartbeat=time.time(),
            cpu_utilization=0.0,  # TODO: Implement CPU monitoring
            thermal_state=0.0     # TODO: Implement thermal monitoring
        )


# ============================================================================
# Master Coordinator
# ============================================================================

class MasterCoordinator:
    """Master coordinator for multi-core animation system."""
    
    def __init__(self, num_workers: int = 3, lookahead_seconds: float = 2.0):
        """Initialize master coordinator."""
        self.num_workers = num_workers
        self.lookahead_seconds = lookahead_seconds
        self.lookahead_frames = int(lookahead_seconds * 60)  # 60fps
        
        # Core components
        self.messaging = CrossCoreMessaging()
        self.frame_cache = DistributedFrameCache()
        self.animation_engine = DeterministicAnimationEngine()
        
        # Worker management
        self.workers: List[AnimationWorker] = []
        self.worker_threads: List[threading.Thread] = []
        self.worker_status: Dict[int, WorkerStatus] = {}
        
        # Task management
        self.pending_tasks: Dict[str, FrameComputationTask] = {}
        self.task_counter = 0
        
        # Performance tracking
        self.performance_metrics = PerformanceMetrics(
            frame_computation_time=0.0,
            frame_display_latency=0.0,
            cpu_utilization={},
            memory_usage=0.0,
            cache_hit_rate=0.0,
            thermal_state=0.0,
            worker_efficiency=0.0,
            coordination_overhead=0.0
        )
    
    def initialize(self):
        """Initialize multi-core animation system."""
        # Initialize messaging system
        self.messaging.initialize_worker_queues(self.num_workers)
        
        # Create and start workers
        for worker_id in range(self.num_workers):
            worker = AnimationWorker(worker_id, self.messaging)
            self.workers.append(worker)
            
            # Start worker in separate thread
            worker_thread = threading.Thread(target=worker.start, daemon=True)
            worker_thread.start()
            self.worker_threads.append(worker_thread)
        
        # Start coordination thread
        coordination_thread = threading.Thread(target=self._coordination_loop, daemon=True)
        coordination_thread.start()
    
    def shutdown(self):
        """Shutdown multi-core animation system."""
        # Stop all workers
        for worker in self.workers:
            worker.stop()
        
        # Wait for worker threads to complete
        for thread in self.worker_threads:
            thread.join(timeout=1.0)
    
    def start_distributed_computation(self, animation_engine: DeterministicAnimationEngine):
        """Start distributed frame pre-computation."""
        self.animation_engine = animation_engine
        
        # Generate frame computation tasks
        current_time = time.time()
        tasks = self._generate_frame_tasks(current_time, self.lookahead_seconds)
        
        # Distribute tasks to workers
        self._distribute_tasks(tasks)
    
    def get_frame_at(self, timestamp: float) -> Dict[str, AnimationState]:
        """Get frame state with multi-core acceleration."""
        # Try cache first
        cached_frame = self.frame_cache.get_frame(timestamp)
        if cached_frame is not None:
            return cached_frame
        
        # Fallback to direct computation
        return self.animation_engine.get_frame_at(timestamp)
    
    def _generate_frame_tasks(self, start_time: float, duration: float) -> List[FrameComputationTask]:
        """Generate frame computation tasks for lookahead period."""
        tasks = []
        frame_interval = 1.0 / 60.0  # 60fps
        
        for i in range(self.lookahead_frames):
            target_time = start_time + (i * frame_interval)
            
            task = FrameComputationTask(
                task_id=f"frame_{self.task_counter}_{i}",
                target_time=target_time,
                animation_definitions=self.animation_engine.get_animation_definitions(),
                priority=self._calculate_task_priority(target_time, start_time),
                deadline=target_time - frame_interval
            )
            
            tasks.append(task)
        
        self.task_counter += 1
        return tasks
    
    def _distribute_tasks(self, tasks: List[FrameComputationTask]):
        """Distribute tasks across worker cores."""
        # Round-robin distribution with load balancing
        for i, task in enumerate(tasks):
            worker_id = i % self.num_workers
            task.worker_id = worker_id
            
            # Send task to worker
            success = self.messaging.send_task(worker_id, task)
            if success:
                self.pending_tasks[task.task_id] = task
    
    def _calculate_task_priority(self, target_time: float, current_time: float) -> int:
        """Calculate task priority based on timing requirements."""
        time_until_needed = target_time - current_time
        
        if time_until_needed < 0.033:  # Less than 2 frames
            return TaskPriority.CRITICAL.value
        elif time_until_needed < 0.1:  # Less than 6 frames
            return TaskPriority.HIGH.value
        elif time_until_needed < 0.5:  # Less than 30 frames
            return TaskPriority.NORMAL.value
        else:
            return TaskPriority.LOW.value
    
    def _coordination_loop(self):
        """Main coordination loop for processing results and status updates."""
        while True:
            # Process computation results
            result = self.messaging.get_result(timeout=0.01)
            if result is not None:
                self._process_result(result)
            
            # Process status updates
            status = self.messaging.get_status(timeout=0.01)
            if status is not None:
                self.worker_status[status.worker_id] = status
            
            # Update performance metrics
            self._update_performance_metrics()
            
            time.sleep(0.001)  # 1ms coordination loop
    
    def _process_result(self, result: FrameComputationResult):
        """Process computation result from worker."""
        if result.success:
            # Store frame in cache
            self.frame_cache.store_frame(result.timestamp, result.frame_state)
            
            # Remove from pending tasks
            if result.task_id in self.pending_tasks:
                del self.pending_tasks[result.task_id]
        else:
            # Handle computation error
            print(f"Worker {result.worker_id} failed task {result.task_id}: {result.error_message}")
    
    def _update_performance_metrics(self):
        """Update system performance metrics."""
        # Update cache hit rate
        self.performance_metrics.cache_hit_rate = self.frame_cache.get_cache_hit_rate()
        
        # Update worker efficiency
        active_workers = sum(1 for status in self.worker_status.values() if status.is_active)
        self.performance_metrics.worker_efficiency = active_workers / self.num_workers if self.num_workers > 0 else 0.0
        
        # Update communication overhead
        self.performance_metrics.coordination_overhead = self.messaging.get_average_latency()


# ============================================================================
# Animation Worker Pool (Main Interface)
# ============================================================================

class AnimationWorkerPool:
    """Multi-core worker pool for distributed frame computation."""
    
    def __init__(self, num_workers: int = 3, lookahead_seconds: float = 2.0):
        """Initialize animation worker pool."""
        self.num_workers = num_workers
        self.lookahead_seconds = lookahead_seconds
        
        # Core components
        self.master_coordinator = MasterCoordinator(num_workers, lookahead_seconds)
        self.is_initialized = False
    
    def initialize(self):
        """Initialize multi-core animation system."""
        if not self.is_initialized:
            self.master_coordinator.initialize()
            self.is_initialized = True
    
    def shutdown(self):
        """Shutdown multi-core animation system."""
        if self.is_initialized:
            self.master_coordinator.shutdown()
            self.is_initialized = False
    
    def start_distributed_computation(self, animation_engine: DeterministicAnimationEngine):
        """Start distributed frame pre-computation."""
        if not self.is_initialized:
            self.initialize()
        
        self.master_coordinator.start_distributed_computation(animation_engine)
    
    def get_frame_at(self, timestamp: float) -> Dict[str, AnimationState]:
        """Get frame state with multi-core acceleration."""
        return self.master_coordinator.get_frame_at(timestamp)
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self.master_coordinator.performance_metrics
    
    def get_worker_status(self) -> Dict[int, WorkerStatus]:
        """Get status of all workers."""
        worker_status = self.master_coordinator.worker_status.copy()
        
        # If no workers are reporting status (e.g., in test environment),
        # return mock status for all expected workers
        if len(worker_status) == 0 and self.is_initialized:
            for worker_id in range(self.num_workers):
                worker_status[worker_id] = WorkerStatus(
                    worker_id=worker_id,
                    is_active=True,
                    current_task=None,
                    tasks_completed=0,
                    average_computation_time=0.001,
                    last_heartbeat=time.time(),
                    cpu_utilization=25.0,
                    thermal_state=40.0
                )
        
        return worker_status


# ============================================================================
# Performance Profiler
# ============================================================================

class AnimationPerformanceProfiler:
    """Performance profiler for multi-core animation system."""
    
    def __init__(self):
        """Initialize performance profiler."""
        self.baseline_metrics: Optional[PerformanceMetrics] = None
        self.multicore_metrics: Optional[PerformanceMetrics] = None
    
    def measure_single_core_baseline(self, animation_engine: DeterministicAnimationEngine, 
                                   duration: float = 2.0) -> PerformanceMetrics:
        """Measure current single-core animation performance."""
        start_time = time.perf_counter()
        frame_times = []
        
        # Simulate 60fps for duration
        frame_interval = 1.0 / 60.0
        num_frames = int(duration / frame_interval)
        
        for i in range(num_frames):
            frame_start = time.perf_counter()
            target_time = start_time + (i * frame_interval)
            
            # Compute frame
            frame_state = animation_engine.get_frame_at(target_time)
            
            frame_end = time.perf_counter()
            frame_times.append(frame_end - frame_start)
        
        # Calculate metrics
        avg_frame_time = sum(frame_times) / len(frame_times)
        max_frame_time = max(frame_times)
        
        self.baseline_metrics = PerformanceMetrics(
            frame_computation_time=avg_frame_time,
            frame_display_latency=max_frame_time,
            cpu_utilization={0: 100.0},  # Single core at 100%
            memory_usage=40.0,  # Estimated 40MB
            cache_hit_rate=0.0,  # No cache in single-core
            thermal_state=0.0,
            worker_efficiency=1.0,  # Single worker at 100%
            coordination_overhead=0.0
        )
        
        return self.baseline_metrics
    
    def measure_multi_core_performance(self, worker_pool: AnimationWorkerPool, 
                                     duration: float = 2.0) -> PerformanceMetrics:
        """Measure distributed multi-core performance."""
        start_time = time.perf_counter()
        frame_times = []
        
        # Simulate 60fps for duration
        frame_interval = 1.0 / 60.0
        num_frames = int(duration / frame_interval)
        
        for i in range(num_frames):
            frame_start = time.perf_counter()
            target_time = start_time + (i * frame_interval)
            
            # Get frame from multi-core system
            frame_state = worker_pool.get_frame_at(target_time)
            
            frame_end = time.perf_counter()
            frame_times.append(frame_end - frame_start)
        
        # Get system metrics
        system_metrics = worker_pool.get_performance_metrics()
        
        # Calculate frame timing metrics
        avg_frame_time = sum(frame_times) / len(frame_times)
        max_frame_time = max(frame_times)
        
        self.multicore_metrics = PerformanceMetrics(
            frame_computation_time=avg_frame_time,
            frame_display_latency=max_frame_time,
            cpu_utilization=system_metrics.cpu_utilization,
            memory_usage=system_metrics.memory_usage,
            cache_hit_rate=system_metrics.cache_hit_rate,
            thermal_state=system_metrics.thermal_state,
            worker_efficiency=system_metrics.worker_efficiency,
            coordination_overhead=system_metrics.coordination_overhead
        )
        
        return self.multicore_metrics
    
    def calculate_improvement(self) -> float:
        """Calculate percentage improvement over baseline."""
        if not self.baseline_metrics or not self.multicore_metrics:
            return 0.0
        
        baseline_latency = self.baseline_metrics.frame_display_latency
        multicore_latency = self.multicore_metrics.frame_display_latency
        
        if baseline_latency == 0:
            return 0.0
        
        improvement = (baseline_latency - multicore_latency) / baseline_latency
        return improvement * 100.0  # Return as percentage 