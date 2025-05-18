#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simplified test to demonstrate the improved dependency tracking.
"""
import sys
import os
import unittest
import logging

# Add the parent directory to the path so that tinyDisplay can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tinyDisplay.utility.dataset import dataset
from tinyDisplay.utility.evaluator import dynamicValue
from tinyDisplay.utility.variable_dependencies import variable_registry
from tinyDisplay.utility.evaluator import evaluator
from tinyDisplay.utility.dynamic import dynamic


class TestDependencyImprovement(unittest.TestCase):
    """Demonstrates the improvements made to dependency tracking."""
    
    def setUp(self):
        """Set up test environment."""
        # Configure logging to show debug messages
        logging.basicConfig(level=logging.DEBUG)
        
        # Create a fresh dataset with nested structure
        self.data = dataset()
        self.data.add('test', {
            'value1': 10,
            'value2': 20,
            'nested': {
                'inner': 30,
                'deeper': {
                    'value': 40
                }
            }
        })
        
        # Create an evaluator
        self.eval = evaluator(self.data)
    
    def test_nested_field_dependency_detection(self):
        """Test that nested field dependencies are now correctly detected."""
        # Create a dynamic value with nested dependencies
        expr = "test['nested']['inner'] + test['nested']['deeper']['value']"
        dv = self.eval.compile(expr, name="test_nested", dynamic=True)
        
        # Check that dependencies were registered correctly
        deps = variable_registry.variable_to_fields.get(dv, set())
        print(f"\nRegistered dependencies: {deps}")
        
        # We should see both nested paths in the dependencies
        self.assertIn("test['nested']['inner']", deps)
        self.assertIn("test['nested']['deeper']['value']", deps)
        
        # Ensure all parent paths are also registered
        self.assertIn("test['nested']", deps)
        self.assertIn("test['nested']['deeper']", deps)
        
        # Initial evaluation
        self.eval.evalAll()
        initial_value = dv.eval()
        self.assertEqual(initial_value, 70)  # 30 + 40
    
    def test_nested_field_update_notification(self):
        """Test that updates to nested fields trigger notifications correctly."""
        # Create a dynamic value that depends on a nested field
        dv = self.eval.compile("test['nested']['inner']", name="test_inner", dynamic=True)
        
        # Initial evaluation
        self.eval.evalAll()
        initial_value = dv.eval()
        self.assertEqual(initial_value, 30)
        
        # Reset needs_update flag
        dv._needs_update = False
        
        # Update the nested field with a new value
        nested = self.data.test['nested'].copy()
        nested['inner'] = 35
        self.data.update('test', {'nested': nested})
        
        # Check that the variable was marked for update
        self.assertTrue(dv._needs_update, 
                      "Variable not marked for update when nested field changed")
        
        # Re-evaluate and check new value
        new_value = dv.eval()
        self.assertEqual(new_value, 35)
    
    def test_deep_nested_update(self):
        """Test updates to deeply nested fields."""
        # Create a dynamic value dependent on a deeply nested field
        dv = self.eval.compile("test['nested']['deeper']['value']", name="test_deep", dynamic=True)
        
        # Initial evaluation
        self.eval.evalAll()
        initial_value = dv.eval()
        self.assertEqual(initial_value, 40)
        
        # Reset needs_update flag
        dv._needs_update = False
        
        # Update the deeply nested field
        nested = self.data.test['nested'].copy()
        deeper = nested['deeper'].copy()
        deeper['value'] = 45
        nested['deeper'] = deeper
        self.data.update('test', {'nested': nested})
        
        # Check that the variable was marked for update
        self.assertTrue(dv._needs_update, 
                      "Variable not marked for update when deeply nested field changed")
        
        # Re-evaluate and check new value
        new_value = dv.eval()
        self.assertEqual(new_value, 45)
    
    def test_new_dynamic_value_system(self):
        """Test that the new DynamicValue system works with improved dependency tracking."""
        # Create DynamicValue objects for nested fields
        dv1 = dynamic("test['nested']['inner']")
        dv2 = dynamic("test['nested']['deeper']['value']")
        
        # Create mock evaluator for DynamicValue evaluation
        class MockEvaluator:
            def __init__(self, dataset):
                self.dataset = dataset
                
            def eval_expression(self, expr):
                # Always use the current dataset values
                return eval(expr, {}, {'test': self.dataset.test})
                
        mock_evaluator = MockEvaluator(self.data)
        
        # Initial evaluation
        v1 = dv1.eval()
        v2 = dv2.eval()
        
        # Check initial values
        self.assertEqual(v1, 30)
        self.assertEqual(v2, 40)
        
        # Reset needs_update flags
        dv1.needs_update = False
        dv2.needs_update = False
        
        # Update a nested field
        nested = self.data.test['nested'].copy()
        nested['inner'] = 35
        self.data.update('test', {'nested': nested})
        
        # Re-evaluate values after update
        v1 = dv1.eval()
        v2 = dv2.eval()
        
        # Check if values were updated
        self.assertEqual(v1, 35)
        self.assertEqual(v2, 40)
        
        # Verify that dv1 was marked for update and dv2 wasn't
        self.assertTrue(dv1.changed, "DynamicValue.changed should be True after update")
        self.assertFalse(dv2.changed, "Unrelated DynamicValue should not be marked as changed")


if __name__ == "__main__":
    unittest.main() 