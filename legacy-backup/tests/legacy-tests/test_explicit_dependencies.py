#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for explicit dependency management in tinyDisplay.
"""

import unittest
from tinyDisplay.utility.dataset import dataset
from tinyDisplay.utility.evaluator import dynamicValue
from tinyDisplay.utility.dynamic import dynamic
from tinyDisplay.utility.dependency_manager import (
    register_variable, define_dependency, apply_dependencies,
    create_variable, create_variables_from_config,
    dependency_manager
)

class TestExplicitDependencies(unittest.TestCase):
    """Test explicit dependency registration and tracking."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a test dataset
        self.data = dataset({
            "test": {
                "value1": 10,
                "value2": 20
            }
        })
        
        # Clear any existing dependencies from previous tests
        dependency_manager.variables = {}
        dependency_manager.dependencies = {}
    
    def test_depends_on_method(self):
        """Test the fluent depends_on method."""
        # Create dynamic values
        dv1 = dynamic("test['value1']")
        dv2 = dynamic("test['value1'] + test['value2']")
        
        # Register explicit dependency
        dv2.depends_on(dv1)
        
        # Set initial values by forcing evaluation
        self.data._dV._statements["__test__"] = dv1
        self.data._dV._statements["__test2__"] = dv2
        self.data._dV.eval("__test__")
        self.data._dV.eval("__test2__")
        
        # Store initial value
        initial_value = dv2.prevValue
        
        # Update the dataset which should trigger dv1 to be marked for update
        self.data.update("test", {"value1": 30})
        
        # Check that dv2 is also marked for update due to explicit dependency
        self.assertTrue(dv2._needs_update, "dv2 should be marked for update when dv1 changes")
        
        # Force evaluation
        self.data._dV.eval("__test__")
        self.data._dV.eval("__test2__")
        
        # Check that dv2 has a new value
        self.assertNotEqual(dv2.prevValue, initial_value, "dv2's value should have changed")
        self.assertEqual(dv2.prevValue, 50, "dv2's value should be 30 + 20 = 50")
    
    def test_depends_on_parameter(self):
        """Test the depends_on parameter at creation time."""
        # Create dynamic values
        dv1 = dynamic("test['value1']")
        dv2 = dynamic("test['value2'] * 2", depends_on=dv1)
        
        # Set initial values by forcing evaluation
        self.data._dV._statements["__test__"] = dv1
        self.data._dV._statements["__test2__"] = dv2
        self.data._dV.eval("__test__")
        self.data._dV.eval("__test2__")
        
        # Store initial value
        initial_value = dv2.prevValue
        
        # Update dataset with value1 change - should trigger dv2 update via explicit dependency
        self.data.update("test", {"value1": 15})
        
        # Check that dv2 is marked for update
        self.assertTrue(dv2._needs_update, "dv2 should be marked for update when dv1 changes")
        
        # Force evaluation
        self.data._dV.eval("__test__")
        self.data._dV.eval("__test2__")
        
        # dv2's expression only references value2, but it should still update due to dependency on dv1
        self.assertEqual(dv2.prevValue, 40, "dv2's value should be 20 * 2 = 40")
    
    def test_dependency_manager(self):
        """Test dependency management with the DependencyManager."""
        # Create dynamic values
        dv1 = dynamic("test['value1']")
        dv2 = dynamic("test['value2']")
        dv3 = dynamic("test['value1'] + test['value2']")
        
        # Register with the dependency manager
        register_variable("value1", dv1)
        register_variable("value2", dv2)
        register_variable("sum", dv3)
        
        # Define dependencies
        define_dependency("sum", ["value1", "value2"])
        
        # Apply dependencies
        apply_dependencies()
        
        # Set initial values by forcing evaluation
        self.data._dV._statements["__test1__"] = dv1
        self.data._dV._statements["__test2__"] = dv2
        self.data._dV._statements["__test3__"] = dv3
        self.data._dV.eval("__test1__")
        self.data._dV.eval("__test2__")
        self.data._dV.eval("__test3__")
        
        # Store initial value
        initial_value = dv3.prevValue
        
        # Update only value2 - should trigger dv3 update via explicit dependency
        self.data.update("test", {"value2": 25})
        
        # Force evaluation
        self.data._dV.eval("__test1__")
        self.data._dV.eval("__test2__")
        self.data._dV.eval("__test3__")
        
        # Check that dv3 has a new value
        self.assertNotEqual(dv3.prevValue, initial_value, "dv3's value should have changed")
        self.assertEqual(dv3.prevValue, 35, "dv3's value should be 10 + 25 = 35")
    
    def test_create_variables_from_config(self):
        """Test creating variables from configuration."""
        # Configuration for variables
        config = {
            "base_value": {
                "expression": "test['value1']"
            },
            "multiplier": {
                "expression": "test['value2'] / 10"
            },
            "computed": {
                "expression": "test['value1'] * (test['value2'] / 10)",
                "depends_on": ["base_value", "multiplier"]
            }
        }
        
        # Create variables from config
        variables = create_variables_from_config(config)
        
        # Set initial values by forcing evaluation
        for name, var in variables.items():
            self.data._dV._statements[name] = var
            self.data._dV.eval(name)
        
        # Check initial values
        self.assertEqual(variables["base_value"].prevValue, 10)
        self.assertEqual(variables["multiplier"].prevValue, 2)
        self.assertEqual(variables["computed"].prevValue, 20)
        
        # Update value1 only
        self.data.update("test", {"value1": 15})
        
        # Force evaluation
        for name in variables:
            self.data._dV.eval(name)
        
        # Check updated values
        self.assertEqual(variables["base_value"].prevValue, 15)
        self.assertEqual(variables["computed"].prevValue, 30, 
                         "computed should be 15 * 2 = 30")
        
        # Update value2 only
        self.data.update("test", {"value2": 30})
        
        # Force evaluation
        for name in variables:
            self.data._dV.eval(name)
        
        # Check final values
        self.assertEqual(variables["multiplier"].prevValue, 3)
        self.assertEqual(variables["computed"].prevValue, 45,
                         "computed should be 15 * 3 = 45")

if __name__ == "__main__":
    unittest.main() 