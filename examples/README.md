# tinyDisplay Examples

This directory contains example applications demonstrating tinyDisplay capabilities.

## Directory Structure

### Basic Examples (`basic/`)
Simple examples for learning tinyDisplay fundamentals:
- `hello_world/` - Simple text display
- `progress_bar/` - Progress bar demonstration
- `image_display/` - Image widget usage

### Intermediate Examples (`intermediate/`)
More complex examples showing advanced features:
- `dashboard/` - Multi-widget dashboard
- `animations/` - Animation coordination
- `data_binding/` - Reactive data examples

### Advanced Examples (`advanced/`)
Complex applications demonstrating full capabilities:
- `music_player/` - Complete music player UI
- `system_monitor/` - System monitoring display
- `multi_canvas/` - Complex canvas sequences

### Migration Examples (`migration/`)
Examples showing migration from legacy tinyDisplay:
- `legacy_to_dsl/` - Migration demonstrations
- `comparison/` - Before/after comparisons

### Performance Examples (`performance/`)
Examples optimized for performance testing:
- `stress_test/` - High widget count tests
- `memory_efficient/` - Memory optimization examples
- `pi_zero_demos/` - Pi Zero 2W optimized applications

## Running Examples

Each example directory contains:
- `app.py` - Main application file
- `README.md` - Example-specific documentation
- `requirements.txt` - Additional dependencies (if any)

To run an example:
```bash
cd examples/basic/hello_world/
python app.py
```

## Performance Testing

Performance examples include benchmarking utilities:
```bash
cd examples/performance/stress_test/
python benchmark.py --target-fps 60 --duration 30
```

## Hardware Requirements

- **Minimum:** Raspberry Pi Zero 2W (512MB RAM)
- **Recommended:** Raspberry Pi 4 (1GB+ RAM)
- **Display:** Any supported display (80x16 to 256x256)

## Contributing Examples

When adding new examples:
1. Follow the directory structure pattern
2. Include comprehensive README.md
3. Add performance benchmarks where applicable
4. Test on target hardware (Pi Zero 2W)
5. Document any additional dependencies 