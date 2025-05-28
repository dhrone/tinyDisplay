"""
Global dataset module for tinyDisplay.

This module provides a singleton dataset that can be accessed from anywhere in a
tinyDisplay application, making it easier to share data between components.

Thread Safety:
    This implementation is thread-safe with the following characteristics:
    - Write operations (initialize, add, update, reset) are synchronized with locks
    - Read operations (get_dataset, get_database) don't require locks by default
    - Helper methods for atomic operations that require multiple reads/writes
    - The lock is exposed for callers that need to implement custom atomic operations

Usage Examples:
    ```python
    # Initialize global dataset
    import tinyDisplay.global_dataset as global_data
    
    # Initialize with initial data
    global_data.initialize({
        'theme': {'color': 'blue', 'font': 'Arial'},
        'user': {'name': 'John'}
    })
    
    # Get a database
    theme = global_data.get_database('theme')
    print(theme['color'])  # 'blue'
    
    # Update a database
    global_data.update_database('theme', {'color': 'red'})
    
    # For atomic operations that read and write
    def increment_counter():
        counters = global_data.get_database('counters')
        current = counters.get('visits', 0)
        global_data.update_database('counters', {'visits': current + 1})
        return current + 1
    
    # Use with_lock for thread safety
    new_count = global_data.with_lock(increment_counter)
    ```
"""
import logging
import threading
from typing import Dict, Any, Optional, Union, Tuple, Callable, TypeVar, List

from tinyDisplay.utility.dataset import dataset

# Global dataset instance
_global_dataset = None
_logger = logging.getLogger("tinyDisplay")
_write_lock = threading.RLock()  # Lock for write operations

# Type variable for generic function return value
T = TypeVar('T')

def initialize(initial_data: Optional[Dict[str, Dict[str, Any]]] = None) -> dataset:
    """Initialize the global dataset.
    
    Args:
        initial_data: Optional dictionary of initial data to populate the dataset
                     Format: {db_name: {key: value}}
    
    Returns:
        The initialized dataset
    
    Note:
        This should be called early in your application initialization.
        This operation is thread-safe.
    """
    global _global_dataset
    
    with _write_lock:
        if _global_dataset is not None:
            _logger.warning("Global dataset was already initialized. Reinitializing will replace existing data.")
        
        _global_dataset = dataset(initial_data or {})
        return _global_dataset

def get_dataset() -> dataset:
    """Get the global dataset instance.
    
    Returns:
        The global dataset instance
    
    Raises:
        RuntimeError: If the global dataset has not been initialized
        
    Note:
        This operation doesn't acquire locks for better performance.
        The caller must ensure thread safety if modifying the returned dataset directly.
        For thread-safe operations on the dataset, use the with_lock() function.
    """
    # Read operations don't acquire the lock for better performance
    # This is safe for reads but callers need to acquire locks if they modify the dataset
    ds = _global_dataset
    if ds is None:
        raise RuntimeError(
            "Global dataset not initialized. Call initialize() before accessing the global dataset."
        )
    
    return ds

def add_database(name: str, data: Dict[str, Any]) -> None:
    """Add a new database to the global dataset.
    
    Args:
        name: Name of the database to add
        data: Dictionary of data to initialize the database with
    
    Raises:
        RuntimeError: If the global dataset has not been initialized
        NameError: If a database with the given name already exists
        
    Note:
        This operation is thread-safe.
    """
    with _write_lock:
        ds = get_dataset()
        ds.add(name, data)

def update_database(name: str, data: Dict[str, Any], merge: bool = True) -> None:
    """Update a database in the global dataset.
    
    Args:
        name: Name of the database to update
        data: Dictionary of data to update
        merge: Whether to merge with existing data or replace (default: merge)
    
    Raises:
        RuntimeError: If the global dataset has not been initialized
        
    Note:
        This operation is thread-safe.
    """
    with _write_lock:
        ds = get_dataset()
        ds.update(name, data, merge=merge)

