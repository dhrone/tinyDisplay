#!/usr/bin/env python3
"""
Data Stream Integration

Provides integration between reactive system and data streams (ring buffer and SQLite),
enabling real-time data binding with persistence and stream processing capabilities.
"""

from typing import Dict, List, Set, Any, Callable, Optional, Union, Tuple
from dataclasses import dataclass, field
import threading
import time
import json
import sqlite3
from collections import deque
from enum import Enum
import weakref

from .reactive import ReactiveValue, ReactiveChange, ReactiveValueType
from .ring_buffer import RingBuffer, BufferEntry
from .dependencies import get_dependency_graph, DependencyType


class StreamType(Enum):
    """Types of data streams."""
    RING_BUFFER = "ring_buffer"
    SQLITE = "sqlite"
    HYBRID = "hybrid"  # Both ring buffer and SQLite


class StreamProcessingMode(Enum):
    """Stream processing modes."""
    REAL_TIME = "real_time"      # Process immediately
    BATCHED = "batched"          # Process in batches
    THROTTLED = "throttled"      # Throttle updates
    DEBOUNCED = "debounced"      # Debounce rapid changes


@dataclass
class StreamConfig:
    """Configuration for data streams."""
    stream_type: StreamType
    processing_mode: StreamProcessingMode = StreamProcessingMode.REAL_TIME
    buffer_size: int = 1000
    batch_size: int = 10
    batch_interval: float = 0.1  # seconds
    throttle_interval: float = 0.05  # seconds
    debounce_delay: float = 0.1  # seconds
    persist_data: bool = True
    transform_function: Optional[Callable[[Any], Any]] = None
    filter_function: Optional[Callable[[Any], bool]] = None
    error_handler: Optional[Callable[[Exception], None]] = None


@dataclass
class StreamStats:
    """Statistics for stream processing."""
    messages_received: int = 0
    messages_processed: int = 0
    messages_filtered: int = 0
    messages_errored: int = 0
    bytes_processed: int = 0
    processing_time: float = 0.0
    last_update_time: float = 0.0
    buffer_utilization: float = 0.0


