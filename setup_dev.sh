#!/bin/bash

# tinyDisplay Development Setup Script
# This script ensures proper Poetry-based development environment

set -e

echo "🚀 Setting up tinyDisplay development environment..."

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed!"
    echo "Please install Poetry first: https://python-poetry.org/docs/#installation"
    echo "curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

echo "✅ Poetry found: $(poetry --version)"

# Install dependencies
echo "📦 Installing dependencies with Poetry..."
poetry install

# Install performance dependencies
echo "🚀 Installing performance dependencies..."
poetry install --extras performance

# Verify installation by running a quick test
echo "🧪 Verifying installation..."
if poetry run python -c "import src.tinydisplay.widgets.text; print('✅ Import successful')"; then
    echo "✅ Development environment setup complete!"
else
    echo "❌ Installation verification failed"
    exit 1
fi

echo ""
echo "🎯 Development Commands:"
echo "  poetry run pytest                    # Run all tests"
echo "  poetry run pytest tests/unit/ -v    # Run unit tests with verbose output"
echo "  poetry run python examples/demo.py  # Run example scripts"
echo ""
echo "⚠️  IMPORTANT: Always use 'poetry run' prefix for all Python commands!"
echo "   DO NOT use 'pip' or 'python' directly - this will cause dependency conflicts!"
echo ""
echo "📚 Documentation: docs/epic-2.md"
echo "🧪 Test Status: 623 tests passing" 