# Safely Interacting with the Global Dataset

This guide provides information on how to safely interact with tinyDisplay's global dataset module, especially in multi-threaded environments.

## Basic Usage

```python
import tinyDisplay.global_dataset as global_data

# Initialize early in your application
global_data.initialize({
    'theme': {'color': 'blue'},
    'user': {'name': 'John'}
})

# Simple read operations
theme = global_data.get_database('theme')
color = theme['color']  # 'blue'

# Simple write operations
global_data.update_database('theme', {'color': 'red'})
```

## Thread Safety Guidelines

1. **Read Operations**: Simple reads (`get_database`, `get_value`) are safe without locks
2. **Write Operations**: All write operations (`update_database`, `add_database`) are internally synchronized
3. **Read-Modify-Write**: Use the atomic helper methods to avoid race conditions

## Atomic Operations

For operations that involve reading and then modifying data:

```python
# UNSAFE pattern - potential race condition:
counter = global_data.get_database('stats')['visits']
global_data.update_database('stats', {'visits': counter + 1})

# SAFE pattern - use update_counter:
new_value = global_data.update_counter('stats', 'visits')

# SAFE pattern - use with_lock for custom operations:
def increment_by_ten():
    counter = global_data.get_database('stats')['visits']
    global_data.update_database('stats', {'visits': counter + 10})
    return counter + 10

new_value = global_data.with_lock(increment_by_ten)
```

## Multi-Value Operations

When working with multiple values that need consistency:

```python
# Reading multiple values atomically:
values = global_data.read_values(
    ('user', 'name'),
    ('user', 'email'),
    ('prefs', 'theme')
)
name = values[('user', 'name')]
email = values[('user', 'email')]

# Updating multiple databases atomically:
global_data.update_multiple({
    'user': {'last_login': now},
    'stats': {'login_count': count + 1}
})
```

## Object-Level Consistency

For related values that must be consistent:

```python
# Group related values into a single object:
global_data.update_database('status', {
    'state': {
        'progress': 50,
        'status': 'running',
        'timestamp': time.time()
    }
})

# Reading the entire object ensures consistency:
state = global_data.get_database('status')['state']
progress = state['progress']
status = state['status']
```

## Best Practices

1. **Initialize Early**: Call `initialize()` during application startup
2. **Prefer Atomic Operations**: Use built-in atomic helpers whenever possible
3. **Structure Data for Consistency**: Group related fields that need consistency
4. **Minimize Lock Time**: In custom `with_lock` operations, minimize the code inside
5. **Don't Modify Directly**: Avoid modifying returned dictionaries directly

## Common Patterns

```python
# Increment a counter
visits = global_data.update_counter('stats', 'visits')

# Safely get or create a database
user_prefs = global_data.get_or_create_database('user_prefs', {'theme': 'dark'})

# Set a single value
global_data.set_value('config', 'debug_mode', True)

# Get a value with default
api_key = global_data.get_value('settings', 'api_key', default='')
```

## Common Pitfalls

1. **Direct Dictionary Modification**: Never modify the dictionaries returned by `get_database` directly
2. **Multiple Step Updates**: Don't read, modify, and update in separate steps without locking
3. **Long Operations in Locks**: Avoid long-running operations inside `with_lock` functions
4. **Nested Locks**: Avoid calling functions that might acquire the same lock from within a locked section

## Available Thread-Safe Methods

| Method | Description |
|--------|-------------|
| `initialize(initial_data=None)` | Initialize the global dataset |
| `get_dataset()` | Get the global dataset instance |
| `add_database(name, data)` | Add a new database |
| `update_database(name, data, merge=True)` | Update a database |
| `get_database(name, default=None)` | Get a database |
| `reset()` | Reset the global dataset |
| `with_lock(func, *args, **kwargs)` | Execute a function with the global dataset lock held |
| `read_values(*paths)` | Read multiple values atomically |
| `update_multiple(updates, merge=True)` | Update multiple databases atomically |
| `get_value(db_name, key, default=None)` | Get a single value |
| `set_value(db_name, key, value)` | Set a single value |
| `get_or_create_database(db_name, default={})` | Get or create a database |
| `update_counter(db_name, counter_name, increment=1)` | Increment a counter |

## Implementation Details

The global dataset uses a readers-writer pattern where:
- Read operations don't need locks (for better performance)
- Write operations are properly synchronized with a `threading.RLock`

This approach allows for high read concurrency while ensuring data consistency during updates. 