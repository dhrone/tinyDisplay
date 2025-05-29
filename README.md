# Marquee Animation Demo

This program demonstrates the various animation capabilities of the tinyDisplay marquee class by creating animated GIFs for different animation types.

## Features

- Demonstrates various marquee animation types:
  - SLIDE: Smooth sliding animations with easing
  - SCROLL: Continuous scrolling text (ticker)
  - SCROLL_BOUNCE: Text that bounces back and forth
  - SCROLL_CLIP: Text that scrolls to a specific point and stops
  - Complex animations combining multiple effects
  - Multi-widget coordinated animations using SYNC and WAIT_FOR

- All animations are saved as animated GIFs at 30 FPS
- Animations show 5 seconds of each effect
- Results are saved to a `test_results` directory
- Includes a cleanup option to remove test results

## Requirements

- Python 3.6+
- tinyDisplay library
- PIL/Pillow for image processing

## Usage

Run the program with:

```
./marquee_demo.py
```

### Command-line options:

- `--animation [type]`: Specify which animation to run
  - Available types: slide, scroll, bounce, clip, complex, multi
  - Default: all (runs all animations)

- `--cleanup`: Remove test results directory and exit

### Examples:

Run all animations:
```
./marquee_demo.py
```

Run only the SLIDE animation:
```
./marquee_demo.py --animation slide
```

Run only the multi-widget coordinated animation:
```
./marquee_demo.py --animation multi
```

Clean up test results:
```
./marquee_demo.py --cleanup
```

## Output

The program creates a `test_results` directory and saves animated GIFs inside it:

- `slide_animation.gif`: SLIDE effect demonstration
- `scroll_animation.gif`: SCROLL_LOOP effect demonstration
- `scroll_bounce_animation.gif`: SCROLL_BOUNCE effect demonstration
- `scroll_clip_animation.gif`: SCROLL_CLIP effect demonstration
- `complex_animation.gif`: Complex animation combining multiple effects
- `multi_widget_animation.gif`: Multiple widgets with coordinated animations

## Customization

You can modify the program to:

- Change animation duration by adjusting `ANIMATION_SECONDS` and `FPS` constants
- Add or modify animation types by creating new demo functions
- Customize text, colors, speeds, and other parameters 

# tinyDisplay

A high-performance, reactive widget system for embedded displays with automatic data binding and sophisticated rendering capabilities.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Poetry (for dependency management)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd tinyDisplay

# Install dependencies using Poetry (REQUIRED)
poetry install

# Install optional performance dependencies
poetry install --extras performance
```

## 🔧 Development

### ⚠️ CRITICAL: Poetry Dependency Management

**This project MUST use Poetry for all development activities:**

```bash
# Run tests (ALWAYS use poetry run)
poetry run pytest

# Run specific test files
poetry run pytest tests/unit/test_text_widget.py -v

# Run all tests with coverage
poetry run pytest tests/unit/ --cov=src --cov-report=html

# Run Python scripts
poetry run python examples/demo.py

# Install new dependencies
poetry add package-name

# Install development dependencies
poetry add --group dev package-name
```

**❌ DO NOT use `pip` or `python` directly - this will cause dependency conflicts!**

### Project Structure

```
src/tinydisplay/
├── core/                    # Core reactive system
│   ├── reactive.py         # Reactive data management
│   └── ring_buffer.py      # High-performance data buffers
├── widgets/                # Widget implementations
│   ├── base.py            # Abstract widget foundation
│   ├── text.py            # Text widget with font rendering
│   ├── image.py           # Image widget with caching
│   ├── progress.py        # Progress bar with animations
│   ├── shapes.py          # Shape primitives
│   ├── styling.py         # Styling framework
│   └── performance.py     # Performance optimization
├── canvas/                 # Canvas composition system
│   └── canvas.py          # Canvas implementation
└── utils/                  # Utilities and helpers

tests/
├── unit/                   # Unit tests (623 tests)
└── integration/           # Integration tests

docs/                       # Documentation
├── epic-1.md              # Epic 1: Foundation
├── epic-2.md              # Epic 2: Core Widgets
└── stories/               # Detailed story documentation
```

## 🧪 Testing

The project has comprehensive test coverage with **623 passing tests**:

```bash
# Run all tests
poetry run pytest tests/unit/ -v

# Run performance tests
poetry run pytest tests/unit/test_performance.py -v

# Run specific widget tests
poetry run pytest tests/unit/test_text_widget.py -v
poetry run pytest tests/unit/test_image_widget.py -v
poetry run pytest tests/unit/test_progress_widget.py -v
```

## 📊 Performance Targets

- **Rendering:** 60fps sustained on Raspberry Pi Zero 2W
- **Memory:** <100MB for 20+ widget applications
- **Reactive Updates:** <50ms response time
- **Widget Creation:** <50ms for 100 widgets

## 🎯 Current Status

### ✅ Epic 1: Foundation (Complete)
- Reactive data management system
- Widget base classes and lifecycle
- Canvas composition framework
- Ring buffer for high-performance data

### ✅ Epic 2: Core Widgets (Complete)
- **Story 2.1:** Core Widget Implementation ✅
  - Text widget with font rendering and caching
  - Image widget with scaling and effects
  - Progress bar with predictive animations
  - Shape widgets (Rectangle, Circle, Line)
  - Comprehensive styling system
  - Performance optimization suite

### 🚧 Epic 3: Advanced Features (Planned)
- Animation coordination system
- Layout managers
- Event handling system

## 🔧 Widget Usage Examples

### Text Widget
```python
from src.tinydisplay.widgets.text import TextWidget
from src.tinydisplay.widgets.base import ReactiveValue

# Static text
text_widget = TextWidget("Hello World", font_size=16)

# Reactive text
reactive_text = ReactiveValue("Dynamic Content")
text_widget = TextWidget(reactive_text, font_size=16)
```

### Image Widget
```python
from src.tinydisplay.widgets.image import ImageWidget, ScaleMode

# Load image with scaling
image_widget = ImageWidget(
    image_source="path/to/image.png",
    scale_mode=ScaleMode.FIT
)
```

### Progress Bar
```python
from src.tinydisplay.widgets.progress import ProgressBarWidget
from src.tinydisplay.widgets.base import ReactiveValue

# Progress with predictive animation
progress_value = ReactiveValue(0.0)
progress_widget = ProgressBarWidget(
    progress_value,
    enable_prediction=True
)
```

## 🛠️ Development Guidelines

1. **Always use Poetry** for dependency management
2. **Write tests** for all new functionality (target >90% coverage)
3. **Follow performance targets** - validate with benchmarks
4. **Use reactive patterns** for dynamic data
5. **Document APIs** with comprehensive docstrings

## 📚 Documentation

- [Epic 1 Documentation](docs/epic-1.md) - Foundation system
- [Epic 2 Documentation](docs/epic-2.md) - Core widgets
- [Story Documentation](docs/stories/) - Detailed implementation guides
- [Project Structure](docs/project-structure.md) - Architecture overview

## 🤝 Contributing

1. Ensure Poetry is installed and used for all operations
2. Run the full test suite before submitting changes
3. Follow the existing code patterns and architecture
4. Update documentation for new features
5. Validate performance targets are maintained

## 📄 License

[License information here] 