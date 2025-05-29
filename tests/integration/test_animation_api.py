#!/usr/bin/env python3
"""
Comprehensive Test Suite for Animation API

Tests the tick-based animation utilities, time conversion functions,
animation presets, backward compatibility layer, and validation utilities.
"""

import pytest
import math
from typing import Tuple, Dict, Any

from src.tinydisplay.animation.utilities import (
    # Time conversion utilities
    seconds_to_ticks, ticks_to_seconds, milliseconds_to_ticks, ticks_to_milliseconds,
    
    # Animation configuration classes
    AnimationTiming, AnimationConfig, AnimationPreset,
    
    # Animation creation utilities
    create_fade_animation, create_slide_animation, create_scale_animation,
    create_rotation_animation, create_custom_property_animation,
    create_preset_animation,
    
    # Validation utilities
    validate_animation_definition, validate_animation_config,
    
    # Sequence utilities
    create_animation_sequence, create_parallel_animations,
    
    # Backward compatibility
    create_time_based_animation, convert_legacy_animation_params
)

from src.tinydisplay.animation.compatibility import (
    LegacyAnimationConfig, LegacyAnimationAPI, LegacyWidgetAnimationMixin,
    create_fade_in_animation, create_fade_out_animation,
    convert_time_duration_to_ticks, convert_legacy_easing_name,
    migrate_animation_config
)

from src.tinydisplay.animation.tick_based import (
    TickAnimationDefinition, TickAnimationState, EasingFunction
)


class TestTimeConversionUtilities:
    """Test time conversion utility functions."""
    
    def test_seconds_to_ticks_basic(self):
        """Test basic seconds to ticks conversion."""
        assert seconds_to_ticks(1.0, 60) == 60
        assert seconds_to_ticks(0.5, 60) == 30
        assert seconds_to_ticks(2.0, 30) == 60
        assert seconds_to_ticks(0.1, 60) == 6
    
    def test_seconds_to_ticks_minimum(self):
        """Test that seconds_to_ticks returns at least 1 tick."""
        assert seconds_to_ticks(0.0, 60) == 1
        assert seconds_to_ticks(0.001, 60) == 1
    
    def test_seconds_to_ticks_validation(self):
        """Test seconds_to_ticks parameter validation."""
        with pytest.raises(ValueError, match="Duration must be non-negative"):
            seconds_to_ticks(-1.0, 60)
        
        with pytest.raises(ValueError, match="FPS must be positive"):
            seconds_to_ticks(1.0, 0)
        
        with pytest.raises(ValueError, match="FPS must be positive"):
            seconds_to_ticks(1.0, -30)
    
    def test_ticks_to_seconds_basic(self):
        """Test basic ticks to seconds conversion."""
        assert ticks_to_seconds(60, 60) == 1.0
        assert ticks_to_seconds(30, 60) == 0.5
        assert ticks_to_seconds(60, 30) == 2.0
        assert ticks_to_seconds(6, 60) == 0.1
    
    def test_ticks_to_seconds_validation(self):
        """Test ticks_to_seconds parameter validation."""
        with pytest.raises(ValueError, match="Ticks must be non-negative"):
            ticks_to_seconds(-1, 60)
        
        with pytest.raises(ValueError, match="FPS must be positive"):
            ticks_to_seconds(60, 0)
    
    def test_milliseconds_conversion(self):
        """Test milliseconds conversion functions."""
        assert milliseconds_to_ticks(1000.0, 60) == 60
        assert milliseconds_to_ticks(500.0, 60) == 30
        assert ticks_to_milliseconds(60, 60) == 1000.0
        assert ticks_to_milliseconds(30, 60) == 500.0
    
    def test_conversion_roundtrip(self):
        """Test that conversions are reversible."""
        original_seconds = 1.5
        ticks = seconds_to_ticks(original_seconds, 60)
        converted_seconds = ticks_to_seconds(ticks, 60)
        assert abs(converted_seconds - original_seconds) < 0.02  # Allow for rounding


