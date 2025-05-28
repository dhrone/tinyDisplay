#!/usr/bin/env python3
"""Test enhanced animation analysis and DSL conversion"""

from migration_tool import AnimationInfo
from dsl_converter import DSLConverter

def test_animation_conversion():
    """Test DSL conversion for various animation types"""
    
    converter = DSLConverter()
    
    # Test different animation types
    animations = [
        AnimationInfo(
            name='text_marquee',
            animation_type='marquee',
            direction='left',
            timing='linear',
            duration=None,  # Infinite loop
            sync_group='startup'
        ),
        AnimationInfo(
            name='widget_fade_in',
            animation_type='fade_in',
            timing='ease-in',
            duration=1000,
            sync_group=None
        ),
        AnimationInfo(
            name='panel_slide',
            animation_type='slide',
            direction='right',
            timing='ease-out',
            duration=800,
            sync_group='panel_group'
        ),
        AnimationInfo(
            name='alert_blink',
            animation_type='blink',
            timing='linear',
            duration=500,
            sync_group=None
        ),
        AnimationInfo(
            name='loading_rotate',
            animation_type='rotate',
            timing='linear',
            duration=2000,
            sync_group=None
        ),
        AnimationInfo(
            name='button_pulse',
            animation_type='pulse',
            timing='ease-in-out',
            duration=600,
            sync_group=None
        )
    ]
    
    print("=== Testing Enhanced Animation Conversion ===")
    for animation in animations:
        animation_dsl = converter.convert_animation_info_to_dsl(animation, "test_widget")
        print(f"{animation.name.replace('_', ' ').title()} Animation DSL:")
        print(f"  {animation_dsl}")
        print()
    
    # Test animation coordination patterns
    print("=== Testing Animation Coordination ===")
    
    # Sequential animations
    seq_animation = AnimationInfo(
        name='sequential_fade',
        animation_type='fade_in',
        timing='ease-in',
        duration=500,
        sync_group='sequence_group'
    )
    seq_dsl = converter.convert_animation_info_to_dsl(seq_animation, "widget1")
    print(f"Sequential Animation DSL:")
    print(f"  {seq_dsl}")
    print()
    
    print("=== Animation Conversion Test Complete ===")

if __name__ == "__main__":
    test_animation_conversion() 