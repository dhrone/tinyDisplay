# Coordinated Marquee Timelines

This document explains the coordinated timeline system for marquee widgets with interdependent animations.

## Overview

The tinyDisplay marquee system has been extended to support deterministic rendering of interdependent marquee animations. This is accomplished using a timeline coordination manager that resolves dependencies between SYNC and WAIT_FOR statements.

## Key Features

1. **Deterministic Rendering**: Animations can be rendered at arbitrary ticks with all dependencies resolved
2. **Precomputed Timelines**: Dependencies are resolved during initialization
3. **Support for Cyclic Dependencies**: The system can handle widgets that depend on each other
4. **Efficient Memory Usage**: Maintains timeline-based implementation without major refactoring
5. **Multi-process Support**: Timelines can be independently rendered across processes
6. **Selective Recalculation**: Only affected widgets and their dependents are recalculated when content changes

## How It Works

### 1. Registration Phase

When a marquee widget is created:
- It registers itself with the `TimelineCoordinationManager`
- It extracts SYNC events from its DSL program and registers them
- It identifies WAIT_FOR dependencies and registers them

### 2. Resolution Phase

Once all marquees are registered:
- The system builds a dependency graph
- It determines an order to resolve timelines using topological sorting
- For cycles, it uses fixed-point iteration to find a stable solution
- Each widget computes its timeline with knowledge of when events occur

### 3. Rendering Phase

During rendering:
- Each widget can render at any arbitrary tick
- Timeline positions are fully deterministic
- No re-computation is needed unless widget content changes

### 4. Recalculation Phase

When content changes:
- Only affected widgets and their dependents are recalculated
- The dependency graph is used to identify which widgets need updates
- Changes propagate through the dependency chain automatically

## Usage

### Basic Setup

```python
from tinyDisplay.render.new_marquee import new_marquee
from tinyDisplay.render.text import text

# Create shared event tracking
shared_events = {}
shared_sync_events = set()

# First marquee generates an event
marquee1 = new_marquee(
    widget=text1,
    program="""
    LOOP(INFINITE) {
        MOVE(LEFT, 100) { step=1 };
        SYNC(event_name);  # Signal an event
    } END;
    """,
    shared_events=shared_events,
    shared_sync_events=shared_sync_events,
)

# Second marquee waits for the event
marquee2 = new_marquee(
    widget=text2,
    program="""
    LOOP(INFINITE) {
        WAIT_FOR(event_name, 50);  # Wait for event with timeout
        MOVE(RIGHT, 100) { step=1 };
    } END;
    """,
    shared_events=shared_events,
    shared_sync_events=shared_sync_events,
)

# Initialize all timelines (resolves dependencies)
new_marquee.initialize_all_timelines()

# Render the widgets (timeline dependencies are already resolved)
for i in range(100):
    img1, _ = marquee1.render(tick=i)
    img2, _ = marquee2.render(tick=i)
```

### Timeline Recalculation

When widget content changes, you have several options:

#### 1. Automatic Recalculation

Content changes are detected automatically during rendering:

```python
# Update widget content
text1.text = "New content"

# Next render will automatically detect the change and recalculate as needed
img1, _ = marquee1.render(tick=next_tick)
img2, _ = marquee2.render(tick=next_tick)  # This will also update if dependent
```

#### 2. Selective Manual Recalculation

For more control, you can explicitly mark widgets for recalculation:

```python
# Update widget content
text1.text = "New content"

# Mark specific widgets for recalculation (and their dependents)
marquee1.mark_for_recalculation()

# Or use the convenience method for multiple widgets
new_marquee.reset_widgets([marquee1, marquee3])
```

#### 3. Full Reset

For a complete reset of all timelines:

```python
# Force a full recalculation of all timelines
new_marquee.reset_all_timelines(force_full_reset=True)
```

## Implementation Components

### TimelineCoordinationManager

The central coordination system that:
- Manages widget registration
- Tracks SYNC event positions
- Resolves dependencies between widgets
- Handles circular dependencies

### MarqueeExecutor Extensions

The executor has been extended to:
- Extract SYNC events without full timeline generation
- Support timeline generation with resolved events
- Track event positions in the timeline

### new_marquee Extensions

The marquee widget has been enhanced to:
- Register with the coordination manager
- Compute timelines with resolved dependencies
- Ensure deterministic rendering at arbitrary ticks
- Support selective recalculation when content changes

## Technical Implementation

The implementation uses these algorithms:
- **Dependency Graph**: For modeling widget relationships
- **Topological Sorting**: For resolving dependencies in order
- **Fixed-Point Iteration**: For resolving circular dependencies
- **Binary Search**: For efficient timeline position lookup
- **Incremental Recalculation**: For updating only affected widgets

## Edge Cases Handled

1. **Circular Dependencies**: Resolved using fixed-point iteration
2. **Missing Events**: Widgets handle timeouts for events that never occur
3. **Variable Changes**: Timelines are invalidated when dependencies change
4. **Multiprocessing**: Each process can independently render any tick
5. **Partial Updates**: Only affected widgets are recalculated when content changes

## Performance Considerations

The selective recalculation feature provides significant performance benefits:

1. **Minimized Computation**: Only the widgets that need updates are recalculated
2. **Dependency Tracking**: Changes automatically propagate through the dependency chain
3. **Memory Efficiency**: Timeline data structures are reused when possible
4. **Fine-grained Control**: API allows specifying exactly which widgets to update

## Limitations

1. The timeline length calculation is still incremental and approximate for complex DSL programs
2. Very complex interdependencies with many widgets may take longer to resolve
3. For absolute determinism, all widgets should be created before rendering begins

## Examples

See `tests/test_coordinated_marquees.py` for a complete working example that demonstrates:
- Two marquees with SYNC/WAIT_FOR coordination
- Timeline initialization and rendering
- Deterministic animation with dependencies 