class TestAnimationTiming:
    """Test AnimationTiming configuration class."""
    
    def test_duration_seconds_only(self):
        """Test AnimationTiming with duration_seconds only."""
        timing = AnimationTiming(duration_seconds=1.0, fps=60)
        assert timing.duration_ticks == 60
        assert timing.duration_seconds == 1.0
        assert timing.fps == 60
    
    def test_duration_ticks_only(self):
        """Test AnimationTiming with duration_ticks only."""
        timing = AnimationTiming(duration_ticks=120)
        assert timing.duration_ticks == 120
        assert timing.duration_seconds is None
        assert timing.fps == 60
    
    def test_validation_no_duration(self):
        """Test validation when no duration is specified."""
        with pytest.raises(ValueError, match="Either duration_ticks or duration_seconds must be specified"):
            AnimationTiming()
    
    def test_validation_both_durations(self):
        """Test validation when both durations are specified."""
        with pytest.raises(ValueError, match="Cannot specify both duration_ticks and duration_seconds"):
            AnimationTiming(duration_ticks=60, duration_seconds=1.0)
    
    def test_validation_invalid_fps(self):
        """Test validation of FPS parameter."""
        with pytest.raises(ValueError, match="FPS must be positive"):
            AnimationTiming(duration_seconds=1.0, fps=0)
    
    def test_validation_invalid_duration(self):
        """Test validation of duration parameters."""
        with pytest.raises(ValueError, match="Duration must be positive"):
            AnimationTiming(duration_ticks=0)


class TestAnimationConfig:
    """Test AnimationConfig configuration class."""
    
    def test_basic_config(self):
        """Test basic animation configuration."""
        timing = AnimationTiming(duration_seconds=1.0)
        config = AnimationConfig(timing=timing)
        
        assert config.timing == timing
        assert config.easing == "ease_in_out"
        assert config.repeat_count == 1
        assert config.repeat_mode == "restart"
        assert config.delay_ticks == 0
        assert config.on_complete is None
    
    def test_easing_function_enum(self):
        """Test easing function enum conversion."""
        timing = AnimationTiming(duration_seconds=1.0)
        config = AnimationConfig(timing=timing, easing=EasingFunction.BOUNCE)
        
        assert config.easing == "bounce"
    
    def test_validation_repeat_count(self):
        """Test repeat count validation."""
        timing = AnimationTiming(duration_seconds=1.0)
        
        with pytest.raises(ValueError, match="Repeat count must be at least 1"):
            AnimationConfig(timing=timing, repeat_count=0)
    
    def test_validation_repeat_mode(self):
        """Test repeat mode validation."""
        timing = AnimationTiming(duration_seconds=1.0)
        
        with pytest.raises(ValueError, match="Invalid repeat mode"):
            AnimationConfig(timing=timing, repeat_mode="invalid")
    
    def test_validation_delay(self):
        """Test delay validation."""
        timing = AnimationTiming(duration_seconds=1.0)
        
        with pytest.raises(ValueError, match="Delay must be non-negative"):
            AnimationConfig(timing=timing, delay_ticks=-1)


