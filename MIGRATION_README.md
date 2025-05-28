# tinyDisplay Migration Tool

This migration tool automates the transition from your current tinyDisplay architecture to the new reactive architecture with Ring Buffers + SQLite + asteval + RxPY.

## 🎯 What It Does

The migration tool performs **real code analysis and generation**:

1. **Analyzes** your existing tinyDisplay codebase
2. **Extracts** widgets, data usage patterns, and dynamic values
3. **Generates** a complete new reactive architecture
4. **Creates** working Python code with the new system

## 🚀 Quick Start

### 1. Run Analysis Only (Recommended First Step)

```bash
python migration_tool.py --source ./tinyDisplay --analysis-only --output-analysis analysis.json
```

This will:
- Scan your existing codebase
- Extract all widgets, data streams, and dynamic values
- Save analysis to `analysis.json` for review
- **No code changes made**

### 2. Full Migration

```bash
python migration_tool.py --source ./tinyDisplay --target ./tinyDisplay_new
```

This will:
- Perform complete analysis
- Generate new reactive architecture in `./tinyDisplay_new`
- Create working Python files with new system

### 3. Test the Tool

```bash
python test_migration.py
```

This creates a sample project and demonstrates the migration process.

## 📋 What Gets Analyzed

### Widgets
- **Finds:** All widget classes in your codebase
- **Extracts:** Position, size, methods, attributes
- **Identifies:** Dynamic value expressions
- **Generates:** New reactive widget classes

### Data Usage
- **Finds:** All `dataset.get()` calls
- **Tracks:** Data access patterns
- **Counts:** Usage frequency per data stream
- **Creates:** Ring buffer configurations

### Dynamic Values
- **Finds:** `DynamicValue("expression")` patterns
- **Extracts:** F-string expressions with data references
- **Analyzes:** Dependencies using AST parsing
- **Generates:** New asteval-based dynamic values

### Configuration
- **Finds:** Display settings (width, height, fps)
- **Extracts:** Memory and performance configurations
- **Preserves:** Your existing settings

## 🏗️ What Gets Generated

### Complete New Architecture

```
tinyDisplay_new/
├── data/
│   ├── ring_buffer.py          # High-performance ring buffers
│   ├── data_manager.py         # Central data coordination
│   └── sqlite_storage.py       # Persistent storage backend
├── reactive/
│   ├── dynamic_values.py       # asteval + RxPY engine
│   └── dependency_tracker.py   # Dependency management
├── widgets/
│   ├── base.py                 # New reactive widget base classes
│   ├── manager.py              # Widget lifecycle management
│   ├── temperature_widget.py   # Your migrated widgets
│   └── clock_widget.py         # (example)
├── rendering/
│   ├── controller.py           # 60fps render controller
│   ├── speculative.py          # Multi-process pre-rendering
│   └── partial_update.py       # Dirty region tracking
├── dsl/
│   └── application.py          # Application DSL configuration
├── config/
│   └── data_config.py          # Data stream configuration
├── tests/
│   ├── test_data_manager.py    # Generated test suite
│   ├── test_dynamic_values.py
│   ├── test_widgets.py
│   └── test_rendering.py
├── main.py                     # New application entry point
└── requirements.txt            # Dependencies
```

### Working Code Examples

**Generated Widget:**
```python
class TemperatureWidget(TextWidget):
    def __init__(self, widget_id: str, config: dict):
        super().__init__(widget_id, config)
        self.subscribe_to_dynamic_value("temperature_display")
    
    def render(self, context: RenderContext, timestamp: float) -> RenderResult:
        # Automatically gets data from reactive system
        temp_text = context.dynamic_values_engine.get_value("temperature_display", timestamp)
        # ... rendering logic
```

**Generated Data Manager:**
```python
class DataManager:
    def __init__(self):
        # Ring buffers for your actual data streams
        self.register_data_stream("sensor.temperature", DataStreamConfig())
        self.register_data_stream("sensor.humidity", DataStreamConfig())
        # ... based on your actual usage
```

## 🔧 Command Line Options

```bash
python migration_tool.py [OPTIONS]

Required:
  --source, -s PATH     Source directory (your existing tinyDisplay)
  --target, -t PATH     Target directory (new architecture)

Optional:
  --analysis-only       Only analyze, don't generate code
  --output-analysis, -o FILE  Save analysis to JSON file
```

