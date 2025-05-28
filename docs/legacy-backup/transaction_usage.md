# tinyDisplay Transaction Usage Guide

This guide provides practical examples and best practices for using the transaction functionality in tinyDisplay's dataset system.

## Basic Concepts

Transactions group multiple updates into a single atomic operation that either completely succeeds or completely fails. They ensure data consistency by preventing partial updates.

Key benefits:
- **Atomicity**: All updates succeed or fail together
- **Consistency**: The dataset is always in a valid state
- **Isolation**: Changes aren't visible to other parts of the application until committed

## Transaction API Options

tinyDisplay provides three ways to use transactions:

### 1. Context Manager API (Recommended)

```python
with dataset.transaction() as tx:
    tx.update("settings", {"theme": "dark"})
    tx.update("user", {"last_login": time.time()})
    # Automatically committed if no errors occur
    # Automatically rolled back if an exception occurs
```

This is the recommended approach for most scenarios because it:
- Handles commit/rollback automatically
- Ensures proper cleanup even if exceptions occur
- Provides a clear visual scope for the transaction

### 2. Begin/Commit/Rollback API

```python
tx = dataset.begin_transaction()
try:
    tx.update("settings", {"theme": "dark"})
    tx.update("user", {"last_login": time.time()})
    
    # Only commit if some condition is met
    if validation_passes:
        tx.commit()
    else:
        tx.rollback()
except Exception:
    tx.rollback()
    raise
```

Use this approach when:
- You need complex conditional logic to decide whether to commit
- You want more control over the transaction lifecycle
- You need to defer the commit decision based on external factors

### 3. Batch Update API

```python
dataset.batch_update({
    "settings": {"theme": "dark", "font_size": 14},
    "user": {"last_login": time.time()},
    "stats": {"login_count": 42}
})
```

Use this approach when:
- You need a simple one-line update across multiple databases
- You don't need to read the pending transaction state
- You don't need complex conditional logic

## Reading Within Transactions

One powerful feature of tinyDisplay transactions is the ability to read the current transaction state before committing:

```python
with dataset.transaction() as tx:
    # Make some updates
    tx.update("counter", {"value": 1})
    
    # Read the pending value (returns 1, not the committed value)
    current = tx.get("counter", "value")
    
    # Make another update based on the pending value
    tx.update("counter", {"value": current + 1})
    
    # Final committed value will be 2
```

This allows for complex interdependent updates within a single transaction.

## Integration with Validation

Transactions respect the dataset's validation rules:

```python
# Set up validation
ds = dataset()
ds.registerValidation(
    "account",
    "balance",
    validate="_VAL_ >= 0",  # Can't have negative balance
    default=0
)

# Transaction with validation
with ds.transaction() as tx:
    current_balance = tx.get("account", "balance", 0)
    withdrawal = 50
    
    # This will fail validation if balance becomes negative
    tx.update("account", {"balance": current_balance - withdrawal})
```

Validation errors will cause the entire transaction to roll back.

## Common Patterns

### 1. Data Migration Pattern

```python
with dataset.transaction() as tx:
    # Read data from source
    source_data = tx.get("source_db")
    
    # Transform data
    transformed = transform_data(source_data)
    
    # Write to destination
    tx.update("destination_db", transformed)
    
    # Remove from source (optional)
    tx.update("source_db", {}, merge=False)  # Replace with empty dict
```

### 2. Multi-Entity Update Pattern

When updating related entities:

```python
with dataset.transaction() as tx:
    # Update user
    tx.update("user", {"name": "Alice", "status": "active"})
    
    # Update related profile
    tx.update("profile", {"user_id": user_id, "theme": "dark"})
    
    # Update statistics
    tx.update("stats", {"user_count": tx.get("stats", "user_count", 0) + 1})
```

### 3. Conditional Update Pattern

```python
tx = dataset.begin_transaction()
try:
    # Read current state
    current_config = tx.get("config")
    
    # Make conditional updates
    if needs_update(current_config):
        tx.update("config", new_config)
        tx.update("audit", {"last_config_change": time.time()})
        tx.commit()
    else:
        # No changes needed
        tx.rollback()
except Exception:
    tx.rollback()
    raise
```

## Best Practices

1. **Keep transactions short**: Long-running transactions can impact performance
2. **Handle exceptions properly**: Always ensure transactions are committed or rolled back
3. **Prefer the context manager**: The `with` statement handles cleanup automatically
4. **Be careful with merge=False**: This replaces the entire database, which may not be what you want
5. **Consider validation rules**: Set up appropriate validation to ensure data consistency

## Limitations

- Transactions are not distributed - they only apply to a single dataset instance
- Transactions don't provide isolation from other processes accessing the dataset
- There's no support for nested transactions (transactions within transactions)

## Performance Considerations

For optimal performance:
- Batch related updates into a single transaction
- Minimize the number of reads within a transaction
- Consider using merge=False for complete database replacements when appropriate
