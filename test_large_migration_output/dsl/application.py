#!/usr/bin/env python3
"""
Generated tinyDisplay DSL Application
Complex multi-canvas application with widget hierarchies
Migrated from legacy codebase using enhanced migration tool
"""

from tinydisplay.dsl import Canvas, Text, ProgressBar, Image, Button, Label, Gauge, Chart
from tinydisplay.reactive import DataManager, DynamicValuesEngine
from tinydisplay.animation import AnimationGroup
from tinydisplay.widgets.hierarchy_manager import HierarchyManager
from tinydisplay.rendering.canvas_manager import CanvasManager

# Canvas configuration
canvas = Canvas(width=128, height=64)

# Widget definitions
w_widget = Text("w")
t_widget = Text("t")
title_widget = Text("title")
subtitle_widget = Text("subtitle")
progress_widget = ProgressBar(value=0.5)
status_widget = Text("status")
title_widget = Text("title")
subtitle_widget = Text("subtitle")
progress_widget = ProgressBar(value=0.5)
status_widget = Text("status")
title_widget = Text("title")
subtitle_widget = Text("subtitle")
progress_widget = ProgressBar(value=0.5)
status_widget = Text("status")
counter_widget = Text("counter")
makeanimation_widget = Text("makeanimation")
widget_widget = Text("widget")

# Widget hierarchy setup
# Container hierarchy: ds
ds_widget.add_children(db_widget)
# Container hierarchy: my_data
my_data_widget.add_children()

# Add widgets to canvas
canvas.add(w_widget, t_widget, title_widget, subtitle_widget, progress_widget, status_widget, title_widget, subtitle_widget, progress_widget, status_widget, title_widget, subtitle_widget, progress_widget, status_widget, counter_widget, makeanimation_widget, widget_widget)

# Animation definitions
widget_0.animate.marquee(direction='left', speed=1.0, loop=True)
widget_1.animate.marquee(direction='left', speed=1.0, loop=True)
widget_2.animate.marquee(direction='left', speed=1.0, loop=True)
widget_3.animate.marquee(direction='left', speed=1.0, loop=True)
widget_4.animate.marquee(direction='left', speed=1.0, loop=True)
widget_5.animate.marquee(direction='left', speed=1.0, loop=True)
widget_6.animate.marquee(direction='left', speed=1.0, loop=True)
widget_7.animate.marquee(direction='left', speed=1.0, loop=True)
widget_8.animate.marquee(direction='left', speed=1.0, loop=True)
widget_9.animate.marquee(direction='left', speed=1.0, loop=True)
widget_10.animate.marquee(direction='left', speed=1.0, loop=True)
widget_11.animate.marquee(direction='left', speed=1.0, loop=True)
widget_12.animate.rotate()
widget_13.animate.rotate()
widget_14.animate.rotate()
widget_15.animate.rotate()
widget_16.animate.rotate()
widget_17.animate.rotate()
widget_18.animate.rotate()
widget_19.animate.rotate()
widget_20.animate.rotate()
widget_21.animate.marquee(direction='left', speed=1.0, loop=True)
widget_22.animate.slide(direction='left', distance=100)
widget_23.animate.rotate()
widget_24.animate.rotate()
widget_25.animate.rotate()
widget_26.animate.marquee(direction='left', speed=1.0, loop=True)
widget_27.animate.marquee(direction='left', speed=1.0, loop=True)
widget_28.animate.marquee(direction='left', speed=1.0, loop=True)
widget_29.animate.marquee(direction='left', speed=1.0, loop=True)
widget_30.animate.marquee(direction='left', speed=1.0, loop=True)
widget_31.animate.marquee(direction='left', speed=1.0, loop=True)
widget_32.animate.marquee(direction='left', speed=1.0, loop=True)
widget_33.animate.marquee(direction='left', speed=1.0, loop=True)
widget_34.animate.marquee(direction='left', speed=1.0, loop=True)
widget_35.animate.marquee(direction='left', speed=1.0, loop=True)
widget_36.animate.marquee(direction='left', speed=1.0, loop=True)
widget_37.animate.marquee(direction='left', speed=1.0, loop=True)
widget_38.animate.marquee(direction='left', speed=1.0, loop=True)
widget_39.animate.marquee(direction='left', speed=1.0, loop=True)
widget_40.animate.marquee(direction='left', speed=1.0, loop=True)
widget_41.animate.marquee(direction='left', speed=1.0, loop=True)
widget_42.animate.marquee(direction='left', speed=1.0, loop=True)
widget_43.animate.marquee(direction='left', speed=1.0, loop=True)
widget_44.animate.marquee(direction='left', speed=1.0, loop=True)
widget_45.animate.marquee(direction='left', speed=1.0, loop=True)
widget_46.animate.marquee(direction='left', speed=1.0, loop=True)
widget_47.animate.marquee(direction='left', speed=1.0, loop=True)
widget_48.animate.marquee(direction='left', speed=1.0, loop=True)
widget_49.animate.marquee(direction='left', speed=1.0, loop=True)
widget_50.animate.marquee(direction='left', speed=1.0, loop=True)
widget_51.animate.marquee(direction='left', speed=1.0, loop=True)
widget_52.animate.marquee(direction='left', speed=1.0, loop=True)
widget_53.animate.marquee(direction='left', speed=1.0, loop=True)
widget_54.animate.slide(direction='DOWN', distance=100)
widget_55.animate.slide(direction='DOWN', distance=100)
widget_56.animate.slide(direction='DOWN', distance=100)
widget_57.animate.slide(direction='DOWN', distance=100)
widget_58.animate.slide(direction='DOWN', distance=100)
widget_59.animate.slide(direction='DOWN', distance=100)
widget_60.animate.slide(direction='DOWN', distance=100)
widget_61.animate.slide(direction='DOWN', distance=100)
widget_62.animate.slide(direction='DOWN', distance=100)
widget_63.animate.slide(direction='DOWN', distance=100)
widget_64.animate.slide(direction='DOWN', distance=100)
widget_65.animate.slide(direction='DOWN', distance=100)
widget_66.animate.slide(direction='DOWN', distance=100)
widget_67.animate.slide(direction='DOWN', distance=100)
widget_68.animate.rotate()
widget_69.animate.rotate()
widget_70.animate.rotate()
widget_71.animate.rotate()
widget_72.animate.rotate()

def create_application():
    """Create and configure the complex tinyDisplay application"""
    # Initialize data manager
    data_manager = DataManager()

    # Initialize dynamic values engine
    dv_engine = DynamicValuesEngine(data_manager)

    # Initialize canvas manager
    canvas_manager = CanvasManager([canvas.name for canvas in self.analysis.canvases])

    return canvas_manager, data_manager, dv_engine

if __name__ == "__main__":
    app_components = create_application()
    print("Complex tinyDisplay DSL application created successfully")