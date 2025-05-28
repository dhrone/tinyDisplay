#!/usr/bin/env python
"""
A script to debug dynamic value evaluation, with focus on f-string handling.
"""
import re
import warnings
from tinyDisplay.render.widget import text
from tinyDisplay.utility.dataset import dataset
from tinyDisplay.utility.evaluator import dynamicValue

# Create a dataset with a known value
test_data = {"artist": "Sting"}
ds = dataset({"db": test_data})

# First, directly test if f-string expression can be compiled and evaluated
print("\n=== DIRECT COMPILATION TEST ===")
expression = "f\"Artist: {db['artist']}\""
print(f"Expression: {expression}")

# Attempt to compile the expression directly to see if there's a syntax error
try:
    warnings.simplefilter("error")
    compiled = compile(expression, "<string>", "eval")
    print(f"Successfully compiled expression, code names: {compiled.co_names}")
    warnings.simplefilter("default")
except Exception as e:
    print(f"Compilation error: {type(e).__name__} - {e}")
    warnings.simplefilter("default")

# Manual approach - since f-strings are a syntax feature, they need to be 
# evaluated differently. Let's try a workaround:
print("\n=== MANUAL EVALUATION TEST ===")
fstring_pattern = r'f"(.*?)"'
match = re.match(fstring_pattern, expression)
if match:
    template = match.group(1)
    print(f"Template: {template}")
    
    # Create a test eval function to simulate what happens
    def evaluate_template(template, data):
        # Replace f-string variable references with actual string formatting
        # Convert {db['artist']} to {0} and then format with the actual value
        placeholder_template = re.sub(r"\{db\['artist'\]\}", "{0}", template)
        print(f"Placeholder template: {placeholder_template}")
        
        try:
            artist_value = data["db"]["artist"]
            print(f"Artist value: {artist_value}")
            result = placeholder_template.format(artist_value)
            print(f"Evaluation result: {result!r}")
            return result
        except Exception as e:
            print(f"Evaluation error: {type(e).__name__} - {e}")
            return None
    
    result = evaluate_template(template, {"db": test_data})
else:
    print("Failed to extract template from f-string expression")

# Create a text widget with the dynamic value
print("\n=== WIDGET TEST ===")
widget = text(
    # Try both a normal string expression (standard approach) and f-string format
    dvalue="db['artist']",  # Traditional approach
    dataset=ds,
    size=(100, 20)
)

# Examine the dynamic value compilation
print("\nInspecting the dynamic value compilation:")
statement = widget._dV._statements.get("_value")
if statement:
    print(f"  Source: {statement.source!r}")
    print(f"  Function: {statement.func!r}")
    print(f"  Is static: {getattr(statement, 'static', 'unknown')}")
    print(f"  Default: {statement.default!r}")
    
    # Try direct evaluation
    try:
        result = statement.eval()
        print(f"  Direct eval result: {result!r}")
    except Exception as e:
        print(f"  Eval error: {type(e).__name__} - {e}")
else:
    print("  No _value statement found")

# Force a render and check the result
print("\nForcing a render:")
img, changed = widget.render(force=True)
print(f"  Changed: {changed}")
print(f"  Widget _value after render: {widget._value!r}")
print(f"  Widget _reprVal after render: {widget._reprVal!r}")

# Update the dataset and check again
print("\nUpdating dataset:")
test_data["artist"] = "Moby"
ds.update("db", test_data)
print(f"  New data: {ds['db']}")

# Force another render
print("\nForcing a render after update:")
img, changed = widget.render(force=True) 
print(f"  Changed: {changed}")
print(f"  Widget _value after render: {widget._value!r}")
print(f"  Widget _reprVal after render: {widget._reprVal!r}")

# Now try with another widget using a string literal instead of an f-string
print("\n=== SECOND WIDGET TEST (WITHOUT F-STRING) ===")
widget2 = text(
    dvalue="db['artist']",  # Traditional approach without f-string
    dataset=ds,
    size=(100, 20)
)

print("\nSecond widget - forcing a render:")
img, changed = widget2.render(force=True)
print(f"  Changed: {changed}")
print(f"  Widget _value after render: {widget2._value!r}")
print(f"  Widget _reprVal after render: {widget2._reprVal!r}") 