# DependencyManager Requirements

## 1. Introduction & Purpose
This document captures the functional and non-functional requirements for the `DependencyManager` class in the **tinyDisplay** application. The `DependencyManager` will track relationships between objects (widgets, datasets, dynamicValues, etc.), batch-change events per display tick, and notify dependents when their upstream data changes.

## 2. Core API for Dependency Registration

- **register(dependent, target or targets) → SubscriptionHandle or List[SubscriptionHandle]**  
  Register one or more observable targets for a dependent. If a single target is passed, returns a single handle; if an iterable is passed, returns a list of handles.
  ```python
  # single target
  handle = dm.register(widget, dataset)
  # bulk targets
  handles = dm.register(widget, [dataset1, dataset2, dataset3])
  ```

- **unregister(handle) or unregister(dependent, target)**  
  Remove a subscription, preventing further notifications. For bulk removal, support passing a list of handles or a dependent with a list of targets.

- *(Optional)* **register_all(dependent, [obs1, obs2, …]) / unregister_all(dependent)**  
  Convenience methods that call register/unregister under the hood for multiple targets.

- **Use weak references** for both observables and dependents to avoid memory leaks.

## 3. Change-Event Model (`ChangeEvent` Protocol)

Use Python’s structural typing (`typing.Protocol`) to define the shape of change events and processors:

```python
from typing import Protocol, Any, Dict, List, runtime_checkable

@runtime_checkable
class ChangeEventProtocol(Protocol):
    # Defines the interface for all change events.
    event_type: str               # e.g. "image_updated", "size_changed"
    source: Any                   # Object that emitted the change
    metadata: Dict[str, Any]      # Additional data (crop rect, dimensions, timestamp)

@runtime_checkable
class ChangeProcessorProtocol(Protocol):
    # Defines the interface for any object that processes change events.
    def process_change(self, events: List[ChangeEventProtocol]) -> None:
        ...
```

- **Extensible**: New event types can be user-defined by matching the protocol.
- **Runtime check**: Managers may optionally verify isinstance(obj, ChangeEventProtocol) before dispatch.

## 4. Notification Dispatch

### 4.1 Raising Change Events

- **raise_event(event: ChangeEventProtocol)** on DependencyManager  
  - Changeable objects (datasets, dynamicValues, widgets, etc.) invoke this method whenever their internal state changes.  
  - Events are enqueued to an internal per-tick queue; no immediate notification is sent.

- **Event queue semantics**  
  - Primary queue for “current tick” events.  
  - Secondary queue for “cascading” events generated during dispatch (see 4.3).

### 4.2 Per-Tick Dispatch

- **Scheduler integration**  
  - A central TinyDisplayScheduler calls DependencyManager.dispatch_events(visible: Optional[Set[Any]] = None) once per tick.

- **dispatch_events workflow**:
  1. Snapshot all events from the primary queue.  
  2. Map each event to its source observable and collect direct dependents via the registration graph.  
  3. Compute transitive closure of dependents to notify, optionally pruned by a visible set (see Section 5).  
  4. Batch events per dependent: aggregate all events relevant to each into a single list.  
  5. Deliver by invoking dependent.process_change(events_batch).  
  6. Swap queues: move any new events from the secondary queue into the primary for the next dispatch cycle.  
  7. Clear the now-empty secondary queue.

- **Delivery behavior**  
  - By default, cascading is enabled (see Section 4.3). Dependents may receive multiple notifications within the same tick if their own change handlers emit new events, up to the fixed-point iteration limit.  
  - Order of notification follows a topological sort of the dependency subgraph (cycles broken gracefully).

### 4.3 Cascading Changes

- During dependent.process_change, the object may modify its own state and call raise_event again.  
- Secondary queue captures these cascading events for the same tick.

#### 4.3.1 Controlling Cascade Storms

To keep things simple in this first version, we’ll only support a fixed-point iteration approach:

- **Fixed-Point Iteration with Max Loops**  
  When dispatching (intra-tick), the loop will:  
  1. Drain the secondary queue of cascading events.  
  2. Deliver notifications to affected dependents.  
  3. Repeat steps 1–2 until the secondary queue is empty *or* a configurable iteration limit (e.g. 10 loops) is reached.  
  4. If the limit is hit, any remaining events are deferred to the next tick.

This ensures all cascades in a tick settle without runaway storms, while allowing dependents to be notified multiple times if needed.

### 4.4 Efficiency Considerations

- Incremental graph traversal: start from changed observables only, not the entire graph.  
- Visited/dependent de-duplication: track notified dependents per tick to avoid duplicate work.  
- Event de-duplication: merge identical (event_type, source) pairs before batching.

### 4.5 API Signatures

```python
class DependencyManager:
    def raise_event(self, event: ChangeEventProtocol) -> None:
        ...
    def dispatch_events(self, visible: Optional[Set[Any]] = None,
                        *, intra_tick_cascade: bool = True) -> None:
        ...
```

## 5. Dependency Graph Management

... (rest of document omitted for brevity) ...
