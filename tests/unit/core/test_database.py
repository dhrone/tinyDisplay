"""Unit tests for database integration layer."""

import pytest
import tempfile
import threading
import time
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from tinydisplay.core.database import (
    ReactiveStateManager,
    DatabaseConfig,
    SerializationFormat,
    DatabaseError,
    ConnectionPoolError,
    SchemaError,
    get_db_connection,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def db_config():
    """Create a test database configuration."""
    return DatabaseConfig(
        path="test.db",
        max_connections=3,
        timeout=5.0,
        cache_size=-1000,  # 1MB cache for testing
    )


@pytest.fixture
def state_manager(temp_db_path, db_config):
    """Create a ReactiveStateManager instance for testing."""
    db_config.path = temp_db_path
    manager = ReactiveStateManager(temp_db_path, db_config)

    yield manager

    # Cleanup
    manager.close()


class TestReactiveStateManagerBasics:
    """Test basic state manager functionality."""

    def test_initialization__creates_database_and_schema(self, temp_db_path, db_config):
        """Test that initialization creates database with proper schema."""
        manager = ReactiveStateManager(temp_db_path, db_config)

        # Database file should exist
        assert temp_db_path.exists()

        # Should be able to query schema
        with manager.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('widget_states', 'state_changes')
            """
            )
            tables = [row[0] for row in cursor.fetchall()]

            assert "widget_states" in tables
            assert "state_changes" in tables

        manager.close()

    def test_set_get_widget_state__json_format__works_correctly(self, state_manager):
        """Test setting and getting widget state with JSON serialization."""
        widget_id = "test_widget"
        state_data = {"value": 42, "enabled": True, "text": "Hello"}

        # Set state
        version = state_manager.set_widget_state(
            widget_id, state_data, SerializationFormat.JSON
        )

        assert version == 1

        # Get state
        retrieved_data, retrieved_version = state_manager.get_widget_state(widget_id)

        assert retrieved_data == state_data
        assert retrieved_version == 1

    def test_set_get_widget_state__pickle_format__works_correctly(self, state_manager):
        """Test setting and getting widget state with pickle serialization."""
        widget_id = "test_widget"
        state_data = {"complex": [1, 2, {"nested": True}], "tuple": (1, 2, 3)}

        # Set state
        version = state_manager.set_widget_state(
            widget_id, state_data, SerializationFormat.PICKLE
        )

        assert version == 1

        # Get state
        retrieved_data, retrieved_version = state_manager.get_widget_state(widget_id)

        assert retrieved_data == state_data
        assert retrieved_version == 1

    def test_set_get_widget_state__blob_format__works_correctly(self, state_manager):
        """Test setting and getting widget state with blob serialization."""
        widget_id = "test_widget"
        state_data = b"binary data here"

        # Set state
        version = state_manager.set_widget_state(
            widget_id, state_data, SerializationFormat.BLOB
        )

        assert version == 1

        # Get state
        retrieved_data, retrieved_version = state_manager.get_widget_state(widget_id)

        assert retrieved_data == state_data
        assert retrieved_version == 1

    def test_get_widget_state__nonexistent__returns_default(self, state_manager):
        """Test getting nonexistent widget state returns default."""
        default_value = {"default": True}

        data, version = state_manager.get_widget_state("nonexistent", default_value)

        assert data == default_value
        assert version == 0

    def test_update_widget_state__increments_version(self, state_manager):
        """Test that updating widget state increments version."""
        widget_id = "test_widget"

        # Set initial state
        version1 = state_manager.set_widget_state(widget_id, {"value": 1})
        assert version1 == 1

        # Update state
        version2 = state_manager.set_widget_state(widget_id, {"value": 2})
        assert version2 == 2

        # Update again
        version3 = state_manager.set_widget_state(widget_id, {"value": 3})
        assert version3 == 3

        # Verify final state
        data, version = state_manager.get_widget_state(widget_id)
        assert data == {"value": 3}
        assert version == 3

    def test_delete_widget_state__removes_state(self, state_manager):
        """Test deleting widget state."""
        widget_id = "test_widget"

        # Set state
        state_manager.set_widget_state(widget_id, {"value": 42})

        # Verify it exists
        data, version = state_manager.get_widget_state(widget_id)
        assert data == {"value": 42}
        assert version == 1

        # Delete state
        deleted = state_manager.delete_widget_state(widget_id)
        assert deleted is True

        # Verify it's gone
        data, version = state_manager.get_widget_state(widget_id, "default")
        assert data == "default"
        assert version == 0

        # Delete again should return False
        deleted = state_manager.delete_widget_state(widget_id)
        assert deleted is False


class TestReactiveStateManagerBatchOperations:
    """Test batch operations for efficiency."""

    def test_get_widget_states__multiple_widgets__returns_all(self, state_manager):
        """Test getting multiple widget states efficiently."""
        # Set up test data
        widgets = {
            "widget1": {"value": 1},
            "widget2": {"value": 2},
            "widget3": {"value": 3},
        }

        for widget_id, data in widgets.items():
            state_manager.set_widget_state(widget_id, data)

        # Get all states
        result = state_manager.get_widget_states()

        assert len(result) == 3
        for widget_id, expected_data in widgets.items():
            assert widget_id in result
            data, version = result[widget_id]
            assert data == expected_data
            assert version == 1

    def test_get_widget_states__specific_widgets__returns_subset(self, state_manager):
        """Test getting specific widget states."""
        # Set up test data
        widgets = {
            "widget1": {"value": 1},
            "widget2": {"value": 2},
            "widget3": {"value": 3},
        }

        for widget_id, data in widgets.items():
            state_manager.set_widget_state(widget_id, data)

        # Get specific widgets
        result = state_manager.get_widget_states(["widget1", "widget3"])

        assert len(result) == 2
        assert "widget1" in result
        assert "widget3" in result
        assert "widget2" not in result

    def test_get_widget_states__since_timestamp__filters_correctly(self, state_manager):
        """Test getting widget states modified since timestamp."""
        # Set initial state
        state_manager.set_widget_state("widget1", {"value": 1})

        # Record timestamp
        timestamp = time.time()
        time.sleep(0.01)  # Small delay to ensure timestamp difference

        # Set more states
        state_manager.set_widget_state("widget2", {"value": 2})
        state_manager.set_widget_state("widget1", {"value": 1.1})  # Update existing

        # Get states since timestamp
        result = state_manager.get_widget_states(since_timestamp=timestamp)

        # Should only get widget2 and updated widget1
        assert len(result) == 2
        assert "widget1" in result
        assert "widget2" in result

        # Check values
        assert result["widget1"][0] == {"value": 1.1}
        assert result["widget2"][0] == {"value": 2}


class TestReactiveStateManagerChangeNotifications:
    """Test change notification system."""

    def test_register_change_callback__receives_notifications(self, state_manager):
        """Test registering and receiving change notifications."""
        notifications = []

        def callback(widget_id, change_type, state_data):
            notifications.append((widget_id, change_type, state_data))

        # Register callback
        state_manager.register_change_callback("test_widget", callback)

        # Make changes
        state_manager.set_widget_state("test_widget", {"value": 1})
        state_manager.set_widget_state("test_widget", {"value": 2})
        state_manager.delete_widget_state("test_widget")

        # Check notifications
        assert len(notifications) == 3

        assert notifications[0] == ("test_widget", "update", {"value": 1})
        assert notifications[1] == ("test_widget", "update", {"value": 2})
        assert notifications[2] == ("test_widget", "delete", None)

    def test_register_wildcard_callback__receives_all_notifications(
        self, state_manager
    ):
        """Test wildcard callback receives notifications for all widgets."""
        notifications = []

        def callback(widget_id, change_type, state_data):
            notifications.append((widget_id, change_type, state_data))

        # Register wildcard callback
        state_manager.register_change_callback("*", callback)

        # Make changes to different widgets
        state_manager.set_widget_state("widget1", {"value": 1})
        state_manager.set_widget_state("widget2", {"value": 2})

        # Check notifications
        assert len(notifications) == 2
        assert notifications[0] == ("widget1", "update", {"value": 1})
        assert notifications[1] == ("widget2", "update", {"value": 2})

    def test_unregister_change_callback__stops_notifications(self, state_manager):
        """Test unregistering change callbacks."""
        notifications = []

        def callback(widget_id, change_type, state_data):
            notifications.append((widget_id, change_type, state_data))

        # Register and test
        state_manager.register_change_callback("test_widget", callback)
        state_manager.set_widget_state("test_widget", {"value": 1})

        assert len(notifications) == 1

        # Unregister and test
        removed = state_manager.unregister_change_callback("test_widget", callback)
        assert removed is True

        state_manager.set_widget_state("test_widget", {"value": 2})

        # Should not receive new notification
        assert len(notifications) == 1

        # Unregister again should return False
        removed = state_manager.unregister_change_callback("test_widget", callback)
        assert removed is False

    def test_broken_callback__gets_removed_automatically(self, state_manager):
        """Test that broken callbacks are automatically removed."""
        good_notifications = []

        def good_callback(widget_id, change_type, state_data):
            good_notifications.append((widget_id, change_type, state_data))

        def broken_callback(widget_id, change_type, state_data):
            raise Exception("Broken callback")

        # Register both callbacks
        state_manager.register_change_callback("test_widget", good_callback)
        state_manager.register_change_callback("test_widget", broken_callback)

        # Make change - should remove broken callback but keep good one
        state_manager.set_widget_state("test_widget", {"value": 1})

        # Good callback should still work
        assert len(good_notifications) == 1

        # Make another change - broken callback should be gone
        state_manager.set_widget_state("test_widget", {"value": 2})

        assert len(good_notifications) == 2


class TestReactiveStateManagerConnectionPooling:
    """Test database connection pooling."""

    def test_connection_pool__reuses_connections(self, temp_db_path):
        """Test that connection pool reuses connections efficiently."""
        config = DatabaseConfig(path=temp_db_path, max_connections=2)
        manager = ReactiveStateManager(temp_db_path, config)

        try:
            # Use connections multiple times
            for i in range(5):
                with manager.get_connection() as conn:
                    cursor = conn.execute("SELECT 1")
                    assert cursor.fetchone()[0] == 1

            # Check stats
            stats = manager.get_stats()
            assert stats["connection_creates"] >= 1
            assert stats["connection_reuses"] >= 1

        finally:
            manager.close()

    def test_connection_pool__concurrent_access__works_correctly(self, temp_db_path):
        """Test concurrent access to connection pool."""
        config = DatabaseConfig(path=temp_db_path, max_connections=3)
        manager = ReactiveStateManager(temp_db_path, config)

        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(10):
                    widget_id = f"worker_{worker_id}_widget_{i}"
                    manager.set_widget_state(
                        widget_id, {"worker": worker_id, "iteration": i}
                    )

                    data, version = manager.get_widget_state(widget_id)
                    results.append((widget_id, data, version))
            except Exception as e:
                errors.append(e)

        try:
            # Start multiple worker threads
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            # Check results
            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(results) == 50  # 5 workers * 10 iterations each

            # Verify all data is correct
            for widget_id, data, version in results:
                parts = widget_id.split("_")
                expected_worker = int(parts[1])
                expected_iteration = int(parts[3])

                assert data["worker"] == expected_worker
                assert data["iteration"] == expected_iteration
                assert version == 1

        finally:
            manager.close()


class TestReactiveStateManagerChangeHistory:
    """Test change history functionality."""

    def test_get_change_history__tracks_all_changes(self, state_manager):
        """Test that change history tracks all state changes."""
        widget_id = "test_widget"

        # Make several changes
        state_manager.set_widget_state(widget_id, {"value": 1})
        state_manager.set_widget_state(widget_id, {"value": 2})
        state_manager.set_widget_state(widget_id, {"value": 3})
        state_manager.delete_widget_state(widget_id)

        # Get change history
        history = state_manager.get_change_history(widget_id)

        # Should have 4 changes (1 insert + 2 updates + 1 delete)
        assert len(history) == 4

        # Check that we have all the expected change types
        change_types = [change["change_type"] for change in history]
        assert "insert" in change_types
        assert "update" in change_types
        assert "delete" in change_types

        # Check that we have the right number of each type
        assert change_types.count("insert") == 1
        assert change_types.count("update") == 2
        assert change_types.count("delete") == 1

        # Find the delete operation (should be most recent)
        delete_change = next(
            change for change in history if change["change_type"] == "delete"
        )
        assert delete_change["old_version"] == 3

        # Find the insert operation (should be first)
        insert_change = next(
            change for change in history if change["change_type"] == "insert"
        )
        assert insert_change["new_version"] == 1

        # Find the update operations
        update_changes = [
            change for change in history if change["change_type"] == "update"
        ]
        assert len(update_changes) == 2

        # Check version progression
        versions = [change.get("new_version") for change in update_changes]
        assert 2 in versions
        assert 3 in versions

    def test_get_change_history__filters_by_timestamp(self, state_manager):
        """Test filtering change history by timestamp."""
        widget_id = "test_widget"

        # Make initial change
        state_manager.set_widget_state(widget_id, {"value": 1})

        # Record timestamp
        timestamp = time.time()
        time.sleep(0.01)

        # Make more changes
        state_manager.set_widget_state(widget_id, {"value": 2})
        state_manager.set_widget_state(widget_id, {"value": 3})

        # Get recent changes only
        history = state_manager.get_change_history(widget_id, since_timestamp=timestamp)

        # Should only have 2 recent changes
        assert len(history) == 2
        assert all(change["timestamp"] > timestamp for change in history)

    def test_cleanup_old_changes__removes_old_records(self, state_manager):
        """Test cleaning up old change history."""
        widget_id = "test_widget"

        # Make some changes
        for i in range(5):
            state_manager.set_widget_state(widget_id, {"value": i})

        # Verify we have changes
        history = state_manager.get_change_history(widget_id)
        assert len(history) == 5

        # Clean up changes older than 0 hours (all of them)
        deleted_count = state_manager.cleanup_old_changes(older_than_hours=0)

        assert deleted_count == 5

        # Verify changes are gone
        history = state_manager.get_change_history(widget_id)
        assert len(history) == 0


class TestReactiveStateManagerPerformance:
    """Test performance characteristics."""

    @pytest.mark.performance
    def test_bulk_operations__high_throughput__meets_target(self, state_manager):
        """Test bulk state operations performance."""
        num_widgets = 1000

        # Measure bulk set performance
        start_time = time.perf_counter()
        for i in range(num_widgets):
            state_manager.set_widget_state(
                f"widget_{i}", {"value": i, "data": f"test_{i}"}
            )
        set_duration = time.perf_counter() - start_time

        # Measure bulk get performance
        start_time = time.perf_counter()
        for i in range(num_widgets):
            data, version = state_manager.get_widget_state(f"widget_{i}")
            assert data["value"] == i
        get_duration = time.perf_counter() - start_time

        # Performance assertions
        set_ops_per_sec = num_widgets / set_duration
        get_ops_per_sec = num_widgets / get_duration

        # Should handle at least 500 ops/sec for database operations
        assert set_ops_per_sec > 500, f"Set performance: {set_ops_per_sec:.0f} ops/sec"
        assert get_ops_per_sec > 1000, f"Get performance: {get_ops_per_sec:.0f} ops/sec"

    def test_get_stats__returns_performance_metrics(self, state_manager):
        """Test that performance statistics are collected."""
        # Perform some operations
        state_manager.set_widget_state("test", {"value": 1})
        state_manager.get_widget_state("test")
        state_manager.set_widget_state("test", {"value": 2})

        # Get stats
        stats = state_manager.get_stats()

        # Check required stats are present
        assert "total_queries" in stats
        assert "total_updates" in stats
        assert "connection_creates" in stats
        assert "connection_reuses" in stats
        assert "database_size_bytes" in stats

        # Check values make sense
        assert stats["total_queries"] >= 1
        assert stats["total_updates"] >= 2
        assert stats["database_size_bytes"] > 0


class TestDatabaseUtilities:
    """Test utility functions and configuration."""

    def test_get_db_connection__creates_manager(self, temp_db_path):
        """Test convenience function for creating database connection."""
        config = DatabaseConfig(path=temp_db_path, max_connections=2)

        manager = get_db_connection(temp_db_path, config)

        assert isinstance(manager, ReactiveStateManager)
        assert manager.db_path == temp_db_path
        assert manager.config.max_connections == 2

        manager.close()

    def test_database_config__default_values__are_reasonable(self):
        """Test that default database configuration values are reasonable."""
        config = DatabaseConfig(path="test.db")

        assert config.max_connections == 5
        assert config.timeout == 30.0
        assert config.enable_wal is True
        assert config.enable_foreign_keys is True
        assert config.cache_size == -2000  # 2MB
        assert config.temp_store == "memory"
        assert config.synchronous == "normal"
        assert config.journal_mode == "wal"
        assert config.auto_vacuum == "incremental"
