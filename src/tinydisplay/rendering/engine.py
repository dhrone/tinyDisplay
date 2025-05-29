#!/usr/bin/env python3
"""
Rendering Engine

Provides the core rendering pipeline for tinyDisplay with frame timing,
memory management, and display abstraction.
"""

from typing import Dict, List, Optional, Tuple, Any, Callable, Protocol
from dataclasses import dataclass
import threading
import time
from enum import Enum
from abc import ABC, abstractmethod

from ..widgets.base import Widget
from ..canvas.canvas import Canvas
from ..animation.tick_based import TickAnimationEngine, TickAnimationState


class RenderingState(Enum):
    """Rendering engine states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class RenderingConfig:
    """Rendering engine configuration."""
    target_fps: float = 60.0
    max_frame_time: float = 0.020  # 20ms max frame time
    vsync_enabled: bool = True
    double_buffered: bool = True
    memory_limit_mb: int = 32  # Memory limit for Pi Zero 2W
    enable_profiling: bool = False
    debug_mode: bool = False


@dataclass
class FrameStats:
    """Frame rendering statistics."""
    frame_number: int
    render_time: float
    widget_count: int
    dirty_regions: int
    memory_usage: float
    fps: float
    dropped_frames: int
    current_tick: int = 0  # Current animation tick
    active_animations: int = 0  # Number of active animations


class DisplayAdapter(Protocol):
    """Protocol for display hardware adapters."""
    
    def initialize(self) -> bool:
        """Initialize the display hardware."""
        ...
    
    def get_size(self) -> Tuple[int, int]:
        """Get display size as (width, height)."""
        ...
    
    def clear(self, color: Tuple[int, int, int] = (0, 0, 0)) -> None:
        """Clear the display with specified color."""
        ...
    
    def present(self, frame_buffer: Any) -> None:
        """Present the frame buffer to the display."""
        ...
    
    def shutdown(self) -> None:
        """Shutdown the display hardware."""
        ...


class FrameTimer:
    """High-precision frame timing for consistent frame rates."""
    
    def __init__(self, target_fps: float = 60.0):
        self._target_fps = target_fps
        self._target_frame_time = 1.0 / target_fps
        self._last_frame_time = 0.0
        self._frame_count = 0
        self._dropped_frames = 0
        self._fps_history: List[float] = []
        self._fps_history_size = 60  # Track last 60 frames for FPS calculation
        
    @property
    def target_fps(self) -> float:
        """Get target FPS."""
        return self._target_fps
    
    @property
    def current_fps(self) -> float:
        """Get current measured FPS."""
        if len(self._fps_history) < 2:
            return 0.0
        
        total_time = sum(self._fps_history)
        return len(self._fps_history) / total_time if total_time > 0 else 0.0
    
    @property
    def frame_count(self) -> int:
        """Get total frame count."""
        return self._frame_count
    
    @property
    def dropped_frames(self) -> int:
        """Get dropped frame count."""
        return self._dropped_frames
    
    def start_frame(self) -> float:
        """Start timing a new frame. Returns current time."""
        current_time = time.time()
        
        # Calculate frame time if not first frame
        if self._last_frame_time > 0:
            frame_time = current_time - self._last_frame_time
            
            # Update FPS history
            self._fps_history.append(frame_time)
            if len(self._fps_history) > self._fps_history_size:
                self._fps_history.pop(0)
            
            # Check for dropped frames
            if frame_time > self._target_frame_time * 1.5:
                self._dropped_frames += 1
        
        self._last_frame_time = current_time
        self._frame_count += 1
        
        return current_time
    
    def wait_for_next_frame(self) -> None:
        """Wait for the next frame time to maintain target FPS."""
        current_time = time.time()
        elapsed = current_time - self._last_frame_time
        
        if elapsed < self._target_frame_time:
            sleep_time = self._target_frame_time - elapsed
            time.sleep(sleep_time)
    
    def reset(self) -> None:
        """Reset frame timing statistics."""
        self._frame_count = 0
        self._dropped_frames = 0
        self._fps_history.clear()
        self._last_frame_time = 0.0


class MemoryManager:
    """Memory management for rendering operations."""
    
    def __init__(self, limit_mb: int = 32):
        self._limit_bytes = limit_mb * 1024 * 1024
        self._allocated_buffers: Dict[str, Any] = {}
        self._buffer_sizes: Dict[str, int] = {}
        self._total_allocated = 0
        self._lock = threading.RLock()
    
    @property
    def memory_limit(self) -> int:
        """Get memory limit in bytes."""
        return self._limit_bytes
    
    @property
    def memory_used(self) -> int:
        """Get currently allocated memory in bytes."""
        return self._total_allocated
    
    @property
    def memory_available(self) -> int:
        """Get available memory in bytes."""
        return self._limit_bytes - self._total_allocated
    
    def allocate_buffer(self, buffer_id: str, size: int) -> bool:
        """Allocate a buffer with specified size.
        
        Args:
            buffer_id: Unique identifier for the buffer
            size: Size in bytes
            
        Returns:
            True if allocation successful, False if would exceed limit
        """
        with self._lock:
            # Check if buffer already exists
            if buffer_id in self._allocated_buffers:
                self.deallocate_buffer(buffer_id)
            
            # Check if allocation would exceed limit
            if self._total_allocated + size > self._limit_bytes:
                return False
            
            # Allocate buffer (placeholder - actual implementation would allocate real buffer)
            self._allocated_buffers[buffer_id] = f"buffer_{buffer_id}_{size}"
            self._buffer_sizes[buffer_id] = size
            self._total_allocated += size
            
            return True
    
    def deallocate_buffer(self, buffer_id: str) -> bool:
        """Deallocate a buffer.
        
        Args:
            buffer_id: Buffer identifier
            
        Returns:
            True if buffer was deallocated, False if not found
        """
        with self._lock:
            if buffer_id in self._allocated_buffers:
                size = self._buffer_sizes.pop(buffer_id)
                self._allocated_buffers.pop(buffer_id)
                self._total_allocated -= size
                return True
            return False
    
    def get_buffer(self, buffer_id: str) -> Optional[Any]:
        """Get a buffer by ID."""
        return self._allocated_buffers.get(buffer_id)
    
    def cleanup_all(self) -> None:
        """Deallocate all buffers."""
        with self._lock:
            self._allocated_buffers.clear()
            self._buffer_sizes.clear()
            self._total_allocated = 0


class RenderingEngine:
    """Core rendering engine for tinyDisplay.
    
    Manages the rendering pipeline including:
    - Frame timing and synchronization
    - Memory management
    - Display adapter coordination
    - Performance monitoring
    """
    
    def __init__(self, config: RenderingConfig, display_adapter: Optional[DisplayAdapter] = None):
        """Initialize the rendering engine.
        
        Args:
            config: Rendering configuration
            display_adapter: Display hardware adapter (optional)
        """
        self._config = config
        self._display_adapter = display_adapter
        
        # Engine state
        self._state = RenderingState.STOPPED
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._render_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Rendering components
        self._frame_timer = FrameTimer(config.target_fps)
        self._memory_manager = MemoryManager(config.memory_limit_mb)
        
        # Tick-based animation system
        self._tick_animation_engine = TickAnimationEngine()
        self._current_tick = 0
        self._animation_frame_states: Dict[str, TickAnimationState] = {}
        
        # Canvas management
        self._current_canvas: Optional[Canvas] = None
        self._render_queue: List[Canvas] = []
        
        # Statistics
        self._frame_stats: List[FrameStats] = []
        self._stats_history_size = 300  # Keep 5 seconds at 60fps
        
        # Event handling
        self._event_handlers: Dict[str, Set[Callable]] = {
            'frame_rendered': set(),
            'error': set(),
            'memory_warning': set(),
            'animation_tick': set(),  # New event for tick advancement
            'animation_state_changed': set()  # New event for animation state changes
        }
    
    # Properties
    @property
    def config(self) -> RenderingConfig:
        """Get rendering configuration."""
        return self._config
    
    @property
    def state(self) -> RenderingState:
        """Get current rendering state."""
        return self._state
    
    @property
    def current_fps(self) -> float:
        """Get current measured FPS."""
        return self._frame_timer.current_fps
    
    @property
    def frame_count(self) -> int:
        """Get total frame count."""
        return self._frame_timer.frame_count
    
    @property
    def memory_usage(self) -> float:
        """Get memory usage as percentage of limit."""
        return (self._memory_manager.memory_used / self._memory_manager.memory_limit) * 100
    
    @property
    def latest_frame_stats(self) -> Optional[FrameStats]:
        """Get the latest frame statistics."""
        return self._frame_stats[-1] if self._frame_stats else None
    
    @property
    def tick_animation_engine(self) -> TickAnimationEngine:
        """Get the tick animation engine."""
        return self._tick_animation_engine
    
    @property
    def current_tick(self) -> int:
        """Get the current animation tick."""
        return self._current_tick
    
    @property
    def active_animation_count(self) -> int:
        """Get the number of active animations."""
        return len(self._tick_animation_engine.get_active_animations_at(self._current_tick))
    
    # Lifecycle methods
    def initialize(self) -> bool:
        """Initialize the rendering engine."""
        if self._state != RenderingState.STOPPED:
            return False
        
        try:
            # Initialize display adapter if provided
            if self._display_adapter:
                if not self._display_adapter.initialize():
                    return False
            
            # Allocate frame buffers
            if self._config.double_buffered:
                display_size = self._display_adapter.get_size() if self._display_adapter else (128, 64)
                buffer_size = display_size[0] * display_size[1] * 4  # RGBA
                
                if not self._memory_manager.allocate_buffer("front_buffer", buffer_size):
                    return False
                if not self._memory_manager.allocate_buffer("back_buffer", buffer_size):
                    return False
            
            self._state = RenderingState.STOPPED
            return True
            
        except Exception as e:
            self._state = RenderingState.ERROR
            self._call_event_handlers('error', e)
            return False
    
    def start(self) -> bool:
        """Start the rendering engine."""
        if self._state != RenderingState.STOPPED:
            return False
        
        try:
            self._state = RenderingState.STARTING
            self._stop_event.clear()
            self._pause_event.clear()
            
            # Start render thread
            self._render_thread = threading.Thread(target=self._render_loop, daemon=True)
            self._render_thread.start()
            
            self._state = RenderingState.RUNNING
            return True
            
        except Exception as e:
            self._state = RenderingState.ERROR
            self._call_event_handlers('error', e)
            return False
    
    def pause(self) -> bool:
        """Pause rendering."""
        if self._state != RenderingState.RUNNING:
            return False
        
        self._state = RenderingState.PAUSING
        self._pause_event.set()
        self._state = RenderingState.PAUSED
        return True
    
    def resume(self) -> bool:
        """Resume rendering."""
        if self._state != RenderingState.PAUSED:
            return False
        
        self._pause_event.clear()
        self._state = RenderingState.RUNNING
        return True
    
    def stop(self) -> bool:
        """Stop the rendering engine."""
        if self._state in (RenderingState.STOPPED, RenderingState.ERROR):
            return True
        
        self._state = RenderingState.STOPPING
        self._stop_event.set()
        
        # Wait for render thread to finish
        if self._render_thread and self._render_thread.is_alive():
            self._render_thread.join(timeout=1.0)
        
        self._state = RenderingState.STOPPED
        return True
    
    def shutdown(self) -> None:
        """Shutdown the rendering engine and clean up resources."""
        self.stop()
        
        # Cleanup memory
        self._memory_manager.cleanup_all()
        
        # Shutdown display adapter
        if self._display_adapter:
            self._display_adapter.shutdown()
        
        # Clear statistics
        self._frame_stats.clear()
    
    # Canvas management
    def set_canvas(self, canvas: Canvas) -> None:
        """Set the current canvas to render."""
        with self._lock:
            self._current_canvas = canvas
    
    def add_canvas_to_queue(self, canvas: Canvas) -> None:
        """Add a canvas to the render queue."""
        with self._lock:
            if canvas not in self._render_queue:
                self._render_queue.append(canvas)
    
    def remove_canvas_from_queue(self, canvas: Canvas) -> bool:
        """Remove a canvas from the render queue."""
        with self._lock:
            if canvas in self._render_queue:
                self._render_queue.remove(canvas)
                return True
            return False
    
    # Event handling
    def add_event_handler(self, event: str, handler: Callable) -> None:
        """Add an event handler."""
        if event in self._event_handlers:
            self._event_handlers[event].add(handler)
    
    def remove_event_handler(self, event: str, handler: Callable) -> None:
        """Remove an event handler."""
        if event in self._event_handlers:
            self._event_handlers[event].discard(handler)
    
    # Statistics
    def get_frame_stats_history(self, count: int = 60) -> List[FrameStats]:
        """Get recent frame statistics."""
        return self._frame_stats[-count:] if self._frame_stats else []
    
    def reset_statistics(self) -> None:
        """Reset all statistics."""
        self._frame_timer.reset()
        self._frame_stats.clear()
    
    # Internal methods
    def _render_loop(self) -> None:
        """Main rendering loop (runs in separate thread)."""
        try:
            while not self._stop_event.is_set():
                # Handle pause
                if self._pause_event.is_set():
                    time.sleep(0.01)  # Small sleep to prevent busy waiting
                    continue
                
                # Start frame timing
                frame_start_time = self._frame_timer.start_frame()
                
                # Advance animation tick once per render cycle
                self._tick_animation_engine.advance_tick()
                self._current_tick = self._tick_animation_engine.current_tick
                
                # Compute current frame animation state using current tick
                self._animation_frame_states = self._tick_animation_engine.compute_frame_state(self._current_tick)
                
                # Apply frame state to widgets and render
                self._apply_frame_state_to_widgets(self._animation_frame_states)
                
                # Render current canvas
                rendered_widgets = 0
                dirty_regions = 0
                
                if self._current_canvas and self._current_canvas.needs_render():
                    rendered_widgets, dirty_regions = self._render_canvas(self._current_canvas)
                
                # Render queued canvases
                for canvas in self._render_queue.copy():
                    if canvas.needs_render():
                        w, d = self._render_canvas(canvas)
                        rendered_widgets += w
                        dirty_regions += d
                
                # Calculate frame statistics
                frame_end_time = time.time()
                render_time = frame_end_time - frame_start_time
                active_animations = self.active_animation_count
                
                frame_stats = FrameStats(
                    frame_number=self._frame_timer.frame_count,
                    render_time=render_time,
                    widget_count=rendered_widgets,
                    dirty_regions=dirty_regions,
                    memory_usage=self.memory_usage,
                    fps=self._frame_timer.current_fps,
                    dropped_frames=self._frame_timer.dropped_frames,
                    current_tick=self._current_tick,
                    active_animations=active_animations
                )
                
                # Store statistics
                self._frame_stats.append(frame_stats)
                if len(self._frame_stats) > self._stats_history_size:
                    self._frame_stats.pop(0)
                
                # Call event handlers
                self._call_event_handlers('frame_rendered', frame_stats)
                self._call_event_handlers('animation_tick', self._current_tick, self._animation_frame_states)
                
                if active_animations > 0:
                    self._call_event_handlers('animation_state_changed', self._animation_frame_states)
                
                # Check for memory warnings
                if self.memory_usage > 80:
                    self._call_event_handlers('memory_warning', self.memory_usage)
                
                # Wait for next frame (real-time only for FPS control, not animation logic)
                if self._config.vsync_enabled:
                    self._frame_timer.wait_for_next_frame()
                
        except Exception as e:
            self._state = RenderingState.ERROR
            self._call_event_handlers('error', e)
    
    def _render_canvas(self, canvas: Canvas) -> Tuple[int, int]:
        """Render a single canvas.
        
        Returns:
            Tuple of (widgets_rendered, dirty_regions)
        """
        try:
            # Clear display if needed
            if self._display_adapter and canvas.config.auto_clear:
                self._display_adapter.clear(canvas.config.background_color)
            
            # Render canvas
            canvas.render()
            
            # Present to display
            if self._display_adapter:
                front_buffer = self._memory_manager.get_buffer("front_buffer")
                if front_buffer:
                    self._display_adapter.present(front_buffer)
            
            # Count rendered widgets and dirty regions
            widget_count = len([w for w in canvas.get_children() if w.needs_render()])
            dirty_regions = len(canvas._dirty_regions) if hasattr(canvas, '_dirty_regions') else 0
            
            return widget_count, dirty_regions
            
        except Exception as e:
            self._call_event_handlers('error', e)
            return 0, 0
    
    def _apply_frame_state_to_widgets(self, frame_states: Dict[str, TickAnimationState]) -> None:
        """Apply tick-based animation states to widgets.
        
        Args:
            frame_states: Dictionary mapping animation_id to animation state
        """
        try:
            # Apply animation states to current canvas widgets
            if self._current_canvas:
                self._apply_animation_states_to_canvas(self._current_canvas, frame_states)
            
            # Apply animation states to queued canvas widgets
            for canvas in self._render_queue:
                self._apply_animation_states_to_canvas(canvas, frame_states)
                
        except Exception as e:
            self._call_event_handlers('error', e)
    
    def _apply_animation_states_to_canvas(self, canvas: Canvas, frame_states: Dict[str, TickAnimationState]) -> None:
        """Apply animation states to all widgets in a canvas.
        
        Args:
            canvas: Canvas containing widgets
            frame_states: Dictionary mapping animation_id to animation state
        """
        try:
            # Update animations for all widgets in canvas
            for widget in canvas.get_children():
                # Call widget's tick-based animation update
                if hasattr(widget, 'update_animations'):
                    widget.update_animations(self._current_tick)
                
                # Apply any specific animation states for this widget
                widget_animation_ids = [aid for aid in frame_states.keys() 
                                      if aid.startswith(f"{widget.widget_id}_")]
                
                for animation_id in widget_animation_ids:
                    animation_state = frame_states[animation_id]
                    self._apply_animation_state_to_widget(widget, animation_state)
                    
        except Exception as e:
            self._call_event_handlers('error', e)
    
    def _apply_animation_state_to_widget(self, widget: Widget, animation_state: TickAnimationState) -> None:
        """Apply a specific animation state to a widget.
        
        Args:
            widget: Widget to apply animation state to
            animation_state: Animation state to apply
        """
        try:
            # Apply position if different
            if widget.position != animation_state.position:
                widget.position = animation_state.position
            
            # Apply opacity/alpha if different
            if abs(widget.alpha - animation_state.opacity) > 0.001:
                widget.alpha = animation_state.opacity
            
            # Apply rotation if widget supports it
            if hasattr(widget, 'rotation') and abs(getattr(widget, 'rotation', 0) - animation_state.rotation) > 0.001:
                widget.rotation = animation_state.rotation
            
            # Apply scale if widget supports it
            if hasattr(widget, 'scale') and getattr(widget, 'scale', (1.0, 1.0)) != animation_state.scale:
                widget.scale = animation_state.scale
            
            # Apply custom properties
            for prop_name, prop_value in animation_state.custom_properties.items():
                if hasattr(widget, prop_name):
                    setattr(widget, prop_name, prop_value)
                    
        except Exception as e:
            self._call_event_handlers('error', e)
    
    def _call_event_handlers(self, event: str, *args, **kwargs) -> None:
        """Call all registered event handlers for an event."""
        for handler in self._event_handlers.get(event, set()).copy():
            try:
                handler(*args, **kwargs)
            except Exception as e:
                print(f"Error in rendering event handler {event}: {e}")
    
    def __repr__(self) -> str:
        return (f"RenderingEngine(state={self._state.value}, fps={self.current_fps:.1f}, "
                f"memory={self.memory_usage:.1f}%)") 