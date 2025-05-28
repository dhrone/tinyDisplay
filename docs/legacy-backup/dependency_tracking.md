# Variable Dependency Tracking in tinyDisplay

tinyDisplay now includes an optimized variable dependency tracking system that significantly improves performance by only re-evaluating dynamic variables when their dependencies change.

## How It Works

The variable dependency system:

1. Automatically analyzes expressions to identify field-level dependencies
2. Tracks relationships between variables and specific data fields
3. Only re-evaluates variables when their dependencies change
4. Handles transitive dependencies (when variables depend on other variables)

This results in fewer calculations and better performance, especially for complex UIs with many interdependent values.

## Benefits

- **Better Performance**: Only values that need to be recalculated are evaluated
- **Resource Efficiency**: Reduced CPU usage, especially valuable for resource-constrained devices
- **Scalability**: More efficient handling of complex UIs with many dynamic values
- **Automatic Optimization**: No manual dependency configuration required in most cases

## Using the System

The variable dependency system works automatically with dynamic values. When you define a dynamic value using the `dynamic()` function, dependencies are automatically tracked:

```python
from tinyDisplay.utility.dynamic import dynamic

# This value depends on theme['text_color']
title = text(
    value="My Title",
    foreground=dynamic("theme['text_color']")
)

# This depends on multiple values
progress_text = text(
    value=dynamic("f\"Progress: {stats['completed']}/{stats['total']}\"")
)
```

The system will:
1. Parse these expressions to identify dependencies
2. Only re-evaluate when `theme['text_color']`, `stats['completed']`, or `stats['total']` changes
3. Skip evaluation when other unrelated data changes

## Variable-to-Variable Dependencies

The system also handles dependencies between variables. For example:

```python
# Calculate percentage
percentage = dynamic("(stats['completed'] / stats['total']) * 100")

# Use the result in a formatted string 
status_text = dynamic(f"Progress: {percentage}%")
```

When `stats['completed']` or `stats['total']` changes:
1. First `percentage` is recalculated
2. Then `status_text` is updated because it depends on `percentage`

## Advanced Usage: Explicit Dependency Registration

For complex cases where the automatic dependency detection isn't sufficient, you can manually register dependencies:

```python
from tinyDisplay import variable_registry

# Register a dependency between a variable and a specific field
variable_registry.register_variable_dependency(my_variable, "db['key']")

# Register a dependency between two variables
variable_registry.register_variable_to_variable_dependency(dependent_var, dependency_var)
```

## Debugging Dependencies

To debug dependency relationships:

```python
from tinyDisplay import variable_registry

# See what depends on a specific field
dependents = variable_registry.get_dependent_variables("theme['accent']")
print(f"Variables that depend on theme['accent']: {dependents}")

# Get all affected variables (including indirect dependencies)
all_affected = variable_registry.get_all_affected_variables("theme['accent']")
print(f"All variables affected by changes to theme['accent']: {all_affected}")
```

## Implementation Notes

- The variable dependency system is separate from but complementary to the widget dependency system
- Dependencies are identified through regex pattern matching on expressions
- A change in a value triggers cascading updates through the dependency graph
- Only variables marked as needing update are re-evaluated during the render cycle 