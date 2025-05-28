#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the new dynamic value system.
"""
import unittest
from unittest.mock import Mock, patch

from tinyDisplay.utility import dataset
from tinyDisplay.utility.evaluator import dynamicValue
from tinyDisplay.utility.dynamic import dynamic, dependency_registry
from tinyDisplay.render.widget import text


class TestDynamicValues(unittest.TestCase):
    """Test the dynamic value system."""

    def setUp(self):
        """Set up test environment."""
        # Create a fresh dataset for each test
        self.data = dataset()
        self.data.add('test', {
            'color': 'red',
            'text': 'Hello',
            'value': 42
        })

    def test_dynamic_value_creation(self):
        """Test creating a DynamicValue."""
        dv = dynamic("test['color']")
        self.assertEqual(dv.source, "test['color']")
        self.assertIn('test', dv.dependencies)

    def test_dynamic_function(self):
        """Test the dynamic() function."""
        dv = dynamic("test['value'] * 2")
        self.assertEqual(dv.source, "test['value'] * 2")
        self.assertIsInstance(dv, dynamicValue)

    def test_widget_with_dynamic_values(self):
        """Test creating a widget with dynamic values."""
        # Create a text widget with dynamic values
        t = text(
            name="test_text",
            value=dynamic("test['text']"),
            foreground=dynamic("test['color']"),
            dataset=self.data
        )
        
        # Initial render
        img, changed = t.render(force=True)
        
        # The text should be 'Hello' with color 'red'
        self.assertTrue(changed)
        self.assertEqual(t._value, 'Hello')
        self.assertEqual(t._foreground, 'red')

    def test_dependency_tracking(self):
        """Test dependency tracking."""
        # Create a text widget with dynamic values
        t = text(
            name="test_text",
            value=dynamic("test['text']"),
            foreground=dynamic("test['color']"),
            dataset=self.data
        )
        
        # Check that dependencies were registered
        widgets = dependency_registry.get_dependent_widgets('test')
        self.assertIn(t, widgets)

    def test_update_notification(self):
        """Test that updates notify dependent widgets."""
        # Create a text widget with dynamic values
        t = text(
            name="test_text",
            value=dynamic("test['text']"),
            foreground=dynamic("test['color']"),
            dataset=self.data
        )
        
        # Initial render
        t.render(force=True)
        
        # Mock the mark_for_update method
        original_mark = t.mark_for_update
        t.mark_for_update = Mock()
        
        # Update the dataset
        self.data.update('test', {'text': 'Updated', 'color': 'blue'})
        
        # Check that mark_for_update was called
        t.mark_for_update.assert_called_once()
        
        # Restore original method
        t.mark_for_update = original_mark
        
        # Render again
        img, changed = t.render()
        
        # Check that values were updated
        self.assertTrue(changed)
        self.assertEqual(t._value, 'Updated')
        self.assertEqual(t._foreground, 'blue')

    def test_legacy_d_prefix_compatibility(self):
        """Test backward compatibility with d-prefixed parameters."""
        # Create a text widget with legacy d-prefixed parameters
        t = text(
            name="legacy_test",
            dvalue="test['text']",
            dforeground="test['color']",
            dataset=self.data
        )
        
        # Initial render
        img, changed = t.render(force=True)
        
        # The text should be 'Hello' with color 'red'
        self.assertTrue(changed)
        self.assertEqual(t._value, 'Hello')
        self.assertEqual(t._foreground, 'red')
        
        # Update the dataset
        self.data.update('test', {'text': 'Legacy Updated', 'color': 'green'})
        
        # Render again
        img, changed = t.render()
        
        # Check that values were updated
        self.assertTrue(changed)
        self.assertEqual(t._value, 'Legacy Updated')
        self.assertEqual(t._foreground, 'green')


if __name__ == '__main__':
    unittest.main() 