class ReactiveDataStream:
    """Integration between reactive system and data streams."""
    
    def __init__(self, stream_id: str, config: StreamConfig):
        self.stream_id = stream_id
        self.config = config
        self._reactive_value: ReactiveValue = ReactiveValue(None, reactive_id=stream_id)
        self._ring_buffer: Optional[RingBuffer] = None
        self._sqlite_connection: Optional[sqlite3.Connection] = None
        self._sqlite_table: Optional[str] = None
        
        # Processing state
        self._processing_queue: deque = deque(maxlen=config.buffer_size)
        self._batch_queue: List[Any] = []
        self._last_process_time = 0.0
        self._last_throttle_time = 0.0
        self._debounce_timer: Optional[threading.Timer] = None
        
        # Statistics and monitoring
        self._stats = StreamStats()
        self._subscribers: Set[Callable[[Any], None]] = set()
        self._error_subscribers: Set[Callable[[Exception], None]] = set()
        
        # Thread safety
        self._lock = threading.RLock()
        self._processing_thread: Optional[threading.Thread] = None
        self._stop_processing = threading.Event()
        
        # Initialize based on stream type
        self._initialize_stream()
        
    def _initialize_stream(self) -> None:
        """Initialize the stream based on configuration."""
        if self.config.stream_type in (StreamType.RING_BUFFER, StreamType.HYBRID):
            self._ring_buffer = RingBuffer(capacity=self.config.buffer_size)
            
        if self.config.stream_type in (StreamType.SQLITE, StreamType.HYBRID):
            self._initialize_sqlite()
            
        # Start processing thread for batched/throttled modes
        if self.config.processing_mode in (StreamProcessingMode.BATCHED, 
                                         StreamProcessingMode.THROTTLED):
            self._start_processing_thread()
            
    def _initialize_sqlite(self) -> None:
        """Initialize SQLite connection and table."""
        try:
            # Use in-memory database for now, can be configured later
            self._sqlite_connection = sqlite3.connect(":memory:", check_same_thread=False)
            self._sqlite_table = f"stream_{self.stream_id.replace('-', '_')}"
            
            # Create table for stream data
            self._sqlite_connection.execute(f'''
                CREATE TABLE IF NOT EXISTS {self._sqlite_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    data TEXT,
                    data_type TEXT,
                    metadata TEXT
                )
            ''')
            self._sqlite_connection.commit()
            
        except Exception as e:
            if self.config.error_handler:
                self.config.error_handler(e)
            else:
                print(f"Error initializing SQLite for stream {self.stream_id}: {e}")
                
    def connect_ring_buffer(self, ring_buffer: RingBuffer) -> None:
        """Connect to an external ring buffer."""
        with self._lock:
            self._ring_buffer = ring_buffer
            ring_buffer.add_subscriber(self._on_ring_buffer_data)
            
    def connect_sqlite(self, db_path: str, table_name: Optional[str] = None) -> None:
        """Connect to an external SQLite database."""
        with self._lock:
            try:
                if self._sqlite_connection:
                    self._sqlite_connection.close()
                    
                self._sqlite_connection = sqlite3.connect(db_path, check_same_thread=False)
                self._sqlite_table = table_name or f"stream_{self.stream_id.replace('-', '_')}"
                
                # Create table if not exists
                self._sqlite_connection.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self._sqlite_table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL,
                        data TEXT,
                        data_type TEXT,
                        metadata TEXT
                    )
                ''')
                self._sqlite_connection.commit()
                
            except Exception as e:
                if self.config.error_handler:
                    self.config.error_handler(e)
                else:
                    print(f"Error connecting to SQLite for stream {self.stream_id}: {e}")
                    
    def push_data(self, data: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Push data to the stream."""
        with self._lock:
            try:
                # Apply filter if configured
                if self.config.filter_function and not self.config.filter_function(data):
                    self._stats.messages_filtered += 1
                    return
                    
                # Apply transformation if configured
                if self.config.transform_function:
                    data = self.config.transform_function(data)
                    
                # Update statistics
                self._stats.messages_received += 1
                if isinstance(data, (str, bytes)):
                    self._stats.bytes_processed += len(data)
                    
                # Process based on mode
                if self.config.processing_mode == StreamProcessingMode.REAL_TIME:
                    self._process_data_immediate(data, metadata)
                elif self.config.processing_mode == StreamProcessingMode.BATCHED:
                    self._queue_for_batch(data, metadata)
                elif self.config.processing_mode == StreamProcessingMode.THROTTLED:
                    self._queue_for_throttle(data, metadata)
                elif self.config.processing_mode == StreamProcessingMode.DEBOUNCED:
                    self._queue_for_debounce(data, metadata)
                    
            except Exception as e:
                self._stats.messages_errored += 1
                if self.config.error_handler:
                    self.config.error_handler(e)
                else:
                    print(f"Error processing data in stream {self.stream_id}: {e}")
                    
    def _process_data_immediate(self, data: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Process data immediately."""
        start_time = time.time()
        
        # Store in ring buffer
        if self._ring_buffer:
            entry = BufferEntry(
                timestamp=start_time,
                data=data,
                metadata=metadata or {}
            )
            self._ring_buffer.add_entry(entry)
            
        # Store in SQLite
        if self._sqlite_connection and self.config.persist_data:
            self._persist_to_sqlite(data, metadata, start_time)
            
        # Update reactive value
        self._reactive_value.value = data
        
        # Notify subscribers
        for subscriber in self._subscribers.copy():
            try:
                subscriber(data)
            except Exception as e:
                if self.config.error_handler:
                    self.config.error_handler(e)
                    
        # Update statistics
        self._stats.messages_processed += 1
        self._stats.processing_time += time.time() - start_time
        self._stats.last_update_time = start_time
        
    def _queue_for_batch(self, data: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Queue data for batch processing."""
        self._batch_queue.append((data, metadata, time.time()))
        
        if len(self._batch_queue) >= self.config.batch_size:
            self._process_batch()
            
    def _queue_for_throttle(self, data: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Queue data for throttled processing."""
        current_time = time.time()
        
        # Add to processing queue
        self._processing_queue.append((data, metadata, current_time))
        
        # Check if enough time has passed since last throttle
        if current_time - self._last_throttle_time >= self.config.throttle_interval:
            if self._processing_queue:
                # Process the most recent data
                latest_data, latest_metadata, _ = self._processing_queue[-1]
                self._processing_queue.clear()
                self._process_data_immediate(latest_data, latest_metadata)
                self._last_throttle_time = current_time
                
    def _queue_for_debounce(self, data: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Queue data for debounced processing."""
        # Cancel existing debounce timer
        if self._debounce_timer:
            self._debounce_timer.cancel()
            
        # Store the latest data
        self._processing_queue.clear()
        self._processing_queue.append((data, metadata, time.time()))
        
        # Start new debounce timer
        self._debounce_timer = threading.Timer(
            self.config.debounce_delay,
            self._process_debounced_data
        )
        self._debounce_timer.start()
        
    def _process_debounced_data(self) -> None:
        """Process debounced data."""
        if self._processing_queue:
            data, metadata, _ = self._processing_queue[-1]
            self._processing_queue.clear()
            self._process_data_immediate(data, metadata)
            
    def _process_batch(self) -> None:
        """Process a batch of data."""
        if not self._batch_queue:
            return
            
        start_time = time.time()
        batch = self._batch_queue.copy()
        self._batch_queue.clear()
        
        try:
            # Process each item in batch
            for data, metadata, timestamp in batch:
                # Store in ring buffer
                if self._ring_buffer:
                    entry = BufferEntry(
                        timestamp=timestamp,
                        data=data,
                        metadata=metadata or {}
                    )
                    self._ring_buffer.add_entry(entry)
                    
                # Store in SQLite
                if self._sqlite_connection and self.config.persist_data:
                    self._persist_to_sqlite(data, metadata, timestamp)
                    
            # Update reactive value with latest data
            if batch:
                latest_data, _, _ = batch[-1]
                self._reactive_value.value = latest_data
                
                # Notify subscribers with latest data
                for subscriber in self._subscribers.copy():
                    try:
                        subscriber(latest_data)
                    except Exception as e:
                        if self.config.error_handler:
                            self.config.error_handler(e)
                            
            # Update statistics
            self._stats.messages_processed += len(batch)
            self._stats.processing_time += time.time() - start_time
            self._stats.last_update_time = start_time
            
        except Exception as e:
            self._stats.messages_errored += len(batch)
            if self.config.error_handler:
                self.config.error_handler(e)
                
    def _persist_to_sqlite(self, data: Any, metadata: Optional[Dict[str, Any]], 
                          timestamp: float) -> None:
        """Persist data to SQLite."""
        try:
            data_str = json.dumps(data) if not isinstance(data, str) else data
            data_type = type(data).__name__
            metadata_str = json.dumps(metadata) if metadata else None
            
            self._sqlite_connection.execute(
                f"INSERT INTO {self._sqlite_table} (timestamp, data, data_type, metadata) VALUES (?, ?, ?, ?)",
                (timestamp, data_str, data_type, metadata_str)
            )
            self._sqlite_connection.commit()
            
        except Exception as e:
            if self.config.error_handler:
                self.config.error_handler(e)
                
    def _on_ring_buffer_data(self, entry: BufferEntry) -> None:
        """Handle data from ring buffer."""
        self.push_data(entry.data, entry.metadata)
        
    def _start_processing_thread(self) -> None:
        """Start background processing thread."""
        if self._processing_thread is None or not self._processing_thread.is_alive():
            self._stop_processing.clear()
            self._processing_thread = threading.Thread(
                target=self._processing_loop,
                name=f"StreamProcessor-{self.stream_id}"
            )
            self._processing_thread.daemon = True
            self._processing_thread.start()
            
    def _processing_loop(self) -> None:
        """Background processing loop for batched/throttled modes."""
        while not self._stop_processing.is_set():
            try:
                if self.config.processing_mode == StreamProcessingMode.BATCHED:
                    if self._batch_queue:
                        time.sleep(self.config.batch_interval)
                        if self._batch_queue:  # Check again after sleep
                            self._process_batch()
                            
                elif self.config.processing_mode == StreamProcessingMode.THROTTLED:
                    if self._processing_queue:
                        current_time = time.time()
                        if current_time - self._last_throttle_time >= self.config.throttle_interval:
                            latest_data, latest_metadata, _ = self._processing_queue[-1]
                            self._processing_queue.clear()
                            self._process_data_immediate(latest_data, latest_metadata)
                            self._last_throttle_time = current_time
                            
                time.sleep(0.01)  # Small sleep to prevent busy waiting
                
            except Exception as e:
                if self.config.error_handler:
                    self.config.error_handler(e)
                    
    def get_reactive_value(self) -> ReactiveValue:
        """Get the reactive value for this stream."""
        return self._reactive_value
        
    def subscribe(self, callback: Callable[[Any], None]) -> None:
        """Subscribe to stream updates."""
        with self._lock:
            self._subscribers.add(callback)
            
    def unsubscribe(self, callback: Callable[[Any], None]) -> None:
        """Unsubscribe from stream updates."""
        with self._lock:
            self._subscribers.discard(callback)
            
    def subscribe_errors(self, callback: Callable[[Exception], None]) -> None:
        """Subscribe to stream errors."""
        with self._lock:
            self._error_subscribers.add(callback)
            
    def unsubscribe_errors(self, callback: Callable[[Exception], None]) -> None:
        """Unsubscribe from stream errors."""
        with self._lock:
            self._error_subscribers.discard(callback)
            
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent history from ring buffer."""
        if self._ring_buffer:
            entries = self._ring_buffer.get_recent_entries(limit)
            return [
                {
                    'timestamp': entry.timestamp,
                    'data': entry.data,
                    'metadata': entry.metadata
                }
                for entry in entries
            ]
        return []
        
    def query_sqlite(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Query SQLite data."""
        if not self._sqlite_connection:
            return []
            
        try:
            cursor = self._sqlite_connection.execute(query, params or ())
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        except Exception as e:
            if self.config.error_handler:
                self.config.error_handler(e)
            return []
            
    def get_stats(self) -> StreamStats:
        """Get stream statistics."""
        with self._lock:
            # Update buffer utilization
            if self._ring_buffer:
                self._stats.buffer_utilization = len(self._ring_buffer) / self._ring_buffer.capacity
            else:
                self._stats.buffer_utilization = len(self._processing_queue) / self.config.buffer_size
                
            return self._stats
            
    def reset_stats(self) -> None:
        """Reset stream statistics."""
        with self._lock:
            self._stats = StreamStats()
            
    def stop(self) -> None:
        """Stop the stream processing."""
        with self._lock:
            self._stop_processing.set()
            
            if self._debounce_timer:
                self._debounce_timer.cancel()
                
            if self._processing_thread and self._processing_thread.is_alive():
                self._processing_thread.join(timeout=1.0)
                
            if self._sqlite_connection:
                self._sqlite_connection.close()
                self._sqlite_connection = None
                
    def __repr__(self) -> str:
        return f"ReactiveDataStream(id={self.stream_id}, type={self.config.stream_type.value})"


class StreamManager:
    """Manages multiple reactive data streams."""
    
    def __init__(self):
        self._streams: Dict[str, ReactiveDataStream] = {}
        self._lock = threading.RLock()
        
    def create_stream(self, stream_id: str, config: StreamConfig) -> ReactiveDataStream:
        """Create a new reactive data stream."""
        with self._lock:
            if stream_id in self._streams:
                raise ValueError(f"Stream {stream_id} already exists")
                
            stream = ReactiveDataStream(stream_id, config)
            self._streams[stream_id] = stream
            
            # Register with dependency graph
            dependency_graph = get_dependency_graph()
            dependency_graph.add_node(stream_id, stream.get_reactive_value())
            
            return stream
            
    def get_stream(self, stream_id: str) -> Optional[ReactiveDataStream]:
        """Get a stream by ID."""
        return self._streams.get(stream_id)
        
    def remove_stream(self, stream_id: str) -> bool:
        """Remove a stream."""
        with self._lock:
            if stream_id in self._streams:
                stream = self._streams[stream_id]
                stream.stop()
                del self._streams[stream_id]
                
                # Remove from dependency graph
                dependency_graph = get_dependency_graph()
                dependency_graph.remove_node(stream_id)
                
                return True
            return False
            
    def list_streams(self) -> List[str]:
        """List all stream IDs."""
        return list(self._streams.keys())
        
    def get_all_stats(self) -> Dict[str, StreamStats]:
        """Get statistics for all streams."""
        return {
            stream_id: stream.get_stats()
            for stream_id, stream in self._streams.items()
        }
        
    def stop_all(self) -> None:
        """Stop all streams."""
        with self._lock:
            for stream in self._streams.values():
                stream.stop()
            self._streams.clear()
            
    def __repr__(self) -> str:
        return f"StreamManager(streams={len(self._streams)})"


# Global stream manager instance
_global_stream_manager: Optional[StreamManager] = None


def get_stream_manager() -> StreamManager:
    """Get the global stream manager instance."""
    global _global_stream_manager
    if _global_stream_manager is None:
        _global_stream_manager = StreamManager()
    return _global_stream_manager


def create_ring_buffer_stream(stream_id: str, buffer_size: int = 1000,
                             processing_mode: StreamProcessingMode = StreamProcessingMode.REAL_TIME) -> ReactiveDataStream:
    """Create a ring buffer stream with default configuration."""
    config = StreamConfig(
        stream_type=StreamType.RING_BUFFER,
        processing_mode=processing_mode,
        buffer_size=buffer_size
    )
    return get_stream_manager().create_stream(stream_id, config)


def create_sqlite_stream(stream_id: str, db_path: str = ":memory:",
                        processing_mode: StreamProcessingMode = StreamProcessingMode.REAL_TIME) -> ReactiveDataStream:
    """Create a SQLite stream with default configuration."""
    config = StreamConfig(
        stream_type=StreamType.SQLITE,
        processing_mode=processing_mode,
        persist_data=True
    )
    stream = get_stream_manager().create_stream(stream_id, config)
    if db_path != ":memory:":
        stream.connect_sqlite(db_path)
    return stream


def create_hybrid_stream(stream_id: str, buffer_size: int = 1000, db_path: str = ":memory:",
                        processing_mode: StreamProcessingMode = StreamProcessingMode.REAL_TIME) -> ReactiveDataStream:
    """Create a hybrid stream with both ring buffer and SQLite."""
    config = StreamConfig(
        stream_type=StreamType.HYBRID,
        processing_mode=processing_mode,
        buffer_size=buffer_size,
        persist_data=True
    )
    stream = get_stream_manager().create_stream(stream_id, config)
    if db_path != ":memory:":
        stream.connect_sqlite(db_path)
    return stream 