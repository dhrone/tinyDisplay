#!/usr/bin/env python3
"""
Tests for Enhanced Reactive Value System

Comprehensive test suite for the enhanced reactive data binding system,
covering primitive types, collections, validation, serialization, and change tracking.
"""

import pytest
import time
import json
from unittest.mock import Mock, patch
from typing import Any, List, Dict

from src.tinydisplay.core.reactive import (
    ReactiveValue, ReactiveValueType, ReactiveChange, ReactiveCollection,
    ReactiveList, ReactiveDict
)


class TestReactiveValue:
    """Test suite for enhanced ReactiveValue class."""
    
    def test_reactive_value__primitive_types__correct_detection(self):
        """Test reactive value type detection for primitive types."""
        # Test integer
        int_value = ReactiveValue(42)
        assert int_value.value_type == ReactiveValueType.PRIMITIVE
        assert int_value.value == 42
        
        # Test float
        float_value = ReactiveValue(3.14)
        assert float_value.value_type == ReactiveValueType.PRIMITIVE
        assert float_value.value == 3.14
        
        # Test string
        str_value = ReactiveValue("hello")
        assert str_value.value_type == ReactiveValueType.PRIMITIVE
        assert str_value.value == "hello"
        
        # Test boolean
        bool_value = ReactiveValue(True)
        assert bool_value.value_type == ReactiveValueType.PRIMITIVE
        assert bool_value.value is True
        
        # Test None
        none_value = ReactiveValue(None)
        assert none_value.value_type == ReactiveValueType.PRIMITIVE
        assert none_value.value is None
        
    def test_reactive_value__collection_types__correct_detection(self):
        """Test reactive value type detection for collection types."""
        # Test list
        list_value = ReactiveValue([1, 2, 3])
        assert list_value.value_type == ReactiveValueType.COLLECTION
        assert list_value.value == [1, 2, 3]
        
        # Test dict
        dict_value = ReactiveValue({"a": 1, "b": 2})
        assert dict_value.value_type == ReactiveValueType.COLLECTION
        assert dict_value.value == {"a": 1, "b": 2}
        
        # Test set
        set_value = ReactiveValue({1, 2, 3})
        assert set_value.value_type == ReactiveValueType.COLLECTION
        assert set_value.value == {1, 2, 3}
        
        # Test tuple
        tuple_value = ReactiveValue((1, 2, 3))
        assert tuple_value.value_type == ReactiveValueType.COLLECTION
        assert tuple_value.value == (1, 2, 3)
        
    def test_reactive_value__object_types__correct_detection(self):
        """Test reactive value type detection for object types."""
        class CustomObject:
            def __init__(self, value):
                self.value = value
                
        obj = CustomObject(42)
        obj_value = ReactiveValue(obj)
        assert obj_value.value_type == ReactiveValueType.OBJECT
        assert obj_value.value.value == 42
        
    def test_reactive_value__change_notification__observers_called(self):
        """Test that observers are notified of value changes."""
        reactive_value = ReactiveValue(10)
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_value.bind(observer)
        
        # Change value
        reactive_value.value = 20
        
        # Verify observer was called
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.old_value == 10
        assert change.new_value == 20
        assert change.change_type == "update"
        assert change.source == reactive_value.reactive_id
        
    def test_reactive_value__no_change__no_notification(self):
        """Test that setting the same value doesn't trigger notifications."""
        reactive_value = ReactiveValue(10)
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_value.bind(observer)
        
        # Set same value
        reactive_value.value = 10
        
        # Verify no notification
        assert len(changes_received) == 0
        
    def test_reactive_value__validation__valid_value_accepted(self):
        """Test that validation function accepts valid values."""
        reactive_value = ReactiveValue(10)
        reactive_value.set_validation(lambda x: isinstance(x, int) and x >= 0)
        
        # Valid value should be accepted
        reactive_value.value = 20
        assert reactive_value.value == 20
        
    def test_reactive_value__validation__invalid_value_rejected(self):
        """Test that validation function rejects invalid values."""
        reactive_value = ReactiveValue(10)
        reactive_value.set_validation(lambda x: isinstance(x, int) and x >= 0)
        
        # Invalid value should be rejected
        with pytest.raises(ValueError, match="Value validation failed"):
            reactive_value.value = -5
            
        # Value should remain unchanged
        assert reactive_value.value == 10
        
    def test_reactive_value__transformation__value_transformed(self):
        """Test that transformation function modifies values."""
        reactive_value = ReactiveValue(10)
        reactive_value.set_transform(lambda x: x * 2)
        
        # Value should be transformed
        reactive_value.value = 5
        assert reactive_value.value == 10  # 5 * 2
        
    def test_reactive_value__serialization__default_json(self):
        """Test default JSON serialization."""
        # Test primitive value
        reactive_value = ReactiveValue({"key": "value", "number": 42})
        serialized = reactive_value.serialize()
        
        # Should be valid JSON
        data = json.loads(serialized)
        assert data == {"key": "value", "number": 42}
        
    def test_reactive_value__serialization__custom_functions(self):
        """Test custom serialization functions."""
        reactive_value = ReactiveValue("hello")
        
        # Set custom serialization
        reactive_value.set_serialization(
            serialize_func=lambda x: f"custom:{x}",
            deserialize_func=lambda x: x.replace("custom:", "")
        )
        
        # Test serialization
        serialized = reactive_value.serialize()
        assert serialized == "custom:hello"
        
        # Test deserialization
        reactive_value.deserialize("custom:world")
        assert reactive_value.value == "world"
        
    def test_reactive_value__deserialization__default_json(self):
        """Test default JSON deserialization."""
        reactive_value = ReactiveValue(None)
        
        # Deserialize JSON
        reactive_value.deserialize('{"key": "value", "number": 42}')
        assert reactive_value.value == {"key": "value", "number": 42}
        
        # Test fallback to string for invalid JSON
        reactive_value.deserialize("not json")
        assert reactive_value.value == "not json"
        
    def test_reactive_value__change_history__records_changes(self):
        """Test that change history is recorded."""
        reactive_value = ReactiveValue(10)
        
        # Make several changes
        reactive_value.value = 20
        reactive_value.value = 30
        reactive_value.value = 40
        
        # Check history
        history = reactive_value.get_change_history()
        assert len(history) == 3
        
        # Check first change
        assert history[0].old_value == 10
        assert history[0].new_value == 20
        
        # Check last change
        assert history[2].old_value == 30
        assert history[2].new_value == 40
        
    def test_reactive_value__change_history__limited_size(self):
        """Test that change history is limited in size."""
        reactive_value = ReactiveValue(0)
        
        # Make more changes than max history
        for i in range(150):  # More than default max of 100
            reactive_value.value = i
            
        # History should be limited
        history = reactive_value.get_change_history()
        assert len(history) == 100
        
        # Should contain most recent changes
        assert history[-1].new_value == 149
        
    def test_reactive_value__dependencies__added_and_removed(self):
        """Test dependency management."""
        source = ReactiveValue(10)
        dependent = ReactiveValue(0)
        
        # Add dependency
        dependent.add_dependency(source)
        
        # Check dependencies
        assert source in dependent.get_dependencies()
        assert dependent in source.get_dependents()
        
        # Remove dependency
        dependent.remove_dependency(source)
        
        # Check dependencies removed
        assert source not in dependent.get_dependencies()
        assert dependent not in source.get_dependents()
        
    def test_reactive_value__dirty_flag__tracks_changes(self):
        """Test that dirty flag tracks changes."""
        reactive_value = ReactiveValue(10)
        
        # Initially not dirty
        assert not reactive_value.is_dirty
        
        # Change value
        reactive_value.value = 20
        
        # Should be dirty
        assert reactive_value.is_dirty
        
        # Mark clean
        reactive_value.mark_clean()
        
        # Should not be dirty
        assert not reactive_value.is_dirty
        
    def test_reactive_value__deep_equality__collections_compared_correctly(self):
        """Test deep equality comparison for collections."""
        # Test list comparison
        list_value = ReactiveValue([1, 2, [3, 4]])
        
        # Same content should not trigger change
        list_value.value = [1, 2, [3, 4]]
        assert not list_value.is_dirty
        
        # Different content should trigger change
        list_value.value = [1, 2, [3, 5]]
        assert list_value.is_dirty
        
    def test_reactive_value__repr__readable_representation(self):
        """Test string representation of reactive value."""
        reactive_value = ReactiveValue(42, reactive_id="test_value")
        repr_str = repr(reactive_value)
        
        assert "test_value" in repr_str
        assert "primitive" in repr_str
        assert "42" in repr_str


