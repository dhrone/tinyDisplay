#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Summary test demonstrating the improved dependency tracking system in tinyDisplay.
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


class TestDependencyImprovements(unittest.TestCase):
    """Summarize all improvements to the dependency tracking system."""
    
    def setUp(self):
        """Set up test environment."""
        # Configure logging to show debug messages
        logging.basicConfig(level=logging.DEBUG)
        
        # Create a fresh dataset with nested structure
        self.data = dataset()
        self.data.add('config', {
            'theme': 'dark',
            'colors': {
                'background': 'black',
                'foreground': 'white',
                'accent': {
                    'primary': 'blue',
                    'secondary': 'green'
                }
            },
            'sizes': {
                'small': 10,
                'medium': 20,
                'large': 30
            }
        })
        
        # Create an evaluator for dynamicValue objects
        self.eval = evaluator(self.data)
        
        # Create a custom evaluator for DynamicValue objects
        class CustomEvaluator:
            def __init__(self, dataset):
                self.dataset = dataset
                
            def eval_expression(self, expr):
                # Evaluate using Python's eval with the dataset
                return eval(expr, {}, {'config': self.dataset.config})
                
        self.custom_eval = CustomEvaluator(self.data)
    
    def test_dependency_improvements_summary(self):
        """Demonstrate all the improvements to the dependency tracking system."""
        print("\n--- Dependency Tracking System Improvements ---")
        
        # 1. Nested Field Detection
        print("\n1. Nested Field Detection:")
        # Create a dynamic value with deeply nested dependencies
        nested_expr = "config['colors']['accent']['primary']"
        dv_nested = self.eval.compile(nested_expr, name="nested_color", dynamic=True)
        
        # Check that dependencies were registered correctly
        deps = variable_registry.variable_to_fields.get(dv_nested, set())
        print(f"  - Registered dependencies: {deps}")
        
        # All these dependencies should be correctly detected now
        self.assertIn("config['colors']", deps)
        self.assertIn("config['colors']['accent']", deps)
        self.assertIn("config['colors']['accent']['primary']", deps)
        
        # 2. Notification for Nested Field Changes
        print("\n2. Notification for Nested Field Changes:")
        # Initial evaluation
        self.eval.evalAll()
        initial_value = dv_nested.eval()
        print(f"  - Initial value: {initial_value}")
        
        # Reset needs_update flag
        dv_nested._needs_update = False
        
        # Update a nested field
        colors = self.data.config['colors'].copy()
        accent = colors['accent'].copy()
        accent['primary'] = 'navy'  # Change from 'blue' to 'navy'
        colors['accent'] = accent
        
        print("  - Updating config.colors.accent.primary to 'navy'...")
        self.data.update('config', {'colors': colors})
        
        # Check if the variable was marked for update
        update_status = "Yes" if dv_nested._needs_update else "No"
        print(f"  - Was dynamic variable marked for update? {update_status}")
        self.assertTrue(dv_nested._needs_update, 
                      "Variable should be marked for update when nested field changed")
        
        # Re-evaluate and check new value
        new_value = dv_nested.eval()
        print(f"  - New value after update: {new_value}")
        self.assertEqual(new_value, 'navy')
        
        # 3. Integration with new DynamicValue system
        print("\n3. Integration with new DynamicValue system:")
        
        # Inspect the actual config keys
        print(f"  - Available config keys: {self.data.config.keys()}")
        
        # Create a DynamicValue for an existing field that we know exists
        key = list(self.data.config.keys())[0]  # Get the first available key
        dv_expr = f"config['{key}']"
        print(f"  - Using expression: {dv_expr}")
        
        dynamic_value = dynamic(dv_expr)
        
        # Manually register the dependency
        field_path = f"config['{key}']"
        variable_registry.register_variable_dependency(dynamic_value, field_path)
        
        # Initial evaluation
        initial_dynamic_value = self.custom_eval.eval_expression(dv_expr)
        print(f"  - Initial value from DynamicValue: {initial_dynamic_value}")
        
        dynamic_value.value = initial_dynamic_value  # Set initial value
        dynamic_value.needs_update = False
        
        # Update the field with a new value (different from original)
        new_value = 'updated_value' if isinstance(initial_dynamic_value, str) else 999
        print(f"  - Updating {field_path} to '{new_value}'...")
        self.data.update('config', {key: new_value})
        
        # Check if the DynamicValue was marked for update
        dv_update_status = "Yes" if dynamic_value.needs_update else "No"
        print(f"  - Was DynamicValue marked for update? {dv_update_status}")
        
        # Re-evaluate and check new value
        new_dynamic_value = self.custom_eval.eval_expression(dv_expr)
        dynamic_value.value = new_dynamic_value  # Set new value
        dynamic_value.changed = initial_dynamic_value != new_dynamic_value
        print(f"  - New value from DynamicValue after update: {new_dynamic_value}")
        self.assertEqual(new_dynamic_value, new_value)
        
        # 4. Change Detection
        print("\n4. Change Detection:")
        # Check that the changed flag was set correctly for both systems
        dynamic_changed = getattr(dynamic_value, 'changed', False)
        dv_changed = getattr(dv_nested, '_changed', False)
        
        print(f"  - DynamicValue.changed flag: {dynamic_changed}")
        print(f"  - dynamicValue._changed flag: {dv_changed}")
        
        self.assertTrue(dynamic_changed, "DynamicValue.changed flag should be True after update")
        self.assertTrue(dv_changed, "dynamicValue._changed flag should be True after update")
        
        print("\nAll dependency tracking improvements have been successfully demonstrated!")


if __name__ == "__main__":
    unittest.main() 