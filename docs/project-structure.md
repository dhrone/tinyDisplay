# tinyDisplay Project Structure

**Version:** 2.0 (Full Migration)  
**Last Updated:** December 2024  
**Architecture:** Ring Buffer + SQLite + asteval + Reactive Patterns  

---

## Root Directory Structure

```
tinyDisplay/
├── src/
│   └── tinydisplay/           # Main package source
├── tests/                     # Test suite
├── examples/                  # Example applications
├── docs/                      # Project documentation
├── bmad-agent/               # BMAD workflow artifacts
├── legacy/                   # Legacy codebase (archived)
├── migration_tool.py         # Migration utility
├── migration_generator.py    # DSL generation tool
├── pyproject.toml           # Modern Python packaging
├── setup.py                 # Fallback packaging
├── README.md                # Project overview
└── MIGRATION_README.md      # Architecture migration guide
```

---

## Source Code Organization (`src/tinydisplay/`)

### Core Architecture
```
src/tinydisplay/
├── __init__.py              # Package initialization
├── core/                    # Core framework components
│   ├── __init__.py
│   ├── ring_buffer.py       # High-performance data flow
│   ├── reactive.py          # Reactive data binding system
│   ├── database.py          # SQLite integration layer
│   ├── expressions.py       # asteval expression evaluation
│   └── performance.py       # Performance monitoring
├── widgets/                 # Widget system
│   ├── __init__.py
│   ├── base.py             # Abstract widget base classes
│   ├── text.py             # Text widget implementation
│   ├── image.py            # Image widget implementation
│   ├── progress.py         # Progress bar widget
│   ├── shapes.py           # Shape primitives
│   └── collections.py      # Canvas, stack, index, sequence
├── animation/              # Animation system
│   ├── __init__.py
│   ├── coordinator.py      # Animation coordination
│   ├── timeline.py         # Timeline management
│   ├── primitives.py       # sync(), wait_for(), barrier()
│   └── dsl.py             # Animation DSL parser
├── canvas/                 # Canvas and composition
│   ├── __init__.py
│   ├── canvas.py          # Canvas base class
│   ├── composition.py     # Widget composition
│   ├── positioning.py     # Coordinate systems
│   ├── layering.py        # Z-order management
│   └── sequences.py       # Display sequences
├── dsl/                   # DSL system
│   ├── __init__.py
│   ├── parser.py          # DSL parser
│   ├── validator.py       # DSL validation
│   ├── generator.py       # Code generation
│   └── examples.py        # DSL examples
├── rendering/             # Rendering pipeline
│   ├── __init__.py
│   ├── engine.py          # Main rendering engine
│   ├── frame_timer.py     # 60fps frame timing
│   ├── memory_manager.py  # Memory optimization
│   └── display_adapter.py # Display hardware abstraction
├── data/                  # Data layer
│   ├── __init__.py
│   ├── sources.py         # Data source abstractions
│   ├── bindings.py        # Reactive data bindings
│   ├── transactions.py    # Transaction management
│   └── schema.py          # Data schema validation
└── utils/                 # Utilities
    ├── __init__.py
    ├── logging.py         # Logging configuration
    ├── config.py          # Configuration management
    ├── validation.py      # Input validation
    └── profiling.py       # Performance profiling
```

---

## Test Organization (`tests/`)

### Test Structure
```
tests/
├── __init__.py
├── conftest.py              # pytest configuration
├── unit/                    # Unit tests
│   ├── core/               # Core component tests
│   ├── widgets/            # Widget tests
│   ├── animation/          # Animation tests
│   ├── canvas/             # Canvas tests
│   ├── dsl/                # DSL tests
│   ├── rendering/          # Rendering tests
│   └── data/               # Data layer tests
├── integration/            # Integration tests
│   ├── widget_rendering/   # Widget + rendering integration
│   ├── animation_coordination/ # Animation system integration
│   ├── data_flow/          # Data + reactive integration
│   └── performance/        # Performance integration tests
├── e2e/                    # End-to-end tests
│   ├── simple_app/         # Simple application tests
│   ├── complex_app/        # Complex application tests
│   └── migration/          # Migration tool tests
├── fixtures/               # Test data and fixtures
│   ├── sample_data/        # Sample datasets
│   ├── legacy_apps/        # Legacy application examples
│   └── dsl_examples/       # DSL test cases
└── performance/            # Performance benchmarks
    ├── memory_usage/       # Memory profiling tests
    ├── frame_rate/         # Frame rate benchmarks
    └── pi_zero_2w/         # Pi Zero 2W specific tests
```

