# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ron Ritchey and contributors
# See License.rst for details

"""
Test of dataset hashing functionality for the tinyDisplay system
"""
import time
import pytest
import random
import string
from unittest.mock import patch, MagicMock

from tinyDisplay.utility import dataset


def random_string(length=10):
    """Generate a random string of fixed length."""
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))


def test_hash_basic_generation():
    """Test that hash values are generated correctly for simple database cases."""
    ds = dataset()
    
    # Add a simple database and verify hash is generated
    ds.add("test_db", {"value1": 123, "value2": "test"})
    hash1 = ds.get_hash("test_db")
    
    assert hash1 is not None, "Hash should be generated for a database"
    assert isinstance(hash1, str), "Hash should be returned as a string"
    assert len(hash1) == 32, "Hash should be a 128-bit value represented as a 32-character hex string"


def test_hash_consistency():
    """Test that identical datasets produce identical hash values."""
    # Create two identical datasets
    ds1 = dataset()
    ds2 = dataset()
    
    # Add identical data
    test_data = {"value1": 123, "value2": "test", "value3": True}
    ds1.add("test_db", test_data)
    ds2.add("test_db", test_data)
    
    # Get hashes
    hash1 = ds1.get_hash("test_db")
    hash2 = ds2.get_hash("test_db")
    
    assert hash1 == hash2, "Identical databases should have identical hash values"
    
    # Also test full dataset hashes
    full_hash1 = ds1.get_hash()
    full_hash2 = ds2.get_hash()
    
    assert full_hash1 == full_hash2, "Identical datasets should have identical hash values"


def test_hash_uniqueness():
    """Test that different datasets produce different hash values."""
    ds = dataset()
    
    # Add first database
    ds.add("test_db1", {"value": 123})
    hash1 = ds.get_hash("test_db1")
    
    # Add second database with different content
    ds.add("test_db2", {"value": 456})
    hash2 = ds.get_hash("test_db2")
    
    assert hash1 != hash2, "Different databases should have different hash values"
    
    # Test that changing a value produces a different hash
    original_hash = ds.get_hash("test_db1")
    ds.update("test_db1", {"value": 789})
    new_hash = ds.get_hash("test_db1")
    
    assert original_hash != new_hash, "Changing a value should change the hash"


def test_hash_complex_values():
    """Test hashing with complex data types."""
    ds = dataset()
    
    # Test with nested structures
    complex_data = {
        "string": "test",
        "number": 42,
        "boolean": True,
        "none": None,
        "list": [1, 2, 3, "four"],
        "dict": {"a": 1, "b": 2},
        "nested": {
            "level1": {
                "level2": [{"key": "value"}]
            }
        }
    }
    
    ds.add("complex_db", complex_data)
    hash1 = ds.get_hash("complex_db")
    
    assert hash1 is not None, "Should generate hash for complex data structures"
    
    # Modify a deeply nested value
    complex_data_modified = complex_data.copy()
    complex_data_modified["nested"]["level1"]["level2"][0]["key"] = "new_value"
    
    ds2 = dataset()
    ds2.add("complex_db", complex_data_modified)
    hash2 = ds2.get_hash("complex_db")
    
    assert hash1 != hash2, "Changing a nested value should change the hash"


def test_hash_incremental_updates():
    """Test that incremental updates correctly modify the hash value."""
    # Create a dataset with the initial state
    ds1 = dataset()
    ds1.add("test_db", {"key1": "value1", "key2": "value2"})
    initial_hash = ds1.get_hash("test_db")
    print(f"Initial DB state: {ds1._dataset['test_db']}")
    print(f"Initial hash: {initial_hash}")

    # Create a dataset with the updated state
    ds2 = dataset()
    ds2.add("test_db", {"key1": "updated", "key2": "value2"})
    updated_hash = ds2.get_hash("test_db")
    print(f"Updated DB state: {ds2._dataset['test_db']}")
    print(f"Updated hash: {updated_hash}")

    # Verify that different states have different hashes
    assert initial_hash != updated_hash, "Hash should change for different states"

    # Create another dataset with the same state as the initial one
    ds3 = dataset()
    ds3.add("test_db", {"key1": "value1", "key2": "value2"})
    reverted_hash = ds3.get_hash("test_db")
    print(f"Reverted DB state: {ds3._dataset['test_db']}")
    print(f"Reverted hash: {reverted_hash}")
    print(f"Initial hash: {initial_hash}")

    # Verify that identical states have identical hashes
    assert reverted_hash == initial_hash, "Identical states should have identical hashes"
    
    # Test incremental updates on dataset hash
    full_hash_before = ds1.get_hash()
    ds1.add("another_db", {"new": "data"})
    full_hash_after = ds1.get_hash()
    
    assert full_hash_before != full_hash_after, "Adding a database should change the dataset hash"


def test_hash_dataset_level():
    """Test dataset-level hashing functionality."""
    ds = dataset()
    
    # Add multiple databases
    ds.add("db1", {"value": 1})
    ds.add("db2", {"value": 2})
    
    # Get dataset hash
    dataset_hash = ds.get_hash()
    
    assert dataset_hash is not None, "Dataset hash should be generated"
    
    # Create identical dataset
    ds2 = dataset()
    ds2.add("db1", {"value": 1})
    ds2.add("db2", {"value": 2})
    
    # Get hash from second dataset
    dataset_hash2 = ds2.get_hash()
    
    assert dataset_hash == dataset_hash2, "Identical datasets should have identical hashes"
    
    # Change order of additions but same final content
    ds3 = dataset()
    ds3.add("db2", {"value": 2})
    ds3.add("db1", {"value": 1})
    
    dataset_hash3 = ds3.get_hash()
    
    assert dataset_hash == dataset_hash3, "Order of additions should not affect final hash"