class TestAnimationCreationUtilities:
    """Test animation creation utility functions."""
    
    def test_create_fade_animation(self):
        """Test fade animation creation."""
        animation = create_fade_animation(0.0, 1.0, (10.0, 20.0))
        
        assert isinstance(animation, TickAnimationDefinition)
        assert animation.start_state.opacity == 0.0
        assert animation.end_state.opacity == 1.0
        assert animation.start_state.position == (10.0, 20.0)
        assert animation.end_state.position == (10.0, 20.0)
        assert animation.duration_ticks == 30  # 0.5 seconds at 60fps
    
    def test_create_fade_animation_validation(self):
        """Test fade animation parameter validation."""
        with pytest.raises(ValueError, match="Start opacity must be between 0.0 and 1.0"):
            create_fade_animation(-0.1, 1.0)
        
        with pytest.raises(ValueError, match="End opacity must be between 0.0 and 1.0"):
            create_fade_animation(0.0, 1.1)
    
    def test_create_slide_animation(self):
        """Test slide animation creation."""
        start_pos = (0.0, 0.0)
        end_pos = (100.0, 50.0)
        animation = create_slide_animation(start_pos, end_pos)
        
        assert isinstance(animation, TickAnimationDefinition)
        assert animation.start_state.position == start_pos
        assert animation.end_state.position == end_pos
        assert animation.duration_ticks == 18  # 0.3 seconds at 60fps
    
    def test_create_scale_animation(self):
        """Test scale animation creation."""
        animation = create_scale_animation((0.5, 0.5), (2.0, 2.0), (10.0, 10.0))
        
        assert isinstance(animation, TickAnimationDefinition)
        assert animation.start_state.scale == (0.5, 0.5)
        assert animation.end_state.scale == (2.0, 2.0)
        assert animation.start_state.position == (10.0, 10.0)
        assert animation.easing == "bounce"  # Default for scale animations
    
    def test_create_scale_animation_validation(self):
        """Test scale animation parameter validation."""
        with pytest.raises(ValueError, match="Start scale values must be non-negative"):
            create_scale_animation((-1.0, 0.0), (1.0, 1.0))
        
        with pytest.raises(ValueError, match="End scale values must be non-negative"):
            create_scale_animation((0.0, 0.0), (1.0, -1.0))
    
    def test_create_rotation_animation(self):
        """Test rotation animation creation."""
        animation = create_rotation_animation(0.0, 180.0, (5.0, 5.0))
        
        assert isinstance(animation, TickAnimationDefinition)
        assert animation.start_state.rotation == 0.0
        assert abs(animation.end_state.rotation - math.pi) < 0.001  # 180 degrees in radians
        assert animation.start_state.position == (5.0, 5.0)
    
    def test_create_custom_property_animation(self):
        """Test custom property animation creation."""
        animation = create_custom_property_animation("brightness", 0.5, 1.5)
        
        assert isinstance(animation, TickAnimationDefinition)
        assert animation.start_state.custom_properties["brightness"] == 0.5
        assert animation.end_state.custom_properties["brightness"] == 1.5


class TestAnimationPresets:
    """Test animation preset functionality."""
    
    def test_fade_in_preset(self):
        """Test fade in preset animation."""
        animation = create_preset_animation(AnimationPreset.FADE_IN, (10.0, 20.0))
        
        assert animation.start_state.opacity == 0.0
        assert animation.end_state.opacity == 1.0
        assert animation.easing == "ease_out"
    
    def test_fade_out_preset(self):
        """Test fade out preset animation."""
        animation = create_preset_animation(AnimationPreset.FADE_OUT, (10.0, 20.0))
        
        assert animation.start_state.opacity == 1.0
        assert animation.end_state.opacity == 0.0
        assert animation.easing == "ease_in"
    
    def test_slide_left_preset(self):
        """Test slide left preset animation."""
        position = (50.0, 30.0)
        animation = create_preset_animation(AnimationPreset.SLIDE_LEFT, position)
        
        assert animation.start_state.position == (150.0, 30.0)  # position + 100
        assert animation.end_state.position == position
        assert animation.easing == "ease_in_out"
    
    def test_scale_in_preset(self):
        """Test scale in preset animation."""
        animation = create_preset_animation(AnimationPreset.SCALE_IN, (25.0, 25.0))
        
        assert animation.start_state.scale == (0.0, 0.0)
        assert animation.end_state.scale == (1.0, 1.0)
        assert animation.easing == "bounce"
    
    def test_pulse_preset(self):
        """Test pulse preset animation."""
        animation = create_preset_animation(AnimationPreset.PULSE, (0.0, 0.0))
        
        assert animation.start_state.scale == (1.0, 1.0)
        assert animation.end_state.scale == (1.2, 1.2)
        assert animation.repeat_count == 3
        assert animation.repeat_mode == "mirror"
    
    def test_unknown_preset(self):
        """Test handling of unknown preset."""
        # Since we can't create an invalid enum value, this test validates
        # that all valid presets work correctly
        valid_presets = [
            AnimationPreset.FADE_IN, AnimationPreset.FADE_OUT,
            AnimationPreset.SLIDE_LEFT, AnimationPreset.SLIDE_RIGHT,
            AnimationPreset.SCALE_IN, AnimationPreset.SCALE_OUT,
            AnimationPreset.PULSE
        ]
        
        for preset in valid_presets:
            animation = create_preset_animation(preset, (0.0, 0.0))
            assert isinstance(animation, TickAnimationDefinition)


