"""
Data Manager - Central coordination for data streams and storage.
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from collections import defaultdict

from .ring_buffer import RingBuffer, TimestampedValue
from .sqlite_storage import SQLiteStorage

@dataclass
class DataStreamConfig:
    """Configuration for a data stream"""
    buffer_size: int = 1000
    data_type: type = Any
    persistence: bool = True
    compression: bool = False

class DataManager:
    """Central data management system"""
    
    def __init__(self):
        self._ring_buffers: Dict[str, RingBuffer] = {}
        self._sqlite_store = SQLiteStorage()
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.RLock()
        
        # Initialize data streams from analysis

    
    def register_data_stream(self, stream_id: str, config: DataStreamConfig):
        """Register a new data stream"""
        with self._lock:
            self._ring_buffers[stream_id] = RingBuffer(config.buffer_size)
            
            if config.persistence:
                self._sqlite_store.create_stream_table(stream_id, config.data_type)
    
    def update_data(self, stream_id: str, value: Any, timestamp: Optional[float] = None):
        """Update data in stream"""
        if timestamp is None:
            timestamp = time.time()
        
        timestamped_value = TimestampedValue(timestamp, value)
        
        with self._lock:
            # Store in ring buffer
            if stream_id in self._ring_buffers:
                self._ring_buffers[stream_id].append(timestamped_value)
            
            # Store in SQLite (background)
            self._sqlite_store.store_value_async(stream_id, timestamped_value)
            
            # Notify subscribers
            for callback in self._subscribers[stream_id]:
                try:
                    callback(stream_id, value)
                except Exception as e:
                    print(f"Error in subscriber callback: {e}")
    
    def get_current_value(self, stream_id: str) -> Any:
        """Get latest value for stream"""
        with self._lock:
            if stream_id in self._ring_buffers:
                latest = self._ring_buffers[stream_id].get_latest(1)
                if latest:
                    return latest[0].value
            return None
    
    def get_history(self, stream_id: str, count: int = 10) -> List[TimestampedValue]:
        """Get recent history for stream"""
        with self._lock:
            if stream_id in self._ring_buffers:
                return self._ring_buffers[stream_id].get_latest(count)
            return []
    
    def subscribe(self, stream_id: str, callback: Callable[[str, Any], None]) -> str:
        """Subscribe to data updates"""
        subscription_id = f"{stream_id}_{len(self._subscribers[stream_id])}"
        self._subscribers[stream_id].append(callback)
        return subscription_id
    
    def unsubscribe(self, stream_id: str, callback: Callable):
        """Unsubscribe from data updates"""
        if stream_id in self._subscribers:
            try:
                self._subscribers[stream_id].remove(callback)
            except ValueError:
                pass
    
    def get_ring_buffer(self, stream_id: str) -> Optional[RingBuffer]:
        """Get ring buffer for stream"""
        return self._ring_buffers.get(stream_id)
