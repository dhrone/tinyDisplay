"""SQLite integration layer for tinyDisplay reactive state management.

This module provides a high-performance SQLite integration optimized for
embedded devices with memory constraints and reactive data patterns.
"""

import sqlite3
import threading
import time
import json
import pickle
from typing import Any, Optional, Dict, List, Tuple, Union, Callable, ContextManager
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum


class SerializationFormat(Enum):
    """Data serialization formats for database storage."""

    JSON = "json"
    PICKLE = "pickle"
    BLOB = "blob"


@dataclass
class DatabaseConfig:
    """Configuration for database connection and behavior."""

    path: Union[str, Path]
    max_connections: int = 5
    timeout: float = 30.0
    enable_wal: bool = True
    enable_foreign_keys: bool = True
    cache_size: int = -2000  # 2MB cache
    temp_store: str = "memory"
    synchronous: str = "normal"
    journal_mode: str = "wal"
    auto_vacuum: str = "incremental"


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


class ConnectionPoolError(DatabaseError):
    """Raised when connection pool operations fail."""

    pass


class SchemaError(DatabaseError):
    """Raised when database schema operations fail."""

    pass


class ReactiveStateManager:
    """Manages reactive state storage and change notifications.

    This class provides the core reactive state management functionality
    for tinyDisplay, storing widget states and managing change notifications
    through SQLite triggers and callbacks.
    """

    def __init__(
        self, db_path: Union[str, Path], config: Optional[DatabaseConfig] = None
    ):
        """Initialize the reactive state manager.

        Args:
            db_path: Path to SQLite database file
            config: Database configuration options
        """
        self.db_path = Path(db_path)
        self.config = config or DatabaseConfig(path=db_path)

        # Connection pool
        self._pool: List[sqlite3.Connection] = []
        self._pool_lock = threading.Lock()
        self._pool_condition = threading.Condition(self._pool_lock)

        # Change notification system
        self._change_callbacks: Dict[str, List[Callable]] = {}
        self._callback_lock = threading.RLock()

        # Performance tracking
        self._stats = {
            "total_queries": 0,
            "total_updates": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "connection_reuses": 0,
            "connection_creates": 0,
        }
        self._stats_lock = threading.Lock()

        # Initialize database
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize database schema and configuration."""
        # Create database directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create initial connection and schema
        with self.get_connection() as conn:
            self._create_schema(conn)
            self._configure_database(conn)

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """Create database schema for reactive state management."""
        schema_sql = """
        -- Widget state storage
        CREATE TABLE IF NOT EXISTS widget_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            widget_id TEXT NOT NULL,
            state_data BLOB NOT NULL,
            serialization_format TEXT NOT NULL DEFAULT 'json',
            timestamp REAL NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            UNIQUE(widget_id)
        );
        
        -- Index for fast widget lookups
        CREATE INDEX IF NOT EXISTS idx_widget_states_widget_id 
        ON widget_states(widget_id);
        
        -- Index for timestamp-based queries
        CREATE INDEX IF NOT EXISTS idx_widget_states_timestamp 
        ON widget_states(timestamp);
        
        -- Change log for reactive notifications
        CREATE TABLE IF NOT EXISTS state_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            widget_id TEXT NOT NULL,
            change_type TEXT NOT NULL, -- 'insert', 'update', 'delete'
            old_version INTEGER,
            new_version INTEGER,
            timestamp REAL NOT NULL,
            change_data BLOB
        );
        
        -- Index for change log queries
        CREATE INDEX IF NOT EXISTS idx_state_changes_widget_id 
        ON state_changes(widget_id);
        
        CREATE INDEX IF NOT EXISTS idx_state_changes_timestamp 
        ON state_changes(timestamp);
        
        -- Reactive bindings table
        CREATE TABLE IF NOT EXISTS reactive_bindings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_widget_id TEXT NOT NULL,
            target_widget_id TEXT NOT NULL,
            binding_expression TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            created_at REAL NOT NULL,
            UNIQUE(source_widget_id, target_widget_id)
        );
        
        -- Performance metrics table
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            metric_value REAL NOT NULL,
            timestamp REAL NOT NULL,
            metadata TEXT
        );
        
        -- Create triggers for change notifications
        CREATE TRIGGER IF NOT EXISTS widget_state_insert_trigger
        AFTER INSERT ON widget_states
        BEGIN
            INSERT INTO state_changes (
                widget_id, change_type, new_version, timestamp, change_data
            ) VALUES (
                NEW.widget_id, 'insert', NEW.version, NEW.timestamp, NEW.state_data
            );
        END;
        
        CREATE TRIGGER IF NOT EXISTS widget_state_update_trigger
        AFTER UPDATE ON widget_states
        BEGIN
            INSERT INTO state_changes (
                widget_id, change_type, old_version, new_version, timestamp, change_data
            ) VALUES (
                NEW.widget_id, 'update', OLD.version, NEW.version, NEW.timestamp, NEW.state_data
            );
        END;
        
        CREATE TRIGGER IF NOT EXISTS widget_state_delete_trigger
        AFTER DELETE ON widget_states
        BEGIN
            INSERT INTO state_changes (
                widget_id, change_type, old_version, timestamp, change_data
            ) VALUES (
                OLD.widget_id, 'delete', OLD.version, unixepoch('subsec'), OLD.state_data
            );
        END;
        """

        conn.executescript(schema_sql)
        conn.commit()

    def _configure_database(self, conn: sqlite3.Connection) -> None:
        """Configure SQLite for optimal performance on embedded devices."""
        config_sql = f"""
        PRAGMA journal_mode = {self.config.journal_mode};
        PRAGMA synchronous = {self.config.synchronous};
        PRAGMA cache_size = {self.config.cache_size};
        PRAGMA temp_store = {self.config.temp_store};
        PRAGMA foreign_keys = {'ON' if self.config.enable_foreign_keys else 'OFF'};
        PRAGMA auto_vacuum = {self.config.auto_vacuum};
        PRAGMA optimize;
        """

        conn.executescript(config_sql)
        conn.commit()

    @contextmanager
    def get_connection(self) -> ContextManager[sqlite3.Connection]:
        """Get a database connection from the pool.

        Yields:
            SQLite connection with proper configuration
        """
        conn = None
        try:
            # Try to get connection from pool
            with self._pool_condition:
                while not self._pool and len(self._pool) < self.config.max_connections:
                    # Create new connection
                    conn = self._create_connection()
                    with self._stats_lock:
                        self._stats["connection_creates"] += 1
                    break

                if self._pool:
                    conn = self._pool.pop()
                    with self._stats_lock:
                        self._stats["connection_reuses"] += 1

            if conn is None:
                # Wait for available connection
                with self._pool_condition:
                    while not self._pool:
                        if not self._pool_condition.wait(timeout=self.config.timeout):
                            raise ConnectionPoolError(
                                "Timeout waiting for database connection"
                            )
                    conn = self._pool.pop()

            yield conn

        finally:
            # Return connection to pool
            if conn is not None:
                try:
                    # Reset connection state
                    conn.rollback()

                    # Return to pool
                    with self._pool_condition:
                        if len(self._pool) < self.config.max_connections:
                            self._pool.append(conn)
                            self._pool_condition.notify()
                        else:
                            conn.close()
                except Exception:
                    # Connection is bad, close it
                    try:
                        conn.close()
                    except Exception:
                        pass

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with proper configuration."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=self.config.timeout,
            check_same_thread=False,
        )

        # Configure connection
        conn.row_factory = sqlite3.Row
        self._configure_database(conn)

        return conn

    def set_widget_state(
        self,
        widget_id: str,
        state_data: Any,
        serialization_format: SerializationFormat = SerializationFormat.JSON,
    ) -> int:
        """Set widget state with automatic versioning and change notification.

        Args:
            widget_id: Unique widget identifier
            state_data: Widget state data to store
            serialization_format: How to serialize the data

        Returns:
            New version number for the widget state
        """
        timestamp = time.time()

        # Serialize data
        if serialization_format == SerializationFormat.JSON:
            serialized_data = json.dumps(state_data).encode("utf-8")
        elif serialization_format == SerializationFormat.PICKLE:
            serialized_data = pickle.dumps(state_data)
        else:  # BLOB
            serialized_data = (
                state_data
                if isinstance(state_data, bytes)
                else str(state_data).encode("utf-8")
            )

        with self.get_connection() as conn:
            # Check if widget already exists
            cursor = conn.execute(
                "SELECT version FROM widget_states WHERE widget_id = ?", (widget_id,)
            )
            existing = cursor.fetchone()

            if existing is None:
                # Insert new widget state
                conn.execute(
                    """
                    INSERT INTO widget_states (
                        widget_id, state_data, serialization_format, timestamp, version
                    ) VALUES (?, ?, ?, ?, 1)
                """,
                    (widget_id, serialized_data, serialization_format.value, timestamp),
                )
                new_version = 1
            else:
                # Update existing widget state
                new_version = existing["version"] + 1
                conn.execute(
                    """
                    UPDATE widget_states 
                    SET state_data = ?, serialization_format = ?, timestamp = ?, version = ?
                    WHERE widget_id = ?
                """,
                    (
                        serialized_data,
                        serialization_format.value,
                        timestamp,
                        new_version,
                        widget_id,
                    ),
                )

            conn.commit()

            with self._stats_lock:
                self._stats["total_updates"] += 1

        # Trigger change notifications
        self._notify_change(widget_id, "update", state_data)

        return new_version

    def get_widget_state(
        self,
        widget_id: str,
        default: Any = None,
    ) -> Tuple[Any, int]:
        """Get widget state and version.

        Args:
            widget_id: Unique widget identifier
            default: Default value if widget not found

        Returns:
            Tuple of (state_data, version) or (default, 0) if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT state_data, serialization_format, version 
                FROM widget_states 
                WHERE widget_id = ?
            """,
                (widget_id,),
            )

            row = cursor.fetchone()

            with self._stats_lock:
                self._stats["total_queries"] += 1

        if row is None:
            return default, 0

        # Deserialize data
        serialization_format = SerializationFormat(row["serialization_format"])

        if serialization_format == SerializationFormat.JSON:
            state_data = json.loads(row["state_data"].decode("utf-8"))
        elif serialization_format == SerializationFormat.PICKLE:
            state_data = pickle.loads(row["state_data"])
        else:  # BLOB
            state_data = row["state_data"]

        return state_data, row["version"]

    def delete_widget_state(self, widget_id: str) -> bool:
        """Delete widget state.

        Args:
            widget_id: Unique widget identifier

        Returns:
            True if widget was deleted, False if not found
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM widget_states WHERE widget_id = ?", (widget_id,)
            )
            conn.commit()

            deleted = cursor.rowcount > 0

            with self._stats_lock:
                self._stats["total_updates"] += 1

        if deleted:
            self._notify_change(widget_id, "delete", None)

        return deleted

    def get_widget_states(
        self,
        widget_ids: Optional[List[str]] = None,
        since_timestamp: Optional[float] = None,
    ) -> Dict[str, Tuple[Any, int]]:
        """Get multiple widget states efficiently.

        Args:
            widget_ids: List of widget IDs to fetch (None = all)
            since_timestamp: Only return states modified since this time

        Returns:
            Dictionary mapping widget_id to (state_data, version)
        """
        with self.get_connection() as conn:
            # Build base query
            if widget_ids is not None:
                placeholders = ",".join("?" * len(widget_ids))
                sql = f"""
                    SELECT widget_id, state_data, serialization_format, version
                    FROM widget_states 
                    WHERE widget_id IN ({placeholders})
                """
                params = widget_ids
            else:
                sql = """
                    SELECT widget_id, state_data, serialization_format, version
                    FROM widget_states
                """
                params = []

            # Add timestamp filter if needed
            if since_timestamp is not None:
                if widget_ids is not None:
                    sql += " AND timestamp > ?"
                else:
                    sql += " WHERE timestamp > ?"
                params.append(since_timestamp)

            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

            with self._stats_lock:
                self._stats["total_queries"] += 1

        result = {}
        for row in rows:
            # Deserialize data
            serialization_format = SerializationFormat(row["serialization_format"])

            if serialization_format == SerializationFormat.JSON:
                state_data = json.loads(row["state_data"].decode("utf-8"))
            elif serialization_format == SerializationFormat.PICKLE:
                state_data = pickle.loads(row["state_data"])
            else:  # BLOB
                state_data = row["state_data"]

            result[row["widget_id"]] = (state_data, row["version"])

        return result

    def register_change_callback(
        self,
        widget_id: str,
        callback: Callable[[str, str, Any], None],
    ) -> None:
        """Register callback for widget state changes.

        Args:
            widget_id: Widget ID to monitor (use '*' for all widgets)
            callback: Function called with (widget_id, change_type, state_data)
        """
        with self._callback_lock:
            if widget_id not in self._change_callbacks:
                self._change_callbacks[widget_id] = []
            self._change_callbacks[widget_id].append(callback)

    def unregister_change_callback(
        self,
        widget_id: str,
        callback: Callable[[str, str, Any], None],
    ) -> bool:
        """Unregister change callback.

        Args:
            widget_id: Widget ID that was being monitored
            callback: Callback function to remove

        Returns:
            True if callback was found and removed
        """
        with self._callback_lock:
            if widget_id in self._change_callbacks:
                try:
                    self._change_callbacks[widget_id].remove(callback)
                    if not self._change_callbacks[widget_id]:
                        del self._change_callbacks[widget_id]
                    return True
                except ValueError:
                    pass
        return False

    def _notify_change(self, widget_id: str, change_type: str, state_data: Any) -> None:
        """Notify registered callbacks of state changes."""
        with self._callback_lock:
            # Notify specific widget callbacks
            if widget_id in self._change_callbacks:
                for callback in self._change_callbacks[widget_id][
                    :
                ]:  # Copy to avoid modification during iteration
                    try:
                        callback(widget_id, change_type, state_data)
                    except Exception:
                        # Remove broken callbacks
                        try:
                            self._change_callbacks[widget_id].remove(callback)
                        except ValueError:
                            pass

            # Notify wildcard callbacks
            if "*" in self._change_callbacks:
                for callback in self._change_callbacks["*"][:]:
                    try:
                        callback(widget_id, change_type, state_data)
                    except Exception:
                        try:
                            self._change_callbacks["*"].remove(callback)
                        except ValueError:
                            pass

    def get_change_history(
        self,
        widget_id: Optional[str] = None,
        since_timestamp: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get change history for debugging and analysis.

        Args:
            widget_id: Widget ID to filter by (None = all widgets)
            since_timestamp: Only return changes since this time
            limit: Maximum number of changes to return

        Returns:
            List of change records
        """
        with self.get_connection() as conn:
            sql = """
                SELECT widget_id, change_type, old_version, new_version, 
                       timestamp, change_data
                FROM state_changes
            """
            params = []

            conditions = []
            if widget_id is not None:
                conditions.append("widget_id = ?")
                params.append(widget_id)

            if since_timestamp is not None:
                conditions.append("timestamp > ?")
                params.append(since_timestamp)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def cleanup_old_changes(self, older_than_hours: int = 24) -> int:
        """Clean up old change history to save space.

        Args:
            older_than_hours: Remove changes older than this many hours

        Returns:
            Number of records deleted
        """
        cutoff_timestamp = time.time() - (older_than_hours * 3600)

        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM state_changes WHERE timestamp < ?", (cutoff_timestamp,)
            )
            conn.commit()

            # Run incremental vacuum to reclaim space
            conn.execute("PRAGMA incremental_vacuum")

            return cursor.rowcount

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics.

        Returns:
            Dictionary of performance metrics
        """
        with self._stats_lock:
            stats = self._stats.copy()

        # Add database-specific stats
        with self.get_connection() as conn:
            cursor = conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]

            cursor = conn.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]

            stats.update(
                {
                    "database_size_bytes": page_count * page_size,
                    "database_pages": page_count,
                    "page_size": page_size,
                }
            )

        return stats

    def close(self) -> None:
        """Close all database connections and cleanup resources."""
        with self._pool_condition:
            while self._pool:
                conn = self._pool.pop()
                try:
                    conn.close()
                except Exception:
                    pass
            self._pool_condition.notify_all()

        # Clear callbacks
        with self._callback_lock:
            self._change_callbacks.clear()


# Convenience function for getting database connection
def get_db_connection(
    db_path: Union[str, Path], config: Optional[DatabaseConfig] = None
) -> ReactiveStateManager:
    """Get a reactive state manager instance.

    Args:
        db_path: Path to SQLite database file
        config: Database configuration options

    Returns:
        ReactiveStateManager instance
    """
    return ReactiveStateManager(db_path, config)
