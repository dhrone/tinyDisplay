# tinyDisplay Migration Guide

## Migrating from d-prefix to the dynamic() Function

tinyDisplay has introduced a new, more intuitive way to define dynamic properties for widgets. This guide will help you migrate your code from the legacy "d"-prefix approach to the new `dynamic()` function approach.

### What's Changed?

1. **New Syntax**: Instead of using "d"-prefixed parameters (like `dvalue`, `dforeground`), you now use the `dynamic()` function to wrap expressions.
2. **Dependency Tracking**: The new system automatically tracks dependencies between data sources and widgets.
3. **Efficient Updates**: Only widgets that depend on changed data are updated.

### Migration Steps

#### 1. Import the dynamic function

Add the import for the dynamic function at the top of your files:

```python
from tinyDisplay.utility.dynamic import dynamic
```

#### 2. Replace d-prefixed parameters

Replace parameters like `dvalue` with their regular name and the `dynamic()` function:

**Before:**
```python
my_text = text(
    value="Hello World",
    dforeground="sys['theme']['text_color']",
    dbackground="sys['theme']['background']"
)
```

**After:**
```python
my_text = text(
    value="Hello World",
    foreground=dynamic("sys['theme']['text_color']"),
    background=dynamic("sys['theme']['background']")
)
```

#### 3. Dynamic values

For dynamic values, replace `dvalue` with `value=dynamic()`:

**Before:**
```python
status = text(
    dvalue="'Progress: ' + str(sys['progress']) + '%'"
)
```

**After:**
```python
status = text(
    value=dynamic("'Progress: ' + str(sys['progress']) + '%'")
)
```

### Migration Examples

#### Example 1: Basic Text Widget

**Before:**
```python
artist_name = text(
    dvalue="f\"Artist: {music['artist']}\"",
    dforeground="theme['text_color']",
    size=(200, 20)
)
```

**After:**
```python
artist_name = text(
    value=dynamic("f\"Artist: {music['artist']}\""),
    foreground=dynamic("theme['text_color']"),
    size=(200, 20)
)
```

#### Example 2: Progress Bar

**Before:**
```python
progress = progressBar(
    dvalue="sys['progress']",
    dfill="theme['accent']",
    size=(200, 20)
)
```

**After:**
```python
progress = progressBar(
    value=dynamic("sys['progress']"),
    fill=dynamic("theme['accent']"),
    size=(200, 20)
)
```

#### Example 3: Canvas with Dynamic Background

**Before:**
```python
main_display = canvas(
    size=(200, 100),
    dbackground="theme['background']"
)
```

**After:**
```python
main_display = canvas(
    size=(200, 100),
    background=dynamic("theme['background']")
)
```

### Backward Compatibility

The legacy "d"-prefix approach is still supported for backward compatibility, but we recommend migrating to the new `dynamic()` function approach for improved readability and performance.

### Benefits of Migration

1. **More intuitive code**: The dynamic nature of properties is explicitly visible.
2. **Better performance**: Only widgets affected by data changes are updated.
3. **Self-documenting code**: It's clear which properties are dynamic.
4. **Easier debugging**: Dependencies are tracked and can be inspected.

### Testing Your Migration

After migrating your code, thoroughly test your application to ensure all dynamic updates still work as expected. Pay special attention to:

1. Initial rendering of widgets
2. Updates when data changes
3. Complex expressions with multiple dependencies 