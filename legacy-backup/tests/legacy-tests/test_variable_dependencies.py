#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for the variable dependency tracking system.
"""
import unittest
from unittest.mock import Mock, patch

from tinyDisplay.utility import dataset
from tinyDisplay.utility.variable_dependencies import VariableDependencyRegistry, variable_registry
from tinyDisplay.utility.evaluator import dynamicValue, evaluator
from tinyDisplay.utility.dynamic import dynamic

class TestDependencyDetection(unittest.TestCase):
    """Test the dependency detection from expressions."""
    
    def setUp(self):
        # Create a fresh registry for each test
        self.registry = VariableDependencyRegistry()
    
    def test_bracket_notation_detection(self):
        """Test detection of dependencies in bracket notation."""
        expression = "db['value'] + theme['color']"
        dependencies = self.registry.parse_dependencies_from_expression(expression)
        
        self.assertEqual(len(dependencies), 2)
        self.assertIn("db['value']", dependencies)
        self.assertIn("theme['color']", dependencies)
    
    def test_dot_notation_detection(self):
        """Test detection of dependencies in dot notation."""
        expression = "db.value + theme.color"
        dependencies = self.registry.parse_dependencies_from_expression(expression)
        
        self.assertEqual(len(dependencies), 2)
        self.assertIn("db.value", dependencies)
        self.assertIn("theme.color", dependencies)
    
    def test_mixed_notation_detection(self):
        """Test detection of dependencies in mixed notation."""
        expression = "db['value'] + theme.color"
        dependencies = self.registry.parse_dependencies_from_expression(expression)
        
        self.assertEqual(len(dependencies), 2)
        self.assertIn("db['value']", dependencies)
        self.assertIn("theme.color", dependencies)
    
    def test_complex_expression_detection(self):
        """Test detection in complex expressions with functions and operators."""
        expression = "f\"Progress: {int((stats['completed'] / stats['total']) * 100)}%\""
        dependencies = self.registry.parse_dependencies_from_expression(expression)
        
        self.assertEqual(len(dependencies), 2)
        self.assertIn("stats['completed']", dependencies)
        self.assertIn("stats['total']", dependencies)
    
    def test_normalize_field_path(self):
        """Test normalization of field paths."""
        self.assertEqual(self.registry._normalize_field_path("db['key']"), "db['key']")
        self.assertEqual(self.registry._normalize_field_path("db.key"), "db['key']")
    
    def test_extract_db_name(self):
        """Test extraction of database names from field paths."""
        self.assertEqual(self.registry._extract_db_name("db['key']"), "db")
        self.assertEqual(self.registry._extract_db_name("db.key"), "db")
        self.assertIsNone(self.registry._extract_db_name("invalid"))

class TestDependencyRegistration(unittest.TestCase):
    """Test dependency registration and tracking."""
    
    def setUp(self):
        self.registry = VariableDependencyRegistry()
        self.var1 = Mock(name="var1")
        self.var2 = Mock(name="var2")
        self.var3 = Mock(name="var3")
    
    def test_register_variable_dependency(self):
        """Test registering a variable dependency on a field."""
        self.registry.register_variable_dependency(self.var1, "db['key']")
        
        self.assertIn(self.var1, self.registry.field_to_variables["db['key']"])
        self.assertIn("db['key']", self.registry.variable_to_fields[self.var1])
    
    def test_register_variable_to_variable_dependency(self):
        """Test registering dependencies between variables."""
        self.registry.register_variable_to_variable_dependency(self.var2, self.var1)
        
        self.assertIn(self.var2, self.registry.variable_dependencies[self.var1])
    
    def test_get_dependent_variables(self):
        """Test retrieving variables dependent on a field."""
        self.registry.register_variable_dependency(self.var1, "db['key']")
        self.registry.register_variable_dependency(self.var2, "db['key']")
        
        dependents = self.registry.get_dependent_variables("db['key']")
        
        self.assertEqual(len(dependents), 2)
        self.assertIn(self.var1, dependents)
        self.assertIn(self.var2, dependents)
    
    def test_get_all_affected_variables(self):
        """Test retrieving all affected variables including transitive dependencies."""
        # Direct dependencies
        self.registry.register_variable_dependency(self.var1, "db['key']")
        
        # Variable-to-variable dependency
        self.registry.register_variable_to_variable_dependency(self.var2, self.var1)
        self.registry.register_variable_to_variable_dependency(self.var3, self.var2)
        
        # Get all affected variables
        affected = self.registry.get_all_affected_variables("db['key']")
        
        self.assertEqual(len(affected), 3)
        self.assertIn(self.var1, affected)  # Direct dependency
        self.assertIn(self.var2, affected)  # Depends on var1
        self.assertIn(self.var3, affected)  # Depends on var2
    
    def test_notify_field_change(self):
        """Test marking dependent variables for update."""
        # Setup mock variables
        self.var1.mark_for_update = Mock()
        self.var2.mark_for_update = Mock()
        self.var3.mark_for_update = Mock()
        
        # Register dependencies
        self.registry.register_variable_dependency(self.var1, "db['key']")
        self.registry.register_variable_to_variable_dependency(self.var2, self.var1)
        self.registry.register_variable_to_variable_dependency(self.var3, self.var2)
        
        # Notify about field change
        self.registry.notify_field_change("db['key']")
        
        # Verify all variables were marked for update
        self.var1.mark_for_update.assert_called_once()
        self.var2.mark_for_update.assert_called_once()
        self.var3.mark_for_update.assert_called_once()
    
    def test_clear_variable_dependencies(self):
        """Test clearing all dependencies for a variable."""
        # Register dependencies
        self.registry.register_variable_dependency(self.var1, "db['key']")
        self.registry.register_variable_to_variable_dependency(self.var2, self.var1)
        
        # Clear dependencies
        self.registry.clear_variable_dependencies(self.var1)
        
        # Verify dependencies were cleared
        self.assertNotIn(self.var1, self.registry.field_to_variables["db['key']"])
        self.assertNotIn(self.var1, self.registry.variable_to_fields)
        self.assertNotIn(self.var1, self.registry.variable_dependencies)
        self.assertNotIn(self.var2, self.registry.variable_dependencies.get(self.var1, set()))

class TestIntegrationWithDataset(unittest.TestCase):
    """Test integration between variable dependencies and dataset."""
    
    def setUp(self):
        # Create a dataset with initial values
        self.data = dataset()
        self.data.add('test', {
            'value1': 10,
            'value2': 20
        })
        
        # Create an evaluator
        self.eval = evaluator(self.data)
        
        # Create some dynamic values
        self.dv1 = self.eval.compile("test['value1']", name="dv1", dynamic=True)
        self.dv2 = self.eval.compile("test['value2']", name="dv2", dynamic=True)
        self.dv3 = self.eval.compile("test['value1'] + test['value2']", name="dv3", dynamic=True)
        
        # Mock the mark_for_update method
        self.original_mark_for_update = dynamicValue.mark_for_update
        dynamicValue.mark_for_update = Mock(wraps=self.original_mark_for_update)
    
    def tearDown(self):
        # Restore the original method
        dynamicValue.mark_for_update = self.original_mark_for_update
    
    def test_dataset_update_notifies_dependencies(self):
        """Test that updating dataset notifies appropriate variables."""
        # Update a value in the dataset
        self.data.update('test', {'value1': 15})
        
        # Check which variables were marked for update
        self.dv1.mark_for_update.assert_called()
        self.dv3.mark_for_update.assert_called()
        
        # dv2 should not be marked for update since it doesn't depend on value1
        self.dv2.mark_for_update.assert_not_called()
    
    def test_only_affected_variables_evaluated(self):
        """Test that only affected variables are re-evaluated."""
        # First evaluation - all variables should be evaluated
        self.eval.evalAll()
        
        # Reset the mock
        dynamicValue.mark_for_update.reset_mock()
        
        # Give all variables a spy to track evaluation
        self.dv1.eval = Mock(wraps=self.dv1.eval)
        self.dv2.eval = Mock(wraps=self.dv2.eval)
        self.dv3.eval = Mock(wraps=self.dv3.eval)
        
        # Update a value in the dataset
        self.data.update('test', {'value1': 25})
        
        # Evaluate all variables
        self.eval.evalAll()
        
        # Only dv1 and dv3 should be evaluated
        self.dv1.eval.assert_called_once()
        self.dv3.eval.assert_called_once()
        
        # dv2 should not be evaluated
        self.dv2.eval.assert_not_called()

class TestDynamicValueEvaluation(unittest.TestCase):
    """Test dynamic value evaluation with dependency tracking."""
    
    def setUp(self):
        # Create a test dataset
        self.data = dataset()
        self.data.add('test', {
            'value1': 10,
            'value2': 20
        })
        
        # Create dynamic values using the dynamic() function
        self.dv1 = dynamic("test['value1']")
        self.dv2 = dynamic("test['value1'] + test['value2']")
        
        # Create a mock evaluator
        self.evaluator = Mock()
        self.evaluator.eval_expression = lambda expr: eval(expr, {}, {'test': self.data.test})
    
    def test_dynamic_value_evaluation(self):
        """Test evaluation of dynamic values."""
        # Initial evaluation
        result1 = self.dv1.eval()
        result2 = self.dv2.eval()
        
        self.assertEqual(result1, 10)
        self.assertEqual(result2, 30)
        
        # Mark as not needing update
        self.dv1.needs_update = False
        self.dv2.needs_update = False
        
        # Update dataset
        self.data.test['value1'] = 15
        
        # Mark dv1 as needing update (simulating notification)
        self.dv1.mark_for_update()
        self.dv2.mark_for_update()
        
        # Re-evaluate
        result1 = self.dv1.eval()
        result2 = self.dv2.eval()
        
        self.assertEqual(result1, 15)
        self.assertEqual(result2, 35)
    
    def test_cached_evaluation(self):
        """Test that values are cached and not re-evaluated when not needed."""
        # Initial evaluation
        self.dv1.eval()
        
        # Store the current value
        self.dv1.value = 42
        self.dv1.needs_update = False
        
        # This should return the cached value without re-evaluating
        result = self.dv1.eval()
        self.assertEqual(result, 42)
        
        # Mark for update and try again
        self.dv1.mark_for_update()
        result = self.dv1.eval()
        self.assertEqual(result, 10)  # Should get the real value from evaluation

if __name__ == "__main__":
    unittest.main() 