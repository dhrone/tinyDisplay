#!/usr/bin/env python3
"""
Generated tinyDisplay DSL Application
Migrated from legacy codebase using enhanced migration tool
"""

from tinydisplay.dsl import Canvas, Text, ProgressBar, Image, Button, Label
from tinydisplay.reactive import DataManager, DynamicValuesEngine
from tinydisplay.animation import AnimationGroup

# Canvas configuration
canvas = Canvas(width=128, height=64)

# Widget definitions
customgauge_widget = Text("Widget").position(0, 0).z_order(1)
complexchart_widget = Text("Widget").position(0, 0).z_order(1)
container_widget = Text("Widget").position(0, 0).z_order(1)

# Add widgets to canvas
    canvas.add(
    customgauge_widget,
    complexchart_widget,
    container_widget
)

# Animation definitions
widget_0.animate.marquee(direction="left", speed=1.0, loop=True)
widget_1.animate.fade(duration=1000, from_alpha=0.0, to_alpha=1.0)
widget_2.animate.fade(duration=1000, from_alpha=0.0, to_alpha=1.0)

def create_application():
    """Create and configure the tinyDisplay application"""
    # Initialize data manager
    data_manager = DataManager()


    # Initialize dynamic values engine
    dv_engine = DynamicValuesEngine(data_manager)


    return canvas, data_manager, dv_engine

if __name__ == "__main__":
    canvas, data_manager, dv_engine = create_application()
    print("tinyDisplay DSL application created successfully")