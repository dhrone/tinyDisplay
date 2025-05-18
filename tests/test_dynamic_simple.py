#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Very simple test for the dynamic value system.
"""
import sys
import os
import unittest
import logging
from unittest.mock import Mock

# Add the parent directory to the path so that tinyDisplay can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tinyDisplay.utility.dataset import dataset
from tinyDisplay.utility.evaluator import dynamicValue
from tinyDisplay.utility.variable_dependencies import variable_registry
from tinyDisplay.utility.dynamic import dynamic


class TestDynamicValueSimple(unittest.TestCase):
    """Test the DynamicValue system in isolation."""
    
    def setUp(self):
        """Set up test environment."""
        # Configure logging to show debug messages
        logging.basicConfig(level=logging.DEBUG)
        
        # Create a fresh dataset with simple values
        self.data = dataset()
        self.data.add('test', {
            'value': 10
        })
    
    def test_direct_notification(self):
        """Test direct notification to DynamicValue objects."""
        # Create a DynamicValue
        dv = dynamic("test['value']")
        
        # Create a simple evaluator for the DynamicValue
        class SimpleEvaluator:
            def __init__(self, data_dict):
                self.data_dict = data_dict
                
            def eval_expression(self, expr):
                return eval(expr, {}, {'test': self.data_dict})
                
        # Get a reference to the actual dict
        test_dict = self.data.test
        evaluator = SimpleEvaluator(test_dict)
        
        # Initial evaluation
        value = dv.eval()
        self.assertEqual(value, 10)
        
        # Reset needs_update flag
        dv.needs_update = False
        
        # Check for registered dependencies
        deps = variable_registry.variable_to_fields.get(dv, set())
        print(f"\nRegistered dependencies: {deps}")
        self.assertIn("test['value']", deps)
        
        # Verify manual notification works
        print("Testing manual notification...")
        variable_registry.notify_field_change("test['value']")
        self.assertTrue(dv.needs_update, "DynamicValue not marked for update after notification")
        
        # Test evaluation after notification
        # Update the reference data directly
        test_dict['value'] = 20
        
        # Re-evaluate
        value = dv.eval()
        self.assertEqual(value, 20, "DynamicValue not updated to new value")
        
        # Test change detection
        self.assertTrue(dv.changed, "DynamicValue.changed should be True after update")
    
    def test_dataset_notification(self):
        """Test notification via dataset updates."""
        # Create a DynamicValue
        dv = dynamic("test['value']")
        
        # Add test for direct dependency check
        deps = variable_registry.variable_to_fields.get(dv, set())
        print(f"\nDirect dependencies: {deps}")
        
        # Track when mark_for_update is called
        original_mark = dv.mark_for_update
        mark_calls = []
        
        def mock_mark():
            mark_calls.append(True)
            return original_mark()
            
        dv.mark_for_update = Mock(side_effect=mock_mark)
        
        # Create a simple evaluator with direct reference to dataset
        class SimpleEvaluator:
            def __init__(self, data_source):
                self.data_source = data_source
                
            def eval_expression(self, expr):
                # Always use the current dataset values
                return eval(expr, {}, {'test': self.data_source})
                
        evaluator = SimpleEvaluator(self.data.test)
        
        # Initial evaluation
        value = dv.eval()
        self.assertEqual(value, 10)
        
        # Update the dataset
        print("Updating dataset...")
        self.data.update('test', {'value': 20})
        
        # Make sure the evaluator has the updated reference
        evaluator.data_source = self.data.test
        
        # Check if mark_for_update was called
        print(f"mark_for_update called: {len(mark_calls) > 0}")
        self.assertTrue(len(mark_calls) > 0, "mark_for_update not called when dataset was updated")
        
        # Verify evaluation after dataset update
        value = dv.eval()
        self.assertEqual(value, 20, "DynamicValue not updated after dataset change")
        self.assertTrue(dv.changed, "DynamicValue.changed should be True after update")


if __name__ == "__main__":
    unittest.main() 