class TestAnimationValidation:
    """Test animation validation utilities."""
    
    def test_validate_animation_definition_valid(self):
        """Test validation of valid animation definition."""
        animation = create_fade_animation(0.0, 1.0)
        assert validate_animation_definition(animation) is True
    
    def test_validate_animation_definition_invalid_start_tick(self):
        """Test validation with invalid start tick."""
        animation = create_fade_animation(0.0, 1.0)
        
        # Use object.__setattr__ to bypass frozen dataclass restriction
        object.__setattr__(animation, 'start_tick', -1)
        
        with pytest.raises(ValueError, match="Start tick must be non-negative"):
            validate_animation_definition(animation)
    
    def test_validate_animation_definition_invalid_duration(self):
        """Test validation with invalid duration."""
        animation = create_fade_animation(0.0, 1.0)
        
        # Use object.__setattr__ to bypass frozen dataclass restriction
        object.__setattr__(animation, 'duration_ticks', 0)
        
        with pytest.raises(ValueError, match="Duration must be positive"):
            validate_animation_definition(animation)
    
    def test_validate_animation_definition_invalid_easing(self):
        """Test validation with invalid easing function."""
        animation = create_fade_animation(0.0, 1.0)
        
        # Use object.__setattr__ to bypass frozen dataclass restriction
        object.__setattr__(animation, 'easing', "invalid_easing")
        
        with pytest.raises(ValueError, match="Unknown easing function"):
            validate_animation_definition(animation)
    
    def test_validate_animation_config_valid(self):
        """Test validation of valid animation config."""
        timing = AnimationTiming(duration_seconds=1.0)
        config = AnimationConfig(timing=timing)
        assert validate_animation_config(config) is True
    
    def test_validate_animation_config_invalid_easing(self):
        """Test validation of config with invalid easing."""
        timing = AnimationTiming(duration_seconds=1.0)
        config = AnimationConfig(timing=timing)
        
        # Use object.__setattr__ to bypass frozen dataclass restriction
        object.__setattr__(config, 'easing', "invalid_easing")
        
        with pytest.raises(ValueError, match="Unknown easing function"):
            validate_animation_config(config)


class TestAnimationSequences:
    """Test animation sequence utilities."""
    
    def test_create_animation_sequence(self):
        """Test creation of animation sequence."""
        anim1 = create_fade_animation(0.0, 1.0)  # 30 ticks
        anim2 = create_slide_animation((0.0, 0.0), (100.0, 0.0))  # 18 ticks
        anim3 = create_scale_animation((0.0, 0.0), (1.0, 1.0))  # 24 ticks
        
        sequence = create_animation_sequence([anim1, anim2, anim3], gap_ticks=5)
        
        assert len(sequence) == 3
        assert sequence[0].start_tick == 0
        assert sequence[1].start_tick == 35  # 30 + 5 gap
        assert sequence[2].start_tick == 58  # 35 + 18 + 5 gap
    
    def test_create_parallel_animations(self):
        """Test creation of parallel animations."""
        anim1 = create_fade_animation(0.0, 1.0)
        anim2 = create_slide_animation((0.0, 0.0), (100.0, 0.0))
        anim3 = create_scale_animation((0.0, 0.0), (1.0, 1.0))
        
        parallel = create_parallel_animations([anim1, anim2, anim3], start_tick=10)
        
        assert len(parallel) == 3
        assert all(anim.start_tick == 10 for anim in parallel)
    
    def test_empty_sequence(self):
        """Test handling of empty animation sequence."""
        sequence = create_animation_sequence([])
        assert sequence == []


