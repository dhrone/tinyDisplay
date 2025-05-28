"""
Ring Buffer implementation for high-performance time-series data storage.
"""

import time
from typing import Any, List, Optional, TypeVar, Generic
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class TimestampedValue(Generic[T]):
    """Value with timestamp"""
    timestamp: float
    value: T

class RingBuffer(Generic[T]):
    """High-performance ring buffer for time-series data"""
    
    def __init__(self, size: int):
        self.size = size
        self.buffer: List[Optional[TimestampedValue[T]]] = [None] * size
        self.head = 0
        self.count = 0
        self._lock = threading.RLock()
    
    def append(self, item: TimestampedValue[T]) -> None:
        """Add new value, evicting oldest if full"""
        with self._lock:
            self.buffer[self.head] = item
            self.head = (self.head + 1) % self.size
            if self.count < self.size:
                self.count += 1
    
    def get_latest(self, n: int = 1) -> List[TimestampedValue[T]]:
        """Get most recent N values"""
        with self._lock:
            if self.count == 0:
                return []
            
            result = []
            for i in range(min(n, self.count)):
                idx = (self.head - 1 - i) % self.size
                if self.buffer[idx] is not None:
                    result.append(self.buffer[idx])
            
            return result
    
    def get_range(self, start_time: float, end_time: float) -> List[TimestampedValue[T]]:
        """Get values within time range"""
        with self._lock:
            result = []
            for i in range(self.count):
                idx = (self.head - 1 - i) % self.size
                item = self.buffer[idx]
                if item and start_time <= item.timestamp <= end_time:
                    result.append(item)
            
            return sorted(result, key=lambda x: x.timestamp)
    
    def is_full(self) -> bool:
        """Check if buffer is full"""
        return self.count == self.size
    
    def clear(self) -> None:
        """Clear all data"""
        with self._lock:
            self.buffer = [None] * self.size
            self.head = 0
            self.count = 0

import threading