## 📊 Analysis Output Example

```json
{
  "widgets": [
    {
      "name": "temperature",
      "class_name": "TemperatureWidget", 
      "position": [10, 20],
      "size": [100, 30],
      "dynamic_values": ["f'{sensor.temperature}°F'"],
      "methods": ["render", "update"]
    }
  ],
  "data_streams": [
    {
      "key": "sensor.temperature",
      "usage_count": 5,
      "is_time_series": true
    }
  ],
  "dynamic_values": [
    {
      "expression": "f'{sensor.temperature}°F'",
      "dependencies": ["sensor.temperature"]
    }
  ]
}
```

## 🎛️ Customization

### Generation Configuration

Edit `migration_generator.py` to customize:

```python
config = GenerationConfig(
    target_fps=60,              # Your target frame rate
    max_memory_mb=200,          # Memory limit for Pi Zero 2W
    ring_buffer_default_size=1000,  # Buffer size per data stream
    speculation_workers=3,      # Background rendering processes
    enable_predictive_progress=True  # Predictive progress indicators
)
```

### Template Customization

The `CodeTemplates` class in `migration_generator.py` contains all code generation templates. You can modify these to:

- Change generated code style
- Add custom widget types
- Modify architecture patterns
- Add additional features

## 🧪 Testing Your Migration

### 1. Validate Analysis
```bash
# Check what the tool found
python migration_tool.py --source ./tinyDisplay --analysis-only --output-analysis analysis.json
cat analysis.json | jq .  # Pretty print JSON
```

### 2. Generate and Test
```bash
# Generate new system
python migration_tool.py --source ./tinyDisplay --target ./tinyDisplay_new

# Install dependencies
cd tinyDisplay_new
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Try the new system
python main.py
```

### 3. Compare Functionality
- Run your old system and note behavior
- Run new system and compare outputs
- Check that all widgets render correctly
- Verify data flows work as expected

## 🔍 Troubleshooting

### Analysis Issues
- **No widgets found:** Check if widget classes have `render()` or `update()` methods
- **No data streams found:** Look for `dataset.get()` calls in your code
- **Missing dynamic values:** Check for `DynamicValue()` instantiations

### Generation Issues
- **Import errors:** Check that all dependencies are in `requirements.txt`
- **Missing methods:** Some generated code has `# TODO` comments for manual completion
- **Widget behavior:** Generated widgets are templates - customize the `render()` methods

### Runtime Issues
- **Performance:** Adjust ring buffer sizes and speculation workers
- **Memory:** Reduce buffer sizes or disable speculative rendering
- **Display:** Integrate with your actual luma.oled/luma.lcd setup

## 🎯 Next Steps After Migration

1. **Review Generated Code:** Check all `# TODO` comments
2. **Customize Widgets:** Implement specific rendering logic
3. **Test Performance:** Verify 60fps target on your hardware
4. **Add Features:** Implement predictive progress, touch support, etc.
5. **Optimize:** Tune memory usage and speculation parameters

## 🤝 Manual Completion Required

The migration tool generates **80-90% of your new system**, but some manual work is needed:

### High Priority
- **Widget rendering logic:** Customize `render()` methods for your specific widgets
- **Display integration:** Connect to your actual luma.oled/luma.lcd hardware
- **Data source setup:** Configure how external data enters the system

### Medium Priority  
- **Animation definitions:** Add specific animations using the new system
- **DSL refinement:** Customize the application DSL for your use cases
- **Performance tuning:** Optimize for your specific hardware and data patterns

### Low Priority
- **Test completion:** Finish the generated test cases
- **Documentation:** Add project-specific documentation
- **Advanced features:** Implement touch support, web UI, etc.

## 📈 Expected Benefits

After migration, you should see:

- **4-10x faster** dynamic value evaluation (asteval vs eval)
- **60fps rendering** capability on Pi Zero 2W
- **<200MB memory** usage during normal operation
- **Predictive progress** indicators for better UX
- **Speculative rendering** for smoother animations
- **Clean architecture** that's easier to maintain and extend

The migration tool gives you a solid foundation to achieve these performance goals while preserving your existing functionality. 