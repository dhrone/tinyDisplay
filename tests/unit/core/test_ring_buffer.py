"""Unit tests for RingBuffer implementation."""

import pytest
import threading
import time
from unittest.mock import patch

from tinydisplay.core.ring_buffer import (
    RingBuffer,
    BufferEntry,
    BufferOverflowPolicy,
    RingBufferError,
    BufferFullError,
    BufferEmptyError,
)


class TestRingBufferBasics:
    """Test basic ring buffer functionality."""

    def test_initialization__valid_size__creates_buffer(self):
        """Test buffer initialization with valid parameters."""
        buffer = RingBuffer(size=10)

        assert buffer.size == 10
        assert buffer.is_empty
        assert not buffer.is_full
        assert len(buffer) == 0
        assert buffer.available_space == 10
        assert buffer.utilization == 0.0

    def test_initialization__invalid_size__raises_error(self):
        """Test buffer initialization with invalid size."""
        with pytest.raises(ValueError, match="Buffer size must be positive"):
            RingBuffer(size=0)

        with pytest.raises(ValueError, match="Buffer size must be positive"):
            RingBuffer(size=-1)

    def test_put_get__single_entry__works_correctly(self):
        """Test putting and getting a single entry."""
        buffer = RingBuffer(size=5)

        # Put entry
        result = buffer.put(42, data_type="numeric")
        assert result is True
        assert len(buffer) == 1
        assert not buffer.is_empty
        assert buffer.utilization == 0.2

        # Get entry
        entry = buffer.get()
        assert entry.value == 42
        assert entry.data_type == "numeric"
        assert entry.sequence_id == 0
        assert isinstance(entry.timestamp, float)

        assert len(buffer) == 0
        assert buffer.is_empty

    def test_put_get__multiple_entries__maintains_order(self):
        """Test FIFO ordering with multiple entries."""
        buffer = RingBuffer(size=5)

        # Put multiple entries
        values = [10, 20, 30, 40]
        for i, value in enumerate(values):
            buffer.put(value, data_type=f"type_{i}")

        assert len(buffer) == 4

        # Get entries and verify order
        for i, expected_value in enumerate(values):
            entry = buffer.get()
            assert entry.value == expected_value
            assert entry.data_type == f"type_{i}"
            assert entry.sequence_id == i

    def test_put__buffer_full_overwrite_policy__overwrites_oldest(self):
        """Test overwrite policy when buffer is full."""
        buffer = RingBuffer(size=3, overflow_policy=BufferOverflowPolicy.OVERWRITE)

        # Fill buffer
        for i in range(3):
            buffer.put(i)

        assert buffer.is_full

        # Add one more (should overwrite first entry)
        buffer.put(99)

        assert len(buffer) == 3
        assert buffer.is_full

        # First entry should be overwritten
        entry = buffer.get()
        assert entry.value == 1  # Original 0 was overwritten

        entry = buffer.get()
        assert entry.value == 2

        entry = buffer.get()
        assert entry.value == 99

    def test_put__buffer_full_drop_policy__drops_new_data(self):
        """Test drop policy when buffer is full."""
        buffer = RingBuffer(size=2, overflow_policy=BufferOverflowPolicy.DROP)

        # Fill buffer
        buffer.put(1)
        buffer.put(2)

        # Try to add more (should be dropped)
        with pytest.raises(BufferFullError):
            buffer.put(3)

        # Non-blocking put should return False
        result = buffer.put(3, block=False)
        assert result is False

        # Original data should be intact
        assert buffer.get().value == 1
        assert buffer.get().value == 2

    def test_get__empty_buffer__raises_error(self):
        """Test getting from empty buffer."""
        buffer = RingBuffer(size=5)

        with pytest.raises(BufferEmptyError):
            buffer.get(block=False)

    def test_peek__various_offsets__returns_correct_entries(self):
        """Test peeking at entries without removing them."""
        buffer = RingBuffer(size=5)

        # Add some data
        for i in range(3):
            buffer.put(i * 10)

        # Peek at different offsets
        assert buffer.peek(0).value == 0  # Oldest
        assert buffer.peek(1).value == 10  # Second oldest
        assert buffer.peek(2).value == 20  # Newest

        # Out of range should return None
        assert buffer.peek(3) is None
        assert buffer.peek(-1) is None

        # Buffer should be unchanged
        assert len(buffer) == 3