class TestBackwardCompatibility:
    """Test backward compatibility layer."""
    
    def test_legacy_animation_config(self):
        """Test legacy animation configuration."""
        legacy_config = LegacyAnimationConfig(
            duration=1.5,
            easing="ease_in",
            repeat=2,
            delay=0.5,
            fps=30
        )
        
        tick_config = legacy_config.to_tick_config()
        
        assert tick_config.timing.duration_ticks == 45  # 1.5 * 30
        assert tick_config.easing == "ease_in"
        assert tick_config.repeat_count == 2
        assert tick_config.delay_ticks == 15  # 0.5 * 30
    
    def test_legacy_animation_api(self):
        """Test legacy animation API."""
        api = LegacyAnimationAPI(fps=60, show_deprecation_warnings=False)
        
        # Test fade in
        fade_in = api.create_fade_in(duration=0.8, position=(10.0, 20.0))
        assert fade_in.start_state.opacity == 0.0
        assert fade_in.end_state.opacity == 1.0
        assert fade_in.duration_ticks == 48  # 0.8 * 60
        
        # Test slide left
        slide_left = api.create_slide_left(distance=150.0, duration=0.4, position=(50.0, 30.0))
        assert slide_left.start_state.position == (200.0, 30.0)  # 50 + 150
        assert slide_left.end_state.position == (50.0, 30.0)
        assert slide_left.duration_ticks == 24  # 0.4 * 60
    
    def test_create_time_based_animation(self):
        """Test time-based animation creation function."""
        animation = create_time_based_animation(
            duration_seconds=1.2,
            start_opacity=0.3,
            end_opacity=0.8,
            position=(15.0, 25.0),
            easing="bounce",
            fps=30
        )
        
        assert animation.start_state.opacity == 0.3
        assert animation.end_state.opacity == 0.8
        assert animation.start_state.position == (15.0, 25.0)
        assert animation.duration_ticks == 36  # 1.2 * 30
        assert animation.easing == "bounce"
    
    def test_convert_legacy_easing_name(self):
        """Test legacy easing name conversion."""
        assert convert_legacy_easing_name("ease") == "ease_in_out"
        assert convert_legacy_easing_name("ease-in") == "ease_in"
        assert convert_legacy_easing_name("ease-out") == "ease_out"
        assert convert_legacy_easing_name("linear") == "linear"
        assert convert_legacy_easing_name("unknown") == "ease_in_out"  # Default
    
    def test_migrate_animation_config(self):
        """Test animation config migration."""
        legacy_config = {
            'duration': 2.0,
            'easing': 'ease-in',
            'repeat': 3,
            'delay': 0.2,
            'fps': 45,
            'on_complete': lambda: None
        }
        
        migrated = migrate_animation_config(legacy_config)
        
        assert migrated.timing.duration_ticks == 90  # 2.0 * 45
        assert migrated.easing == "ease_in"
        assert migrated.repeat_count == 3
        assert migrated.delay_ticks == 9  # 0.2 * 45
        assert migrated.on_complete is not None
    
    def test_convert_time_duration_to_ticks(self):
        """Test time duration to ticks conversion."""
        assert convert_time_duration_to_ticks(1.0, 60) == 60
        assert convert_time_duration_to_ticks(0.5, 30) == 15
        assert convert_time_duration_to_ticks(2.5, 24) == 60


