"""pytest configuration and fixtures for tinyDisplay tests."""

import pytest
import sys
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import Mock

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_db():
    """Provide a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Create database with basic schema
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS widget_states (
            id INTEGER PRIMARY KEY,
            widget_id TEXT NOT NULL,
            state_data BLOB NOT NULL,
            timestamp REAL NOT NULL,
            version INTEGER NOT NULL
        )
    """
    )
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def mock_display():
    """Provide a mock display for testing rendering without hardware."""
    display = Mock()
    display.width = 128
    display.height = 64
    display.mode = "RGB"
    return display


@pytest.fixture
def sample_ring_buffer_data():
    """Provide sample data for ring buffer testing."""
    return [
        {"timestamp": 1.0, "value": 10, "type": "numeric"},
        {"timestamp": 2.0, "value": "hello", "type": "string"},
        {"timestamp": 3.0, "value": b"binary", "type": "binary"},
        {"timestamp": 4.0, "value": 25, "type": "numeric"},
        {"timestamp": 5.0, "value": "world", "type": "string"},
    ]


@pytest.fixture
def performance_test_config():
    """Configuration for performance tests."""
    return {
        "target_fps": 60,
        "max_memory_mb": 100,
        "test_duration_seconds": 5,
        "widget_count": 20,
    }


# Performance test markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "security: mark test as security-related test")
