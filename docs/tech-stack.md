# tinyDisplay Technology Stack

**Version:** 2.0 (Full Migration)  
**Last Updated:** December 2024  
**Target Platform:** Raspberry Pi Zero 2W (ARM Cortex-A53, 512MB RAM)  

---

## Core Architecture Stack

### Programming Language
**Python 3.8+**
- **Rationale:** Raspberry Pi compatibility, rich ecosystem, rapid development
- **Version Range:** 3.8 - 3.11 (tested and supported)
- **Performance:** Optimized for embedded devices with memory constraints

### Data Flow Architecture
**Ring Buffers + SQLite + Reactive Patterns**
- **Ring Buffers:** High-performance circular data structures for real-time data streams
- **SQLite:** Embedded database for persistent state and complex queries
- **Reactive Patterns:** Automatic dependency tracking and update propagation
- **Performance Target:** 60fps sustained on Pi Zero 2W

---

## Core Dependencies

### Expression Evaluation
**asteval 0.9.28+**
```python
# Secure expression evaluation for DSL
import asteval

evaluator = asteval.Interpreter(
    use_numpy=False,
    max_time=1.0,
    max_memory=10 * 1024 * 1024,  # 10MB limit
    no_for_loops=True,
    no_while_loops=True,
)
```
- **Purpose:** Safe evaluation of user-defined expressions in DSL
- **Security:** Sandboxed execution with resource limits
- **Performance:** Optimized for embedded constraints

### Image Processing
**Pillow (PIL) 9.0.0+**
```python
from PIL import Image, ImageDraw, ImageFont

# Optimized for small displays
image = Image.new('RGB', (128, 64), color='black')
draw = ImageDraw.Draw(image)

# Efficient pixel data handling for embedded devices
pixel_data = image.tobytes()  # Raw pixel data as bytes
pixel_buffer = bytearray(128 * 64 * 3)  # RGB pixel buffer
```
- **Purpose:** Image loading, manipulation, and rendering
- **Optimization:** Memory-efficient operations for small displays
- **Formats:** PNG, JPEG, BMP support
- **Pixel Data:** Native Python types (bytes, bytearray) sufficient for small displays

---

## Development Stack

### Testing Framework
**pytest 7.0.0+**
```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.performance
def test_rendering_performance():
    """Performance tests for 60fps target."""
    pass
```
- **Features:** Fixtures, parametrization, performance markers
- **Coverage:** pytest-cov for coverage reporting
- **Target:** >90% test coverage

### Code Quality Tools
**Black + Flake8 + mypy**
```bash
# Code formatting and linting pipeline
black src/ tests/ examples/
flake8 src/ tests/ examples/
mypy src/
```
- **Black:** Code formatting (88 character line length)
- **Flake8:** Linting and style checking
- **mypy:** Static type checking

### Package Management
**Modern Python Packaging (pyproject.toml)**
```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "tinydisplay"
version = "2.0.0"
dependencies = [
    "asteval>=0.9.28,<1.0.0",
    "pillow>=9.0.0,<11.0.0",
]
```

---

## Database Layer

### SQLite Configuration
**SQLite 3.35+ (Python stdlib)**
```python
import sqlite3
from contextlib import contextmanager

# Optimized for embedded usage
@contextmanager
def get_db_connection():
    conn = sqlite3.connect(
        'tinydisplay.db',
        timeout=5.0,
        check_same_thread=False
    )
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=2000')  # 2MB cache
    try:
        yield conn
    finally:
        conn.close()
```

### Schema Design
**Reactive Data Storage**
```sql
-- Widget state table
CREATE TABLE widget_states (
    id INTEGER PRIMARY KEY,
    widget_id TEXT NOT NULL,
    state_data BLOB NOT NULL,
    timestamp REAL NOT NULL,
    version INTEGER NOT NULL
);

-- Data dependencies table
CREATE TABLE data_dependencies (
    id INTEGER PRIMARY KEY,
    source_key TEXT NOT NULL,
    dependent_widget TEXT NOT NULL,
    dependency_type TEXT NOT NULL
);

-- Ring buffer metadata
CREATE TABLE ring_buffers (
    id INTEGER PRIMARY KEY,
    buffer_name TEXT UNIQUE NOT NULL,
    size INTEGER NOT NULL,
    head_position INTEGER NOT NULL,
    tail_position INTEGER NOT NULL
);
```

---

## Performance Optimization Stack

### Memory Management
**Custom Memory Pool + Object Recycling**
```python
class WidgetPool:
    """Object pool for widget recycling."""
    
    def __init__(self, widget_class, initial_size=10):
        self._pool = [widget_class() for _ in range(initial_size)]
        self._available = list(self._pool)
        self._in_use = set()
    
    def acquire(self):
        if self._available:
            widget = self._available.pop()
            self._in_use.add(widget)
            return widget
        return self._create_new()
    
    def release(self, widget):
        if widget in self._in_use:
            self._in_use.remove(widget)
            widget.reset()
            self._available.append(widget)
```

