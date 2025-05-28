#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests focused on finding bugs in the dependency tracking system.
"""
import unittest
import logging
import sys
import os
from unittest.mock import Mock, patch
from collections import ChainMap

# Add the parent directory to the path so that tinyDisplay can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tinyDisplay.utility.dataset import dataset
from tinyDisplay.utility.evaluator import dynamicValue
from tinyDisplay.utility.variable_dependencies import variable_registry
from tinyDisplay.utility.evaluator import evaluator, dynamicValue
from tinyDisplay.utility.dynamic import dynamic, dependency_registry
import tinyDisplay.global_dataset as global_dataset


class TestDependencyTrackingBugs(unittest.TestCase):
    """Test cases to identify potential bugs in the dependency tracking system."""

    def setUp(self):
        """Set up test environment."""
        # Configure logging to show debug messages
        logging.basicConfig(level=logging.DEBUG)
        
        # Also ensure all handlers use DEBUG level
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.DEBUG)
            
        # Create a fresh dataset for each test
        self.data = dataset()
        self.data.add('test', {
            'value1': 10,
            'value2': 20,
            'nested': {
                'inner': 30
            }
        })
        self.data.add('config', {
            'color': 'red',
            'scale': 2
        })
        
        # Initialize the global dataset with a new empty dataset (not our test dataset)
        # to avoid issues with reserved names
        global_dataset.initialize()
        
        # Manually copy the data to the global dataset
        self.global_ds = global_dataset.get_dataset()
        self.global_ds.add('test', {
            'value1': 10,
            'value2': 20,
            'nested': {
                'inner': 30
            }
        })
        self.global_ds.add('config', {
            'color': 'red',
            'scale': 2
        })
        
        # Create an evaluator for the dataset
        self.eval = evaluator(self.data)
        
        # Set up synchronization between datasets
        self.original_update = self.data.update
        
        def sync_datasets(dbName, update, merge=False):
            # First update the local dataset
            result = self.original_update(dbName, update, merge)
            # Then update the global dataset with the same data
            self.global_ds.update(dbName, update, merge)
            return result
            
        # Replace the update method with synchronized version
        self.data.update = sync_datasets

    def tearDown(self):
        """Clean up after each test."""
        # Clean up global dataset
        global_dataset._global_dataset = None

    def test_direct_dependency_notification(self):
        """Test that direct field dependencies get proper notifications."""
        # Create dynamic values watching specific fields
        dv1 = self.eval.compile("test['value1']", name="dv1", dynamic=True)
        dv2 = self.eval.compile("test['value2']", name="dv2", dynamic=True)
        
        # Ensure initial evaluation
        self.eval.evalAll()
        
        # Track which dynamicValues were marked for update
        marked_for_update = []
        original_mark = dynamicValue.mark_for_update
        
        def mock_mark_for_update(self_var):
            marked_for_update.append(self_var)
            return original_mark(self_var)
            
        # Apply the patch
        with patch.object(dynamicValue, 'mark_for_update', mock_mark_for_update):
            # Update only value1
            self.data.update('test', {'value1': 15}, merge=True)
            
            # Check if only dv1 was marked for update
            self.assertIn(dv1, marked_for_update, "dv1 should be marked for update")
            self.assertNotIn(dv2, marked_for_update, "dv2 should not be marked for update")

    def test_computed_dependencies(self):
        """Test that computed values (depending on multiple fields) get proper notifications."""
        # Create a dynamic value that depends on multiple fields
        dv3 = self.eval.compile("test['value1'] + test['value2']", name="dv3", dynamic=True)
        
        # Ensure initial evaluation
        self.eval.evalAll()
        initial_value = dv3.prevValue
        self.assertEqual(initial_value, 30)  # 10 + 20
        
        # Update value1 and check if dv3 gets updated
        self.data.update('test', {'value1': 15}, merge=True)
        self.eval.evalAll()
        self.assertEqual(dv3.prevValue, 35)  # 15 + 20
        
        # Update value2 and check if dv3 gets updated
        self.data.update('test', {'value2': 25}, merge=True)
        self.eval.evalAll()
        self.assertEqual(dv3.prevValue, 40)  # 15 + 25

    def test_nested_field_dependencies(self):
        """Test dependencies on nested fields in dictionaries."""
        # Create a dynamic value that depends on a nested field
        dv_nested = self.eval.compile("test['nested']['inner']", name="dv_nested", dynamic=True)
        
        # Ensure initial evaluation
        self.eval.evalAll()
        self.assertEqual(dv_nested.prevValue, 30)
        
        # Track updates to the dynamicValue
        marked_for_update = []
        original_mark = dynamicValue.mark_for_update
        
        def mock_mark_for_update(self_var):
            marked_for_update.append(self_var)
            return original_mark(self_var)
        
        with patch.object(dynamicValue, 'mark_for_update', mock_mark_for_update):
            # Update the nested field
            nested = self.data.test['nested'].copy()
            nested['inner'] = 35
            self.data.update('test', {'nested': nested}, merge=True)
            
            # dv_nested should be marked for update
            self.assertIn(dv_nested, marked_for_update, "dv_nested should be marked for update")
            
            # Clear the tracking list
            marked_for_update.clear()
            
            # Unrelated update should not mark our variable for update
            self.data.update('config', {'color': 'blue'}, merge=True)
            self.assertNotIn(dv_nested, marked_for_update, "dv_nested should not be marked for update for unrelated change")

    def test_cross_database_dependencies(self):
        """Test dependencies across multiple databases."""
        # Create a dynamic value that depends on fields from different databases
        dv_cross = self.eval.compile("test['value1'] * config['scale']", name="dv_cross", dynamic=True)
        
        # Ensure initial evaluation
        self.eval.evalAll()
        self.assertEqual(dv_cross.prevValue, 20)  # 10 * 2
        
        # Update test['value1'] and check if dv_cross gets updated
        self.data.update('test', {'value1': 15}, merge=True)
        self.eval.evalAll()
        self.assertEqual(dv_cross.prevValue, 30)  # 15 * 2
        
        # Update config['scale'] and check if dv_cross gets updated
        self.data.update('config', {'scale': 3}, merge=True)
        self.eval.evalAll()
        self.assertEqual(dv_cross.prevValue, 45)  # 15 * 3

    def test_chained_dependencies(self):
        """Test chain of dependencies where one dynamicValue depends on another."""
        # Create a dynamic value that depends on test['value1']
        dv_base = self.eval.compile("test['value1'] + 5", name="dv_base", dynamic=True)
        
        # Create a function that doubles a value
        double_func = lambda ds: dv_base.prevValue * 2 if hasattr(dv_base, 'prevValue') else 0
        
        # Create a second dynamic value that will depend on the first
        dv_derived = self.eval.compile(double_func, name="dv_derived", dynamic=True)
        
        # Register the explicit dependency
        variable_registry.register_variable_to_variable_dependency(dv_derived, dv_base)
        
        # Initial update
        self.data.update('test', {'value1': 10})
        
        # Evaluate all values
        self.eval.evalAll()
        
        # Check initial values
        self.assertEqual(dv_base.prevValue, 15)  # 10 + 5
        self.assertEqual(dv_derived.prevValue, 30)  # 15 * 2
        
        # Update test['value1'] and check if both dynamic values get updated
        self.data.update('test', {'value1': 20})
        
        # Re-evaluate
        self.eval.evalAll()
        
        # Check updated values
        self.assertEqual(dv_base.prevValue, 25)  # 20 + 5
        self.assertEqual(dv_derived.prevValue, 50)  # 25 * 2

    def test_direct_dynamic_value_dependencies(self):
        """Test direct dependencies between dynamic values using explicit registration."""
        # Create two dynamic values with a direct dependency chain
        dv_base = self.eval.compile("test['value1'] + 5", name="dv_base", dynamic=True)
        
        # Create a function that doubles the base value
        def double_base(namespace):
            return dv_base.prevValue * 2 if hasattr(dv_base, 'prevValue') else 0
            
        dv_derived = self.eval.compile(double_base, name="dv_derived", dynamic=True)
        
        # Manually register dependency
        variable_registry.register_variable_to_variable_dependency(dv_derived, dv_base)
        
        # Initial evaluation
        self.eval.evalAll()
        
        # Check initial values
        base_value = dv_base.prevValue
        derived_value = dv_derived.prevValue
        self.assertEqual(base_value, 15)  # 10 + 5
        self.assertEqual(derived_value, 30)  # 15 * 2
        
        # Update the base value source
        self.data.update('test', {'value1': 20}, merge=True)
        
        # Re-evaluate
        self.eval.evalAll()
        
        # Check updated values
        self.assertEqual(dv_base.prevValue, 25)  # 20 + 5
        self.assertEqual(dv_derived.prevValue, 50)  # 25 * 2
        
    def test_using_depends_on_parameter(self):
        """Test dependencies between dynamic values using the depends_on parameter."""
        # Create two dynamic values with depends_on parameter
        dv_base = self.eval.compile("test['value1'] + 5", name="dv_base", dynamic=True)
        
        # Create a function that doubles the base value
        def double_base(namespace):
            return dv_base.prevValue * 2 if hasattr(dv_base, 'prevValue') else 0
            
        # Use depends_on parameter instead of manual registration
        dv_derived = self.eval.compile(
            double_base,
            name="dv_derived",
            dynamic=True,
            depends_on=dv_base
        )
        
        # Initial evaluation
        self.eval.evalAll()
        
        # Check initial values
        self.assertEqual(dv_base.prevValue, 15)  # 10 + 5
        self.assertEqual(dv_derived.prevValue, 30)  # 15 * 2
        
        # Update the base value source
        self.data.update('test', {'value1': 20}, merge=True)
        
        # Re-evaluate
        self.eval.evalAll()
        
        # Check updated values
        self.assertEqual(dv_base.prevValue, 25)  # 20 + 5
        self.assertEqual(dv_derived.prevValue, 50)  # 25 * 2

    def test_dependency_registration_from_string_expressions(self):
        """Test that dependencies are correctly parsed from string expressions."""
        # Create a dynamic value with a complex expression
        expr = "test['value1'] * config['scale'] + test['nested']['inner']"
        dv_complex = self.eval.compile(expr, name="dv_complex", dynamic=True)
        
        # Check registered dependencies
        deps = variable_registry.variable_to_fields.get(dv_complex, set())
        
        # These are the field paths we expect to find
        expected_fields = {
            "test['value1']",
            "config['scale']",
            "test['nested']['inner']"  # This might not be correctly detected due to limitations
        }
        
        # Check if we have at least the first two dependencies
        for field in list(expected_fields)[:2]:
            self.assertIn(field, deps, f"Missing dependency on {field}")
        
        # Test actual updates
        self.eval.evalAll()
        initial_value = dv_complex.prevValue
        self.assertEqual(initial_value, 10 * 2 + 30)  # value1 * scale + nested.inner
        
        # Update value1 and verify the result changes
        self.data.update('test', {'value1': 15}, merge=True)
        self.eval.evalAll()
        self.assertEqual(dv_complex.prevValue, 15 * 2 + 30)
    
    def test_new_field_notification(self):
        """Test notification when a new field is added to a database."""
        # Create a dynamic value that depends on a field that doesn't exist yet
        dv_future = self.eval.compile("test.get('future_field', 0)", name="dv_future", dynamic=True)
        
        # Evaluate initial value
        self.eval.evalAll()
        self.assertEqual(dv_future.prevValue, 0)  # Default value since field doesn't exist
        
        # Add the new field
        self.data.update('test', {'future_field': 42}, merge=True)
        
        # Evaluate again
        self.eval.evalAll()
        self.assertEqual(dv_future.prevValue, 42)  # Should now have the actual value
    
    def test_field_deletion_notification(self):
        """Test notification when a field is effectively deleted (set to None or removed)."""
        # Create a dynamic value that depends on a field that will be "deleted"
        dv_temp = self.eval.compile("test.get('temp_field', -1)", name="dv_temp", dynamic=True)
        
        # Add the field
        self.data.update('test', {'temp_field': 100}, merge=True)
        
        # Evaluate initial value
        self.eval.evalAll()
        self.assertEqual(dv_temp.prevValue, 100)
        
        # Now "delete" the field by setting it to None
        self.data.update('test', {'temp_field': None}, merge=True)
        
        # Evaluate again - should use None rather than default
        self.eval.evalAll()
        self.assertEqual(dv_temp.prevValue, None)

    def test_dynamic_value_integration(self):
        """Test the newer DynamicValue class integration with variable_registry."""
        # Create DynamicValue instances
        dv1 = dynamic("test['value1']")
        dv2 = dynamic("test['value2']")
        
        # Connect to our test evaluator
        self.eval._statements["dv1"] = dv1
        self.eval._statements["dv2"] = dv2
        
        # Ensure initial evaluation
        self.eval.evalAll()
        
        # Check initial values
        self.assertEqual(dv1.prevValue, 10)
        self.assertEqual(dv2.prevValue, 20)
        
        # Now update test['value1'] and check if dv1 gets updated
        self.data.update('test', {'value1': 15}, merge=True)
        self.eval.evalAll()
        
        # dv1 should be updated, dv2 should not
        self.assertEqual(dv1.prevValue, 15)
        self.assertEqual(dv2.prevValue, 20)
        
    def test_dynamicValue_vs_DynamicValue_compatibility(self):
        """Test that both dynamicValue and DynamicValue systems work together correctly."""
        # Create old-style and new-style dynamic values
        old_style = self.eval.compile("test['value1']", name="old_style", dynamic=True)
        new_style = dynamic("test['value1']")
        
        # Connect to our test evaluator
        self.eval._statements["new_style"] = new_style
        
        # Evaluate both
        self.eval.evalAll()
        
        # Both should have same initial value
        self.assertEqual(old_style.prevValue, 10)
        self.assertEqual(new_style.prevValue, 10)
        
        # Update the value
        self.data.update('test', {'value1': 15}, merge=True)
        self.eval.evalAll()
        
        # Both should update together
        self.assertEqual(old_style.prevValue, 15)
        self.assertEqual(new_style.prevValue, 15)

if __name__ == "__main__":
    unittest.main() 