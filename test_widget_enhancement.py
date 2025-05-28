#!/usr/bin/env python3
"""Test enhanced widget analysis"""

from migration_tool import WidgetInfo

# Test the enhanced WidgetInfo with new fields
widget = WidgetInfo(
    name='test',
    file_path='test.py', 
    class_name='TestWidget',
    methods=['render'],
    attributes={},
    dynamic_values=[],
    position=(10, 10),
    size=(100, 20),
    animations=['fade_in'],
    bindings=['bind_value'],
    z_order=5,
    visibility='visible'
)

print('Enhanced WidgetInfo created successfully')
print(f'Animations: {widget.animations}')
print(f'Bindings: {widget.bindings}')
print(f'Z-order: {widget.z_order}')
print(f'Visibility: {widget.visibility}') 