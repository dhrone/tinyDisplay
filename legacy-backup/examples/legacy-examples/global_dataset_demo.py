#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Global Dataset Demo

This example demonstrates how to use the global dataset module in tinyDisplay,
including thread-safe operations.
"""

import time
import threading
from PIL import Image

import tinyDisplay.global_dataset as global_data
from tinyDisplay.utility.dynamic import dynamic
from tinyDisplay.render.widget import text, progressBar
from tinyDisplay.render.collection import stack, canvas

# Initialize the global dataset early in your application
global_data.initialize({
    'theme': {
        'text_color': 'white',
        'background': 'black',
        'accent': 'blue',
    },
    'stats': {
        'total': 100,
        'completed': 25
    },
    'counters': {
        'visits': 0
    }
})

# Create a function that creates widgets that use the global dataset
def create_dashboard():
    """Create a dashboard with widgets that use the global dataset."""
    
    # Get direct access to the dataset if needed
    ds = global_data.get_dataset()
    
    # Create widgets with dynamic properties that depend on global data
    title = text(
        name="title",
        value="Global Dataset Demo",
        foreground=dynamic("theme['text_color']"),
        size=(200, 20),
        dataset=ds  # Pass the dataset to each widget
    )
    
    subtitle = text(
        name="subtitle",
        value="Using the global dataset module",
        foreground=dynamic("theme['accent']"),
        size=(200, 20),
        dataset=ds
    )
    
    progress = progressBar(
        name="progress",
        value=dynamic("(stats['completed'] / stats['total']) * 100"),
        size=(200, 20),
        fill=dynamic("theme['accent']"),
        dataset=ds
    )
    
    status = text(
        name="status",
        value=dynamic("f\"Progress: {stats['completed']}/{stats['total']} ({int((stats['completed'] / stats['total']) * 100)}%)\""),
        size=(200, 20),
        dataset=ds
    )
    
    counter = text(
        name="counter",
        value=dynamic("f\"Visits: {counters['visits']}\""),
        size=(200, 20),
        dataset=ds
    )
    
    content = stack(
        name="content", 
        orientation="vertical",
        gap=5,
        size=(200, 120),
        background=dynamic("theme['background']"),
        dataset=ds
    )
    
    content.append(title)
    content.append(subtitle)
    content.append(progress)
    content.append(status)
    content.append(counter)
    
    main_display = canvas(
        name="main",
        size=(200, 120),
        background=dynamic("theme['background']"),
        dataset=ds
    )
    main_display.append(content)
    
    return main_display

# Function to update data from another part of the application
def update_progress(completed_value):
    """Update the progress in the global dataset.
    
    This could be called from anywhere in your application.
    """
    global_data.update_database('stats', {'completed': completed_value})
    print(f"Updated progress to {completed_value}%")

# Function to change the theme
def change_theme(new_theme):
    """Update the theme in the global dataset.
    
    This could be called from a settings screen or configuration module.
    """
    global_data.update_database('theme', new_theme)
    print(f"Updated theme: {new_theme}")

# Thread-safe counter increment
def increment_visits():
    """Atomically increment the visit counter."""
    new_count = global_data.update_counter('counters', 'visits')
    print(f"Visit counter incremented to {new_count}")

# Demonstrate thread-safe operations
def thread_safe_demo():
    """Demonstrate thread-safe operations with multiple threads."""
    print("\nStarting thread safety demonstration...")
    
    # Create multiple threads that will increment the counter
    threads = []
    for i in range(5):
        thread = threading.Thread(
            target=lambda: [increment_visits() for _ in range(10)],
            name=f"counter-thread-{i}"
        )
        threads.append(thread)
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify the final counter value (should be 50)
    final_count = global_data.get_value('counters', 'visits')
    print(f"Final visit count: {final_count}")
    
    # Example of atomic multi-database update
    global_data.update_multiple({
        'stats': {'total': 200},
        'theme': {'accent': 'green'}
    })
    print("Atomic multi-database update completed")
    
    # Example of with_lock for custom atomic operations
    def complex_operation():
        # Get the current theme
        theme = global_data.get_database('theme')
        
        # Compute a new color based on current setting
        current = theme['text_color']
        new_color = 'black' if current == 'white' else 'white'
        
        # Update the theme
        global_data.update_database('theme', {'text_color': new_color})
        
        return f"Changed text color from {current} to {new_color}"
    
    result = global_data.with_lock(complex_operation)
    print(result)

def main():
    """Run the demo application."""
    # Create the dashboard
    dashboard = create_dashboard()
    
    # Initial render
    print("\nInitial render:")
    img, _ = dashboard.render(force=True)
    img.show()
    
    # Update progress
    time.sleep(1)
    update_progress(50)
    
    # Re-render
    print("\nAfter progress update:")
    img, changed = dashboard.render()
    if changed:
        img.show()
    
    # Change theme
    time.sleep(1)
    change_theme({
        'text_color': 'black',
        'background': 'white',
        'accent': 'red'
    })
    
    # Re-render
    print("\nAfter theme change:")
    img, changed = dashboard.render()
    if changed:
        img.show()
    
    # You can also add new databases at runtime
    time.sleep(1)
    global_data.add_database('user', {
        'name': 'John Doe',
        'role': 'Admin'
    })
    
    print("\nAdded user database to global dataset")
    print(f"User: {global_data.get_database('user')}")
    
    # Run thread safety demo
    thread_safe_demo()
    
    # Final render after thread-safe operations
    print("\nFinal render after thread-safe operations:")
    img, changed = dashboard.render()
    if changed:
        img.show()

if __name__ == "__main__":
    main() 