class TestReactiveCollection:
    """Test suite for ReactiveCollection class."""
    
    def test_reactive_collection__item_change_notification__observers_called(self):
        """Test that item-level changes notify observers."""
        collection = ReactiveCollection([1, 2, 3])
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        collection.bind(observer)
        
        # Notify item change
        collection.notify_item_change("[1]", 2, 5, "update")
        
        # Verify observer was called
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.old_value == 2
        assert change.new_value == 5
        assert change.change_type == "update"
        assert change.path == "[1]"
        
    def test_reactive_collection__item_observers__path_specific_notifications(self):
        """Test path-specific item observers."""
        collection = ReactiveCollection({"a": 1, "b": 2})
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        # Bind to specific path
        collection.bind_item(".a", observer)
        
        # Change specific item
        collection.notify_item_change(".a", 1, 10, "update")
        
        # Verify observer was called
        assert len(changes_received) == 1
        
        # Change different item
        collection.notify_item_change(".b", 2, 20, "update")
        
        # Verify observer was not called for different path
        assert len(changes_received) == 1
        
    def test_reactive_collection__unbind_item__observer_removed(self):
        """Test unbinding item observers."""
        collection = ReactiveCollection([1, 2, 3])
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        # Bind and unbind
        collection.bind_item("[0]", observer)
        collection.unbind_item("[0]", observer)
        
        # Change item
        collection.notify_item_change("[0]", 1, 10, "update")
        
        # Verify observer was not called
        assert len(changes_received) == 0