### Frame Timing
**Precise 60fps Timing**
```python
import time
from typing import Callable

class FrameTimer:
    """Precise frame timing for 60fps target."""
    
    def __init__(self, target_fps: float = 60.0):
        self.target_frame_time = 1.0 / target_fps
        self.last_frame_time = time.perf_counter()
    
    def wait_for_next_frame(self):
        """Wait for next frame maintaining target FPS."""
        current_time = time.perf_counter()
        elapsed = current_time - self.last_frame_time
        
        if elapsed < self.target_frame_time:
            time.sleep(self.target_frame_time - elapsed)
        
        self.last_frame_time = time.perf_counter()
```

### Profiling Tools
**Built-in Performance Monitoring**
```python
import cProfile
import pstats
from functools import wraps

def profile_performance(func):
    """Decorator for performance profiling."""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            profiler.disable()
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            # Log performance data
    
    return wrapper
```

---

## Display Hardware Abstraction

### Display Drivers
**Modular Display Support**
```python
from abc import ABC, abstractmethod
from typing import Tuple

class DisplayDriver(ABC):
    """Abstract base class for display drivers."""
    
    @abstractmethod
    def get_resolution(self) -> Tuple[int, int]:
        """Get display resolution."""
        pass
    
    @abstractmethod
    def update_display(self, image_data: bytes) -> None:
        """Update display with new image data."""
        pass
    
    @abstractmethod
    def clear_display(self) -> None:
        """Clear the display."""
        pass

# Specific driver implementations
class SSD1306Driver(DisplayDriver):
    """Driver for SSD1306 OLED displays."""
    pass

class ST7735Driver(DisplayDriver):
    """Driver for ST7735 TFT displays."""
    pass
```

### Hardware Interface
**I2C/SPI Communication**
```python
# Hardware communication abstraction
try:
    import spidev
    import smbus
    HAS_HARDWARE = True
except ImportError:
    HAS_HARDWARE = False
    # Fallback to simulation mode

class HardwareInterface:
    """Hardware communication interface."""
    
    def __init__(self, interface_type: str = "auto"):
        self.interface_type = interface_type
        self.connection = self._initialize_connection()
    
    def _initialize_connection(self):
        if not HAS_HARDWARE:
            return MockHardwareConnection()
        
        if self.interface_type == "spi":
            return spidev.SpiDev()
        elif self.interface_type == "i2c":
            return smbus.SMBus(1)
        else:
            # Auto-detect hardware
            return self._detect_hardware()
```

---

## DSL Processing Stack

### Parser Architecture
**Custom DSL Parser + AST**
```python
import ast
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class DSLNode:
    """Base class for DSL AST nodes."""
    node_type: str
    children: List['DSLNode']
    attributes: Dict[str, Any]

class DSLParser:
    """Parser for tinyDisplay DSL."""
    
    def parse(self, dsl_code: str) -> DSLNode:
        """Parse DSL code into AST."""
        # Tokenize
        tokens = self._tokenize(dsl_code)
        
        # Parse into AST
        ast_root = self._parse_tokens(tokens)
        
        # Validate AST
        self._validate_ast(ast_root)
        
        return ast_root
```

### Code Generation
**DSL to Python Code Generation**
```python
class DSLCodeGenerator:
    """Generate Python code from DSL AST."""
    
    def generate(self, ast_node: DSLNode) -> str:
        """Generate Python code from DSL AST."""
        if ast_node.node_type == "widget":
            return self._generate_widget_code(ast_node)
        elif ast_node.node_type == "canvas":
            return self._generate_canvas_code(ast_node)
        elif ast_node.node_type == "animation":
            return self._generate_animation_code(ast_node)
        else:
            raise DSLError(f"Unknown node type: {ast_node.node_type}")
    
    def _generate_widget_code(self, node: DSLNode) -> str:
        """Generate widget creation code."""
        widget_type = node.attributes['type']
        params = node.attributes['parameters']
        
        param_str = ', '.join(f"{k}={repr(v)}" for k, v in params.items())
        return f"{widget_type}Widget({param_str})"
```

---

## Animation System Stack