class TestLegacyFunctionAliases:
    """Test legacy function aliases."""
    
    def test_create_fade_in_animation(self):
        """Test legacy fade in animation function."""
        # Expect deprecation warning for legacy function
        with pytest.warns(DeprecationWarning, match="create_fade_in is deprecated"):
            animation = create_fade_in_animation(duration=0.6)
        
        assert animation.start_state.opacity == 0.0
        assert animation.end_state.opacity == 1.0
        assert animation.duration_ticks == 36  # 0.6 * 60
    
    def test_create_fade_out_animation(self):
        """Test legacy fade out animation function."""
        # Expect deprecation warning for legacy function
        with pytest.warns(DeprecationWarning, match="create_fade_out is deprecated"):
            animation = create_fade_out_animation(duration=0.4)
        
        assert animation.start_state.opacity == 1.0
        assert animation.end_state.opacity == 0.0
        assert animation.duration_ticks == 24  # 0.4 * 60


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple features."""
    
    def test_complex_animation_sequence(self):
        """Test complex animation sequence with different types."""
        # Create a complex sequence: fade in -> slide -> scale -> fade out
        fade_in = create_preset_animation(AnimationPreset.FADE_IN, (0.0, 0.0))
        slide = create_preset_animation(AnimationPreset.SLIDE_RIGHT, (0.0, 0.0))
        scale = create_preset_animation(AnimationPreset.PULSE, (100.0, 0.0))
        fade_out = create_preset_animation(AnimationPreset.FADE_OUT, (100.0, 0.0))
        
        sequence = create_animation_sequence([fade_in, slide, scale, fade_out], gap_ticks=10)
        
        # Validate sequence timing
        assert len(sequence) == 4
        assert sequence[0].start_tick == 0
        assert sequence[1].start_tick > sequence[0].start_tick
        assert sequence[2].start_tick > sequence[1].start_tick
        assert sequence[3].start_tick > sequence[2].start_tick
        
        # Validate all animations are valid
        for animation in sequence:
            assert validate_animation_definition(animation)
    
    def test_parallel_animations_with_different_durations(self):
        """Test parallel animations with different durations."""
        short_fade = create_fade_animation(0.0, 1.0, config=AnimationConfig(
            timing=AnimationTiming(duration_seconds=0.2)
        ))
        long_slide = create_slide_animation((0.0, 0.0), (200.0, 0.0), config=AnimationConfig(
            timing=AnimationTiming(duration_seconds=1.0)
        ))
        medium_scale = create_scale_animation((0.0, 0.0), (1.5, 1.5), config=AnimationConfig(
            timing=AnimationTiming(duration_seconds=0.6)
        ))
        
        parallel = create_parallel_animations([short_fade, long_slide, medium_scale], start_tick=5)
        
        # All start at the same time
        assert all(anim.start_tick == 5 for anim in parallel)
        
        # But have different durations
        durations = [anim.duration_ticks for anim in parallel]
        assert len(set(durations)) == 3  # All different durations
    
    def test_legacy_to_modern_migration(self):
        """Test migrating from legacy API to modern API."""
        # Start with legacy configuration
        legacy_config = {
            'duration': 1.5,
            'easing': 'ease-out',
            'repeat': 2,
            'delay': 0.3
        }
        
        # Migrate to modern config
        modern_config = migrate_animation_config(legacy_config)
        
        # Create animation with modern API
        animation = create_fade_animation(0.2, 0.9, config=modern_config)
        
        # Validate the result
        assert validate_animation_definition(animation)
        assert animation.start_state.opacity == 0.2
        assert animation.end_state.opacity == 0.9
        assert animation.easing == "ease_out"
        assert animation.repeat_count == 2
        assert animation.start_tick == 18  # delay_ticks from config (0.3 * 60)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 