def test_hash_timestamp_excluded():
    """Test that timestamps don't affect hash values."""
    ds = dataset()
    ds.add("test_db", {"value": "test"})
    
    # Get initial hash
    initial_hash = ds.get_hash("test_db")
    
    # Wait a moment to ensure timestamp would change
    time.sleep(0.1)
    
    # Update with same value (which should update timestamp but not content)
    ds.update("test_db", {"value": "test"})
    
    # Get new hash
    new_hash = ds.get_hash("test_db")
    
    assert initial_hash == new_hash, "Timestamps should not affect hash values"


def test_hash_incremental_update_performance():
    """Test that updates are O(1) with respect to dataset size."""
    # Create a large dataset
    large_data = {f'key_{i}': f'value_{i}' for i in range(1000)}
    ds = dataset()
    ds.add('large_db', large_data)
    
    # Get initial hash (this will do the full calculation)
    start_time = time.perf_counter()
    initial_hash = ds.get_hash('large_db')
    full_calc_time = time.perf_counter() - start_time
    
    # Make a small update
    update_data = {'key_0': 'updated_value'}
    
    # Time the update operation
    start_time = time.perf_counter()
    ds.update('large_db', update_data)
    update_time = time.perf_counter() - start_time
    
    # Get the updated hash (should be fast)
    start_time = time.perf_counter()
    updated_hash = ds.get_hash('large_db')
    hash_lookup_time = time.perf_counter() - start_time
    
    # Verify the hash changed
    assert initial_hash != updated_hash, "Hash should change after update"
    
    # The update and hash retrieval should be much faster than the initial calculation
    assert update_time < full_calc_time * 0.1, "Update should be O(1) time"
    assert hash_lookup_time < full_calc_time * 0.1, "Hash lookup should be O(1) time"


def test_lazy_evaluation():
    """Test that hashes are only calculated when needed."""
    # Patch the _compute_hash_for_db method to track calls
    with patch('tinyDisplay.utility.dataset.dataset._compute_hash_for_db') as mock_compute_hash:
        ds = dataset()
        
        # Add some data
        ds.add('test_db', {'key1': 'value1'})
        
        # Update without getting hash - should not trigger hash calculation
        ds.update('test_db', {'key1': 'value2'})
        mock_compute_hash.assert_not_called()
        
        # Now get the hash - should trigger calculation
        _ = ds.get_hash('test_db')
        mock_compute_hash.assert_called_once()
        
        # Get hash again - should not trigger another calculation
        mock_compute_hash.reset_mock()
        _ = ds.get_hash('test_db')
        mock_compute_hash.assert_not_called()


def test_hash_consistency_after_multiple_updates():
    """Test that multiple updates produce the same final hash regardless of order."""
    # Create two datasets with the same final state
    ds1 = dataset()
    ds2 = dataset()
    
    # Create the final state that both datasets should have
    final_state = {
        'key1': 'updated1',
        'key2': 'updated2',
        'key3': 'value3'
    }
    
    # Add the final state to both datasets
    ds1.add('test_db', final_state)
    ds2.add('test_db', final_state)
    
    # Print final states for debugging
    print(f"\nDS1 state: {sorted(ds1._dataset['test_db'].items())}")
    print(f"DS2 state: {sorted(ds2._dataset['test_db'].items())}")
    
    # Get hashes
    hash1 = ds1.get_hash('test_db')
    hash2 = ds2.get_hash('test_db')
    print(f"DS1 hash: {hash1}")
    print(f"DS2 hash: {hash2}")
    
    # Final hash should be the same for identical datasets
    assert hash1 == hash2, "Identical datasets should have the same hash"


def test_hash_with_large_values():
    """Test hashing with very large values."""
    ds = dataset()
    
    # Generate a large string (1MB)
    large_value = 'x' * (1024 * 1024)
    
    # Add to dataset
    ds.add('large_value_db', {'large_key': large_value})
    hash1 = ds.get_hash('large_value_db')
    
    # Change one character
    different_large_value = large_value[:-1] + 'y'
    
    # Update with slightly different large value
    ds2 = dataset()
    ds2.add('large_value_db', {'large_key': different_large_value})
    hash2 = ds2.get_hash('large_value_db')
    
    # Hashes should be different
    assert hash1 != hash2, "Different large values should produce different hashes"


def test_hash_with_deeply_nested_structures():
    """Test hashing with very deeply nested structures."""
    ds = dataset()
    
    # Create a deeply nested dictionary
    def make_nested(depth):
        if depth == 0:
            return 'base_value'
        return {'level': depth, 'next': make_nested(depth - 1)}
    
    nested_data = make_nested(20)  # 20 levels deep
    
    # Add to dataset
    ds.add('nested_db', {'data': nested_data})
    hash1 = ds.get_hash('nested_db')
    
    # Create a modified version
    def modify_nested(data):
        if isinstance(data, dict):
            if data.get('level') == 10:  # Change something deep in the structure
                return {'level': data['level'], 'next': 'modified_value'}
            return {k: modify_nested(v) for k, v in data.items()}
        return data
    
    modified_data = modify_nested(nested_data)
    
    # Add modified version to a new dataset
    ds2 = dataset()
    ds2.add('nested_db', {'data': modified_data})
    hash2 = ds2.get_hash('nested_db')
    
    # Hashes should be different
    assert hash1 != hash2, "Different nested structures should produce different hashes"
