# tinyDisplay Development Guide

## 🚨 CRITICAL: Poetry Dependency Management

**This project REQUIRES Poetry for ALL development activities. Using `pip` or `python` directly WILL cause dependency conflicts and test failures.**

### Quick Setup

```bash
# 1. Run the setup script
./setup_dev.sh

# 2. Verify everything works
poetry run pytest tests/unit/ --tb=no -q
```

## 🔧 Daily Development Commands

### Testing (ALWAYS use poetry run)
```bash
# Run all tests
poetry run pytest tests/unit/ -v

# Run specific test files
poetry run pytest tests/unit/test_text_widget.py -v
poetry run pytest tests/unit/test_performance.py -v

# Run tests with coverage
poetry run pytest tests/unit/ --cov=src --cov-report=html

# Quick test status check
poetry run pytest tests/unit/ --tb=no -q
```

### Running Code
```bash
# Run Python scripts
poetry run python examples/demo.py
poetry run python -c "from src.tinydisplay.widgets import *; print('Success!')"

# Interactive Python shell with dependencies
poetry shell
```

### Managing Dependencies
```bash
# Add new dependencies
poetry add package-name

# Add development dependencies
poetry add --group dev package-name

# Update dependencies
poetry update

# Show dependency tree
poetry show --tree
```

## 🚫 Common Mistakes to Avoid

### ❌ DON'T DO THIS:
```bash
pip install package-name          # Wrong - bypasses Poetry
python -m pytest                  # Wrong - uses system Python
python examples/demo.py           # Wrong - missing dependencies
```

### ✅ DO THIS INSTEAD:
```bash
poetry add package-name           # Correct - managed by Poetry
poetry run pytest                 # Correct - uses Poetry environment
poetry run python examples/demo.py # Correct - all dependencies available
```

## 🧪 Test Status Verification

The project should always maintain **623 passing tests**:

```bash
# Quick verification
poetry run pytest tests/unit/ --tb=no -q

# Expected output:
# 623 passed, 4 skipped in X.XXs
```

If you see failures, check:
1. Are you using `poetry run`?
2. Are performance dependencies installed? (`poetry install --extras performance`)
3. Are there import errors? (usually indicates Poetry not used)

## 🔍 Troubleshooting

### Import Errors
```bash
# Problem: ModuleNotFoundError or ImportError
# Solution: Always use poetry run
poetry run python your_script.py
```

### Missing psutil
```bash
# Problem: No module named 'psutil'
# Solution: Install performance dependencies
poetry install --extras performance
```

### Test Failures
```bash
# Problem: Tests failing that should pass
# Solution: Verify Poetry environment
poetry env info
poetry run python -c "import sys; print(sys.executable)"
```

### Dependency Conflicts
```bash
# Problem: Conflicting package versions
# Solution: Clean and reinstall
poetry env remove python
poetry install
poetry install --extras performance
```

## 📊 Performance Monitoring

The project includes comprehensive performance monitoring:

```bash
# Run performance benchmarks
poetry run pytest tests/unit/test_performance.py -v

# Check memory usage
poetry run python -c "
from src.tinydisplay.widgets.performance import get_performance_monitor
monitor = get_performance_monitor()
print(f'Memory: {monitor.memory_manager.get_memory_usage():.1f}MB')
"
```

## 🎯 Development Workflow

1. **Start Development Session:**
   ```bash
   cd tinyDisplay
   poetry shell  # Activate Poetry environment
   ```

2. **Make Changes:**
   - Edit code in `src/tinydisplay/`
   - Add tests in `tests/unit/`

3. **Test Changes:**
   ```bash
   poetry run pytest tests/unit/test_your_changes.py -v
   ```

4. **Verify Full Suite:**
   ```bash
   poetry run pytest tests/unit/ --tb=no -q
   ```

5. **Performance Check:**
   ```bash
   poetry run pytest tests/unit/test_performance.py -v
   ```

## 📚 Key Files

- `pyproject.toml` - Poetry configuration and dependencies
- `poetry.lock` - Locked dependency versions (DO NOT edit manually)
- `setup_dev.sh` - Development environment setup script
- `README.md` - Project overview with Poetry instructions
- `tests/unit/` - 623 comprehensive tests

## 🤝 Contributing

Before submitting changes:

1. ✅ All tests pass: `poetry run pytest tests/unit/ --tb=no -q`
2. ✅ Performance tests pass: `poetry run pytest tests/unit/test_performance.py -v`
3. ✅ No import errors: `poetry run python -c "from src.tinydisplay.widgets import *"`
4. ✅ Documentation updated if needed

## 🆘 Getting Help

If you encounter issues:

1. Check this guide first
2. Verify Poetry is being used correctly
3. Run `./setup_dev.sh` to reset environment
4. Check the test output for specific error messages

**Remember: When in doubt, use `poetry run` prefix for all Python commands!** 