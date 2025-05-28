#!/usr/bin/env python3
"""Test enhanced widget conversion with different widget types"""

from migration_tool import WidgetInfo
from dsl_converter import DSLConverter

def test_enhanced_widgets():
    """Test DSL conversion for various widget types"""
    
    converter = DSLConverter()
    
    # Test different widget types
    widgets = [
        WidgetInfo(
            name='gauge',
            file_path='test.py',
            class_name='GaugeWidget',
            methods=['render'],
            attributes={'min': 0, 'max': 100, 'value': 'data.temperature'},
            dynamic_values=[],
            position=(10, 10),
            size=(80, 80)
        ),
        WidgetInfo(
            name='chart',
            file_path='test.py',
            class_name='ChartWidget',
            methods=['render'],
            attributes={'chart_type': 'bar', 'data': 'data.sales'},
            dynamic_values=[],
            position=(100, 10),
            size=(120, 80)
        ),
        WidgetInfo(
            name='checkbox',
            file_path='test.py',
            class_name='CheckboxWidget',
            methods=['render'],
            attributes={'checked': True, 'label': 'Enable notifications'},
            dynamic_values=[],
            position=(10, 100),
            size=(150, 20)
        ),
        WidgetInfo(
            name='slider',
            file_path='test.py',
            class_name='SliderWidget',
            methods=['render'],
            attributes={'min': 0, 'max': 255, 'value': 'data.brightness'},
            dynamic_values=[],
            position=(10, 130),
            size=(100, 20)
        )
    ]
    
    print("=== Testing Enhanced Widget Conversion ===")
    for widget in widgets:
        widget_dsl = converter.convert_widget_info_to_dsl(widget)
        print(f"{widget.name.capitalize()} Widget DSL:")
        print(f"  {widget_dsl}")
        print()
    
    print("=== Enhanced Widget Test Complete ===")

if __name__ == "__main__":
    test_enhanced_widgets() 