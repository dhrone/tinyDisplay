# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ron Ritchey and contributors
# See License.rst for details

"""
Test of dataset hashing functionality for the tinyDisplay system
"""
import pytest

from tinyDisplay.utility import dataset


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
    ds = dataset()
    
    # Initial data
    ds.add("test_db", {"key1": "value1", "key2": "value2"})
    initial_hash = ds.get_hash("test_db")
    
    # Update one key
    ds.update("test_db", {"key1": "updated"})
    updated_hash = ds.get_hash("test_db")
    
    assert initial_hash != updated_hash, "Hash should change after an update"
    
    # Revert the change - should go back to original hash
    ds.update("test_db", {"key1": "value1"})
    reverted_hash = ds.get_hash("test_db")
    
    assert reverted_hash == initial_hash, "Reverting a change should restore the original hash"
    
    # Test incremental updates on dataset hash
    full_hash_before = ds.get_hash()
    ds.add("another_db", {"new": "data"})
    full_hash_after = ds.get_hash()
    
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
    import time
    time.sleep(0.1)
    
    # Update with same value (which should update timestamp but not content)
    ds.update("test_db", {"value": "test"})
    
    # Get new hash
    new_hash = ds.get_hash("test_db")
    
    assert initial_hash == new_hash, "Timestamps should not affect hash values"
