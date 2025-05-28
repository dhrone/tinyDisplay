"""
Test the dynamic value update functionality.

This test specifically focuses on whether widgets correctly detect
changes to their dynamic values when the underlying data changes.
"""
import pytest
from PIL import Image

from tinyDisplay.render.widget import text
from tinyDisplay.utility.dataset import dataset
from tinyDisplay.utility.dynamic import dynamic


def test_widget_detects_dataset_changes():
    """Test that a widget detects changes in its dataset."""
    # Create a dataset with an initial value
    test_data = {"artist": "Sting"}
    ds = dataset({"db": test_data})
    
    # Create a text widget that uses the dynamic value
    # Note: Using string expression which has worked traditionally
    widget = text(
        dvalue="f\"Artist {db['artist']}\"",  # Use string expression directly
        dataset=ds,  # Pass the dataset to the widget
        size=(100, 20)  # Set a size for the widget
    )
    
    # Check if widget has been registered with the dependency system
    from tinyDisplay.utility.dynamic import dependency_registry
    print("\nDependencies registered for db:", dependency_registry.dependencies.get("db"))
    
    # Register the widget with the dependency explicitly for testing
    dependency_registry.register(widget, "db")
    print("After manual registration:", dependency_registry.dependencies.get("db"))
    
    # First render - should return that it changed (initial render)
    img1, changed1 = widget.render(force=True)  # Force=True to ensure it shows as changed
    assert changed1, "Initial render should indicate the widget changed"
    
    # Check the widget's repr value which should contain the text
    print("Initial widget repr value:", widget._reprVal)
    
    # Print all the widget's dynamic values for debugging
    print("\nAll dynamic statements in widget:")
    for key, stmt in widget._dV._statements.items():
        print(f"  {key}: {getattr(stmt, 'prevValue', 'unknown')}")
    
    # Second render - should return no change since nothing has changed
    img2, changed2 = widget.render()
    assert not changed2, "Second render should indicate no change"
    
    # Update the data in the dataset
    test_data["artist"] = "Moby"
    ds.update("db", test_data)
    
    # Check if widget has the _needs_update flag
    print("\nWidget needs update?", hasattr(widget, "_needs_update") and widget._needs_update)
    
    # Force mark widget for update
    widget.mark_for_update()
    print("After mark_for_update: needs_update=", widget._needs_update)
    
    # Third render - should detect the data change and return changed=True
    img3, changed3 = widget.render()
    print("Third render changed?", changed3)
    
    # Check text content after update
    print("Updated widget repr value:", widget._reprVal)
    
    # Run a manual update on all dynamic values
    print("\nRunning manual evaluation of all dynamic statements:")
    for key, stmt in widget._dV._statements.items():
        try:
            value = stmt.eval()
            print(f"  {key}: changed={getattr(stmt, '_changed', 'unknown')}, value={value}")
        except Exception as e:
            print(f"  {key}: Error evaluating - {e}")
        
    # Expect the rendering to change due to the update
    assert changed3, "Widget should detect data change and report it changed"


def test_widget_detects_dataset_changes_with_dvalue():
    """Test that a widget detects changes using traditional dvalue method."""
    # Create a dataset with an initial value
    test_data = {"message": "Hello"}
    ds = dataset({"data": test_data})
    
    # Create a text widget that uses the dynamic value with the legacy dvalue approach
    widget = text(
        dvalue="data['message']",  # Dynamic value using traditional syntax
        dataset=ds,  # Pass the dataset to the widget
        size=(100, 20)  # Set a size for the widget
    )
    
    # Check if widget has been registered with the dependency system
    from tinyDisplay.utility.dynamic import dependency_registry
    print("\nDependencies registered for data:", dependency_registry.dependencies.get("data"))
    
    # Register the widget with the dependency explicitly for testing
    dependency_registry.register(widget, "data")
    print("After manual registration:", dependency_registry.dependencies.get("data"))
    
    # First render - should return that it changed (initial render)
    img1, changed1 = widget.render(force=True)  # Force=True to ensure it shows as changed
    assert changed1, "Initial render should indicate the widget changed"
    
    # Check the widget's repr value which should contain the text
    print("Initial widget repr value:", widget._reprVal)
    
    # Second render - should return no change since nothing has changed
    img2, changed2 = widget.render()
    assert not changed2, "Second render should indicate no change"
    
    # Update the data in the dataset
    test_data["message"] = "World"
    ds.update("data", test_data)
    
    # Check if widget has the _needs_update flag
    print("\nWidget needs update?", hasattr(widget, "_needs_update") and widget._needs_update)
    
    # Force mark widget for update
    widget.mark_for_update()
    print("After mark_for_update: needs_update=", widget._needs_update)
    
    # Third render - should detect the data change and return changed=True
    img3, changed3 = widget.render()
    print("Third render changed?", changed3)
    
    # Check text content after update
    print("Updated widget repr value:", widget._reprVal)
        
    # Expect the rendering to change due to the update
    assert changed3, "Widget should detect data change and report it changed"


def test_dynamic_format_string():
    """Test using dynamic values in format strings."""
    # Create a dataset with initial values
    test_data = {"first": "Hello", "last": "World"}
    ds = dataset({"data": test_data})
    
    # Create a text widget that uses format string with multiple dataset values
    widget = text(
        dvalue="f\"{data['first']} {data['last']}\"",  # Correctly quoted f-string
        dataset=ds,
        size=(100, 20)
    )
    
    # Register the widget with the dependency explicitly for testing
    from tinyDisplay.utility.dynamic import dependency_registry
    dependency_registry.register(widget, "data")
    print("\nAfter manual registration:", dependency_registry.dependencies.get("data"))
    
    # Initial render
    img1, changed1 = widget.render(force=True)
    print("Initial widget repr value:", widget._reprVal)
    
    # Update just one part of the data
    test_data["last"] = "Universe"
    ds.update("data", test_data)
    
    # Force mark widget for update
    widget.mark_for_update()
    
    # Render after update - should detect change
    img2, changed = widget.render()
    print("After update widget repr value:", widget._reprVal)
    assert changed, "Widget should detect partial data change"
    
    # Update another part
    test_data["first"] = "Goodbye"
    ds.update("data", test_data)
    
    # Force mark widget for update
    widget.mark_for_update()
    
    # Render after second update
    img3, changed = widget.render()
    print("After second update widget repr value:", widget._reprVal)
    assert changed, "Widget should detect second data change" 