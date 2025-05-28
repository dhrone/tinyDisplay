#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Focused test to identify bug in field dependency tracking.
"""
import sys
import os
import unittest
import logging

# Add the parent directory to the path so that tinyDisplay can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tinyDisplay.utility.dataset import dataset
from tinyDisplay.utility.variable_dependencies import variable_registry
from tinyDisplay.utility.evaluator import evaluator, dynamicValue


class TestFieldDependencyBug(unittest.TestCase):
    """Test to identify the specific bug in field dependency tracking."""

    def setUp(self):
        """Set up test environment."""
        # Enable debug logging
        logging.basicConfig(level=logging.DEBUG)
        
        # Create a fresh dataset
        self.data = dataset()
        self.data.add('test', {
            'value1': 10,
            'value2': 20
        })
        
        # Create an evaluator
        self.eval = evaluator(self.data)
        
        # Let's inspect the mark_for_update method
        print("\nChecking mark_for_update method in dynamicValue class:")
        if hasattr(dynamicValue, 'mark_for_update'):
            print(f"  Found mark_for_update: {dynamicValue.mark_for_update}")
        else:
            print("  mark_for_update method not found in dynamicValue class!")
            
        # Check the implementation in evaluator.py
        print("\nInspecting dynamicValue implementation...")
        attrs = [attr for attr in dir(dynamicValue) if not attr.startswith('_')]
        print(f"  Available attributes: {attrs}")
    
    def test_field_dependency_parser(self):
        """Test how field dependencies are parsed from expressions."""
        expression = "test['value1'] + test['value2']"
        
        # Parse dependencies
        dependencies = variable_registry.parse_dependencies_from_expression(expression)
        print(f"\nParsed dependencies: {dependencies}")
        
        # Check if the expected dependencies were found
        self.assertIn("test['value1']", dependencies)
        self.assertIn("test['value2']", dependencies)
        
        # Create a dynamic value
        dv = self.eval.compile(expression, name="test_dv", dynamic=True)
        
        # Check if dependencies were registered with the variable
        var_deps = variable_registry.variable_to_fields.get(dv, set())
        print(f"Registered dependencies: {var_deps}")
        
        # Check for both expected dependencies
        self.assertIn("test['value1']", var_deps)
        self.assertIn("test['value2']", var_deps)
    
    def test_nested_field_detection(self):
        """Test detection of nested field dependencies."""
        # Add nested data
        self.data.update('test', {'nested': {'inner': 30}})
        
        # Create an expression with nested access
        expression = "test['nested']['inner'] * 2"
        
        # Parse dependencies
        dependencies = variable_registry.parse_dependencies_from_expression(expression)
        print(f"\nParsed nested dependencies: {dependencies}")
        
        # Check if nested dependency was found
        self.assertIn("test['nested']['inner']", dependencies,
                    "Nested field dependency not detected correctly")
    
    def test_field_notification(self):
        """Test notification when a field changes."""
        # Create a dynamic value
        dv = self.eval.compile("test['value1']", name="test_dv", dynamic=True)
        
        # Evaluate initially
        self.eval.evalAll()
        initial_value = dv.eval()  # Should be 10
        
        print(f"\nInitial value: {initial_value}")
        
        # Check if the dynamicValue has the needs_update attribute
        if hasattr(dv, '_needs_update'):
            print(f"  _needs_update attribute found: {dv._needs_update}")
        else:
            print("  _needs_update attribute not found!")
        
        # Update the field
        print("\nUpdating test['value1'] to 15")
        self.data.update('test', {'value1': 15})
        
        # Check if marked for update
        if hasattr(dv, '_needs_update'):
            print(f"  _needs_update after field change: {dv._needs_update}")
        else:
            print("  _needs_update attribute not found!")
        
        # Re-evaluate
        print("\nRe-evaluating dynamicValue")
        new_value = dv.eval()
        print(f"  New value: {new_value}")
        
        # Check if value was updated
        self.assertEqual(new_value, 15, 
                        "Value not updated after field change")


if __name__ == "__main__":
    unittest.main() 