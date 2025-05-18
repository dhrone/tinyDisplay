#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Variable Dependencies Demo

This example demonstrates how the variable dependency tracking system
in tinyDisplay optimizes re-evaluation of dynamic variables.
"""

import time
from PIL import Image

from tinyDisplay.utility import dataset
from tinyDisplay.utility.dynamic import dynamic
from tinyDisplay.render.widget import text, progressBar
from tinyDisplay.render.collection import stack, canvas
from tinyDisplay.utility.variable_dependencies import variable_registry

# Create a dataset with some initial values
my_data = dataset()
my_data.add('theme', {
    'text_color': 'white',
    'background': 'black',
    'accent': 'blue',
    'progress': 50
})
my_data.add('stats', {
    'total': 100,
    'completed': 25
})

# Create widgets with dynamic properties that have dependencies
title = text(
    name="title",
    value="Variable Dependencies Demo",
    foreground=dynamic("theme['text_color']"),
    size=(200, 20)
)

# This depends on theme['accent']
subtitle = text(
    name="subtitle",
    value="Optimized variable evaluation",
    foreground=dynamic("theme['accent']"),
    size=(200, 20)
)

# This has multiple dependencies (stats['completed'] and stats['total'])
progress = progressBar(
    name="progress",
    value=dynamic("(stats['completed'] / stats['total']) * 100"),
    size=(200, 20),
    fill=dynamic("theme['accent']")
)

# This also depends on stats['completed'] and stats['total']
status = text(
    name="status",
    value=dynamic("f\"Progress: {stats['completed']}/{stats['total']} ({int((stats['completed'] / stats['total']) * 100)}%)\""),
    size=(200, 20)
)

# Create a stack to hold our widgets
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

# Function to monitor which variables are updated
def print_variable_changes(message):
    print(f"\n{message}")
    print("-" * 50)

# Initial render
print_variable_changes("Initial render (all variables evaluated)")
img, _ = main_display.render(force=True)
img.show()

# Update the theme color only
print_variable_changes("Updating theme['accent'] to 'red'")
my_data.update('theme', {'accent': 'red'})
img, changed = main_display.render()
print(f"Canvas changed: {changed}")
if changed:
    img.show()

# Update the stats data
print_variable_changes("Updating stats['completed'] to 50")
my_data.update('stats', {'completed': 50})
img, changed = main_display.render()
print(f"Canvas changed: {changed}")
if changed:
    img.show()

# Change something with no dependents
print_variable_changes("Updating a value with no dependents")
my_data.update('theme', {'unused_value': 'ignored'})
img, changed = main_display.render()
print(f"Canvas changed: {changed}")

# Show dependency graph
print("\nVariable Dependency Graph:")
print("-" * 50)
for field_path, variables in variable_registry.field_to_variables.items():
    print(f"{field_path} -> {len(variables)} dependent variables")

# Show evaluation efficiency
print("\nEvaluation Efficiency:")
print("-" * 50)
print("When theme['accent'] changes, only these need updating:")
for var in variable_registry.get_all_affected_variables("theme['accent']"):
    if hasattr(var, 'name'):
        print(f"  - {var.name}")

print("\nWhen stats['completed'] changes, only these need updating:")
for var in variable_registry.get_all_affected_variables("stats['completed']"):
    if hasattr(var, 'name'):
        print(f"  - {var.name}") 