class TestReactiveList:
    """Test suite for ReactiveList class."""
    
    def test_reactive_list__append__item_added_with_notification(self):
        """Test appending items to reactive list."""
        reactive_list = ReactiveList([1, 2])
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_list.bind(observer)
        
        # Append item
        reactive_list.append(3)
        
        # Verify list updated
        assert reactive_list.value == [1, 2, 3]
        
        # Verify notification
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.new_value == 3
        assert change.change_type == "add"
        assert change.path == "[2]"
        
    def test_reactive_list__insert__item_inserted_with_notification(self):
        """Test inserting items into reactive list."""
        reactive_list = ReactiveList([1, 3])
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_list.bind(observer)
        
        # Insert item
        reactive_list.insert(1, 2)
        
        # Verify list updated
        assert reactive_list.value == [1, 2, 3]
        
        # Verify notification
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.new_value == 2
        assert change.change_type == "add"
        assert change.path == "[1]"
        
    def test_reactive_list__remove__item_removed_with_notification(self):
        """Test removing items from reactive list."""
        reactive_list = ReactiveList([1, 2, 3])
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_list.bind(observer)
        
        # Remove item
        reactive_list.remove(2)
        
        # Verify list updated
        assert reactive_list.value == [1, 3]
        
        # Verify notification
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.old_value == 2
        assert change.change_type == "remove"
        assert change.path == "[1]"
        
    def test_reactive_list__pop__item_popped_with_notification(self):
        """Test popping items from reactive list."""
        reactive_list = ReactiveList([1, 2, 3])
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_list.bind(observer)
        
        # Pop item
        result = reactive_list.pop()
        
        # Verify return value and list updated
        assert result == 3
        assert reactive_list.value == [1, 2]
        
        # Verify notification
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.old_value == 3
        assert change.change_type == "remove"
        assert change.path == "[2]"
        
    def test_reactive_list__clear__list_cleared_with_notification(self):
        """Test clearing reactive list."""
        reactive_list = ReactiveList([1, 2, 3])
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_list.bind(observer)
        
        # Clear list
        reactive_list.clear()
        
        # Verify list cleared
        assert reactive_list.value == []
        
        # Verify notification
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.old_value == [1, 2, 3]
        assert change.new_value == []
        assert change.change_type == "clear"
        
    def test_reactive_list__setitem__item_updated_with_notification(self):
        """Test setting items in reactive list."""
        reactive_list = ReactiveList([1, 2, 3])
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_list.bind(observer)
        
        # Set item
        reactive_list[1] = 5
        
        # Verify list updated
        assert reactive_list.value == [1, 5, 3]
        
        # Verify notification
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.old_value == 2
        assert change.new_value == 5
        assert change.change_type == "update"
        assert change.path == "[1]"
        
    def test_reactive_list__getitem__returns_correct_item(self):
        """Test getting items from reactive list."""
        reactive_list = ReactiveList([1, 2, 3])
        
        assert reactive_list[0] == 1
        assert reactive_list[1] == 2
        assert reactive_list[2] == 3
        
    def test_reactive_list__len__returns_correct_length(self):
        """Test getting length of reactive list."""
        reactive_list = ReactiveList([1, 2, 3])
        assert len(reactive_list) == 3
        
        reactive_list.append(4)
        assert len(reactive_list) == 4