---

## Examples Organization (`examples/`)

### Example Applications
```
examples/
├── README.md               # Examples overview
├── basic/                  # Basic examples
│   ├── hello_world/        # Simple text display
│   ├── progress_bar/       # Progress bar demo
│   └── image_display/      # Image widget demo
├── intermediate/           # Intermediate examples
│   ├── dashboard/          # Multi-widget dashboard
│   ├── animations/         # Animation coordination
│   └── data_binding/       # Reactive data examples
├── advanced/               # Advanced examples
│   ├── music_player/       # Complete music player UI
│   ├── system_monitor/     # System monitoring display
│   └── multi_canvas/       # Complex canvas sequences
├── migration/              # Migration examples
│   ├── legacy_to_dsl/      # Migration demonstrations
│   └── comparison/         # Before/after comparisons
└── performance/            # Performance examples
    ├── stress_test/        # High widget count tests
    ├── memory_efficient/   # Memory optimization examples
    └── pi_zero_demos/      # Pi Zero 2W optimized apps
```

---

## Documentation Organization (`docs/`)

### Documentation Structure
```
docs/
├── index.md                # Main documentation index
├── epic-{n}.md            # Epic definitions (1-5)
├── stories/               # Individual story files
│   └── {epic}.{story}.story.md
├── project-structure.md   # This file
├── operational-guidelines.md # Coding standards
├── tech-stack.md          # Technology choices
├── api/                   # API documentation
│   ├── widgets.md         # Widget API reference
│   ├── animation.md       # Animation API reference
│   ├── canvas.md          # Canvas API reference
│   └── dsl.md             # DSL reference
├── guides/                # Implementation guides
│   ├── getting-started.md # Quick start guide
│   ├── widget-development.md # Widget creation guide
│   ├── animation-guide.md # Animation coordination guide
│   └── performance-optimization.md # Performance guide
└── reference/             # Legacy reference docs
    └── (existing legacy docs)
```

---

## Configuration Files

### Package Configuration (`pyproject.toml`)
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "tinydisplay"
version = "2.0.0"
description = "High-performance display framework for embedded devices"
dependencies = [
    "asteval>=0.9.28",
    "pillow>=9.0.0",
    # Additional core dependencies (minimal set)
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=22.0.0",
    "flake8>=5.0.0",
    "mypy>=0.991",
]
```

### Testing Configuration (`tests/conftest.py`)
```python
# pytest configuration for tinyDisplay testing
import pytest
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@pytest.fixture
def sample_data():
    """Provide sample data for tests"""
    # Implementation details
```

---

## File Naming Conventions

### Python Files
- **Snake case:** `ring_buffer.py`, `animation_coordinator.py`
- **Class names:** PascalCase (`RingBuffer`, `AnimationCoordinator`)
- **Function names:** snake_case (`create_widget`, `validate_dsl`)
- **Constants:** UPPER_SNAKE_CASE (`MAX_WIDGETS`, `DEFAULT_FRAME_RATE`)

### Test Files
- **Pattern:** `test_{module_name}.py`
- **Test classes:** `Test{ClassName}`
- **Test methods:** `test_{functionality}__{condition}`

### Documentation Files
- **Epics:** `epic-{number}.md` (e.g., `epic-1.md`)
- **Stories:** `{epic}.{story}.story.md` (e.g., `1.1.story.md`)
- **Guides:** `{topic}-guide.md` (e.g., `animation-guide.md`)

---

## Import Conventions

### Internal Imports
```python
# Absolute imports from package root
from tinydisplay.core.reactive import ReactiveValue
from tinydisplay.widgets.text import TextWidget
from tinydisplay.animation.coordinator import AnimationCoordinator

# Relative imports within modules
from .base import Widget
from ..core.reactive import ReactiveBinding
```

### External Dependencies
```python
# Standard library first
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict

# Third-party dependencies
import asteval
from PIL import Image

# Local package imports last
from tinydisplay.core import ReactiveValue
```

---

## Directory Creation Guidelines

### New Module Creation
1. Create directory with `__init__.py`
2. Add module to parent `__init__.py`
3. Create corresponding test directory
4. Add documentation to appropriate guide
5. Update this structure document

### File Organization Principles
- **Single responsibility:** One class per file (exceptions for small helper classes)
- **Logical grouping:** Related functionality in same directory
- **Clear hierarchy:** Deep nesting only when necessary
- **Test mirroring:** Test structure mirrors source structure

---

**Last Updated:** December 2024  
**Next Review:** After Epic 1 completion  
**Maintained By:** Technical Lead 