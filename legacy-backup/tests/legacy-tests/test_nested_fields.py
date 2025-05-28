#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for nested field updates and dependency tracking.
"""
import sys
import os
import unittest
import logging
from unittest.mock import Mock, patch

# Add the parent directory to the path so that tinyDisplay can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tinyDisplay.utility.dataset import dataset
from tinyDisplay.utility.variable_dependencies import variable_registry
from tinyDisplay.utility.evaluator import evaluator, dynamicValue


class TestNestedFieldUpdates(unittest.TestCase):
    """Test case for nested field updates and dependency detection."""
    
    def setUp(self):
        # Configure logging to show debug messages
        logging.basicConfig(level=logging.DEBUG)
        
        # Create a fresh dataset with nested structure
        self.data = dataset()
        self.data.add('test', {
            'value': 10,
            'nested': {
                'inner': 20,
                'deeper': {
                    'value': 30
                }
            }
        })
        
        # Create an evaluator
        self.eval = evaluator(self.data)
    
    def test_nested_field_dependency_detection(self):
        """Test if nested field dependencies are properly detected."""
        # Create a dynamic value that directly depends on a nested field
        dv_nested = self.eval.compile("test['nested']['inner']", name="dv_nested", dynamic=True)
        
        # Check registered dependencies for this variable
        deps = variable_registry.variable_to_fields.get(dv_nested, set())
        print(f"\nRegistered dependencies for dv_nested: {deps}")
        
        # The expression should have registered a dependency on the nested field
        # However, due to the regex issue in parse_dependencies_from_expression,
        # it might only register "test['nested']" instead of "test['nested']['inner']"
        self.assertIn("test['nested']['inner']", deps, 
                      "Dependency on nested field not properly registered")
    
    def test_nested_field_update_notification(self):
        """Test if updates to nested fields trigger the right notifications."""
        # Create a dynamic value depending on the nested field
        dv_nested = self.eval.compile("test['nested']['inner']", name="dv_nested", dynamic=True)
        
        # Initial evaluation
        self.eval.evalAll()
        initial_value = dv_nested.prevValue
        self.assertEqual(initial_value, 20)
        
        # Track mark_for_update calls
        mark_spy = Mock(wraps=dv_nested.mark_for_update)
        dv_nested.mark_for_update = mark_spy
        
        # Update the nested field by creating a new nested dict with a different value
        nested = self.data.test['nested'].copy()
        
        # Make sure we're changing the value from what it currently is
        current_value = self.data.test['nested']['inner']
        new_value = current_value + 5  # Make sure we're actually changing the value
        
        print(f"\nCurrent inner value: {current_value}, new value: {new_value}")
        nested['inner'] = new_value
        
        # Update the dataset
        self.data.update('test', {'nested': nested})
        
        # Check if mark_for_update was called
        print(f"\nmark_for_update called: {mark_spy.called}")
        self.assertTrue(mark_spy.called, 
                       "mark_for_update not called when nested field was updated")
        
        # Re-evaluate and check if value was updated
        self.eval.evalAll()
        new_actual_value = dv_nested.prevValue
        self.assertEqual(new_actual_value, new_value,
                        "Value not updated after nested field change")
    
    def test_direct_nested_update(self):
        """
        Test a more direct approach to nested field updates.
        
        This test demonstrates that the issue is not with the dependency tracking
        but with how nested field updates are handled in the dataset.
        """
        # Manually construct a variable_registry notification to test the infrastructure
        dv_direct = self.eval.compile("test['nested']['inner']", name="dv_direct", dynamic=True)
        
        # Initial evaluation
        self.eval.evalAll()
        initial_value = dv_direct.prevValue
        self.assertEqual(initial_value, 20)
        
        # Set needs_update to False so we can detect when it changes
        dv_direct._needs_update = False
        
        # Directly notify the dependency system about the nested field change
        variable_registry.notify_field_change("test['nested']['inner']")
        
        # Check if variable was marked for update
        self.assertTrue(dv_direct._needs_update,
                       "Variable not marked for update after direct notification")
        
        # This proves the dependency notification system works,
        # but the dataset isn't notifying about nested fields correctly
    
    def test_field_update_visibility(self):
        """Test to see how field updates are handled in the dataset."""
        # Create a dynamic value that depends on the whole nested dictionary
        dv_parent = self.eval.compile("test['nested']", name="dv_parent", dynamic=True)
        
        # Create a dynamic value that depends on a specific nested field
        dv_child = self.eval.compile("test['nested']['inner']", name="dv_child", dynamic=True)
        
        # Initial evaluation
        self.eval.evalAll()
        parent_value = dv_parent.prevValue
        child_value = dv_child.prevValue
        self.assertEqual(child_value, 20)
        
        # Reset update flags
        dv_parent._needs_update = False
        dv_child._needs_update = False
        
        # Create a new modified dictionary rather than modifying in place
        nested = self.data.test['nested'].copy()  # Make a copy
        nested['inner'] = 25  # Change a value
        
        # Add debug to check what the value looks like before update
        print(f"\nBefore update - test['nested']: {self.data.test['nested']}")
        print(f"Modified nested dict: {nested}")
        print(f"Dictionary id before: {id(self.data.test['nested'])}, modified: {id(nested)}")
        
        # Use a hook to see what field change notifications are sent
        original_notify = variable_registry.notify_field_change
        notifications = []
        
        def notify_hook(field_path):
            notifications.append(field_path)
            return original_notify(field_path)
        
        # Replace notification method with our hook
        variable_registry.notify_field_change = notify_hook
        
        # Update the dataset
        self.data.update('test', {'nested': nested})
        
        # Restore original methods
        variable_registry.notify_field_change = original_notify
        
        # Print debugging info
        print(f"After update - test['nested']: {self.data.test['nested']}")
        print(f"Dictionary id after: {id(self.data.test['nested'])}")
        print(f"Field change notifications: {notifications}")
        print(f"dv_parent needs update: {dv_parent._needs_update}")
        print(f"dv_child needs update: {dv_child._needs_update}")
        
        # Add direct dependency check debug
        parent_deps = variable_registry.variable_to_fields.get(dv_parent, set())
        child_deps = variable_registry.variable_to_fields.get(dv_child, set())
        print(f"dv_parent dependencies: {parent_deps}")
        print(f"dv_child dependencies: {child_deps}")
        
        # Check that both variables were marked for update after the dataset update
        self.assertTrue(dv_parent._needs_update, 
                       "Parent variable not marked for update")
        self.assertTrue(dv_child._needs_update, 
                       "Child variable not marked for update")
        
        # Reset update flags for further tests
        dv_parent._needs_update = False
        dv_child._needs_update = False
        
        # Try direct notification as a test
        print("\nForcing notifications manually to verify mechanism works:")
        variable_registry.notify_field_change("test['nested']")
        print(f"After direct parent notify - dv_parent: {dv_parent._needs_update}, dv_child: {dv_child._needs_update}")
        
        # Reset again
        dv_parent._needs_update = False
        dv_child._needs_update = False
        
        variable_registry.notify_field_change("test['nested']['inner']")
        print(f"After direct child notify - dv_parent: {dv_parent._needs_update}, dv_child: {dv_child._needs_update}")


if __name__ == "__main__":
    unittest.main() 