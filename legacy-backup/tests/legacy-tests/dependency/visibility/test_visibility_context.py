"""Tests for the visibility context implementation."""

import unittest
import weakref
from unittest.mock import Mock, call
from dataclasses import dataclass

from tinyDisplay.dependency.visibility.context import VisibilityContext


@dataclass(frozen=True)
class MockVisibilityObject:
    """A simple test object that supports weak references."""
    name: str = "test"
    
    def __hash__(self):
        return hash((MockVisibilityObject, self.name))


class TestVisibilityContext(unittest.TestCase):
    """Test cases for VisibilityContext."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.context = VisibilityContext()
        self.obj1 = MockVisibilityObject("obj1")
        self.obj2 = MockVisibilityObject("obj2")
    
    def test_set_visible_updates_state(self):
        """Test that set_visible updates the visibility state."""
        self.context.set_visible(self.obj1, True)
        self.assertTrue(self.context.is_visible(self.obj1))
        
        self.context.set_visible(self.obj1, False)
        self.assertFalse(self.context.is_visible(self.obj1))
    
    def test_default_visibility(self):
        """Test that objects are visible by default."""
        self.assertTrue(self.context.is_visible(self.obj1))
    
    def test_visibility_is_per_object(self):
        """Test that visibility states are independent per object."""
        self.context.set_visible(self.obj1, True)
        self.context.set_visible(self.obj2, False)
        
        self.assertTrue(self.context.is_visible(self.obj1))
        self.assertFalse(self.context.is_visible(self.obj2))
    
    def test_listener_notified_on_change(self):
        """Test that listeners are notified when visibility changes."""
        callback = Mock()
        self.context.add_listener(self.obj1, callback)
        
        # First change should notify
        self.context.set_visible(self.obj1, False)
        callback.assert_called_once_with(self.obj1, False)
        
        # No change, should not notify
        callback.reset_mock()
        self.context.set_visible(self.obj1, False)
        callback.assert_not_called()
        
        # Change back, should notify
        self.context.set_visible(self.obj1, True)
        callback.assert_called_once_with(self.obj1, True)
    
    def test_remove_listener(self):
        """Test that listeners can be removed."""
        callback = Mock()
        self.context.add_listener(self.obj1, callback)
        
        # First change notifies
        self.context.set_visible(self.obj1, False)
        callback.assert_called_once()
        
        # Remove and change again
        callback.reset_mock()
        self.context.remove_listener(self.obj1, callback)
        self.context.set_visible(self.obj1, True)
        callback.assert_not_called()
    
    def test_weak_references(self):
        """Test that objects are weakly referenced and don't prevent garbage collection."""
        # Create an object and add it to the context
        obj = MockVisibilityObject("test")
        self.context.set_visible(obj, False)
        
        # Verify the object is tracked
        self.assertIn(obj, self.context)
        self.assertFalse(self.context.is_visible(obj))
        
        # Get the weak reference count before deletion
        import sys
        ref_count_before = sys.getrefcount(obj) if hasattr(sys, 'getrefcount') else None
        
        # Delete the only reference to the object
        obj_id = id(obj)
        del obj
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # The context shouldn't prevent garbage collection of the object
        # We can verify this by checking that the context no longer contains the object
        # by using a custom assertion that handles the weak reference safely
        def is_object_in_context():
            for ref in self.context._weak_refs.values():
                if ref() is not None and id(ref()) == obj_id:
                    return True
            return False
        
        # The object should no longer be in the context
        self.assertFalse(is_object_in_context(), 
                        "Context should not prevent garbage collection of tracked objects")
    
    def test_get_visible_objects(self):
        """Test getting all visible objects."""
        # Initially no objects are explicitly set
        self.assertEqual(len(self.context.get_visible_objects()), 0)
        
        # Add some objects with different visibilities
        obj3 = MockVisibilityObject("obj3")
        self.context.set_visible(self.obj1, True)
        self.context.set_visible(self.obj2, False)
        self.context.set_visible(obj3, True)
        
        # Should only get back the visible ones
        visible = self.context.get_visible_objects()
        self.assertEqual(len(visible), 2)
        self.assertIn(self.obj1, visible)
        self.assertIn(obj3, visible)
        self.assertNotIn(self.obj2, visible)
    
    def test_contains(self):
        """Test the __contains__ method."""
        self.assertNotIn(self.obj1, self.context)
        self.context.set_visible(self.obj1, True)
        self.assertIn(self.obj1, self.context)
    
    def test_len(self):
        """Test the __len__ method."""
        self.assertEqual(len(self.context), 0)
        self.context.set_visible(self.obj1, True)
        self.assertEqual(len(self.context), 1)
        self.context.set_visible(self.obj2, False)
        self.assertEqual(len(self.context), 2)


if __name__ == '__main__':
    unittest.main()
