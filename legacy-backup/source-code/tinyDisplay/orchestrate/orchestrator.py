"""
Orchestration system for tinyDisplay.

This module provides the RenderOrchestrator class which manages the rendering process,
with optional parallel rendering using multiprocessing or threading.
"""

import logging
import time
import threading
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from queue import Queue, Empty
import multiprocessing
from PIL import Image

from tinyDisplay.dependency.protocols import ChangeEventProtocol, ChangeProcessorProtocol
from tinyDisplay.dependency.manager import DependencyManager


class RenderOrchestrator:
    """
    Master controller for a tinyDisplay application.
    
    Responsible for coordinating the rendering process and optimizing performance
    through parallel rendering using multiprocessing or threading.
    """
    
    def __init__(self, dependency_manager: DependencyManager, dataset: dict,
                 display_canvas: Any, max_queue_size: int = 10, 
                 mode: str = "single", heartbeat_interval: float = 1.0):
        """
        Initialize the orchestrator with required components.
        
        Args:
            dependency_manager: The dependency manager instance to take ownership of
            dataset: The dataset instance to use for rendering
            display_canvas: The root canvas of the display system
            max_queue_size: Maximum size of the render queue
            mode: Operating mode - "single", "threading", or "multiprocessing"
            heartbeat_interval: How often workers should send heartbeats (seconds)
        """
        # Take ownership of system components
        self.dependency_manager = dependency_manager
        self.dataset = dataset
        self.display_canvas = display_canvas
        
        # Rendering configuration
        self.max_queue_size = max_queue_size
        self.mode = mode.lower()
        self.heartbeat_interval = heartbeat_interval
        self.current_tick = 0
        
        # Validate mode
        if self.mode not in ("single", "threading", "multiprocessing"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'single', 'threading', or 'multiprocessing'")
            
        # Initialize variables based on mode
        self.use_workers = self.mode != "single"
        self.use_multiprocessing = self.mode == "multiprocessing"
        
        # Select appropriate queue and process classes based on mode
        if self.use_multiprocessing:
            self.QueueClass = multiprocessing.Queue
            self.EventClass = multiprocessing.Event
            self.ProcessClass = multiprocessing.Process
        else:
            self.QueueClass = Queue
            self.EventClass = threading.Event
            self.ProcessClass = threading.Thread
        
        # Worker management
        self.workers = []  # List of worker processes/threads
        self.worker_heartbeats = {}  # worker_id -> last heartbeat time
        self.worker_command_queues = {}  # worker_id -> queue for commands
        self.master_queues = {}  # worker_id -> queue for responses
        
        # Main render queue
        self.render_queue = self.QueueClass(maxsize=max_queue_size)
        
        # Heartbeat monitoring
        self._heartbeat_monitor = None
        self._heartbeat_stop_event = threading.Event()
        
        # Configure logging
        self.logger = logging.getLogger("tinyDisplay.orchestrator")
        
        # Event handling
        self._event_subscription = None
    
    def initialize(self, worker_count: Optional[int] = None):
        """
        Initialize the orchestrator and start worker processes/threads if needed.
        
        Args:
            worker_count: Number of workers to spawn. If None, uses CPU count - 1 for
                         multiprocessing or 2 for threading. Ignored in single-thread mode.
        """
        # Register for dependency events
        # The orchestrator itself acts as a dependent that responds to all change events
        self._event_subscription = self.dependency_manager.register(
            self.handle_state_change, self.dependency_manager
        )
        
        if not self.use_workers:
            # Single-thread mode - nothing more to initialize
            self.logger.info("RenderOrchestrator initialized in single-thread mode")
            return
            
        # Determine number of workers for threading/multiprocessing modes
        if worker_count is None:
            if self.use_multiprocessing:
                worker_count = max(1, multiprocessing.cpu_count() - 1)
            else:
                worker_count = 2  # Default for threading mode
        
        # Start worker processes/threads
        self._start_workers(worker_count)
        
        # Start heartbeat monitor
        self._start_heartbeat_monitor()
        
        self.logger.info(f"RenderOrchestrator initialized with {worker_count} workers "
                         f"using {self.mode} mode")
    
    def _start_workers(self, worker_count: int):
        """
        Start worker processes or threads for parallel rendering.
        
        Args:
            worker_count: Number of workers to start
        """
        for i in range(worker_count):
            worker_id = f"worker-{i}"
            
            # Create communication queues
            cmd_queue = self.QueueClass()
            master_queue = self.QueueClass()
            
            # Create and start worker
            worker = self.ProcessClass(
                target=self._worker_process if self.use_multiprocessing else self._worker_thread,
                args=(worker_id, cmd_queue, master_queue, self.render_queue, 
                      self.heartbeat_interval),
                name=f"RenderWorker-{i}"
            )
            
            # Make workers daemon so they exit when main thread/process exits
            worker.daemon = True
            worker.start()
            
            # Store worker and queues
            self.workers.append(worker)
            self.worker_command_queues[worker_id] = cmd_queue
            self.master_queues[worker_id] = master_queue
            self.worker_heartbeats[worker_id] = time.time()
            
            self.logger.debug(f"Started {worker_id}")
    
    def _start_heartbeat_monitor(self):
        """
        Start a thread to monitor worker heartbeats.
        """
        self._heartbeat_stop_event.clear()
        self._heartbeat_monitor = threading.Thread(
            target=self._monitor_heartbeats,
            name="HeartbeatMonitor"
        )
        self._heartbeat_monitor.daemon = True
        self._heartbeat_monitor.start()
        
        self.logger.debug("Started heartbeat monitor")
    
    def _monitor_heartbeats(self):
        """
        Monitor worker heartbeats and restart workers if needed.
        """
        while not self._heartbeat_stop_event.is_set():
            current_time = time.time()
            
            # Check each worker's heartbeat
            for worker_id, last_heartbeat in list(self.worker_heartbeats.items()):
                # Check if heartbeat is too old (3x the interval is considered missed)
                if current_time - last_heartbeat > self.heartbeat_interval * 3:
                    self.logger.warning(f"Worker {worker_id} missed heartbeats, restarting")
                    self._restart_worker(worker_id)
            
            # Check master queues for heartbeats and other messages
            for worker_id, queue in list(self.master_queues.items()):
                try:
                    while True:
                        msg = queue.get_nowait()
                        if msg[0] == "heartbeat":
                            self.worker_heartbeats[worker_id] = time.time()
                        # Handle other messages
                        elif msg[0] == "render_complete":
                            tick, image = msg[1], msg[2]
                            # Add to render queue if there's space
                            if not self.render_queue.full():
                                self.render_queue.put((tick, image))
                except Empty:
                    pass
            
            time.sleep(0.1)  # Sleep briefly to avoid busy waiting
    
    def _worker_process(self, worker_id: str, cmd_queue, master_queue, render_queue, heartbeat_interval):
        """
        Worker process function for multiprocessing mode.
        
        Args:
            worker_id: ID of this worker
            cmd_queue: Queue to receive commands from main process
            master_queue: Queue to send responses to main process
            render_queue: Queue to place rendered images in
            heartbeat_interval: How often to send heartbeats (seconds)
        """
        # Set up logging for this worker
        logger = logging.getLogger(f"tinyDisplay.orchestrator.{worker_id}")
        logger.info(f"Worker {worker_id} started")
        
        # Set up heartbeat timer
        last_heartbeat = 0
        
        try:
            # Main worker loop
            while True:
                # Send heartbeat if needed
                current_time = time.time()
                if current_time - last_heartbeat > heartbeat_interval:
                    master_queue.put(("heartbeat", worker_id))
                    last_heartbeat = current_time
                
                # Check for commands from main process
                try:
                    cmd = cmd_queue.get_nowait()
                    
                    # Handle commands
                    if cmd[0] == "stop":
                        logger.info(f"Worker {worker_id} received stop command")
                        break
                    elif cmd[0] == "render":
                        tick = cmd[1]
                        logger.debug(f"Worker {worker_id} rendering tick {tick}")
                        image = self._perform_render(tick)
                        master_queue.put(("render_complete", tick, image))
                    elif cmd[0] == "update_dataset":
                        dataset_changes = cmd[1]
                        logger.debug(f"Worker {worker_id} updating dataset")
                        self._apply_dataset_changes(dataset_changes)
                        master_queue.put(("dataset_updated", worker_id))
                except Empty:
                    # No commands, sleep briefly
                    time.sleep(0.01)
                    
        except Exception as e:
            logger.error(f"Error in worker {worker_id}: {e}", exc_info=True)
        finally:
            logger.info(f"Worker {worker_id} exiting")
    
    def _worker_thread(self, *args, **kwargs):
        """
        Worker thread function - wrapper around worker_process for threading mode.
        """
        return self._worker_process(*args, **kwargs)
        
    def _perform_render(self, tick):
        """
        Perform rendering for a specific tick.
        
        Args:
            tick: The tick to render for
            
        Returns:
            The rendered image
        """
        try:
            # Call the display_canvas's render method to get the image
            image = self.display_canvas.render()[0]  # Assuming render returns (image, changed)
            return image
        except Exception as e:
            logging.getLogger("tinyDisplay.orchestrator.worker").error(
                f"Error rendering for tick {tick}: {e}", exc_info=True
            )
            # Return a blank image in case of error
            return Image.new('RGB', (1, 1), color='black')
            
    def _apply_dataset_changes(self, changes):
        """
        Apply changes to the local dataset copy.
        
        Args:
            changes: Dictionary of dataset changes
        """
        # Update dataset with changes
        for key, value in changes.items():
            self.dataset[key] = value
    
    def render_next_frame(self, current_tick: int) -> Image.Image:
        """
        Get the next frame to display.
        
        If a pre-rendered frame is available, it will be used.
        Otherwise, a new frame will be rendered synchronously.
        
        Args:
            current_tick: The current system tick
            
        Returns:
            The rendered image
        """
        self.current_tick = current_tick
        
        # In single-thread mode, just render synchronously
        if not self.use_workers:
            return self._perform_render(current_tick)
        
        # Check if we have a pre-rendered frame from workers
        try:
            tick, image = self.render_queue.get_nowait()
            self.logger.debug(f"Using pre-rendered frame for tick {tick}")
            return image
        except Empty:
            # If not, render synchronously
            self.logger.debug(f"No pre-rendered frame available, rendering synchronously")
            return self._perform_render(current_tick)
    
    def schedule_future_renders(self, current_tick: int, count: int = 5):
        """
        Schedule rendering for future ticks.
        
        In worker modes, this distributes rendering tasks to workers.
        In single-thread mode, this is a no-op since there are no workers.
        
        Args:
            current_tick: The current system tick
            count: Number of future ticks to render
        """
        # In single-thread mode, do nothing
        if not self.use_workers:
            return
            
        # Get available workers
        worker_ids = list(self.worker_command_queues.keys())
        if not worker_ids:
            return
            
        # Calculate the ticks to render
        future_ticks = list(range(current_tick + 1, current_tick + count + 1))
        
        # Distribute to workers with interleaving
        # This ensures we don't assign consecutive ticks to the same worker
        num_workers = len(worker_ids)
        
        # Sort workers to ensure consistent assignment order
        worker_ids.sort()
        
        # Assign each tick to a worker
        for tick in future_ticks:
            # Use a different formula for assigning workers to better distribute load
            # This formula interleaves assignments among workers
            worker_index = tick % num_workers
            worker_id = worker_ids[worker_index]
            
            self.logger.debug(f"Scheduling tick {tick} on worker {worker_id}")
            self.worker_command_queues[worker_id].put(("render", tick))
    
    def update_dataset(self, changes):
        """
        Update dataset and notify workers of changes.
        
        Args:
            changes: Dictionary of dataset changes
        """
        # Update main process dataset
        for key, value in changes.items():
            self.dataset[key] = value
        
        # Notify all workers
        for worker_id, queue in self.worker_command_queues.items():
            queue.put(("update_dataset", changes))
    
    def _restart_worker(self, worker_id):
        """
        Restart a worker that has failed or become unresponsive.
        
        Args:
            worker_id: ID of the worker to restart
        """
        # Find the worker in the list
        for i, worker in enumerate(self.workers):
            if worker.name.endswith(worker_id):
                # Clean up old worker
                if self.use_multiprocessing:
                    worker.terminate()
                
                # Remove from tracking collections
                self.workers.pop(i)
                old_cmd_queue = self.worker_command_queues.pop(worker_id)
                old_master_queue = self.master_queues.pop(worker_id)
                self.worker_heartbeats.pop(worker_id)
                
                # Create new queues
                cmd_queue = self.QueueClass()
                master_queue = self.QueueClass()
                
                # Create and start new worker
                new_worker = self.ProcessClass(
                    target=self._worker_process if self.use_multiprocessing else self._worker_thread,
                    args=(worker_id, cmd_queue, master_queue, self.render_queue, 
                          self.heartbeat_interval),
                    name=f"RenderWorker-{worker_id}"
                )
                
                new_worker.daemon = True
                new_worker.start()
                
                # Store new worker and queues
                self.workers.append(new_worker)
                self.worker_command_queues[worker_id] = cmd_queue
                self.master_queues[worker_id] = master_queue
                self.worker_heartbeats[worker_id] = time.time()
                
                # Send current dataset to new worker
                cmd_queue.put(("update_dataset", self.dataset))
                
                self.logger.info(f"Worker {worker_id} restarted")
                return
    
    def handle_state_change(self, event: ChangeEventProtocol):
        """
        Handle state changes that may invalidate pre-rendered frames.
        
        This is called when the dependency manager detects a relevant change.
        
        Args:
            event: The change event
        """
        # When a change is detected that affects visible objects
        # Simply invalidate all pre-rendered frames
        self.logger.debug(f"Received change event, purging render queue")
        self.purge_render_queue()
    
    def purge_render_queue(self):
        """
        Clear the render queue of all pre-rendered frames.
        """
        # Clear the entire render queue
        while True:
            try:
                self.render_queue.get_nowait()
            except Empty:
                break
    
    def shutdown(self):
        """
        Shutdown the orchestrator and clean up resources.
        """
        # If using workers, shut them down
        if self.use_workers:
            # Signal heartbeat monitor to stop
            self._heartbeat_stop_event.set()
            if self._heartbeat_monitor and self._heartbeat_monitor.is_alive():
                self._heartbeat_monitor.join(timeout=1.0)
            
            # Stop all workers
            for worker_id, queue in self.worker_command_queues.items():
                self.logger.info(f"Stopping worker {worker_id}")
                queue.put(("stop",))
            
            # Wait for workers to terminate
            for worker in self.workers:
                worker.join(timeout=1.0)
                if self.use_multiprocessing and worker.is_alive():
                    self.logger.warning(f"Worker {worker.name} did not terminate, killing")
                    worker.terminate()
            
            # Clear queues
            self.purge_render_queue()
        
        # Unregister from dependency manager
        if self._event_subscription:
            self.dependency_manager.unregister(self._event_subscription)
            self._event_subscription = None
        
        self.logger.info(f"RenderOrchestrator shutdown complete (mode: {self.mode})")
