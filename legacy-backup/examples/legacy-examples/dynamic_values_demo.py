#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dynamic Values Demo

This example demonstrates how to use the new dynamic value system in tinyDisplay.
"""

import time
from PIL import Image

from tinyDisplay.utility import dataset
from tinyDisplay.utility.dynamic import dynamic
from tinyDisplay.render.widget import text, progressBar
from tinyDisplay.render.collection import stack, canvas

# Create a dataset with some initial values
my_data = dataset()
my_data.add('theme', {
    'text_color': 'white',
    'background': 'black',
    'accent': 'blue',
    'progress': 50
})

# Create widgets with dynamic properties
title = text(
    name="title",
    value="Dynamic Values Demo",
    foreground=dynamic("theme['text_color']"),
    size=(200, 20)
)

subtitle = text(
    name="subtitle",
    value="Using the new dynamic() function",
    foreground=dynamic("theme['accent']"),
    size=(200, 20)
)

# Create a progress bar that updates based on theme['progress']
progress = progressBar(
    name="progress",
    value=dynamic("theme['progress']"),
    size=(200, 20),
    fill=dynamic("theme['accent']")
)

# Create a status text that shows the current progress value
status = text(
    name="status",
    value=dynamic("'Progress: ' + str(theme['progress']) + '%'"),
    size=(200, 20)
)

# Stack our widgets vertically
content = stack(
    name="content", 
    orientation="vertical",
    gap=5,
    size=(200, 100),
    background=dynamic("theme['background']")
)

# Add widgets to the stack
content.append(title)
content.append(subtitle)
content.append(progress)
content.append(status)

# Create a main canvas to hold everything
main_display = canvas(
    name="main",
    size=(200, 100),
    background=dynamic("theme['background']")
)
main_display.append(content)

# Initial render
img, _ = main_display.render(force=True)
img.show()

# Demonstrate updating values and seeing automatic updates
print("Initial render complete. Updating values in 2 seconds...")
time.sleep(2)

# Update the theme colors and progress value
my_data.update('theme', {
    'text_color': 'yellow',
    'accent': 'green',
    'progress': 75
})

# Render again - only affected widgets will update
img, _ = main_display.render()
img.show()

print("First update complete. Changing theme in 2 seconds...")
time.sleep(2)

# Change to a dark theme
my_data.update('theme', {
    'text_color': 'lime',
    'background': 'navy',
    'accent': 'red',
    'progress': 100
})

# Final render
img, _ = main_display.render()
img.show()

print("Demo complete!") 