### Timeline Management
**High-Precision Animation Timing**
```python
import time
from typing import Dict, List, Callable
from dataclasses import dataclass

@dataclass
class AnimationFrame:
    """Single animation frame definition."""
    timestamp: float
    widget_id: str
    property_name: str
    value: Any
    easing_function: Callable[[float], float]

class AnimationTimeline:
    """Manages animation timeline and coordination."""
    
    def __init__(self):
        self.frames: List[AnimationFrame] = []
        self.start_time: float = 0
        self.current_time: float = 0
        self.sync_points: Dict[str, float] = {}
    
    def add_sync_point(self, name: str, timestamp: float):
        """Add synchronization point for coordination."""
        self.sync_points[name] = timestamp
    
    def wait_for_sync(self, sync_name: str):
        """Wait for synchronization point."""
        if sync_name in self.sync_points:
            target_time = self.sync_points[sync_name]
            while self.current_time < target_time:
                time.sleep(0.001)  # 1ms precision
                self.current_time = time.perf_counter() - self.start_time
```

### Easing Functions
**Animation Easing Library**
```python
import math
from typing import Callable

class EasingFunctions:
    """Collection of easing functions for animations."""
    
    @staticmethod
    def linear(t: float) -> float:
        """Linear easing (no acceleration)."""
        return t
    
    @staticmethod
    def ease_in_quad(t: float) -> float:
        """Quadratic ease-in."""
        return t * t
    
    @staticmethod
    def ease_out_quad(t: float) -> float:
        """Quadratic ease-out."""
        return 1 - (1 - t) * (1 - t)
    
    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        """Cubic ease-in-out."""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2
```

---

## CI/CD and Deployment Stack

### Continuous Integration
**GitHub Actions Workflow**
```yaml
name: tinyDisplay CI/CD
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
    
    - name: Run linting
      run: |
        black --check src/ tests/
        flake8 src/ tests/
        mypy src/
    
    - name: Run tests
      run: |
        pytest --cov=src/tinydisplay --cov-report=xml
    
    - name: Performance tests
      run: |
        pytest -m performance --benchmark-only
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build package
      run: |
        pip install build
        python -m build
    
    - name: Publish to PyPI
      if: startsWith(github.ref, 'refs/tags/')
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}
```

### Package Distribution
**PyPI Package Configuration**
```toml
[project]
name = "tinydisplay"
version = "2.0.0"
description = "High-performance display framework for embedded devices"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "tinyDisplay Team", email = "team@tinydisplay.org"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: System :: Hardware",
]
keywords = ["embedded", "display", "raspberry-pi", "gui", "framework"]

[project.urls]
Homepage = "https://github.com/tinydisplay/tinydisplay"
Documentation = "https://tinydisplay.readthedocs.io/"
Repository = "https://github.com/tinydisplay/tinydisplay"
Issues = "https://github.com/tinydisplay/tinydisplay/issues"
```

---

## Development Environment

### Recommended Setup
**Development Environment Configuration**
```bash
# Python environment setup
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install development dependencies
pip install -e .[dev]

# Pre-commit hooks setup
pip install pre-commit
pre-commit install
```

### IDE Configuration
**VS Code / Cursor IDE Settings**
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "88"],
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        ".coverage": true,
        "htmlcov": true
    }
}
```

---

## Platform-Specific Considerations

### Raspberry Pi Optimization
**Pi Zero 2W Specific Optimizations**
```python
import os
import psutil

class PiOptimizations:
    """Raspberry Pi specific optimizations."""
    
    @staticmethod
    def configure_for_pi():
        """Configure system for optimal Pi performance."""
        # Set CPU governor to performance
        if os.path.exists('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'):
            with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', 'w') as f:
                f.write('performance')
        
        # Increase GPU memory split
        os.system('sudo raspi-config nonint do_memory_split 128')
        
        # Optimize Python garbage collection
        import gc
        gc.set_threshold(700, 10, 10)
    
    @staticmethod
    def monitor_resources():
        """Monitor Pi resource usage."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        temperature = PiOptimizations.get_cpu_temperature()
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_mb': memory.available / 1024 / 1024,
            'temperature_c': temperature
        }
    
    @staticmethod
    def get_cpu_temperature():
        """Get CPU temperature on Raspberry Pi."""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = int(f.read()) / 1000.0
                return temp
        except:
            return None
```

---

## Migration and Legacy Support

### Legacy Code Handling
**Migration Tool Integration**
```python
from migration_tool import MigrationTool
from migration_generator import DSLGenerator

class LegacyMigration:
    """Handle migration from legacy tinyDisplay."""
    
    def __init__(self):
        self.migration_tool = MigrationTool()
        self.dsl_generator = DSLGenerator()
    
    def migrate_application(self, legacy_app_path: str) -> str:
        """Migrate legacy application to new architecture."""
        # Analyze legacy code
        analysis = self.migration_tool.analyze_legacy_code(legacy_app_path)
        
        # Generate new DSL code
        dsl_code = self.dsl_generator.generate_from_analysis(analysis)
        
        # Validate generated code
        self._validate_generated_code(dsl_code)
        
        return dsl_code
```

---

**Last Updated:** December 2024  
**Next Review:** After Epic 1 completion  
**Maintained By:** Technical Lead 