class TestRingBufferBatchOperations:
    """Test batch operations."""

    def test_get_batch__multiple_entries__returns_correct_count(self):
        """Test getting multiple entries at once."""
        buffer = RingBuffer(size=10)

        # Add some data
        for i in range(5):
            buffer.put(i)

        # Get batch
        entries = buffer.get_batch(max_count=3)

        assert len(entries) == 3
        assert [e.value for e in entries] == [0, 1, 2]
        assert len(buffer) == 2  # 2 entries remaining

    def test_get_batch__more_requested_than_available__returns_available(self):
        """Test batch get when requesting more than available."""
        buffer = RingBuffer(size=10)

        # Add 2 entries
        buffer.put(10)
        buffer.put(20)

        # Request 5 entries
        entries = buffer.get_batch(max_count=5)

        assert len(entries) == 2
        assert [e.value for e in entries] == [10, 20]
        assert buffer.is_empty

    def test_put_batch__multiple_entries__stores_all(self):
        """Test putting multiple entries at once."""
        buffer = RingBuffer(size=10)

        values = [(10, "int"), (20, "int"), (30, "int")]
        stored_count = buffer.put_batch(values)

        assert stored_count == 3
        assert len(buffer) == 3

        # Verify order
        for expected_value, _ in values:
            entry = buffer.get()
            assert entry.value == expected_value

    def test_put_batch__buffer_too_small__stores_partial(self):
        """Test batch put when buffer is too small."""
        buffer = RingBuffer(size=2, overflow_policy=BufferOverflowPolicy.DROP)

        values = [(10, "int"), (20, "int"), (30, "int")]
        stored_count = buffer.put_batch(values, block=False)

        assert stored_count == 2  # Only first 2 stored
        assert buffer.is_full


class TestRingBufferThreadSafety:
    """Test thread safety of ring buffer operations."""

    def test_concurrent_put_get__multiple_threads__maintains_integrity(self):
        """Test concurrent put/get operations."""
        buffer = RingBuffer(size=1000)
        results = []
        errors = []

        def producer(start_value, count):
            """Producer thread function."""
            try:
                for i in range(count):
                    buffer.put(start_value + i, data_type="producer")
            except Exception as e:
                errors.append(e)

        def consumer(count):
            """Consumer thread function."""
            try:
                consumed = []
                for _ in range(count):
                    entry = buffer.get(timeout=1.0)
                    consumed.append(entry.value)
                results.extend(consumed)
            except Exception as e:
                errors.append(e)

        # Start producer and consumer threads
        producer_threads = [
            threading.Thread(target=producer, args=(i * 100, 50)) for i in range(4)
        ]
        consumer_threads = [
            threading.Thread(target=consumer, args=(50,)) for _ in range(4)
        ]

        # Start all threads
        for t in producer_threads + consumer_threads:
            t.start()

        # Wait for completion
        for t in producer_threads + consumer_threads:
            t.join()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 200  # 4 producers * 50 items each
        assert len(set(results)) == 200  # All values should be unique

    def test_blocking_operations__timeout__works_correctly(self):
        """Test blocking operations with timeout."""
        buffer = RingBuffer(size=1, overflow_policy=BufferOverflowPolicy.BLOCK)

        # Fill buffer
        buffer.put(1)

        # Try to put with timeout (should timeout)
        start_time = time.time()
        result = buffer.put(2, timeout=0.1)
        elapsed = time.time() - start_time

        assert result is False
        assert 0.1 <= elapsed <= 0.2  # Should timeout around 0.1 seconds

        # Empty buffer
        buffer.get()

        # Try to get with timeout from empty buffer
        start_time = time.time()
        with pytest.raises(BufferEmptyError):
            buffer.get(timeout=0.1)
        elapsed = time.time() - start_time

        assert 0.1 <= elapsed <= 0.2


class TestRingBufferUtilities:
    """Test utility methods and properties."""

    def test_clear__removes_all_entries(self):
        """Test clearing the buffer."""
        buffer = RingBuffer(size=5)

        # Add some data
        for i in range(3):
            buffer.put(i)

        assert len(buffer) == 3

        # Clear buffer
        buffer.clear()

        assert len(buffer) == 0
        assert buffer.is_empty
        assert buffer.available_space == 5

    def test_resize__larger_size__preserves_data(self):
        """Test resizing buffer to larger size."""
        buffer = RingBuffer(size=3)

        # Add data
        for i in range(3):
            buffer.put(i)

        # Resize to larger
        buffer.resize(5)

        assert buffer.size == 5
        assert len(buffer) == 3

        # Data should be preserved
        for i in range(3):
            assert buffer.get().value == i

    def test_resize__smaller_size__truncates_data(self):
        """Test resizing buffer to smaller size."""
        buffer = RingBuffer(size=5)

        # Add data
        for i in range(5):
            buffer.put(i)

        # Resize to smaller
        buffer.resize(3)

        assert buffer.size == 3
        assert len(buffer) == 3

        # Only first 3 entries should remain
        for i in range(3):
            assert buffer.get().value == i

    def test_iteration__iterates_in_order(self):
        """Test iterating over buffer entries."""
        buffer = RingBuffer(size=5)

        # Add data
        values = [10, 20, 30]
        for value in values:
            buffer.put(value)

        # Iterate and verify order
        iterated_values = [entry.value for entry in buffer]
        assert iterated_values == values

        # Buffer should be unchanged after iteration
        assert len(buffer) == 3

    def test_bool_conversion__reflects_empty_state(self):
        """Test boolean conversion of buffer."""
        buffer = RingBuffer(size=5)

        assert not buffer  # Empty buffer is falsy

        buffer.put(1)
        assert buffer  # Non-empty buffer is truthy

        buffer.get()
        assert not buffer  # Empty again


