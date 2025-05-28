#!/usr/bin/env python
"""
Test the evaluator component directly with different types of expressions.
"""
from tinyDisplay.utility.evaluator import dynamicValue
from tinyDisplay.utility.dataset import dataset
from tinyDisplay.render.widget import text, widget
import inspect

# Create a dataset with test data
test_data = {"artist": "Sting", "count": 5}
ds = dataset({"db": test_data})

# Test expressions
expressions = [
    # Simple variable access
    "db['artist']",
    
    # Simple expression
    "db['artist'] + ' - ' + str(db['count'])",
    
    # String format method
    "'Artist: {}'.format(db['artist'])",
    
    # F-string 
    "f\"Artist: {db['artist']}\"",
    
    # Double evaluation needed
    "\"\\\"Artist: \\\" + db['artist']\"",
]

print("\n===== DIRECT EVALUATOR TESTS =====\n")

for expr in expressions:
    print(f"Expression: {expr!r}")
    
    # Create dynamic value
    dv = dynamicValue()
    
    # Add dataset
    dv._dataset = ds
    
    try:
        # Compile and evaluate
        dv.compile(expr, dynamic=True)
        result = dv.eval()
        print(f"  Result: {result!r}")
        print(f"  Static: {getattr(dv, 'static', 'unknown')}")
        print(f"  Function: {dv.func!r}")
    except Exception as e:
        print(f"  Error: {type(e).__name__} - {e}")
    
    print()

print("\n===== DIRECT PYTHON EVAL TESTS =====\n")

# Test with Python's built-in eval for comparison
for expr in expressions:
    print(f"Expression: {expr!r}")
    
    try:
        # Setup context
        context = {"db": test_data}
        
        # Try to compile
        try:
            compiled = compile(expr, "<string>", "eval")
            print(f"  Compiled: {compiled}")
            
            # Evaluate
            result = eval(compiled, {}, context)
            print(f"  Result: {result!r}")
        except SyntaxError:
            print("  SyntaxError during compile, trying with exec...")
            # For f-strings, we might need to use exec instead
            result_var = None
            exec(f"result_var = {expr}", {}, {"db": test_data, "result_var": None})
            print(f"  Result via exec: {result_var!r}")
            
    except Exception as e:
        print(f"  Error: {type(e).__name__} - {e}")
    
    print()

print("\n===== WIDGET EVALUATOR TESTS =====\n")

for expr in expressions:
    print(f"Expression: {expr!r}")
    
    # Create a widget and inspect its evaluator
    try:
        w = text(dvalue=expr, dataset=ds, size=(100, 20))
        
        # Check what's in the evaluator
        print(f"  Inspecting widget._dV:")
        print(f"  Statements: {list(w._dV._statements.keys())}")
        
        if '_value' in w._dV._statements:
            value_stmt = w._dV._statements['_value']
            print(f"  _value source: {getattr(value_stmt, 'source', None)!r}")
            print(f"  _value func: {getattr(value_stmt, 'func', None)!r}")
            print(f"  _value static: {getattr(value_stmt, 'static', 'unknown')}")
            
            # Try rendering the widget
            print(f"  Rendering widget...")
            img, changed = w.render(force=True)
            print(f"  Changed: {changed}")
            print(f"  _value after render: {w._value!r}")
            print(f"  _reprVal after render: {w._reprVal!r}")
            
            # Try direct eval on the widget's evaluator
            try:
                direct_result = w._dV.eval('_value')
                print(f"  Direct eval result: {direct_result!r}")
            except Exception as e:
                print(f"  Direct eval error: {type(e).__name__} - {e}")
                
        else:
            print("  No _value statement found in widget")
    except Exception as e:
        print(f"  Widget creation error: {type(e).__name__} - {e}")
    
    print()

# Debug the initArguments method
print("\n===== DEBUGGING WIDGET INITIALIZATION =====\n")

# Patch the _initArguments method to add debug output
original_initArguments = widget._initArguments

def debug_initArguments(self, argSpec, argValues, exclude=None):
    print(f"_initArguments called:")
    print(f"  argSpec[0] (args): {argSpec[0]}")
    print(f"  argValues: {argValues[0]}, {argValues[1]}, {argValues[2]}")
    print(f"  kwargs: {argValues[3]['kwargs']}")
    
    # Get dvalue if present
    dvalue = argValues[3]['kwargs'].get('dvalue')
    if dvalue:
        print(f"\n  dvalue detected: {dvalue!r}")
        print(f"  Checking if d-prefixed args will be processed...")
        args = [item for item in argSpec[0][1:] if item not in exclude] if exclude is not None else argSpec[0][1:]
        for a in args:
            if f"d{a}" in argValues[3]['kwargs']:
                print(f"    Found d{a}: {argValues[3]['kwargs'][f'd{a}']!r}")
                
    # Call original method
    result = original_initArguments(self, argSpec, argValues, exclude)
    return result

# Apply the patch (only temporarily)
widget._initArguments = debug_initArguments

# Test with one expression
expr = "f\"Artist: {db['artist']}\""
print(f"Creating widget with dvalue={expr!r}")
try:
    w = text(dvalue=expr, dataset=ds, size=(100, 20))
    
    # Check if _value was created
    if hasattr(w, '_dV') and '_value' in w._dV._statements:
        print(f"\nValue statement after initialization:")
        print(f"  Source: {w._dV._statements['_value'].source!r}")
        print(f"  Function: {w._dV._statements['_value'].func!r}")
        print(f"  Static: {w._dV._statements['_value'].static}")
except Exception as e:
    print(f"Error: {type(e).__name__} - {e}")

# Restore original method
widget._initArguments = original_initArguments 