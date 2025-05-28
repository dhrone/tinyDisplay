"""High-performance ring buffer implementation for tinyDisplay.

This module provides a thread-safe, memory-efficient circular buffer
for real-time data streams in embedded environments.
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional


class BufferOverflowPolicy(Enum):
    """Policy for handling buffer overflow conditions."""

    OVERWRITE = "overwrite"  # Overwrite oldest data (default)
    BLOCK = "block"  # Block until space available
    DROP = "drop"  # Drop new data


@dataclass
class BufferEntry:
    """Single entry in the ring buffer."""

    timestamp: float
    value: Any
    data_type: str
    sequence_id: int


class RingBufferError(Exception):
    """Base exception for ring buffer operations."""

    pass


class BufferFullError(RingBufferError):
    """Raised when buffer is full and cannot accept new data."""

    pass


class BufferEmptyError(RingBufferError):
    """Raised when attempting to read from empty buffer."""

    pass


class RingBuffer:
    """Thread-safe circular buffer for high-performance data streams.

    Optimized for embedded devices with memory constraints. Supports
    multiple data types and configurable overflow policies.

    Args:
        size: Maximum number of entries in the buffer
        overflow_policy: How to handle buffer overflow
        enable_stats: Whether to collect performance statistics

    Example:
        >>> buffer = RingBuffer(size=1000)
        >>> buffer.put(42, data_type="numeric")
        >>> entry = buffer.get()
        >>> print(entry.value)  # 42
    """

    def __init__(
        self,
        size: int,
        overflow_policy: BufferOverflowPolicy = BufferOverflowPolicy.OVERWRITE,
        enable_stats: bool = True,
    ) -> None:
        if size <= 0:
            raise ValueError("Buffer size must be positive")

        self._size = size
        self._overflow_policy = overflow_policy
        self._enable_stats = enable_stats

        # Pre-allocate buffer for memory efficiency
        self._buffer: List[Optional[BufferEntry]] = [None] * size
        self._head = 0  # Next write position
        self._tail = 0  # Next read position
        self._count = 0  # Current number of entries
        self._sequence_counter = 0

        # Thread safety
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)

        # Performance statistics
        self._stats = (
            {
                "total_writes": 0,
                "total_reads": 0,
                "overflows": 0,
                "drops": 0,
                "blocks": 0,
                "max_size_reached": 0,
            }
            if enable_stats
            else None
        )

    def put(
        self,
        value: Any,
        data_type: str = "unknown",
        timeout: Optional[float] = None,
        block: bool = True,
    ) -> bool:
        """Add an entry to the buffer.

        Args:
            value: Data to store
            data_type: Type identifier for the data
            timeout: Maximum time to wait if blocking (None = infinite)
            block: Whether to block if buffer is full

        Returns:
            True if data was stored, False if dropped

        Raises:
            BufferFullError: If buffer is full and policy is DROP
        """
        timestamp = time.perf_counter()

        with self._lock:
            # Handle full buffer based on policy
            if self._count == self._size:
                if self._overflow_policy == BufferOverflowPolicy.DROP:
                    if self._enable_stats:
                        self._stats["drops"] += 1
                    if not block:
                        return False
                    raise BufferFullError("Buffer is full")

                elif self._overflow_policy == BufferOverflowPolicy.BLOCK:
                    if not block:
                        return False

                    if self._enable_stats:
                        self._stats["blocks"] += 1

                    if not self._not_full.wait(timeout):
                        return False  # Timeout

                elif self._overflow_policy == BufferOverflowPolicy.OVERWRITE:
                    # Advance tail to overwrite oldest entry
                    self._tail = (self._tail + 1) % self._size
                    self._count -= 1
                    if self._enable_stats:
                        self._stats["overflows"] += 1

            # Create and store entry
            entry = BufferEntry(
                timestamp=timestamp,
                value=value,
                data_type=data_type,
                sequence_id=self._sequence_counter,
            )

            self._buffer[self._head] = entry
            self._head = (self._head + 1) % self._size
            self._count += 1
            self._sequence_counter += 1

            # Update statistics
            if self._enable_stats:
                self._stats["total_writes"] += 1
                self._stats["max_size_reached"] = max(
                    self._stats["max_size_reached"], self._count
                )

            # Notify waiting readers
            self._not_empty.notify()

            return True

    def get(self, timeout: Optional[float] = None, block: bool = True) -> BufferEntry:
        """Get the oldest entry from the buffer.

        Args:
            timeout: Maximum time to wait if blocking (None = infinite)
            block: Whether to block if buffer is empty

        Returns:
            The oldest buffer entry

        Raises:
            BufferEmptyError: If buffer is empty and not blocking
        """
        with self._lock:
            # Wait for data if buffer is empty
            if self._count == 0:
                if not block:
                    raise BufferEmptyError("Buffer is empty")

                if not self._not_empty.wait(timeout):
                    raise BufferEmptyError("Timeout waiting for data")

            # Get entry and advance tail
            entry = self._buffer[self._tail]
            self._buffer[self._tail] = None  # Clear reference for GC
            self._tail = (self._tail + 1) % self._size
            self._count -= 1

            # Update statistics
            if self._enable_stats:
                self._stats["total_reads"] += 1

            # Notify waiting writers
            self._not_full.notify()

            return entry

    def peek(self, offset: int = 0) -> Optional[BufferEntry]:
        """Peek at an entry without removing it.

        Args:
            offset: Offset from tail (0 = oldest, 1 = second oldest, etc.)

        Returns:
            Buffer entry at offset, or None if offset is out of range
        """
        with self._lock:
            if offset < 0 or offset >= self._count:
                return None

            index = (self._tail + offset) % self._size
            return self._buffer[index]

    def get_batch(
        self, max_count: int, timeout: Optional[float] = None
    ) -> List[BufferEntry]:
        """Get multiple entries from the buffer.

        Args:
            max_count: Maximum number of entries to retrieve
            timeout: Maximum time to wait for at least one entry

        Returns:
            List of buffer entries (may be fewer than max_count)
        """
        entries = []

        # Get first entry (may block)
        try:
            first_entry = self.get(timeout=timeout, block=True)
            entries.append(first_entry)
        except BufferEmptyError:
            return entries

        # Get additional entries without blocking
        for _ in range(max_count - 1):
            try:
                entry = self.get(block=False)
                entries.append(entry)
            except BufferEmptyError:
                break

        return entries

    def put_batch(self, values: List[tuple], block: bool = True) -> int:
        """Put multiple entries into the buffer.

        Args:
            values: List of (value, data_type) tuples
            block: Whether to block on full buffer

        Returns:
            Number of entries successfully stored
        """
        stored_count = 0

        for value, data_type in values:
            if self.put(value, data_type, block=block):
                stored_count += 1
            else:
                break  # Stop on first failure

        return stored_count

    def clear(self) -> None:
        """Clear all entries from the buffer."""
        with self._lock:
            for i in range(self._size):
                self._buffer[i] = None

            self._head = 0
            self._tail = 0
            self._count = 0

            # Notify all waiting threads
            self._not_empty.notify_all()
            self._not_full.notify_all()

    def resize(self, new_size: int) -> None:
        """Resize the buffer (may lose data if shrinking).

        Args:
            new_size: New buffer size

        Raises:
            ValueError: If new_size is not positive
        """
        if new_size <= 0:
            raise ValueError("Buffer size must be positive")

        with self._lock:
            # Extract current data
            current_data = []
            while self._count > 0:
                entry = self._buffer[self._tail]
                current_data.append(entry)
                self._tail = (self._tail + 1) % self._size
                self._count -= 1

            # Recreate buffer
            self._size = new_size
            self._buffer = [None] * new_size
            self._head = 0
            self._tail = 0
            self._count = 0

            # Restore data (up to new size)
            for entry in current_data[:new_size]:
                self._buffer[self._head] = entry
                self._head = (self._head + 1) % self._size
                self._count += 1

    def __len__(self) -> int:
        """Return current number of entries in buffer."""
        with self._lock:
            return self._count

    def __bool__(self) -> bool:
        """Return True if buffer is not empty."""
        return len(self) > 0

    def __iter__(self) -> Iterator[BufferEntry]:
        """Iterate over buffer entries (oldest to newest)."""
        with self._lock:
            # Create snapshot to avoid holding lock during iteration
            entries = []
            for i in range(self._count):
                index = (self._tail + i) % self._size
                entries.append(self._buffer[index])

        return iter(entries)

    @property
    def size(self) -> int:
        """Maximum buffer size."""
        return self._size

    @property
    def is_empty(self) -> bool:
        """True if buffer is empty."""
        with self._lock:
            return self._count == 0

    @property
    def is_full(self) -> bool:
        """True if buffer is full."""
        with self._lock:
            return self._count == self._size

    @property
    def available_space(self) -> int:
        """Number of available slots in buffer."""
        with self._lock:
            return self._size - self._count

    @property
    def utilization(self) -> float:
        """Buffer utilization as percentage (0.0 to 1.0)."""
        with self._lock:
            return self._count / self._size

    @property
    def stats(self) -> Optional[Dict[str, int]]:
        """Performance statistics (if enabled)."""
        if not self._enable_stats:
            return None

        with self._lock:
            return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset performance statistics."""
        if self._enable_stats:
            with self._lock:
                for key in self._stats:
                    self._stats[key] = 0
