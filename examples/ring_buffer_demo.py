#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demonstration of the widget ring buffer functionality.

This script demonstrates how to use the ring buffer for testing and debugging
widget rendering, including change detection, animation tracking, and visualization.
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
parent_dir = str(Path(__file__).parent.parent.absolute())
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from tinyDisplay.render.widget import scroll, text
from tinyDisplay.utility import dataset
from tinyDisplay.utility.dynamic import dynamic


def demo_text_widget_variable():
    """Demonstrate tracking changes in a text widget with a variable."""
    print("\n=== DEMO: Text Widget with Variable ===")
    
    # Create dataset with a dynamic value
    db = {"value": "initial"}
    ds = dataset()
    ds.add("db", db)
    
    # Create text widget with buffer size 4
    print("Creating text widget with buffer size 4 and dynamic value")
    w = text(
        name="DynamicText", 
        value=dynamic("db['value']"),  # Use dynamic() instead of dvalue
        dataset=ds, 
        bufferSize=4
    )
    
    # Render twice with same value
    print("\nRendering twice with same value 'initial'")
    w.render()
    w.render()
    
    # Show buffer contents
    print("\nBuffer contents after 2 renders:")
    w.print(2)
    
    # Change the value and render again
    print("\nChanging value to 'changed' and rendering again")
    db["value"] = "changed"
    ds.update("db", db)
    w.render()
    
    # Show buffer contents
    print("\nBuffer contents after value change:")
    w.print(3)
    
    # Save the buffer to a file
    output_file = "text_widget_buffer.png"
    print(f"\nSaving buffer to {output_file}")
    w.save(output_file, 3)
    print(f"Saved to {os.path.abspath(output_file)}")
    
    # Check if images are static
    print(f"\nAre all 3 images identical? {w.static(3)}")
    print(f"Are the last 2 images identical? {w.static(2)}")
    
    # Show buffer statistics
    print("\nBuffer statistics:")
    stats = w.buffer_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


def demo_scroll_widget_animation():
    """Demonstrate tracking animation in a scroll widget."""
    print("\n\n=== DEMO: Scroll Widget Animation ===")
    
    # Create text widget
    t = text(name="ScrolledText", value="This is text in a scroll widget")
    
    # Create scroll widget with 3-tick pause at start and buffer size 5
    print("Creating scroll widget with 3-tick pause and buffer size 5")
    s = scroll(
        name="ScrollDemo",
        widget=t,
        actions=[("pause", 3), ("rtl",)],
        bufferSize=5
    )
    
    # Render several times to show the animation
    print("\nRendering 5 times to capture animation sequence:")
    for i in range(5):
        tick_status = "paused" if i < 3 else "moving"
        print(f"  Render {i+1}: ({tick_status})")
        s.render(tick=i)
        
    # Show buffer contents
    print("\nBuffer contents (5 frames):")
    s.print(5)
    
    # Check static status of different frame combinations
    print("\nStatic analysis:")
    print(f"  First 3 frames static? {s.static(3)}")
    print(f"  All 5 frames static? {s.static(5)}")
    print(f"  Last 2 frames static? {s.static(2)}")
    
    # Save animation frames
    output_file = "scroll_animation.png"
    print(f"\nSaving animation frames to {output_file}")
    s.save(output_file, 5)
    print(f"Saved to {os.path.abspath(output_file)}")


if __name__ == "__main__":
    demo_text_widget_variable()
    demo_scroll_widget_animation()
    print("\nDemonstration complete. Check the output PNG files for visual results.") 