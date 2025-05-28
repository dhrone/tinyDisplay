# tinyDisplay Operational Guidelines

**Version:** 2.0 (Full Migration)  
**Last Updated:** December 2024  
**Scope:** All development activities for tinyDisplay framework  

---

## Coding Standards

### Python Code Style

**PEP 8 Compliance:**
- Line length: 88 characters (Black formatter standard)
- Indentation: 4 spaces (no tabs)
- Imports: Standard library, third-party, local (separated by blank lines)
- Docstrings: Google style for all public functions and classes

**Code Formatting Tools:**
```bash
# Required tools for all code
black src/ tests/ examples/
flake8 src/ tests/ examples/
mypy src/
```

**Example Code Structure:**
```python
"""Module docstring describing purpose and usage."""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Protocol

import asteval
from PIL import Image

from tinydisplay.core.reactive import ReactiveValue
from .base import Widget


class TextWidget(Widget):
    """Text widget for displaying dynamic text content.
    
    This widget supports reactive data binding and automatic
    re-rendering when bound data changes.
    
    Args:
        text: Initial text content or reactive value
        font_size: Font size in pixels (default: 12)
        color: Text color as RGB tuple (default: (255, 255, 255))
        
    Example:
        >>> widget = TextWidget("Hello World", font_size=16)
        >>> widget.bind_data(data_source.cpu_usage)
    """
    
    def __init__(
        self,
        text: str | ReactiveValue,
        font_size: int = 12,
        color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        super().__init__()
        self._text = self._ensure_reactive(text)
        self._font_size = font_size
        self._color = color
        
    def render(self, canvas: Canvas) -> None:
        """Render the text widget to the canvas."""
        # Implementation details
        pass
```

### Performance Standards

**Memory Management:**
- Use `__slots__` for frequently instantiated classes
- Implement proper cleanup in `__del__` methods
- Monitor memory usage in long-running operations
- Target <100MB total memory usage for typical applications

**Performance Targets:**
- 60fps sustained rendering on Raspberry Pi Zero 2W
- <50ms response time for reactive updates
- <2 seconds application startup time
- Efficient CPU usage (<80% on single core)

**Performance Monitoring:**
```python
from tinydisplay.utils.profiling import profile_performance

@profile_performance
def expensive_operation():
    """All performance-critical functions should be profiled."""
    pass
```

---

## Testing Strategy

### Test Coverage Requirements

**Minimum Coverage:** 90% for all production code
**Critical Components:** 95% coverage required for:
- Core reactive system
- Widget base classes
- Animation coordination
- Data layer operations
- DSL parsing and validation

### Test Categories

**Unit Tests:**
```python
import pytest
from unittest.mock import Mock, patch

from tinydisplay.widgets.text import TextWidget
from tinydisplay.core.reactive import ReactiveValue


class TestTextWidget:
    """Test suite for TextWidget functionality."""
    
    def test_initialization__with_string__creates_reactive_value(self):
        """Test that string input is converted to ReactiveValue."""
        widget = TextWidget("Hello")
        assert isinstance(widget._text, ReactiveValue)
        assert widget._text.value == "Hello"
        
    def test_render__with_valid_canvas__updates_display(self):
        """Test rendering updates canvas correctly."""
        widget = TextWidget("Test")
        canvas = Mock()
        
        widget.render(canvas)
        
        canvas.draw_text.assert_called_once()
        
    @pytest.mark.performance
    def test_render_performance__under_load__meets_target(self):
        """Test rendering performance under load."""
        widget = TextWidget("Performance Test")
        canvas = Mock()
        
        import time
        start = time.perf_counter()
        for _ in range(1000):
            widget.render(canvas)
        duration = time.perf_counter() - start
        
        # Should render 1000 times in under 100ms
        assert duration < 0.1
```

**Integration Tests:**
```python
import pytest
from tinydisplay.core.reactive import ReactiveDataSource
from tinydisplay.widgets.text import TextWidget
from tinydisplay.canvas.canvas import Canvas


class TestWidgetDataIntegration:
    """Test widget and data layer integration."""
    
    def test_reactive_update__data_change__triggers_render(self):
        """Test that data changes trigger widget re-rendering."""
        data_source = ReactiveDataSource()
        widget = TextWidget(data_source.bind("cpu_usage"))
        canvas = Canvas(128, 64)
        
        # Initial render
        widget.render(canvas)
        initial_state = canvas.get_state()
        
        # Update data
        data_source.update("cpu_usage", "85%")
        
        # Verify re-render occurred
        widget.render(canvas)
        updated_state = canvas.get_state()
        
        assert initial_state != updated_state
```

