#!/usr/bin/env python
"""
A script to test f-string vs regular string evaluation in tinyDisplay widgets.
"""
from tinyDisplay.render.widget import text
from tinyDisplay.utility.dataset import dataset

# Create a dataset with a known value
test_data = {"artist": "Sting"}
ds = dataset({"db": test_data})

# For detailed output of what's happening
debug = True

# Test with a regular expression first
print("\n====== CREATING WIDGET WITH REGULAR EXPRESSION ======")
widget_reg = text(
    dvalue="db['artist']",  # Regular expression
    dataset=ds,
    size=(100, 20)
)

# Print debug info about the widget
if debug:
    print("\nWidget details after initialization:")
    print(f"  - Value statements: {list(widget_reg._dV._statements.keys())}")
    if '_value' in widget_reg._dV._statements:
        stmt = widget_reg._dV._statements['_value']
        print(f"  - _value source: {getattr(stmt, 'source', None)}")
        print(f"  - _value func: {getattr(stmt, 'func', None)}")
        print(f"  - _value static: {getattr(stmt, 'static', False)}")
    else:
        print("  - No _value statement found")

print("\n====== FORCING RENDER OF REGULAR EXPRESSION WIDGET ======")
img_reg, changed_reg = widget_reg.render(force=True)
print(f"Changed: {changed_reg}")
print(f"Widget _value after render: {widget_reg._value!r}")
print(f"Widget _reprVal after render: {widget_reg._reprVal!r}")

# Test with an f-string
print("\n====== CREATING WIDGET WITH F-STRING ======")
widget_f = text(
    dvalue="f\"Artist {db['artist']}\"",  # F-string format
    dataset=ds,
    size=(100, 20)
)

# Print debug info about the widget
if debug:
    print("\nWidget details after initialization:")
    print(f"  - Value statements: {list(widget_f._dV._statements.keys())}")
    if '_value' in widget_f._dV._statements:
        stmt = widget_f._dV._statements['_value']
        print(f"  - _value source: {getattr(stmt, 'source', None)}")
        print(f"  - _value func: {getattr(stmt, 'func', None)}")
        print(f"  - _value static: {getattr(stmt, 'static', False)}")
    else:
        print("  - No _value statement found")

print("\n====== FORCING RENDER OF F-STRING WIDGET ======")
img_f, changed_f = widget_f.render(force=True)
print(f"Changed: {changed_f}")
print(f"Widget _value after render: {widget_f._value!r}")
print(f"Widget _reprVal after render: {widget_f._reprVal!r}")

# Let's also test what happens with standalone Python eval of an f-string
print("\n====== PYTHON EVAL TEST ======")
try:
    # Define the f-string expression
    expr = "f\"Artist {db['artist']}\""
    print(f"Expression: {expr!r}")
    
    # Compile the expression
    compiled = compile(expr, "<string>", "eval")
    print(f"Compile successful: {compiled}")
    
    # Create a test context
    context = {"db": {"artist": "Test Artist"}}
    
    # Evaluate in that context
    result = eval(compiled, {}, context)
    print(f"Eval result: {result!r}")
except Exception as e:
    print(f"Error: {type(e).__name__} - {e}")

# Test with string using format method for comparison
print("\n====== FORMAT METHOD TEST ======")
widget_format = text(
    dvalue="'Artist: {}'.format(db['artist'])",  # format method
    dataset=ds,
    size=(100, 20)
)

# Print debug info
if debug:
    print("\nWidget details after initialization:")
    print(f"  - Value statements: {list(widget_format._dV._statements.keys())}")
    if '_value' in widget_format._dV._statements:
        stmt = widget_format._dV._statements['_value']
        print(f"  - _value source: {getattr(stmt, 'source', None)}")
        print(f"  - _value func: {getattr(stmt, 'func', None)}")
        print(f"  - _value static: {getattr(stmt, 'static', False)}")
    else:
        print("  - No _value statement found")

# Render the format method widget
print("\n====== FORCING RENDER OF FORMAT METHOD WIDGET ======")
img_format, changed_format = widget_format.render(force=True)
print(f"Changed: {changed_format}")
print(f"Widget _value after render: {widget_format._value!r}")
print(f"Widget _reprVal after render: {widget_format._reprVal!r}") 