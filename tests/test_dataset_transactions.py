# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Test of Dataset transaction functionality for the tinyDisplay system
"""

import pytest

from tinyDisplay.exceptions import ValidationError, UpdateError
from tinyDisplay.utility.dataset import dataset


class TestDatasetTransaction:
    """Tests for the dataset transaction functionality."""

    def test_context_manager_api(self):
        """Test the context manager (with statement) API."""
        ds = dataset()
        
        # Use the context manager to perform atomic updates
        with ds.transaction() as tx:
            tx.update("db1", {"key1": "value1"})
            tx.update("db2", {"key2": "value2"})
            
            # Verify values are visible within the transaction
            assert tx.get("db1", "key1") == "value1"
            assert tx.get("db2", "key2") == "value2"
            
            # Verify values are not visible outside the transaction yet
            assert "db1" not in ds
            assert "db2" not in ds
        
        # After the transaction completes, verify values are visible
        assert ds["db1"]["key1"] == "value1"
        assert ds["db2"]["key2"] == "value2"
    
    def test_begin_commit_api(self):
        """Test the begin/commit transaction API."""
        ds = dataset()
        
        # Use the begin/commit API
        tx = ds.begin_transaction()
        tx.update("db1", {"key1": "value1"})
        tx.update("db2", {"key2": "value2"})
        
        # Verify values are not visible outside the transaction yet
        assert "db1" not in ds
        assert "db2" not in ds
        
        # Commit the transaction
        tx.commit()
        
        # After commit, verify values are visible
        assert ds["db1"]["key1"] == "value1"
        assert ds["db2"]["key2"] == "value2"
    
    def test_batch_update_api(self):
        """Test the batch_update API."""
        ds = dataset()
        
        # Use the batch_update API
        ds.batch_update({
            "db1": {"key1": "value1"},
            "db2": {"key2": "value2"}
        })
        
        # Verify values are visible
        assert ds["db1"]["key1"] == "value1"
        assert ds["db2"]["key2"] == "value2"
    
    def test_rollback(self):
        """Test transaction rollback."""
        ds = dataset()
        
        # Add initial data
        ds.update("db1", {"key1": "initial1"})
        
        # Begin a transaction
        tx = ds.begin_transaction()
        tx.update("db1", {"key1": "changed1"})
        tx.update("db2", {"key2": "value2"})
        
        # Verify changes are visible within the transaction
        assert tx.get("db1", "key1") == "changed1"
        assert tx.get("db2", "key2") == "value2"
        
        # Rollback the transaction
        tx.rollback()
        
        # Verify original state is preserved
        assert ds["db1"]["key1"] == "initial1"
        assert "db2" not in ds
    
    def test_automatic_rollback_on_exception(self):
        """Test automatic rollback when an exception occurs in a transaction."""
        # Create dataset with debug mode enabled to ensure validation errors are raised
        ds = dataset()
        
        # Force debug mode on to ensure validation errors are raised
        ds._debug = True
        
        # Set up validation rules before adding data
        ds.registerValidation(
            "db1",
            "key1",
            type=int,  # Ensure it's an integer
            validate="_VAL_ < 100",  # Will fail for values >= 100
            default=0
        )
        
        # Add initial data
        ds.update("db1", {"key1": 50})
        
        # Use context manager which should rollback on validation error
        with pytest.raises(ValidationError):
            with ds.transaction() as tx:
                # First update should succeed
                tx.update("db2", {"key2": "value2"})
                
                # This update should fail validation and cause the transaction to abort
                tx.update("db1", {"key1": 150})
        
        # Verify original state is preserved (no changes committed)
        assert ds["db1"]["key1"] == 50
        assert "db2" not in ds
        
    def test_transaction_exception_rollback(self):
        """Test rollback when an exception occurs during transaction execution."""
        ds = dataset()
        
        # Add initial data
        ds.update("db1", {"key1": 50})
        
        # Use context manager which should automatically rollback on any exception
        try:
            with ds.transaction() as tx:
                tx.update("db1", {"key1": 60})
                tx.update("db2", {"key2": "value2"})
                # Simulate an arbitrary exception during processing
                raise RuntimeError("Simulated error")
        except RuntimeError:
            # Expected exception
            pass
        
        # Verify original state is preserved
        assert ds["db1"]["key1"] == 50
        assert "db2" not in ds
    
    def test_transaction_read_operations(self):
        """Test read operations within a transaction."""
        ds = dataset()
        
        # Add initial data
        ds.update("db1", {"key1": "value1", "key2": "value2"})
        
        # Begin a transaction
        tx = ds.begin_transaction()
        
        # Test read operations with existing data
        assert tx.get("db1") == {"key1": "value1", "key2": "value2"}
        assert tx.get("db1", "key1") == "value1"
        assert tx.get("db1", "missing", "default") == "default"
        assert tx["db1"] == {"key1": "value1", "key2": "value2"}
        
        # Make changes within transaction
        tx.update("db1", {"key1": "changed", "key3": "new"})
        
        # Test read operations with pending changes
        assert tx.get("db1") == {"key1": "changed", "key2": "value2", "key3": "new"}
        assert tx.get("db1", "key1") == "changed"
        assert tx.get("db1", "key3") == "new"
        assert tx["db1"]["key1"] == "changed"
        
        # Verify changes aren't visible outside the transaction
        assert ds["db1"]["key1"] == "value1"
        assert "key3" not in ds["db1"]
        
        # Commit and verify changes
        tx.commit()
        assert ds["db1"]["key1"] == "changed"
        assert ds["db1"]["key3"] == "new"
    
    def test_nested_data_transaction(self):
        """Test transactions with nested dictionary data."""
        ds = dataset()
        
        # Add initial nested data
        ds.update("config", {"system": {"version": "1.0", "name": "tinyDisplay"}})
        
        # Update in a transaction
        with ds.transaction() as tx:
            # Get current data and modify nested values
            config = tx.get("config")
            config["system"]["version"] = "2.0"
            config["system"]["debug"] = True
            
            # Update with modified data
            tx.update("config", config)
        
        # Verify nested changes were applied
        assert ds["config"]["system"]["version"] == "2.0"
        assert ds["config"]["system"]["name"] == "tinyDisplay"
        assert ds["config"]["system"]["debug"] is True
    
    def test_multiple_transaction_updates(self):
        """Test updating the same key multiple times in a transaction."""
        ds = dataset()
        
        # Begin a transaction
        with ds.transaction() as tx:
            tx.update("counter", {"value": 1})
            tx.update("counter", {"value": 2})
            tx.update("counter", {"value": 3})
            
            # Verify only the latest value is seen within the transaction
            assert tx.get("counter", "value") == 3
        
        # Verify only the final value is committed
        assert ds["counter"]["value"] == 3
    
    def test_transaction_after_closed(self):
        """Test that operations on a closed transaction raise exceptions."""
        ds = dataset()
        tx = ds.begin_transaction()
        tx.update("db", {"key": "value"})
        tx.commit()
        
        # All operations after close should raise RuntimeError
        with pytest.raises(RuntimeError):
            tx.update("db", {"key2": "value2"})
            
        with pytest.raises(RuntimeError):
            tx.get("db")
            
        with pytest.raises(RuntimeError):
            tx.commit()
            
        with pytest.raises(RuntimeError):
            tx.rollback()
            
        with pytest.raises(RuntimeError):
            value = tx["db"]
    
    def test_conflict_merge_settings(self):
        """Test handling of conflicting merge settings."""
        ds = dataset()
        
        # Begin a transaction
        tx = ds.begin_transaction()
        
        # First update with merge=True
        tx.update("db", {"key1": "value1"}, merge=True)
        
        # Second update to same database with merge=False should raise ValueError
        with pytest.raises(ValueError):
            tx.update("db", {"key2": "value2"}, merge=False)