**Performance Tests:**
```python
import pytest
import psutil
import time
from tinydisplay.examples.stress_test import create_stress_test_app


@pytest.mark.performance
@pytest.mark.slow
class TestPerformanceTargets:
    """Verify performance targets are met."""
    
    def test_frame_rate__stress_test__achieves_60fps(self):
        """Test 60fps target under stress conditions."""
        app = create_stress_test_app(widget_count=50)
        
        frame_times = []
        for _ in range(300):  # 5 seconds at 60fps
            start = time.perf_counter()
            app.render_frame()
            frame_time = time.perf_counter() - start
            frame_times.append(frame_time)
            
        avg_frame_time = sum(frame_times) / len(frame_times)
        fps = 1.0 / avg_frame_time
        
        assert fps >= 60.0, f"Average FPS: {fps:.1f}"
        
    def test_memory_usage__typical_app__under_100mb(self):
        """Test memory usage stays under 100MB."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        app = create_typical_app()
        app.run_for_duration(60)  # Run for 1 minute
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = final_memory - initial_memory
        
        assert memory_used < 100, f"Memory used: {memory_used:.1f}MB"
```

### Test Execution

**Local Development:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/tinydisplay --cov-report=html

# Run performance tests
pytest -m performance

# Run specific test category
pytest tests/unit/widgets/
```

**CI/CD Pipeline:**
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e .[dev]
    
    - name: Run tests
      run: |
        pytest --cov=src/tinydisplay --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

## Error Handling

### Exception Hierarchy

```python
"""tinyDisplay exception hierarchy."""

class TinyDisplayError(Exception):
    """Base exception for all tinyDisplay errors."""
    pass

class ConfigurationError(TinyDisplayError):
    """Raised when configuration is invalid."""
    pass

class RenderingError(TinyDisplayError):
    """Raised when rendering operations fail."""
    pass

class DataBindingError(TinyDisplayError):
    """Raised when data binding operations fail."""
    pass

class AnimationError(TinyDisplayError):
    """Raised when animation operations fail."""
    pass

class DSLError(TinyDisplayError):
    """Raised when DSL parsing or validation fails."""
    pass
```

### Error Handling Patterns

**Graceful Degradation:**
```python
def render_widget(widget: Widget, canvas: Canvas) -> bool:
    """Render widget with graceful error handling.
    
    Returns:
        True if rendering succeeded, False otherwise.
    """
    try:
        widget.render(canvas)
        return True
    except RenderingError as e:
        logger.warning(f"Widget rendering failed: {e}")
        # Render fallback or skip widget
        render_fallback_widget(canvas)
        return False
    except Exception as e:
        logger.error(f"Unexpected error in widget rendering: {e}")
        # Log for debugging but don't crash the application
        return False
```

**Resource Management:**
```python
from contextlib import contextmanager

@contextmanager
def database_transaction():
    """Context manager for database transactions."""
    conn = get_database_connection()
    trans = conn.begin()
    try:
        yield conn
        trans.commit()
    except Exception:
        trans.rollback()
        raise
    finally:
        conn.close()
```

**Validation and Early Returns:**
```python
def create_widget(widget_type: str, config: dict) -> Widget:
    """Create widget with comprehensive validation."""
    if not widget_type:
        raise ConfigurationError("Widget type cannot be empty")
    
    if widget_type not in SUPPORTED_WIDGETS:
        raise ConfigurationError(
            f"Unsupported widget type: {widget_type}. "
            f"Supported types: {list(SUPPORTED_WIDGETS.keys())}"
        )
    
    if not isinstance(config, dict):
        raise ConfigurationError("Widget config must be a dictionary")
    
    # Validate required fields
    required_fields = WIDGET_SCHEMAS[widget_type].required_fields
    missing_fields = required_fields - config.keys()
    if missing_fields:
        raise ConfigurationError(
            f"Missing required fields for {widget_type}: {missing_fields}"
        )
    
    return SUPPORTED_WIDGETS[widget_type](**config)
```

---

## Security Practices

### Expression Evaluation Security

**asteval Configuration:**
```python
import asteval

# Secure asteval configuration for DSL expressions
SAFE_EVALUATOR = asteval.Interpreter(
    # Restrict available functions
    max_time=1.0,  # 1 second timeout
    max_memory=10 * 1024 * 1024,  # 10MB memory limit
    
    # Disable dangerous operations
    no_for_loops=True,
    no_while_loops=True,
    no_try=True,
    no_functiondef=True,
    no_ifexp=False,
    no_listcomp=False,
    no_augassign=False,
    
    # Allowed built-ins only
    builtins_readonly=True,
)

# Remove dangerous built-ins
for name in ['open', 'exec', 'eval', '__import__', 'compile']:
    if name in SAFE_EVALUATOR.symtable:
        del SAFE_EVALUATOR.symtable[name]
```

**Input Validation:**
```python
import re
from typing import Any

def validate_dsl_expression(expression: str) -> str:
    """Validate DSL expression for security."""
    if not isinstance(expression, str):
        raise DSLError("Expression must be a string")
    
    if len(expression) > 1000:
        raise DSLError("Expression too long (max 1000 characters)")
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r'__\w+__',  # Dunder methods
        r'import\s+',  # Import statements
        r'exec\s*\(',  # Exec calls
        r'eval\s*\(',  # Eval calls
        r'open\s*\(',  # File operations
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, expression, re.IGNORECASE):
            raise DSLError(f"Dangerous pattern detected: {pattern}")
    
    return expression.strip()
```

### Data Validation

**Schema Validation:**
```python
from typing import Dict, Any, Type
from dataclasses import dataclass