class TestReactiveDict:
    """Test suite for ReactiveDict class."""
    
    def test_reactive_dict__setitem__item_added_with_notification(self):
        """Test setting items in reactive dict."""
        reactive_dict = ReactiveDict({"a": 1})
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_dict.bind(observer)
        
        # Add new item
        reactive_dict["b"] = 2
        
        # Verify dict updated
        assert reactive_dict.value == {"a": 1, "b": 2}
        
        # Verify notification
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.new_value == 2
        assert change.change_type == "add"
        assert change.path == ".b"
        
    def test_reactive_dict__setitem__item_updated_with_notification(self):
        """Test updating items in reactive dict."""
        reactive_dict = ReactiveDict({"a": 1, "b": 2})
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_dict.bind(observer)
        
        # Update existing item
        reactive_dict["a"] = 10
        
        # Verify dict updated
        assert reactive_dict.value == {"a": 10, "b": 2}
        
        # Verify notification
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.old_value == 1
        assert change.new_value == 10
        assert change.change_type == "update"
        assert change.path == ".a"
        
    def test_reactive_dict__delitem__item_removed_with_notification(self):
        """Test deleting items from reactive dict."""
        reactive_dict = ReactiveDict({"a": 1, "b": 2})
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_dict.bind(observer)
        
        # Delete item
        del reactive_dict["a"]
        
        # Verify dict updated
        assert reactive_dict.value == {"b": 2}
        
        # Verify notification
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.old_value == 1
        assert change.change_type == "remove"
        assert change.path == ".a"
        
    def test_reactive_dict__pop__item_popped_with_notification(self):
        """Test popping items from reactive dict."""
        reactive_dict = ReactiveDict({"a": 1, "b": 2})
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_dict.bind(observer)
        
        # Pop item
        result = reactive_dict.pop("a")
        
        # Verify return value and dict updated
        assert result == 1
        assert reactive_dict.value == {"b": 2}
        
        # Verify notification
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.old_value == 1
        assert change.change_type == "remove"
        assert change.path == ".a"
        
    def test_reactive_dict__update__multiple_items_updated(self):
        """Test updating reactive dict with another dict."""
        reactive_dict = ReactiveDict({"a": 1})
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_dict.bind(observer)
        
        # Update with another dict
        reactive_dict.update({"b": 2, "c": 3})
        
        # Verify dict updated
        assert reactive_dict.value == {"a": 1, "b": 2, "c": 3}
        
        # Verify notifications (one for each new item)
        assert len(changes_received) == 2
        
    def test_reactive_dict__clear__dict_cleared_with_notification(self):
        """Test clearing reactive dict."""
        reactive_dict = ReactiveDict({"a": 1, "b": 2})
        changes_received = []
        
        def observer(change: ReactiveChange):
            changes_received.append(change)
            
        reactive_dict.bind(observer)
        
        # Clear dict
        reactive_dict.clear()
        
        # Verify dict cleared
        assert reactive_dict.value == {}
        
        # Verify notification
        assert len(changes_received) == 1
        change = changes_received[0]
        assert change.old_value == {"a": 1, "b": 2}
        assert change.new_value == {}
        assert change.change_type == "clear"
        
    def test_reactive_dict__getitem__returns_correct_item(self):
        """Test getting items from reactive dict."""
        reactive_dict = ReactiveDict({"a": 1, "b": 2})
        
        assert reactive_dict["a"] == 1
        assert reactive_dict["b"] == 2
        
    def test_reactive_dict__dict_methods__work_correctly(self):
        """Test dict methods work correctly."""
        reactive_dict = ReactiveDict({"a": 1, "b": 2})
        
        # Test keys, values, items
        assert set(reactive_dict.keys()) == {"a", "b"}
        assert set(reactive_dict.values()) == {1, 2}
        assert set(reactive_dict.items()) == {("a", 1), ("b", 2)}
        
        # Test get
        assert reactive_dict.get("a") == 1
        assert reactive_dict.get("c", "default") == "default"
        
        # Test contains
        assert "a" in reactive_dict
        assert "c" not in reactive_dict
        
        # Test len
        assert len(reactive_dict) == 2


class TestReactiveValuePerformance:
    """Performance tests for reactive values."""
    
    @pytest.mark.performance
    def test_reactive_value__high_frequency_updates__meets_targets(self):
        """Test performance with high frequency updates."""
        reactive_value = ReactiveValue(0)
        
        # Track update times
        start_time = time.perf_counter()
        
        # Perform rapid updates
        for i in range(1000):
            reactive_value.value = i
            
        total_time = time.perf_counter() - start_time
        
        # Should complete under 50ms (target from story)
        assert total_time < 0.05, f"Updates took {total_time:.3f}s, expected <0.05s"
        
    @pytest.mark.performance
    def test_reactive_collection__large_collection__efficient_operations(self):
        """Test performance with large collections."""
        # Create large list
        large_list = list(range(10000))
        reactive_list = ReactiveList(large_list)
        
        start_time = time.perf_counter()
        
        # Perform operations
        reactive_list.append(10000)
        reactive_list.insert(5000, 9999)
        reactive_list.pop()
        
        total_time = time.perf_counter() - start_time
        
        # Should complete efficiently
        assert total_time < 0.1, f"Large collection operations took {total_time:.3f}s" 