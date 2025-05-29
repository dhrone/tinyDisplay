#!/usr/bin/env python3
"""
Test Suite for Widget Styling Framework

Comprehensive tests for styling system functionality including color management,
border styling, background styling, visual effects, style inheritance, and validation.
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.tinydisplay.widgets.styling import (
    Color, ColorFormat, BorderStyleType, BackgroundType, EffectType, BlendMode,
    GradientStop, BorderStyle, BackgroundStyle, VisualEffect, WidgetStyle,
    StyleInheritance, StyleValidator, NAMED_COLORS,
    get_style_inheritance, create_style, parse_color,
    create_gradient_background, create_shadow_effect, create_glow_effect
)


class TestColor:
    """Test Color class functionality."""
    
    def test_color__rgb_tuple__correct_initialization(self):
        """Test Color initialization with RGB tuple."""
        color = Color((255, 128, 64))
        assert color.r == 255
        assert color.g == 128
        assert color.b == 64
        assert color.a == 1.0
        assert color.rgb == (255, 128, 64)
        assert color.rgba == (255, 128, 64, 1.0)
    
    def test_color__rgba_tuple__correct_initialization(self):
        """Test Color initialization with RGBA tuple."""
        color = Color((255, 128, 64, 0.8))
        assert color.r == 255
        assert color.g == 128
        assert color.b == 64
        assert color.a == 0.8
        assert color.rgba == (255, 128, 64, 0.8)
    
    def test_color__hex_string__correct_initialization(self):
        """Test Color initialization with hex string."""
        color = Color("#ff8040")
        assert color.r == 255
        assert color.g == 128
        assert color.b == 64
        assert color.a == 1.0
        assert color.hex == "#ff8040"
    
    def test_color__short_hex_string__correct_initialization(self):
        """Test Color initialization with short hex string."""
        color = Color("#f84")
        assert color.r == 255
        assert color.g == 136
        assert color.b == 68
        assert color.a == 1.0
    
    def test_color__hex_with_alpha__correct_initialization(self):
        """Test Color initialization with hex string including alpha."""
        color = Color("#ff8040cc")
        assert color.r == 255
        assert color.g == 128
        assert color.b == 64
        assert abs(color.a - 0.8) < 0.01  # 204/255 ≈ 0.8
    
    def test_color__named_color__correct_initialization(self):
        """Test Color initialization with named color."""
        color = Color("red")
        assert color.r == 255
        assert color.g == 0
        assert color.b == 0
        assert color.a == 1.0
    
    def test_color__copy_constructor__correct_initialization(self):
        """Test Color initialization from another Color."""
        original = Color((255, 128, 64, 0.8))
        copy_color = Color(original)
        assert copy_color.rgba == original.rgba
        assert copy_color is not original
    
    def test_color__alpha_override__uses_override(self):
        """Test alpha override parameter."""
        color = Color((255, 128, 64), alpha=0.5)
        assert color.a == 0.5
    
    def test_color__invalid_rgb_values__raises_error(self):
        """Test Color with invalid RGB values raises error."""
        with pytest.raises(ValueError, match="RGB components must be between 0 and 255"):
            Color((256, 128, 64))
        
        with pytest.raises(ValueError, match="RGB components must be between 0 and 255"):
            Color((-1, 128, 64))
    
    def test_color__invalid_alpha__raises_error(self):
        """Test Color with invalid alpha raises error."""
        with pytest.raises(ValueError, match="Alpha must be between 0.0 and 1.0"):
            Color((255, 128, 64), alpha=1.5)
    
    def test_color__invalid_hex_format__raises_error(self):
        """Test Color with invalid hex format raises error."""
        with pytest.raises(ValueError, match="Invalid hex color format"):
            Color("#ff80")  # Invalid length
    
    def test_color__hsv_property__correct_conversion(self):
        """Test HSV property conversion."""
        color = Color((255, 0, 0))  # Pure red
        h, s, v = color.hsv
        assert abs(h - 0.0) < 0.1  # Hue should be 0 for red
        assert abs(s - 1.0) < 0.1  # Full saturation
        assert abs(v - 1.0) < 0.1  # Full value
    
    def test_color__rgba_int_property__correct_conversion(self):
        """Test RGBA integer property."""
        color = Color((255, 128, 64, 0.8))
        rgba_int = color.rgba_int
        assert rgba_int == (255, 128, 64, 204)  # 0.8 * 255 = 204
    
    def test_color__hex_alpha_property__correct_format(self):
        """Test hex with alpha property."""
        color = Color((255, 128, 64, 0.5))
        hex_alpha = color.hex_alpha
        assert hex_alpha == "#ff804080"  # 0.5 * 255 = 128 = 0x80
    
    def test_color__with_alpha__creates_new_color(self):
        """Test with_alpha method creates new color."""
        original = Color((255, 128, 64))
        new_color = original.with_alpha(0.5)
        
        assert new_color.rgb == original.rgb
        assert new_color.a == 0.5
        assert original.a == 1.0  # Original unchanged
    
    def test_color__lighten__creates_lighter_color(self):
        """Test lighten method."""
        color = Color((128, 64, 32))
        lighter = color.lighten(0.2)
        
        # Should have higher value in HSV
        assert lighter.hsv[2] > color.hsv[2]
        assert lighter.a == color.a  # Alpha preserved
    
    def test_color__darken__creates_darker_color(self):
        """Test darken method."""
        color = Color((128, 64, 32))
        darker = color.darken(0.2)
        
        # Should have lower value in HSV
        assert darker.hsv[2] < color.hsv[2]
        assert darker.a == color.a  # Alpha preserved
    
    def test_color__saturate__creates_more_saturated_color(self):
        """Test saturate method."""
        color = Color((200, 150, 150))  # Somewhat desaturated
        saturated = color.saturate(0.3)
        
        # Should have higher saturation in HSV
        assert saturated.hsv[1] > color.hsv[1]
    
    def test_color__desaturate__creates_less_saturated_color(self):
        """Test desaturate method."""
        color = Color((255, 0, 0))  # Pure red (fully saturated)
        desaturated = color.desaturate(0.3)
        
        # Should have lower saturation in HSV
        assert desaturated.hsv[1] < color.hsv[1]
    
    def test_color__blend__creates_blended_color(self):
        """Test blend method."""
        red = Color((255, 0, 0))
        blue = Color((0, 0, 255))
        
        # 50% blend should create purple
        blended = red.blend(blue, 0.5)
        assert blended.r == 127  # (255 + 0) / 2
        assert blended.g == 0
        assert blended.b == 127  # (0 + 255) / 2
    
    def test_color__blend__invalid_ratio__raises_error(self):
        """Test blend with invalid ratio raises error."""
        red = Color((255, 0, 0))
        blue = Color((0, 0, 255))
        
        with pytest.raises(ValueError, match="Blend ratio must be between 0.0 and 1.0"):
            red.blend(blue, 1.5)
    
    def test_color__from_hsv__creates_correct_color(self):
        """Test from_hsv class method."""
        color = Color.from_hsv(0, 1.0, 1.0)  # Pure red in HSV
        assert color.r == 255
        assert color.g == 0
        assert color.b == 0
    
    def test_color__from_hsv__invalid_values__raises_error(self):
        """Test from_hsv with invalid values raises error."""
        with pytest.raises(ValueError, match="Hue must be between 0 and 360"):
            Color.from_hsv(400, 1.0, 1.0)
        
        with pytest.raises(ValueError, match="Saturation must be between 0 and 1"):
            Color.from_hsv(0, 1.5, 1.0)
    
    def test_color__equality__correct_comparison(self):
        """Test color equality comparison."""
        color1 = Color((255, 128, 64, 0.8))
        color2 = Color((255, 128, 64, 0.8))
        color3 = Color((255, 128, 65, 0.8))
        
        assert color1 == color2
        assert color1 != color3
        assert color1 != "not a color"
    
    def test_color__repr__useful_string(self):
        """Test color string representation."""
        color = Color((255, 128, 64, 0.8))
        repr_str = repr(color)
        
        assert "Color" in repr_str
        assert "r=255" in repr_str
        assert "g=128" in repr_str
        assert "b=64" in repr_str
        assert "a=0.80" in repr_str


class TestGradientStop:
    """Test GradientStop functionality."""
    
    def test_gradient_stop__valid_values__correct_initialization(self):
        """Test GradientStop with valid values."""
        color = Color((255, 128, 0))
        stop = GradientStop(0.5, color)
        
        assert stop.position == 0.5
        assert stop.color == color
    
    def test_gradient_stop__auto_color_conversion__converts_color(self):
        """Test GradientStop automatically converts color."""
        stop = GradientStop(0.5, (255, 128, 0))
        
        assert isinstance(stop.color, Color)
        assert stop.color.rgb == (255, 128, 0)
    
    def test_gradient_stop__invalid_position__raises_error(self):
        """Test GradientStop with invalid position raises error."""
        with pytest.raises(ValueError, match="Gradient position must be between 0.0 and 1.0"):
            GradientStop(1.5, Color((255, 128, 0)))


class TestBorderStyle:
    """Test BorderStyle functionality."""
    
    def test_border_style__default_values__correct_initialization(self):
        """Test BorderStyle with default values."""
        border = BorderStyle()
        
        assert border.width == 0.0
        assert border.style == BorderStyleType.SOLID
        assert isinstance(border.color, Color)
        assert border.radius == 0.0
    
    def test_border_style__custom_values__correct_initialization(self):
        """Test BorderStyle with custom values."""
        border = BorderStyle(
            width=2.0,
            style=BorderStyleType.DASHED,
            color=Color((255, 0, 0)),
            radius=5.0
        )
        
        assert border.width == 2.0
        assert border.style == BorderStyleType.DASHED
        assert border.color.rgb == (255, 0, 0)
        assert border.radius == 5.0
    
    def test_border_style__auto_color_conversion__converts_color(self):
        """Test BorderStyle automatically converts color."""
        border = BorderStyle(color=(255, 0, 0))
        
        assert isinstance(border.color, Color)
        assert border.color.rgb == (255, 0, 0)
    
    def test_border_style__side_specific_properties__correct_values(self):
        """Test side-specific border properties."""
        border = BorderStyle(
            width=2.0,
            color=Color((255, 0, 0)),
            top_width=3.0,
            right_color=Color((0, 255, 0))
        )
        
        assert border.get_width("top") == 3.0
        assert border.get_width("bottom") == 2.0  # Falls back to default
        assert border.get_color("right").rgb == (0, 255, 0)
        assert border.get_color("left").rgb == (255, 0, 0)  # Falls back to default
    
    def test_border_style__invalid_width__raises_error(self):
        """Test BorderStyle with invalid width raises error."""
        with pytest.raises(ValueError, match="Border width must be non-negative"):
            BorderStyle(width=-1.0)
    
    def test_border_style__invalid_radius__raises_error(self):
        """Test BorderStyle with invalid radius raises error."""
        with pytest.raises(ValueError, match="Border radius must be non-negative"):
            BorderStyle(radius=-1.0)


class TestBackgroundStyle:
    """Test BackgroundStyle functionality."""
    
    def test_background_style__default_values__correct_initialization(self):
        """Test BackgroundStyle with default values."""
        background = BackgroundStyle()
        
        assert background.type == BackgroundType.NONE
        assert background.color is None
        assert background.gradient_stops == []
        assert background.gradient_angle == 0.0
    
    def test_background_style__solid_color__correct_initialization(self):
        """Test BackgroundStyle with solid color."""
        background = BackgroundStyle(
            type=BackgroundType.SOLID,
            color=Color((255, 128, 0))
        )
        
        assert background.type == BackgroundType.SOLID
        assert background.color.rgb == (255, 128, 0)
    
    def test_background_style__auto_color_conversion__converts_colors(self):
        """Test BackgroundStyle automatically converts colors."""
        background = BackgroundStyle(
            color=(255, 128, 0),
            pattern_color=(0, 255, 128)
        )
        
        assert isinstance(background.color, Color)
        assert isinstance(background.pattern_color, Color)
        assert background.color.rgb == (255, 128, 0)
        assert background.pattern_color.rgb == (0, 255, 128)
    
    def test_background_style__gradient_stops_validation__validates_stops(self):
        """Test BackgroundStyle validates gradient stops."""
        stop = GradientStop(0.5, Color((255, 0, 0)))
        background = BackgroundStyle(gradient_stops=[stop])
        
        assert len(background.gradient_stops) == 1
        assert background.gradient_stops[0] == stop
    
    def test_background_style__invalid_gradient_stops__raises_error(self):
        """Test BackgroundStyle with invalid gradient stops raises error."""
        with pytest.raises(ValueError, match="Gradient stops must be GradientStop instances"):
            BackgroundStyle(gradient_stops=["not a gradient stop"])


class TestVisualEffect:
    """Test VisualEffect functionality."""
    
    def test_visual_effect__shadow__correct_initialization(self):
        """Test VisualEffect shadow initialization."""
        effect = VisualEffect(
            type=EffectType.SHADOW,
            offset=(2.0, 2.0),
            blur_radius=4.0,
            color=Color((0, 0, 0, 0.5))
        )
        
        assert effect.type == EffectType.SHADOW
        assert effect.enabled is True
        assert effect.offset == (2.0, 2.0)
        assert effect.blur_radius == 4.0
        assert effect.color.rgba == (0, 0, 0, 0.5)
    
    def test_visual_effect__auto_color_conversion__converts_color(self):
        """Test VisualEffect automatically converts color."""
        effect = VisualEffect(
            type=EffectType.GLOW,
            color=(255, 255, 255)
        )
        
        assert isinstance(effect.color, Color)
        assert effect.color.rgb == (255, 255, 255)
    
    def test_visual_effect__invalid_blur_radius__raises_error(self):
        """Test VisualEffect with invalid blur radius raises error."""
        with pytest.raises(ValueError, match="Blur radius must be non-negative"):
            VisualEffect(type=EffectType.BLUR, blur_radius=-1.0)
    
    def test_visual_effect__invalid_spread_radius__raises_error(self):
        """Test VisualEffect with invalid spread radius raises error."""
        with pytest.raises(ValueError, match="Spread radius must be non-negative"):
            VisualEffect(type=EffectType.SHADOW, spread_radius=-1.0)


class TestWidgetStyle:
    """Test WidgetStyle functionality."""
    
    def test_widget_style__default_values__correct_initialization(self):
        """Test WidgetStyle with default values."""
        style = WidgetStyle()
        
        assert style.visible is True
        assert style.opacity == 1.0
        assert style.foreground_color is None
        assert isinstance(style.background, BackgroundStyle)
        assert isinstance(style.border, BorderStyle)
        assert style.margin == (0.0, 0.0, 0.0, 0.0)
        assert style.padding == (0.0, 0.0, 0.0, 0.0)
        assert style.effects == []
        assert style.rotation == 0.0
        assert style.scale == (1.0, 1.0)
    
    def test_widget_style__custom_values__correct_initialization(self):
        """Test WidgetStyle with custom values."""
        style = WidgetStyle(
            opacity=0.8,
            foreground_color=Color((255, 0, 0)),
            margin=(10.0, 5.0, 10.0, 5.0),
            rotation=45.0
        )
        
        assert style.opacity == 0.8
        assert style.foreground_color.rgb == (255, 0, 0)
        assert style.margin == (10.0, 5.0, 10.0, 5.0)
        assert style.rotation == 45.0
    
    def test_widget_style__auto_color_conversion__converts_foreground_color(self):
        """Test WidgetStyle automatically converts foreground color."""
        style = WidgetStyle(foreground_color=(255, 128, 0))
        
        assert isinstance(style.foreground_color, Color)
        assert style.foreground_color.rgb == (255, 128, 0)
    
    def test_widget_style__add_effect__adds_effect(self):
        """Test adding visual effect to style."""
        style = WidgetStyle()
        effect = VisualEffect(type=EffectType.SHADOW)
        
        style.add_effect(effect)
        
        assert len(style.effects) == 1
        assert style.effects[0] == effect
    
    def test_widget_style__remove_effect__removes_effect(self):
        """Test removing visual effect from style."""
        style = WidgetStyle()
        shadow = VisualEffect(type=EffectType.SHADOW)
        glow = VisualEffect(type=EffectType.GLOW)
        
        style.add_effect(shadow)
        style.add_effect(glow)
        
        removed = style.remove_effect(EffectType.SHADOW)
        
        assert removed is True
        assert len(style.effects) == 1
        assert style.effects[0] == glow
    
    def test_widget_style__get_effect__returns_effect(self):
        """Test getting visual effect by type."""
        style = WidgetStyle()
        shadow = VisualEffect(type=EffectType.SHADOW)
        
        style.add_effect(shadow)
        
        found_effect = style.get_effect(EffectType.SHADOW)
        assert found_effect == shadow
        
        not_found = style.get_effect(EffectType.GLOW)
        assert not_found is None
    
    def test_widget_style__set_margin__css_like_syntax(self):
        """Test setting margin with CSS-like syntax."""
        style = WidgetStyle()
        
        # All sides
        style.set_margin(10.0)
        assert style.margin == (10.0, 10.0, 10.0, 10.0)
        
        # Top/bottom and left/right
        style.set_margin(10.0, 5.0)
        assert style.margin == (10.0, 5.0, 10.0, 5.0)
        
        # Top, left/right, bottom
        style.set_margin(10.0, 5.0, 8.0)
        assert style.margin == (10.0, 5.0, 8.0, 5.0)
        
        # All different
        style.set_margin(10.0, 5.0, 8.0, 3.0)
        assert style.margin == (10.0, 5.0, 8.0, 3.0)
    
    def test_widget_style__set_padding__css_like_syntax(self):
        """Test setting padding with CSS-like syntax."""
        style = WidgetStyle()
        
        style.set_padding(5.0, 10.0)
        assert style.padding == (5.0, 10.0, 5.0, 10.0)
    
    def test_widget_style__clone__creates_deep_copy(self):
        """Test cloning style creates deep copy."""
        original = WidgetStyle(
            opacity=0.8,
            foreground_color=Color((255, 0, 0))
        )
        original.add_effect(VisualEffect(type=EffectType.SHADOW))
        
        cloned = original.clone()
        
        assert cloned is not original
        assert cloned.opacity == original.opacity
        assert cloned.foreground_color == original.foreground_color
        assert len(cloned.effects) == len(original.effects)
        assert cloned.effects[0] is not original.effects[0]  # Deep copy
    
    def test_widget_style__merge__combines_styles(self):
        """Test merging styles combines properties."""
        base = WidgetStyle(
            opacity=0.8,
            foreground_color=Color((255, 0, 0))
        )
        base.add_effect(VisualEffect(type=EffectType.SHADOW))
        
        override = WidgetStyle(
            opacity=0.6,
            margin=(10.0, 10.0, 10.0, 10.0)
        )
        override.add_effect(VisualEffect(type=EffectType.GLOW))
        
        merged = base.merge(override)
        
        # Override takes precedence
        assert merged.opacity == 0.6
        # Base properties preserved if not overridden
        assert merged.foreground_color.rgb == (255, 0, 0)
        # New properties added
        assert merged.margin == (10.0, 10.0, 10.0, 10.0)
        # Effects combined
        assert len(merged.effects) == 2
    
    def test_widget_style__invalid_opacity__raises_error(self):
        """Test WidgetStyle with invalid opacity raises error."""
        with pytest.raises(ValueError, match="Opacity must be between 0.0 and 1.0"):
            WidgetStyle(opacity=1.5)
    
    def test_widget_style__invalid_margin__raises_error(self):
        """Test WidgetStyle with invalid margin raises error."""
        with pytest.raises(ValueError, match="margin must be a tuple of 4 values"):
            WidgetStyle(margin=(10.0, 5.0))  # Wrong number of values
        
        with pytest.raises(ValueError, match="margin values must be non-negative"):
            WidgetStyle(margin=(10.0, -5.0, 10.0, 5.0))  # Negative value
    
    def test_widget_style__invalid_scale__raises_error(self):
        """Test WidgetStyle with invalid scale raises error."""
        with pytest.raises(ValueError, match="Scale must be a tuple of 2 values"):
            WidgetStyle(scale=(1.0,))  # Wrong number of values
        
        with pytest.raises(ValueError, match="Scale factors must be positive"):
            WidgetStyle(scale=(1.0, 0.0))  # Zero scale factor


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_style__valid_parameters__creates_style(self):
        """Test create_style with valid parameters."""
        style = create_style(
            opacity=0.8,
            foreground_color=Color((255, 0, 0))
        )
        
        assert isinstance(style, WidgetStyle)
        assert style.opacity == 0.8
        assert style.foreground_color.rgb == (255, 0, 0)
    
    def test_create_style__invalid_parameters__raises_error(self):
        """Test create_style with invalid parameters raises error."""
        with pytest.raises(ValueError, match="Invalid style configuration"):
            create_style(opacity=1.5)
    
    def test_parse_color__various_formats__creates_color(self):
        """Test parse_color with various formats."""
        assert parse_color((255, 128, 0)).rgb == (255, 128, 0)
        assert parse_color("#ff8000").rgb == (255, 128, 0)
        assert parse_color("red").rgb == (255, 0, 0)
    
    def test_create_gradient_background__linear__creates_background(self):
        """Test create_gradient_background for linear gradient."""
        stops = [(0.0, "red"), (1.0, "blue")]
        background = create_gradient_background(stops, "linear", 45.0)
        
        assert background.type == BackgroundType.LINEAR_GRADIENT
        assert len(background.gradient_stops) == 2
        assert background.gradient_angle == 45.0
        assert background.gradient_stops[0].color.rgb == (255, 0, 0)
        assert background.gradient_stops[1].color.rgb == (0, 0, 255)
    
    def test_create_gradient_background__radial__creates_background(self):
        """Test create_gradient_background for radial gradient."""
        stops = [(0.0, "white"), (1.0, "black")]
        background = create_gradient_background(stops, "radial")
        
        assert background.type == BackgroundType.RADIAL_GRADIENT
        assert len(background.gradient_stops) == 2
    
    def test_create_shadow_effect__creates_shadow(self):
        """Test create_shadow_effect."""
        shadow = create_shadow_effect(
            offset=(3.0, 3.0),
            blur=5.0,
            color="black",
            spread=1.0
        )
        
        assert shadow.type == EffectType.SHADOW
        assert shadow.offset == (3.0, 3.0)
        assert shadow.blur_radius == 5.0
        assert shadow.spread_radius == 1.0
        assert shadow.color.rgb == (0, 0, 0)
    
    def test_create_glow_effect__creates_glow(self):
        """Test create_glow_effect."""
        glow = create_glow_effect(
            blur=6.0,
            color="white",
            spread=2.0
        )
        
        assert glow.type == EffectType.GLOW
        assert glow.offset == (0.0, 0.0)
        assert glow.blur_radius == 6.0
        assert glow.spread_radius == 2.0
        assert glow.color.rgb == (255, 255, 255)
    
    def test_get_style_inheritance__returns_global_instance(self):
        """Test get_style_inheritance returns global instance."""
        inheritance1 = get_style_inheritance()
        inheritance2 = get_style_inheritance()
        
        assert inheritance1 is inheritance2


class TestNamedColors:
    """Test named color constants."""
    
    def test_named_colors__basic_colors__correct_values(self):
        """Test basic named colors have correct values."""
        assert NAMED_COLORS['black'] == (0, 0, 0)
        assert NAMED_COLORS['white'] == (255, 255, 255)
        assert NAMED_COLORS['red'] == (255, 0, 0)
        assert NAMED_COLORS['green'] == (0, 255, 0)
        assert NAMED_COLORS['blue'] == (0, 0, 255)
    
    def test_named_colors__extended_colors__correct_values(self):
        """Test extended named colors have correct values."""
        assert NAMED_COLORS['orange'] == (255, 165, 0)
        assert NAMED_COLORS['purple'] == (128, 0, 128)
        assert NAMED_COLORS['brown'] == (165, 42, 42)
    
    def test_named_colors__gray_variants__correct_values(self):
        """Test gray color variants."""
        assert NAMED_COLORS['gray'] == (128, 128, 128)
        assert NAMED_COLORS['grey'] == (128, 128, 128)  # Alternative spelling
        assert NAMED_COLORS['dark_gray'] == (64, 64, 64)
        assert NAMED_COLORS['light_gray'] == (192, 192, 192)
    
    def test_named_colors__transparent__has_alpha(self):
        """Test transparent color has alpha component."""
        assert NAMED_COLORS['transparent'] == (0, 0, 0, 0)


class TestStylingPerformance:
    """Test styling system performance characteristics."""
    
    @pytest.mark.performance
    def test_color__creation_performance__meets_target(self):
        """Test color creation performance."""
        start_time = time.perf_counter()
        
        colors = []
        for i in range(1000):
            color = Color((i % 256, (i * 2) % 256, (i * 3) % 256))
            colors.append(color)
        
        creation_time = time.perf_counter() - start_time
        
        # Should create 1000 colors in under 100ms
        assert creation_time < 0.1
        assert len(colors) == 1000
    
    @pytest.mark.performance
    def test_color__manipulation_performance__meets_target(self):
        """Test color manipulation performance."""
        color = Color((128, 64, 192))
        
        start_time = time.perf_counter()
        
        for _ in range(1000):
            lighter = color.lighten(0.1)
            darker = color.darken(0.1)
            saturated = color.saturate(0.1)
            desaturated = color.desaturate(0.1)
        
        manipulation_time = time.perf_counter() - start_time
        
        # Should perform 4000 manipulations in under 100ms
        assert manipulation_time < 0.1
    
    @pytest.mark.performance
    def test_widget_style__creation_performance__meets_target(self):
        """Test widget style creation performance."""
        start_time = time.perf_counter()
        
        styles = []
        for i in range(100):
            style = WidgetStyle(
                opacity=0.8,
                foreground_color=Color((i % 256, 128, 64)),
                margin=(float(i), float(i), float(i), float(i))
            )
            styles.append(style)
        
        creation_time = time.perf_counter() - start_time
        
        # Should create 100 styles in under 50ms
        assert creation_time < 0.05
        assert len(styles) == 100
    
    @pytest.mark.performance
    def test_style_inheritance__performance__meets_target(self):
        """Test style inheritance performance."""
        inheritance = StyleInheritance()
        
        # Register parent styles
        for i in range(10):
            parent_style = WidgetStyle(opacity=0.8 + i * 0.01)
            inheritance.register_parent_style(f"parent_{i}", parent_style)
        
        start_time = time.perf_counter()
        
        # Perform inheritance operations
        for i in range(100):
            child_style = WidgetStyle(foreground_color=Color((i % 256, 128, 64)))
            inherited = inheritance.inherit_style(child_style, f"parent_{i % 10}")
        
        inheritance_time = time.perf_counter() - start_time
        
        # Should perform 100 inheritance operations in under 50ms
        assert inheritance_time < 0.05


class TestStylingIntegration:
    """Test styling system integration."""
    
    def test_styling__complete_widget_style__all_features(self):
        """Test complete widget style with all features."""
        # Create comprehensive style
        style = WidgetStyle(
            opacity=0.9,
            foreground_color=Color((255, 255, 255)),
            margin=(10.0, 5.0, 10.0, 5.0),
            padding=(5.0, 5.0, 5.0, 5.0),
            rotation=15.0,
            scale=(1.2, 1.2)
        )
        
        # Add background
        style.background = BackgroundStyle(
            type=BackgroundType.LINEAR_GRADIENT,
            gradient_stops=[
                GradientStop(0.0, Color("red")),
                GradientStop(1.0, Color("blue"))
            ],
            gradient_angle=45.0
        )
        
        # Add border
        style.border = BorderStyle(
            width=2.0,
            style=BorderStyleType.SOLID,
            color=Color("black"),
            radius=5.0
        )
        
        # Add effects
        style.add_effect(create_shadow_effect((2.0, 2.0), 4.0, "black"))
        style.add_effect(create_glow_effect(3.0, "white"))
        
        # Validate complete style
        errors = StyleValidator.validate_style(style)
        assert errors == []
        
        # Test all properties are accessible
        assert style.opacity == 0.9
        assert style.foreground_color.rgb == (255, 255, 255)
        assert style.background.type == BackgroundType.LINEAR_GRADIENT
        assert len(style.background.gradient_stops) == 2
        assert style.border.width == 2.0
        assert len(style.effects) == 2
        assert style.rotation == 15.0
        assert style.scale == (1.2, 1.2)
    
    def test_styling__style_merging_chain__combines_correctly(self):
        """Test chaining style merges."""
        base = WidgetStyle(opacity=0.8)
        theme = WidgetStyle(foreground_color=Color("white"))
        component = WidgetStyle(margin=(10.0, 10.0, 10.0, 10.0))
        
        # Chain merges
        final = base.merge(theme).merge(component)
        
        assert final.opacity == 0.8
        assert final.foreground_color.rgb == (255, 255, 255)
        assert final.margin == (10.0, 10.0, 10.0, 10.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 