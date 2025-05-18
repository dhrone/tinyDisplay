# TinyDisplay Dependency Management System

A lightweight, type-safe dependency management system with support for reactive programming patterns, namespacing, and efficient event propagation.

## Table of Contents
- [Core Concepts](#core-concepts)
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [API Reference](#api-reference)
- [Advanced Features](#advanced-features)
- [Best Practices](#best-practices)
- [Performance Considerations](#performance-considerations)
- [Troubleshooting](#troubleshooting)

## Core Concepts

### Dependency Graph
- **Nodes**: Represent observable objects and their dependents
- **Edges**: Represent dependencies between nodes (A → B means "B depends on A")
- **Directed Acyclic Graph (DAG)**: Ensures no circular dependencies

### Event Propagation
- **Direct Dependencies**: Events only propagate to direct dependents
- **Active Propagation**: Use `CascadingRelay` for multi-hop event propagation
- **Event Deduplication**: Automatic deduplication of events in the same tick

### Namespacing
- Isolate dependency graphs
- Control visibility and accessibility
- Support for global and namespaced events

## Installation

```bash
# Using pip
pip install tinydisplay

# Using poetry
poetry add tinydisplay
```

## Basic Usage

### Creating and Using a Dependency Manager

```python
from tinyDisplay.dependency import DependencyManager

# Create a new dependency manager
manager = DependencyManager()

# Create observable objects
class DataSource:
    def __init__(self, manager, name):
        self.manager = manager
        self.name = name
    
    def update(self, value):
        self.manager.raise_event(ChangeEvent(
            event_type="data_updated",
            source=self,
            data=value
        ))

# Create a dependent
class DataProcessor(ChangeProcessorProtocol):
    def process_change(self, events):
        for event in events:
            print(f"Processing {event.event_type} from {event.source.name}: {event.data}")

# Set up dependencies
source = DataSource(manager, "sensor1")
processor = DataProcessor()
manager.register(processor, source)

# Trigger updates
source.update(42)  # Will trigger processor.process_change
```

## API Reference

### DependencyManager

#### Methods
- `register(dependent: Any, observable: Any) -> SubscriptionHandle`: Register a dependency
- `unregister(handle: SubscriptionHandle)`: Remove a specific dependency
- `unregister_all(dependent: Any)`: Remove all dependencies for a dependent
- `raise_event(event: ChangeEvent)`: Queue an event for processing
- `dispatch_events()`: Process all queued events
- `get_dependents(observable: Any) -> Set[Any]`: Get all dependents of an observable
- `clear()`: Clear all dependencies and queued events

### ChangeEvent

#### Attributes
- `event_type: str`: Type of the event
- `source: Any`: Source object that raised the event
- `data: Any`: Optional data payload
- `metadata: Dict[str, Any]`: Additional metadata

## Advanced Features

### Active Propagation with CascadingRelay

```python
class CascadingRelay(ChangeProcessorProtocol):
    def __init__(self, manager, target):
        self.manager = manager
        self.target = target
    
    def process_change(self, events):
        # Forward events to the target
        for event in events:
            self.manager.raise_event(ChangeEvent(
                event_type=event.event_type,
                source=self.target,
                data=event.data,
                metadata={"original_source": event.source}
            ))

# Usage
source = DataSource(manager, "source")
relay = CascadingRelay(manager, relay_target)
processor = DataProcessor()

manager.register(relay, source)
manager.register(processor, relay_target)
```

### Namespacing

```python
from tinyDisplay.dependency.namespace import get_namespaced_manager

# Create namespaced managers
ui_manager = get_namespaced_manager("ui")
data_manager = get_namespaced_manager("data")

# These operate independently
ui_source = DataSource(ui_manager, "ui_source")
data_source = DataSource(data_manager, "data_source")

# Global events still work
@manager.global_handler
def handle_all_events(events):
    for event in events:
        print(f"Global event: {event.event_type}")
```

## Best Practices

### 1. Use Strong Typing
```python
class TemperatureEvent(ChangeEvent):
    def __init__(self, source, celsius: float):
        super().__init__("temperature_update", source, data=celsius)
    
    @property
    def temperature_celsius(self) -> float:
        return self.data
```

### 2. Keep Event Handlers Light
```python
class DataProcessor(ChangeProcessorProtocol):
    def process_change(self, events):
        # Do minimal processing here
        for event in events:
            self._process_event_async(event)
    
    @background_task
def _process_event_async(self, event):
    # Heavy processing here
    pass
```

### 3. Use Context Managers for Cleanup
```python
with manager.temporary_subscription(processor, source):
    # processor is subscribed to source in this block
    source.update("temporary data")
# Automatically unsubscribed here
```

## Performance Considerations

- **Batch Processing**: Events are processed in batches during `dispatch_events()`
- **Weak References**: Uses weak references to prevent memory leaks
- **Event Deduplication**: Duplicate events in the same tick are automatically deduplicated
- **Lazy Evaluation**: Dependencies are only evaluated when needed

## Troubleshooting

### Common Issues

#### Events Not Being Received
- Verify the dependent is properly registered
- Check that `dispatch_events()` is being called
- Ensure the event type matches what the dependent is expecting

#### Memory Leaks
- Use `unregister` or `unregister_all` when dependencies are no longer needed
- Avoid strong references in event handlers
- Use the `weakref` module for custom event handlers

### Debugging
Enable debug logging to track event flow:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("tinyDisplay.dependency")
```

## License

MIT License - See [LICENSE](../LICENSE) for details.
