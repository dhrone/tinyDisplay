#!/usr/bin/env python3
"""
Test DSL Generation

Simple test to verify the enhanced migration tool generates proper DSL syntax.
"""

from migration_tool import SystemAnalysis, WidgetInfo, AnimationInfo, DataStreamInfo, DynamicValueInfo
from migration_generator import CodeGenerator, GenerationConfig
from dsl_converter import DSLConverter

def test_dsl_generation():
    """Test DSL generation with sample data"""
    
    # Create sample analysis data
    sample_widgets = [
        WidgetInfo(
            name='test_text',
            file_path='test.py',
            class_name='TestTextWidget',
            methods=['render'],
            attributes={'text': 'Hello World'},
            dynamic_values=[],
            position=(10, 10),
            size=(100, 20)
        ),
        WidgetInfo(
            name='progress_bar',
            file_path='test.py',
            class_name='ProgressWidget',
            methods=['render', 'update'],
            attributes={'value': 50},
            dynamic_values=['data.cpu_usage'],
            position=(10, 40),
            size=(80, 10)
        )
    ]
    
    sample_animations = [
        AnimationInfo(
            name='scroll_text',
            animation_type='scroll',
            direction='left',
            timing='linear',
            duration=2000
        )
    ]
    
    sample_dynamic_values = [
        DynamicValueInfo(
            name='cpu_display',
            expression='f"CPU: {cpu_usage}%"',
            dependencies=['cpu_usage'],
            usage_locations=['test.py']
        )
    ]
    
    sample_data_streams = [
        DataStreamInfo(
            key='cpu_usage',
            data_type='float',
            sample_values=[25.5, 30.2, 45.1],
            usage_count=3,
            is_time_series=True
        )
    ]
    
    # Create analysis object
    analysis = SystemAnalysis(
        widgets=sample_widgets,
        data_streams=sample_data_streams,
        dynamic_values=sample_dynamic_values,
        display_config={'width': 128, 'height': 64},
        project_structure={'test': ['test.py']},
        animations=sample_animations,
        dsl_patterns=[]
    )
    
    # Test DSL converter directly
    print("=== Testing DSL Converter ===")
    converter = DSLConverter()
    
    for widget in sample_widgets:
        widget_dsl = converter.convert_widget_info_to_dsl(widget)
        print(f"Widget '{widget.name}' DSL:")
        print(f"  {widget_dsl}")
        print()
    
    for animation in sample_animations:
        animation_dsl = converter.convert_animation_info_to_dsl(animation, "test_widget")
        print(f"Animation '{animation.name}' DSL:")
        print(f"  {animation_dsl}")
        print()
    
    # Test JSON to DSL conversion
    print("=== Testing JSON to DSL Conversion ===")
    sample_json = {
        "canvas": {
            "width": 128,
            "height": 64,
            "widgets": [
                {
                    "type": "text",
                    "content": "System Status",
                    "position": {"x": 5, "y": 5},
                    "z_order": 1
                },
                {
                    "type": "progress",
                    "value": "data.cpu_usage",
                    "position": {"x": 5, "y": 25},
                    "size": {"width": 100, "height": 8},
                    "z_order": 2
                }
            ]
        },
        "animations": [
            {
                "type": "fade",
                "duration": 1000,
                "sync_group": "startup"
            }
        ]
    }
    
    dsl_code = converter.convert_json_to_dsl(sample_json)
    print("Generated DSL from JSON:")
    print(dsl_code)
    print()
    
    # Validate syntax
    is_valid, errors = converter.validate_dsl_syntax(dsl_code)
    print(f"DSL Syntax Valid: {is_valid}")
    if errors:
        print("Validation Errors:")
        for error in errors:
            print(f"  - {error}")
    
    print("\n=== DSL Generation Test Complete ===")

if __name__ == "__main__":
    test_dsl_generation() 