def get_database(name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get a database from the global dataset.
    
    Args:
        name: Name of the database to retrieve
        default: Default value to return if the database doesn't exist
    
    Returns:
        The requested database or the default value
    
    Raises:
        RuntimeError: If the global dataset has not been initialized
        
    Note:
        This operation doesn't acquire locks for better performance.
        The caller must ensure thread safety if modifying the returned database directly.
        For thread-safe reads of multiple values, use the with_lock() function.
    """
    ds = get_dataset()
    return ds.get(name, default)

def reset() -> None:
    """Reset the global dataset to None.
    
    This is primarily useful for testing or when you need to completely
    restart your application state.
    
    Note:
        This operation is thread-safe.
    """
    global _global_dataset
    with _write_lock:
        _global_dataset = None

def with_lock(func: Callable[..., T], *args, **kwargs) -> T:
    """Execute a function with the global dataset lock held.
    
    This is useful for operations that need to read and write to the dataset atomically.
    
    Args:
        func: The function to execute
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The return value of the function
        
    Example:
        ```python
        # Atomic increment
        def increment_counter():
            db = global_dataset.get_database('counters')
            current = db.get('visits', 0)
            global_dataset.update_database('counters', {'visits': current + 1})
            return current + 1
            
        # This will be thread-safe
        new_value = global_dataset.with_lock(increment_counter)
        ```
    """
    with _write_lock:
        return func(*args, **kwargs)

def read_values(*paths: Tuple[str, str]) -> Dict[Tuple[str, str], Any]:
    """Read multiple values from the dataset atomically.
    
    Args:
        *paths: Tuples of (database_name, key) to read
        
    Returns:
        Dictionary mapping (database, key) tuples to their values
        
    Example:
        ```python
        # Atomic read of multiple values
        values = global_dataset.read_values(
            ('user', 'name'),
            ('preferences', 'theme')
        )
        username = values[('user', 'name')]
        theme = values[('preferences', 'theme')]
        ```
    """
    result = {}
    
    with _write_lock:
        ds = get_dataset()
        for db_name, key in paths:
            db = ds.get(db_name, {})
            if key in db:
                result[(db_name, key)] = db[key]
    
    return result

def update_multiple(updates: Dict[str, Dict[str, Any]], merge: bool = True) -> None:
    """Update multiple databases atomically.
    
    Args:
        updates: Dictionary mapping database names to update dictionaries
        merge: Whether to merge with existing data (default: True)
        
    Example:
        ```python
        # Atomic update of related databases
        global_dataset.update_multiple({
            'user': {'last_login': now},
            'stats': {'login_count': login_count + 1}
        })
        ```
    """
    with _write_lock:
        ds = get_dataset()
        for db_name, data in updates.items():
            ds.update(db_name, data, merge=merge)

def get_value(db_name: str, key: str, default: Any = None) -> Any:
    """Get a single value from a database atomically.
    
    Args:
        db_name: Name of the database
        key: Key in the database
        default: Default value if key doesn't exist
    
    Returns:
        The value at the specified key or the default
        
    Example:
        ```python
        # Get a single value
        color = global_dataset.get_value('theme', 'color', default='black')
        ```
    """
    db = get_database(db_name, {})
    return db.get(key, default)

def set_value(db_name: str, key: str, value: Any) -> None:
    """Set a single value in a database atomically.
    
    Args:
        db_name: Name of the database
        key: Key in the database
        value: Value to set
        
    Example:
        ```python
        # Set a single value
        global_dataset.set_value('theme', 'color', 'blue')
        ```
    """
    with _write_lock:
        update_database(db_name, {key: value})

def get_or_create_database(db_name: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
    """Get a database or create it if it doesn't exist.
    
    Args:
        db_name: Name of the database
        default: Default data if database doesn't exist
        
    Returns:
        The database
        
    Example:
        ```python
        # Get or create a database
        counters = global_dataset.get_or_create_database('counters', {'visits': 0})
        ```
    """
    default = default or {}
    
    with _write_lock:
        ds = get_dataset()
        if db_name not in ds:
            add_database(db_name, default)
        return get_database(db_name)
        
def update_counter(db_name: str, counter_name: str, increment: int = 1) -> int:
    """Atomically increment a counter and return the new value.
    
    Args:
        db_name: The name of the database containing the counter
        counter_name: The name of the counter to increment
        increment: The amount to increment by (default: 1)
        
    Returns:
        The new counter value
        
    Example:
        ```python
        # Increment a counter
        new_count = global_dataset.update_counter('stats', 'visits')
        ```
    """
    def _increment():
        db = get_database(db_name, {})
        current = db.get(counter_name, 0)
        new_value = current + increment
        update_database(db_name, {counter_name: new_value})
        return new_value
    
    return with_lock(_increment) 