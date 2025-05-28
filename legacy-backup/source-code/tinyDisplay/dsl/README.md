# tinyDisplay Domain-Specific Languages (DSLs)

This directory contains the Domain-Specific Languages (DSLs) for the tinyDisplay system.

## Directory Structure

- `common/`: Common code shared between all DSL implementations
- `marquee/`: Marquee Animation DSL for defining widget animations
- `application/`: Application Widget DSL for defining complete UI applications (future implementation)

## Marquee Animation DSL

The Marquee Animation DSL allows for declarative definition of animated widget behavior, including:

- Movement (MOVE, SCROLL, SLIDE)
- Timing (PAUSE, timing controls)
- Looping and repetition
- Conditional behaviors
- Coordination between widgets
- Timeline optimization

See `marquee_class_dsl.md` for the complete specification.

## Application Widget DSL

The Application Widget DSL (future implementation) will provide a way to declaratively define complete applications, including:

- Widget declarations
- Collections (canvas, stack, sequence)
- Theme definitions
- State management
- Hardware configuration

## Usage

Both DSLs will follow a common usage pattern:

```python
from tinyDisplay.dsl import parse_and_validate_dsl  # Uses marquee by default

# For Marquee DSL specifically:
from tinyDisplay.dsl.marquee import parse_and_validate_marquee_dsl

# Parse and validate a DSL string
dsl_code = """
MOVE(LEFT, 100) { step=2, interval=1 };
PAUSE(10);
"""

# Get the AST and validation errors
ast, errors = parse_and_validate_marquee_dsl(dsl_code)

if errors:
    print("Validation errors:")
    for error in errors:
        print(f"  {error}")
else:
    # Use the AST to generate animations
    print("Validation successful!") 