class TestRingBufferStatistics:
    """Test performance statistics collection."""

    def test_stats__enabled__collects_statistics(self):
        """Test statistics collection when enabled."""
        buffer = RingBuffer(size=5, enable_stats=True)

        # Perform operations
        buffer.put(1)
        buffer.put(2)
        buffer.get()

        stats = buffer.stats
        assert stats is not None
        assert stats["total_writes"] == 2
        assert stats["total_reads"] == 1
        assert stats["max_size_reached"] == 2
        assert stats["overflows"] == 0

    def test_stats__disabled__returns_none(self):
        """Test statistics when disabled."""
        buffer = RingBuffer(size=5, enable_stats=False)

        buffer.put(1)
        buffer.get()

        assert buffer.stats is None

    def test_stats__overflow_tracking__counts_overflows(self):
        """Test overflow statistics tracking."""
        buffer = RingBuffer(size=2, overflow_policy=BufferOverflowPolicy.OVERWRITE)

        # Fill buffer and cause overflow
        buffer.put(1)
        buffer.put(2)
        buffer.put(3)  # Should cause overflow

        stats = buffer.stats
        assert stats["overflows"] == 1
        assert stats["total_writes"] == 3

    def test_reset_stats__clears_statistics(self):
        """Test resetting statistics."""
        buffer = RingBuffer(size=5, enable_stats=True)

        # Generate some stats
        buffer.put(1)
        buffer.get()

        assert buffer.stats["total_writes"] == 1
        assert buffer.stats["total_reads"] == 1

        # Reset stats
        buffer.reset_stats()

        stats = buffer.stats
        assert stats["total_writes"] == 0
        assert stats["total_reads"] == 0


@pytest.mark.performance
class TestRingBufferPerformance:
    """Performance tests for ring buffer."""

    def test_put_get_performance__high_throughput__meets_target(self):
        """Test put/get performance under high throughput."""
        # Use reasonable numbers for testing - buffer size >= operations
        num_operations = 5000
        buffer_size = num_operations  # Ensure buffer can hold all data

        buffer = RingBuffer(size=buffer_size)

        # Measure put performance
        start_time = time.perf_counter()
        for i in range(num_operations):
            buffer.put(i, data_type="perf_test")
        put_duration = time.perf_counter() - start_time

        # Verify all items were stored
        assert len(buffer) == num_operations

        # Measure get performance
        start_time = time.perf_counter()
        for _ in range(num_operations):
            buffer.get()
        get_duration = time.perf_counter() - start_time

        # Verify buffer is empty
        assert len(buffer) == 0

        # Performance assertions (should be very fast)
        put_ops_per_sec = num_operations / put_duration
        get_ops_per_sec = num_operations / get_duration

        # Should handle at least 5k ops/sec (conservative target)
        assert put_ops_per_sec > 5000, f"Put performance: {put_ops_per_sec:.0f} ops/sec"
        assert get_ops_per_sec > 5000, f"Get performance: {get_ops_per_sec:.0f} ops/sec"

    def test_memory_efficiency__large_buffer__reasonable_overhead(self):
        """Test memory efficiency of large buffers."""
        import sys

        # Create moderately large buffer
        buffer_size = 1000
        buffer = RingBuffer(size=buffer_size, enable_stats=False)

        # Fill with small objects
        for i in range(buffer_size):
            buffer.put(i)

        # Memory usage should be reasonable
        # (This is a basic check - more sophisticated memory profiling
        # would be done in integration tests)
        buffer_memory = sys.getsizeof(buffer._buffer)

        # Should not use excessive memory per entry
        memory_per_entry = buffer_memory / buffer_size
        assert memory_per_entry < 1000, f"Memory per entry: {memory_per_entry} bytes"
