# TinyDisplay Orchestration System
The orchestration system is used to coordinate all of the activities across tinyDisplay. It is the primary interface used to render the image intended to be sent to the display.

## Time
In TinyDisplay, a tick is a unit of time that is used to determine what actions should be taken at specific times during execution. The actual amount of time that a tick represents is determined by the system that is running TinyDisplay. For example, if TinyDisplay renders at 60 frames per second, then a tick would be 1/60 of a second.  

## Sequence
The orchestration system follows a specific sequence of events to coordinate the activities across tinyDisplay. For each tick, the orchestration system follows the following sequence:
  1. Get updates from any data sources
  2. Update any dependent objects using the DependencyManager
  3. Render the image to be sent to the display
    + Future update will allow for multi-process rendering
  4. Update the system tick value

## RenderOrchestrator

The `RenderOrchestrator` class serves as the master controller for a tinyDisplay application, responsible for coordinating the rendering process and optimizing performance through parallel rendering.

### Core Responsibilities

1. **System Coordination**: Take ownership of the DependencyManager and Dataset instances
2. **Rendering Execution**: Trigger the render process and collect the resulting image
3. **Parallel Processing**: Utilize threads or multiprocessing to generate images ahead of time
4. **Render Queue Management**: Maintain an ordered queue of pre-rendered images
5. **State Change Detection**: Monitor system changes that invalidate pre-rendered images

### Architecture

```
┌─────────────────────────────────┐
│       RenderOrchestrator        │
├─────────────────────────────────┤
│ - dependency_manager            │
│ - dataset                       │
│ - scene_graph                   │
│ - render_queue                  │
│ - worker_pool                   │
├─────────────────────────────────┤
│ + initialize()                  │
│ + render_next_frame()           │
│ + schedule_future_renders()     │
│ + handle_state_change(event)    │
│ + purge_render_queue()          │
└─────────────────────────────────┘
```

### Key Components

#### Dependency Management
- Takes ownership of the DependencyManager instance (replacing the global dependency manager)
- Relies on the existing event system to detect state changes
- Uses the DependencyManager's filtering capabilities to process events

#### Dataset Management
- Maintains the application's dataset instance
- Provides data access to rendering components

#### Render Queue
- Tick-ordered queue of pre-rendered images
- Configurable maximum size
- FIFO structure with timestamp/tick information
- Thread-safe implementation for concurrent access

#### Worker Pool
- Thread or process pool for parallel rendering
- Workers render images for future ticks
- Configurable number of workers based on system capabilities
- Mechanism to terminate workers when necessary

### State Invalidation Strategy

When detecting state changes that affect the rendered output:

1. **Event Monitoring**: Listen for events from the DependencyManager
2. **Visible Object Focus**: Only changes to visible objects or their dependencies are relevant
3. **Simple Invalidation**: When a relevant change is detected, purge the entire render queue
4. **Efficient Processing**: Assume all detected changes require invalidation rather than performing detailed analysis

The DependencyManagement system's event filtering will help ensure that only relevant events (those affecting visible objects) are processed. When such events are detected, the orchestrator will invalidate all pre-rendered images by purging the queue.

### Implementation Approach

```python
class RenderOrchestrator:
    def __init__(self, dependency_manager, dataset, scene_graph, max_queue_size=10):
        # Take ownership of system components
        self.dependency_manager = dependency_manager
        self.dataset = dataset
        self.scene_graph = scene_graph
        
        self.render_queue = Queue(maxsize=max_queue_size)
        self.worker_pool = None
        
    def initialize(self, worker_count=4):
        # Set up event handling from dependency manager
        self.dependency_manager.register_for_events(self.handle_state_change)
        # Initialize worker pool
        self.worker_pool = ThreadPoolExecutor(max_workers=worker_count)
        
    def render_next_frame(self, current_tick):
        # Check if we have a pre-rendered frame
        if not self.render_queue.empty():
            return self.render_queue.get()
        
        # If not, render synchronously
        return self._perform_render(current_tick)
        
    def schedule_future_renders(self, current_tick, count=5):
        # Submit render jobs for future ticks
        future_ticks = range(current_tick + 1, current_tick + count + 1)
        for tick in future_ticks:
            if not self.render_queue.full():
                self.worker_pool.submit(self._render_and_queue, tick)
    
    def handle_state_change(self, event):
        # When a change is detected that affects visible objects
        # Simply invalidate all pre-rendered frames
        self.purge_render_queue()
    
    def purge_render_queue(self):
        # Clear the entire render queue
        while not self.render_queue.empty():
            try:
                self.render_queue.get_nowait()
            except Empty:
                break
```

### Integration Points

- **Dependency System**: Uses the existing DependencyManager to monitor state changes
- **Visibility System**: Relies on the visibility filtering system to focus on relevant events
- **Rendering System**: Interfaces with the render pipeline to produce images

### Next Steps

1. Define the detailed class interface
2. Implement the core orchestration logic
3. Develop thread-safe queue management
4. Create test cases for concurrent rendering scenarios
5. Benchmark performance with different worker configurations