@dataclass
class WidgetSchema:
    """Schema definition for widget validation."""
    required_fields: set[str]
    optional_fields: set[str]
    field_types: dict[str, Type]
    field_validators: dict[str, callable]

def validate_widget_config(config: Dict[str, Any], schema: WidgetSchema) -> Dict[str, Any]:
    """Validate widget configuration against schema."""
    # Check required fields
    missing = schema.required_fields - config.keys()
    if missing:
        raise ConfigurationError(f"Missing required fields: {missing}")
    
    # Check unknown fields
    all_fields = schema.required_fields | schema.optional_fields
    unknown = config.keys() - all_fields
    if unknown:
        raise ConfigurationError(f"Unknown fields: {unknown}")
    
    # Validate field types
    validated_config = {}
    for field, value in config.items():
        expected_type = schema.field_types.get(field)
        if expected_type and not isinstance(value, expected_type):
            raise ConfigurationError(
                f"Field '{field}' must be {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )
        
        # Apply field-specific validation
        validator = schema.field_validators.get(field)
        if validator:
            value = validator(value)
        
        validated_config[field] = value
    
    return validated_config
```

---

## Logging and Monitoring

### Logging Configuration

```python
import logging
import sys
from pathlib import Path

def setup_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """Configure logging for tinyDisplay."""
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # File handler (optional)
    handlers = [console_handler]
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers,
        force=True
    )
    
    # Set specific logger levels
    logging.getLogger('tinydisplay.performance').setLevel(logging.DEBUG)
    logging.getLogger('tinydisplay.animation').setLevel(logging.INFO)
```

### Performance Monitoring

```python
import time
import functools
from typing import Callable, Any

def monitor_performance(func: Callable) -> Callable:
    """Decorator to monitor function performance."""
    
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.perf_counter() - start_time
            logger = logging.getLogger('tinydisplay.performance')
            logger.debug(f"{func.__name__} took {duration:.4f}s")
            
            # Alert on slow operations
            if duration > 0.1:  # 100ms threshold
                logger.warning(f"Slow operation: {func.__name__} took {duration:.4f}s")
    
    return wrapper
```

---

## Documentation Standards

### Code Documentation

**Docstring Requirements:**
- All public functions and classes must have docstrings
- Use Google style docstrings
- Include examples for complex functions
- Document all parameters and return values
- Include type hints for all function signatures

**Example Documentation:**
```python
def create_animation_sequence(
    widgets: List[Widget],
    coordination_type: str = "sequential",
    timing: Dict[str, float] | None = None,
) -> AnimationSequence:
    """Create a coordinated animation sequence for multiple widgets.
    
    This function creates an animation sequence that coordinates the timing
    and execution of animations across multiple widgets. The coordination
    can be sequential, parallel, or custom-timed.
    
    Args:
        widgets: List of widgets to include in the animation sequence.
            Must contain at least one widget.
        coordination_type: Type of coordination to apply. Options are:
            - "sequential": Animations run one after another
            - "parallel": All animations start simultaneously
            - "custom": Use timing parameter for custom coordination
        timing: Custom timing configuration when coordination_type is "custom".
            Dictionary mapping widget indices to start times in seconds.
            
    Returns:
        AnimationSequence object that can be executed to run the coordinated
        animations.
        
    Raises:
        AnimationError: If widgets list is empty or coordination_type is invalid.
        ConfigurationError: If timing is required but not provided.
        
    Example:
        >>> widgets = [text_widget, progress_widget, image_widget]
        >>> sequence = create_animation_sequence(
        ...     widgets,
        ...     coordination_type="sequential"
        ... )
        >>> sequence.start()
        
        >>> # Custom timing example
        >>> timing = {0: 0.0, 1: 0.5, 2: 1.0}  # Staggered start times
        >>> sequence = create_animation_sequence(
        ...     widgets,
        ...     coordination_type="custom",
        ...     timing=timing
        ... )
    """
    # Implementation details
```

---

## Dependency Management

### Approved Dependencies

**Core Dependencies (Required):**
- `asteval>=0.9.28` - Safe expression evaluation
- `pillow>=9.0.0` - Image processing

**Development Dependencies:**
- `pytest>=7.0.0` - Testing framework
- `pytest-cov>=4.0.0` - Coverage reporting
- `black>=22.0.0` - Code formatting
- `flake8>=5.0.0` - Linting
- `mypy>=0.991` - Type checking

**Dependency Addition Process:**
1. Evaluate necessity and alternatives
2. Check license compatibility
3. Assess security implications
4. Consider embedded device constraints
5. Get approval from Technical Lead
6. Update `pyproject.toml` and documentation

### Version Pinning Strategy

```toml
# pyproject.toml - Production dependencies
[project]
dependencies = [
    "asteval>=0.9.28,<1.0.0",  # Pin major version
    "pillow>=9.0.0,<11.0.0",   # Allow minor updates
]

# Development dependencies can be more flexible
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=22.0.0",
    "flake8>=5.0.0",
    "mypy>=0.991",
]
```

---

**Last Updated:** December 2024  
**Next Review:** After Epic 1 completion  
**Maintained By:** Technical Lead 