# Migrating from DynamicValue to dynamicValue

tinyDisplay has consolidated two similar classes - `DynamicValue` and `dynamicValue` - into a single implementation to reduce confusion and improve maintainability. This guide will help you transition your code to use the new unified implementation.

## What Changed

1. The `DynamicValue` class from `tinyDisplay.utility.dynamic` has been **removed completely**.
2. All functionality from `DynamicValue` is now in the `dynamicValue` class in `tinyDisplay.utility.evaluator`.
3. The `dynamic()` function now creates a `dynamicValue` instance.

## Why This Change Was Made

Previously, there were two ways to create dynamic values in tinyDisplay:

1. Using the `DynamicValue` class from `tinyDisplay.utility.dynamic`
2. Using the `dynamicValue` class from `tinyDisplay.utility.evaluator`

This created confusion and made the codebase harder to maintain. The consolidation:

- Provides a single, unified way to create dynamic values
- Combines the best features of both implementations
- Makes dependency tracking more consistent
- Simplifies the codebase and API

## How to Migrate

### Automatic Migration

We've created a tool to help you automate this migration. From your project directory, run:

```bash
python -m tools.migrate_dynamicvalue_removal
```

Add `--dry-run` to see what files would be modified without actually changing them:

```bash
python -m tools.migrate_dynamicvalue_removal --dry-run
```

### Manual Migration Steps

If you prefer to update your code manually, follow these steps:

1. **Replace direct usage of `DynamicValue`**:

   Replace:
   ```python
   from tinyDisplay.utility.dynamic import DynamicValue
   
   dv = DynamicValue("db['value']") 
   ```

   With:
   ```python
   from tinyDisplay.utility.dynamic import dynamic
   
   dv = dynamic("db['value']")
   ```

2. **Update type annotations**:

   Replace:
   ```python
   def process_value(value: DynamicValue):
       # ...
   ```

   With:
   ```python
   from tinyDisplay.utility.evaluator import dynamicValue
   
   def process_value(value: dynamicValue):
       # ...
   ```

3. **Replace code that works with `DynamicValue` properties and methods**:

   Replace:
   ```python
   expression = dv.expression
   value = dv.evaluate(evaluator)
   if dv.needs_update:
       # ...
   ```

   With:
   ```python
   expression = dv.source
   value = dv.eval()
   if dv._needs_update:
       # ...
   ```

## Key Differences When Using dynamicValue

When migrating code, be aware of these differences:

- `DynamicValue.expression` → `dynamicValue.source`
- `DynamicValue.evaluate(evaluator)` → `dynamicValue.eval()`
- `DynamicValue.needs_update` → `dynamicValue._needs_update`
- Both classes use `prevValue` to store the previously evaluated value

## Technical Details

The merged implementation in `dynamicValue`:

1. Provides field-level dependency tracking 
2. Supports variable-to-variable dependency tracking
3. Integrates with the variable dependency registry
4. Can be created using the `dynamic()` function

If you encounter any issues during migration, please report them on our issue tracker. 