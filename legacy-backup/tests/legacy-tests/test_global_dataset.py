#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for the global dataset module.
"""
import unittest
import threading
import time
from unittest.mock import patch, MagicMock

import tinyDisplay.global_dataset as global_dataset
from tinyDisplay.utility.dataset import dataset

class TestGlobalDataset(unittest.TestCase):
    """Test the global dataset functionality."""
    
    def setUp(self):
        """Reset the global dataset before each test."""
        global_dataset.reset()
    
    def tearDown(self):
        """Reset the global dataset after each test."""
        global_dataset.reset()
    
    def _remove_timestamp(self, data):
        """Remove __timestamp__ field from dictionary for comparison."""
        if isinstance(data, dict) and '__timestamp__' in data:
            return {k: v for k, v in data.items() if k != '__timestamp__'}
        return data
    
    def test_initialize(self):
        """Test initializing the global dataset."""
        # Initialize with data
        initial_data = {
            'test': {'value': 42}
        }
        
        ds = global_dataset.initialize(initial_data)
        
        # Verify the dataset was created correctly
        self.assertIsInstance(ds, dataset)
        self.assertEqual(self._remove_timestamp(ds.get('test')), {'value': 42})
        
        # Verify we can get the dataset
        retrieved_ds = global_dataset.get_dataset()
        self.assertIs(retrieved_ds, ds)
    
    def test_initialize_empty(self):
        """Test initializing an empty global dataset."""
        ds = global_dataset.initialize()
        self.assertIsInstance(ds, dataset)
        self.assertEqual(len(ds), 0)
    
    def test_initialize_twice_warning(self):
        """Test that initializing twice logs a warning."""
        with patch('tinyDisplay.global_dataset._logger') as mock_logger:
            # Initialize once
            global_dataset.initialize()
            
            # Initialize again
            global_dataset.initialize()
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
    
    def test_get_dataset_without_init(self):
        """Test getting dataset without initializing raises an error."""
        with self.assertRaises(RuntimeError):
            global_dataset.get_dataset()
    
    def test_add_database(self):
        """Test adding a database to the global dataset."""
        # Initialize
        global_dataset.initialize()
        
        # Add database
        global_dataset.add_database('test', {'value': 42})
        
        # Verify
        ds = global_dataset.get_dataset()
        self.assertEqual(self._remove_timestamp(ds.get('test')), {'value': 42})
    
    def test_update_database(self):
        """Test updating a database in the global dataset."""
        # Initialize with data
        global_dataset.initialize({
            'test': {'value': 42}
        })
        
        # Update database
        global_dataset.update_database('test', {'value': 100})
        
        # Verify
        ds = global_dataset.get_dataset()
        self.assertEqual(self._remove_timestamp(ds.get('test')), {'value': 100})
    
    def test_update_database_merge(self):
        """Test updating a database with merge option."""
        # Initialize with data
        global_dataset.initialize({
            'test': {'value1': 42, 'value2': 'hello'}
        })
        
        # Update database with merge
        global_dataset.update_database('test', {'value1': 100}, merge=True)
        
        # Verify both values exist
        ds = global_dataset.get_dataset()
        test_db = self._remove_timestamp(ds.get('test'))
        self.assertEqual(test_db['value1'], 100)
        self.assertEqual(test_db['value2'], 'hello')
    
    def test_update_database_replace(self):
        """Test updating a database with replace option."""
        # Initialize with data
        global_dataset.initialize({
            'test': {'value1': 42, 'value2': 'hello'}
        })
        
        # Update database without merge (replace)
        global_dataset.update_database('test', {'value1': 100}, merge=False)
        
        # Verify only new value exists
        ds = global_dataset.get_dataset()
        test_db = self._remove_timestamp(ds.get('test'))
        self.assertEqual(test_db['value1'], 100)
        self.assertNotIn('value2', test_db)
    
    def test_get_database(self):
        """Test getting a database from the global dataset."""
        # Initialize with data
        global_dataset.initialize({
            'test': {'value': 42}
        })
        
        # Get database
        test_db = global_dataset.get_database('test')
        
        # Verify
        self.assertEqual(self._remove_timestamp(test_db), {'value': 42})
    
    def test_get_database_default(self):
        """Test getting a non-existent database with default value."""
        # Initialize empty
        global_dataset.initialize()
        
        # Get non-existent database with default
        default_value = {'default': True}
        test_db = global_dataset.get_database('nonexistent', default_value)
        
        # Verify default was returned
        self.assertEqual(test_db, default_value)
    
    def test_reset(self):
        """Test resetting the global dataset."""
        # Initialize
        global_dataset.initialize()
        
        # Reset
        global_dataset.reset()
        
        # Verify it's uninitialized
        with self.assertRaises(RuntimeError):
            global_dataset.get_dataset()
    
    def test_with_lock(self):
        """Test using the with_lock helper function."""
        # Initialize the dataset
        global_dataset.initialize({
            'counter': {'value': 10}
        })
        
        # Define a function that reads and updates atomically
        def increment():
            db = global_dataset.get_database('counter')
            current = db['value']
            global_dataset.update_database('counter', {'value': current + 1})
            return current + 1
        
        # Execute with lock
        result = global_dataset.with_lock(increment)
        
        # Verify the result and updated value
        self.assertEqual(result, 11)
        self.assertEqual(global_dataset.get_database('counter')['value'], 11)
    
    def test_read_values(self):
        """Test reading multiple values atomically."""
        # Initialize the dataset
        global_dataset.initialize({
            'user': {'name': 'John', 'age': 30},
            'prefs': {'theme': 'dark'}
        })
        
        # Read multiple values
        values = global_dataset.read_values(
            ('user', 'name'),
            ('user', 'age'),
            ('prefs', 'theme')
        )
        
        # Verify the results
        self.assertEqual(values[('user', 'name')], 'John')
        self.assertEqual(values[('user', 'age')], 30)
        self.assertEqual(values[('prefs', 'theme')], 'dark')
    
    def test_update_multiple(self):
        """Test updating multiple databases atomically."""
        # Initialize the dataset
        global_dataset.initialize({
            'user': {'name': 'John', 'visits': 5},
            'stats': {'total_users': 10}
        })
        
        # Update multiple databases
        global_dataset.update_multiple({
            'user': {'visits': 6},
            'stats': {'total_users': 11}
        })
        
        # Verify the updates
        user_db = global_dataset.get_database('user')
        stats_db = global_dataset.get_database('stats')
        
        self.assertEqual(user_db['visits'], 6)
        self.assertEqual(stats_db['total_users'], 11)

class TestGlobalDatasetIntegration(unittest.TestCase):
    """Test integrating the global dataset with other components."""
    
    def setUp(self):
        """Reset the global dataset before each test."""
        global_dataset.reset()
    
    def tearDown(self):
        """Reset the global dataset after each test."""
        global_dataset.reset()
    
    @unittest.skip("Widget test requires all tinyDisplay components to be set up")
    def test_with_widget_creation(self):
        """Test using the global dataset with widget creation."""
        from tinyDisplay.render.widget import text
        from tinyDisplay.utility.dynamic import dynamic
        
        # Initialize global dataset
        global_dataset.initialize({
            'theme': {'text_color': 'red'}
        })
        ds = global_dataset.get_dataset()
        
        # Create a widget using the global dataset
        widget = text(
            name="test",
            value="Test Widget",
            foreground=dynamic("theme['text_color']"),
            dataset=ds
        )
        
        # Render the widget
        img, _ = widget.render(force=True)
        
        # Verify the dataset was used correctly (foreground should be red)
        self.assertEqual(widget._foreground, 'red')
        
        # Update the dataset
        global_dataset.update_database('theme', {'text_color': 'blue'})
        
        # Re-render
        img, changed = widget.render()
        
        # Verify the update was applied
        self.assertTrue(changed)
        self.assertEqual(widget._foreground, 'blue')

class TestThreadSafety(unittest.TestCase):
    """Test thread safety of the global dataset implementation."""
    
    def setUp(self):
        """Reset the global dataset before each test."""
        global_dataset.reset()
    
    def tearDown(self):
        """Reset the global dataset after each test."""
        global_dataset.reset()
    
    def _remove_timestamp(self, data):
        """Remove __timestamp__ field from dictionary for comparison."""
        if isinstance(data, dict) and '__timestamp__' in data:
            return {k: v for k, v in data.items() if k != '__timestamp__'}
        return data
    
    def test_concurrent_reads(self):
        """Test that multiple threads can read concurrently without issues."""
        # Initialize the dataset
        global_dataset.initialize({
            'counter': {'value': 0}
        })
        
        # Track errors that might occur in threads
        errors = []
        
        def read_task():
            """Read from the global dataset repeatedly."""
            try:
                for _ in range(100):
                    # Perform reads
                    db = global_dataset.get_database('counter')
                    # Small sleep to increase chance of thread interleaving
                    time.sleep(0.001)
                    # Verify data is consistent
                    self.assertIn('value', db)
            except Exception as e:
                errors.append(e)
        
        # Create and start multiple reader threads
        threads = []
        for _ in range(10):
            t = threading.Thread(target=read_task)
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Check if any errors occurred
        self.assertEqual(len(errors), 0, f"Errors in threads: {errors}")
    
    def test_concurrent_writes(self):
        """Test that concurrent writes are properly synchronized."""
        # Initialize the dataset
        global_dataset.initialize({
            'counter': {'value': 0}
        })
        
        # Number of iterations per thread
        iterations = 50
        # Number of threads
        thread_count = 5
        
        # Define an atomic increment function
        def increment_atomic():
            db = global_dataset.get_database('counter')
            current = db['value']
            global_dataset.update_database('counter', {'value': current + 1})
        
        def increment_task():
            """Increment the counter in the global dataset."""
            for _ in range(iterations):
                # Use the with_lock helper for atomic operations
                global_dataset.with_lock(increment_atomic)
                
                # Sleep outside the lock to allow other threads to run
                time.sleep(0.001)
        
        # Create and start multiple writer threads
        threads = []
        for _ in range(thread_count):
            t = threading.Thread(target=increment_task)
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Check the final value - should be iterations * thread_count if synchronized
        final_value = global_dataset.get_database('counter')['value']
        self.assertEqual(final_value, iterations * thread_count,
                         f"Expected {iterations * thread_count}, got {final_value}")
    
    def test_mixed_read_write(self):
        """Test a basic scenario with a counter that's incremented and read."""
        # Initialize with simple data
        global_dataset.initialize({
            'counter': {'value': 0}
        })
        
        # Iteration count
        iterations = 50
        # Track the actual number of increments
        actual_increments = 0
        # Collect all read values for verification
        all_read_values = []
        # Event to signal readers to stop
        stop_event = threading.Event()
        
        def writer_task():
            """Increment the counter atomically."""
            nonlocal actual_increments
            for _ in range(iterations):
                # Use with_lock for atomic increment
                def increment():
                    nonlocal actual_increments
                    db = global_dataset.get_database('counter')
                    current = db['value']
                    global_dataset.update_database('counter', {'value': current + 1})
                    actual_increments += 1
                
                # Execute the increment atomically
                global_dataset.with_lock(increment)
                time.sleep(0.01)  # Sleep to allow readers to interleave
        
        def reader_task():
            """Read the counter value until signaled to stop."""
            while not stop_event.is_set():
                # Read the counter value
                value = global_dataset.get_database('counter')['value']
                all_read_values.append(value)
                time.sleep(0.005)  # Small sleep to reduce contention
        
        # Start one writer and multiple readers
        writer = threading.Thread(target=writer_task)
        readers = []
        for _ in range(3):
            reader = threading.Thread(target=reader_task)
            reader.daemon = True  # Make readers daemon threads for easy cleanup
            readers.append(reader)
        
        # Start threads
        for reader in readers:
            reader.start()
        writer.start()
        
        # Wait for writer to complete
        writer.join()
        
        # Signal readers to stop and wait for them
        stop_event.set()
        time.sleep(0.1)  # Give readers time to exit
        
        # Verify final state
        final_counter = global_dataset.get_database('counter')['value']
        
        # Check that the counter was incremented exactly the expected number of times
        self.assertEqual(actual_increments, iterations,
                        f"Expected {iterations} increments, got {actual_increments}")
        
        # Check that the final counter value matches the number of increments
        self.assertEqual(final_counter, iterations,
                        f"Final counter should be {iterations}, got {final_counter}")
        
        # Verify that we never read any value higher than the final value
        self.assertTrue(all(v <= iterations for v in all_read_values),
                       f"Read values should not exceed the final value: {max(all_read_values)}")
        
        # Verify that all counter values were non-negative
        self.assertTrue(all(v >= 0 for v in all_read_values),
                       "All counter values should be non-negative")

if __name__ == "__main__":
    unittest.main() 