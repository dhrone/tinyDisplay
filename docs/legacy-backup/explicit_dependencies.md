# Explicit Dependency Management

tinyDisplay now provides multiple ways to explicitly define dependencies between dynamic variables, giving you more control over when variables get updated.

## Why Use Explicit Dependencies?

While tinyDisplay's automatic dependency tracking works well for many cases, there are situations where you might want more control:

1. **Complex relationships**: When the relationship between variables isn't obvious from the expressions alone
2. **Performance optimization**: By explicitly controlling which variables trigger updates
3. **Multiple data sources**: When a variable depends on multiple inputs not directly referenced in the expression
4. **External triggers**: When variables should update based on events not captured in the expression

## Three Ways to Define Dependencies

tinyDisplay provides three different approaches to defining explicit dependencies, each suited for different use cases:

### 1. Using the `depends_on()` Method (Fluent API)

The simplest approach is to use the fluent `depends_on()` method, which can be chained to variable creation:

```python
# Create dynamic variables
value = dynamic("data['value']")
text = dynamic("f'Value: {value}'").depends_on(value)

# You can also add dependencies later
doubled = dynamic("value * 2")
doubled.depends_on(value)

# Register multiple dependencies at once
combined = dynamic("calculate_result()")
combined.depends_on(value, text, doubled)
```

### 2. Using the `depends_on` Parameter

For direct dependencies at creation time, use the `depends_on` parameter:

```python
value = dynamic("data['value']")
result = dynamic("calculate_result()", depends_on=value)

# Multiple dependencies can be passed as a list
combined = dynamic("complex_expression()", depends_on=[value, result])
```

### 3. Using the Dependency Manager (Configuration-Based)

For more complex dependency management, especially for larger applications or when dependencies come from configuration, use the dependency manager:

```python
from tinyDisplay.utility import (
    register_variable, define_dependency, apply_dependencies,
    create_variable, create_variables_from_config
)

# Register existing variables
value = dynamic("data['value']")
register_variable("value", value)

# Create new variables with dependencies
percentage = create_variable("percentage", "min(data['value'], 100)", depends_on="value")

# Create multiple variables from configuration
variables = create_variables_from_config({
    "status": {
        "expression": "f'Status: {data[\"status\"]}'",
    },
    "progress_text": {
        "expression": "f'Progress: {percentage}%'",
        "depends_on": ["percentage"]
    }
})

# Apply all dependencies
apply_dependencies()
```

## Advanced Usage: Creating Dependency Hierarchies

You can create complex dependency hierarchies by combining these approaches:

```python
# Create a network of dependent variables
base_value = dynamic("data['value']")
multiplier = dynamic("data['multiplier']")

# First level of dependencies
adjusted_value = dynamic("base_value * multiplier").depends_on(base_value, multiplier)

# Second level of dependencies - depends on first level
status = dynamic("f'Status: {adjusted_value}'", depends_on=adjusted_value)

# Configuration-based dependencies can reference both levels
register_variable("base_value", base_value)
register_variable("adjusted_value", adjusted_value)

complex_variables = create_variables_from_config({
    "display_text": {
        "expression": "generate_display_text(adjusted_value)",
        "depends_on": ["adjusted_value"]
    }
})
```

## Best Practices

1. **Prefer automatic dependencies** when the relationships can be inferred from the expressions
2. **Use explicit dependencies** when the relationships are complex or not obvious
3. **Choose the approach** based on your use case:
   - Use `depends_on()` for simple, one-off dependencies
   - Use the `depends_on` parameter for direct dependencies at creation time
   - Use the dependency manager for complex applications or configuration-driven dependencies
4. **Apply dependencies early** in your application lifecycle, before any rendering

## Example

See the `examples/explicit_dependencies_demo.py` file for a complete working example of all three approaches.

```python
# APPROACH 1: Using the fluent .depends_on() method
value_dv = dynamic("stats['value']")
progress_dv = dynamic("stats['value']").depends_on(value_dv)

# APPROACH 2: Using depends_on parameter at creation time
double_value_dv = dynamic("stats['value'] * 2", depends_on=value_dv)

# APPROACH 3: Using the dependency manager
register_variable("value", value_dv)
percentage_dv = create_variable("percentage", "min(stats['value'], 100)", depends_on="value")
```

## Performance Considerations

Explicit dependencies can help optimize performance by:

1. Reducing unnecessary evaluations
2. Making complex dependency relationships clearer
3. Allowing for more control over when variables are updated

However, maintaining explicit dependencies requires additional care to ensure that the dependency relationships are kept in sync with any changes to the expressions. 