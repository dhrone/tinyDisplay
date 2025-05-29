#!/usr/bin/env python3
"""
Widget Styling Framework

Provides comprehensive styling capabilities for tinyDisplay widgets including:
- Color management with RGB, HSV, and named colors
- Border styling with width, style, color, and radius
- Background styling with solid colors, gradients, and patterns
- Visual effects including shadows, glow, and blur
- Style inheritance and cascading system
- Style validation and error handling
"""

from typing import Union, Optional, Tuple, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import colorsys
import threading
import math
from abc import ABC, abstractmethod

from .base import ReactiveValue


class ColorFormat(Enum):
    """Supported color formats."""
    RGB = "rgb"
    RGBA = "rgba"
    HSV = "hsv"
    HSVA = "hsva"
    HEX = "hex"
    NAMED = "named"


class BorderStyleType(Enum):
    """Border style types."""
    NONE = "none"
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"
    DOUBLE = "double"
    GROOVE = "groove"
    RIDGE = "ridge"
    INSET = "inset"
    OUTSET = "outset"


class BackgroundType(Enum):
    """Background type options."""
    NONE = "none"
    SOLID = "solid"
    LINEAR_GRADIENT = "linear_gradient"
    RADIAL_GRADIENT = "radial_gradient"
    PATTERN = "pattern"
    IMAGE = "image"


class EffectType(Enum):
    """Visual effect types."""
    SHADOW = "shadow"
    GLOW = "glow"
    BLUR = "blur"
    EMBOSS = "emboss"
    OUTLINE = "outline"


class BlendMode(Enum):
    """Blend modes for effects and overlays."""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft_light"
    HARD_LIGHT = "hard_light"
    COLOR_DODGE = "color_dodge"
    COLOR_BURN = "color_burn"


# Named color constants
NAMED_COLORS = {
    # Basic colors
    'black': (0, 0, 0),
    'white': (255, 255, 255),
    'red': (255, 0, 0),
    'green': (0, 255, 0),
    'blue': (0, 0, 255),
    'yellow': (255, 255, 0),
    'cyan': (0, 255, 255),
    'magenta': (255, 0, 255),
    
    # Gray scale
    'gray': (128, 128, 128),
    'grey': (128, 128, 128),
    'dark_gray': (64, 64, 64),
    'light_gray': (192, 192, 192),
    'silver': (192, 192, 192),
    
    # Extended colors
    'orange': (255, 165, 0),
    'purple': (128, 0, 128),
    'brown': (165, 42, 42),
    'pink': (255, 192, 203),
    'lime': (0, 255, 0),
    'navy': (0, 0, 128),
    'teal': (0, 128, 128),
    'olive': (128, 128, 0),
    'maroon': (128, 0, 0),
    'aqua': (0, 255, 255),
    'fuchsia': (255, 0, 255),
    
    # Transparent
    'transparent': (0, 0, 0, 0),
}


class Color:
    """Advanced color management with multiple format support."""
    
    __slots__ = ('_r', '_g', '_b', '_a', '_lock')
    
    def __init__(self, color: Union[str, Tuple[int, ...], 'Color'], alpha: Optional[float] = None):
        self._r: int = 0
        self._g: int = 0
        self._b: int = 0
        self._a: float = 1.0
        self._lock = threading.RLock()
        
        self._parse_color(color, alpha)
    
    def __deepcopy__(self, memo):
        """Support deep copying by creating new Color instance."""
        return Color((self._r, self._g, self._b, self._a))
    
    def _parse_color(self, color: Union[str, Tuple[int, ...], 'Color'], alpha: Optional[float]) -> None:
        """Parse color from various input formats."""
        with self._lock:
            if isinstance(color, Color):
                self._r, self._g, self._b, self._a = color._r, color._g, color._b, color._a
            elif isinstance(color, str):
                self._parse_string_color(color)
            elif isinstance(color, (tuple, list)):
                self._parse_tuple_color(color)
            else:
                raise ValueError(f"Unsupported color format: {type(color)}")
            
            # Override alpha if provided
            if alpha is not None:
                self._validate_alpha(alpha)
                self._a = alpha
    
    def _parse_string_color(self, color_str: str) -> None:
        """Parse string color (hex or named)."""
        color_str = color_str.lower().strip()
        
        # Named color
        if color_str in NAMED_COLORS:
            color_tuple = NAMED_COLORS[color_str]
            if len(color_tuple) == 3:
                self._r, self._g, self._b = color_tuple
                self._a = 1.0
            else:
                self._r, self._g, self._b, self._a = color_tuple
            return
        
        # Hex color
        if color_str.startswith('#'):
            color_str = color_str[1:]
        
        if len(color_str) == 3:
            # Short hex format (e.g., "f0a")
            self._r = int(color_str[0] * 2, 16)
            self._g = int(color_str[1] * 2, 16)
            self._b = int(color_str[2] * 2, 16)
            self._a = 1.0
        elif len(color_str) == 6:
            # Full hex format (e.g., "ff00aa")
            self._r = int(color_str[0:2], 16)
            self._g = int(color_str[2:4], 16)
            self._b = int(color_str[4:6], 16)
            self._a = 1.0
        elif len(color_str) == 8:
            # Hex with alpha (e.g., "ff00aa80")
            self._r = int(color_str[0:2], 16)
            self._g = int(color_str[2:4], 16)
            self._b = int(color_str[4:6], 16)
            self._a = int(color_str[6:8], 16) / 255.0
        else:
            raise ValueError(f"Invalid hex color format: {color_str}")
    
    def _parse_tuple_color(self, color_tuple: Tuple[int, ...]) -> None:
        """Parse tuple color (RGB or RGBA)."""
        if len(color_tuple) == 3:
            self._r, self._g, self._b = color_tuple
            self._a = 1.0
        elif len(color_tuple) == 4:
            self._r, self._g, self._b = color_tuple[:3]
            self._a = color_tuple[3] if isinstance(color_tuple[3], float) else color_tuple[3] / 255.0
        else:
            raise ValueError(f"Color tuple must have 3 or 4 components, got {len(color_tuple)}")
        
        # Validate RGB values
        for component in [self._r, self._g, self._b]:
            if not 0 <= component <= 255:
                raise ValueError(f"RGB components must be between 0 and 255, got {component}")
        
        self._validate_alpha(self._a)
    
    def _validate_alpha(self, alpha: float) -> None:
        """Validate alpha value."""
        if not 0.0 <= alpha <= 1.0:
            raise ValueError(f"Alpha must be between 0.0 and 1.0, got {alpha}")
    
    # Properties
    @property
    def r(self) -> int:
        """Red component (0-255)."""
        return self._r
    
    @property
    def g(self) -> int:
        """Green component (0-255)."""
        return self._g
    
    @property
    def b(self) -> int:
        """Blue component (0-255)."""
        return self._b
    
    @property
    def a(self) -> float:
        """Alpha component (0.0-1.0)."""
        return self._a
    
    @property
    def rgb(self) -> Tuple[int, int, int]:
        """RGB tuple."""
        return (self._r, self._g, self._b)
    
    @property
    def rgba(self) -> Tuple[int, int, int, float]:
        """RGBA tuple."""
        return (self._r, self._g, self._b, self._a)
    
    @property
    def rgba_int(self) -> Tuple[int, int, int, int]:
        """RGBA tuple with integer alpha (0-255)."""
        return (self._r, self._g, self._b, int(self._a * 255))
    
    @property
    def hsv(self) -> Tuple[float, float, float]:
        """HSV tuple (hue: 0-360, saturation: 0-1, value: 0-1)."""
        h, s, v = colorsys.rgb_to_hsv(self._r / 255.0, self._g / 255.0, self._b / 255.0)
        return (h * 360, s, v)
    
    @property
    def hex(self) -> str:
        """Hex color string."""
        return f"#{self._r:02x}{self._g:02x}{self._b:02x}"
    
    @property
    def hex_alpha(self) -> str:
        """Hex color string with alpha."""
        alpha_hex = round(self._a * 255)
        return f"#{self._r:02x}{self._g:02x}{self._b:02x}{alpha_hex:02x}"
    
    # Color manipulation methods
    def with_alpha(self, alpha: float) -> 'Color':
        """Create new color with different alpha."""
        return Color(self.rgb, alpha)
    
    def lighten(self, amount: float) -> 'Color':
        """Create lighter version of color."""
        h, s, v = self.hsv
        new_v = min(1.0, v + amount)
        r, g, b = colorsys.hsv_to_rgb(h / 360, s, new_v)
        return Color((int(r * 255), int(g * 255), int(b * 255)), self._a)
    
    def darken(self, amount: float) -> 'Color':
        """Create darker version of color."""
        h, s, v = self.hsv
        new_v = max(0.0, v - amount)
        r, g, b = colorsys.hsv_to_rgb(h / 360, s, new_v)
        return Color((int(r * 255), int(g * 255), int(b * 255)), self._a)
    
    def saturate(self, amount: float) -> 'Color':
        """Create more saturated version of color."""
        h, s, v = self.hsv
        new_s = min(1.0, s + amount)
        r, g, b = colorsys.hsv_to_rgb(h / 360, new_s, v)
        return Color((int(r * 255), int(g * 255), int(b * 255)), self._a)
    
    def desaturate(self, amount: float) -> 'Color':
        """Create less saturated version of color."""
        h, s, v = self.hsv
        new_s = max(0.0, s - amount)
        r, g, b = colorsys.hsv_to_rgb(h / 360, new_s, v)
        return Color((int(r * 255), int(g * 255), int(b * 255)), self._a)
    
    def blend(self, other: 'Color', ratio: float = 0.5) -> 'Color':
        """Blend with another color."""
        if not 0.0 <= ratio <= 1.0:
            raise ValueError("Blend ratio must be between 0.0 and 1.0")
        
        r = int(self._r * (1 - ratio) + other._r * ratio)
        g = int(self._g * (1 - ratio) + other._g * ratio)
        b = int(self._b * (1 - ratio) + other._b * ratio)
        a = self._a * (1 - ratio) + other._a * ratio
        
        return Color((r, g, b), a)
    
    @classmethod
    def from_hsv(cls, h: float, s: float, v: float, a: float = 1.0) -> 'Color':
        """Create color from HSV values."""
        if not 0 <= h <= 360:
            raise ValueError("Hue must be between 0 and 360")
        if not 0 <= s <= 1:
            raise ValueError("Saturation must be between 0 and 1")
        if not 0 <= v <= 1:
            raise ValueError("Value must be between 0 and 1")
        
        r, g, b = colorsys.hsv_to_rgb(h / 360, s, v)
        return cls((int(r * 255), int(g * 255), int(b * 255)), a)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Color):
            return False
        return (self._r, self._g, self._b, self._a) == (other._r, other._g, other._b, other._a)
    
    def __repr__(self) -> str:
        return f"Color(r={self._r}, g={self._g}, b={self._b}, a={self._a:.2f})"


@dataclass
class GradientStop:
    """Gradient color stop with position and color."""
    position: float  # 0.0 to 1.0
    color: Color
    
    def __post_init__(self):
        if not 0.0 <= self.position <= 1.0:
            raise ValueError("Gradient position must be between 0.0 and 1.0")
        if not isinstance(self.color, Color):
            self.color = Color(self.color)


@dataclass
class BorderStyle:
    """Border styling configuration."""
    width: float = 0.0
    style: BorderStyleType = BorderStyleType.SOLID
    color: Color = field(default_factory=lambda: Color('black'))
    radius: float = 0.0
    
    # Advanced border properties
    top_width: Optional[float] = None
    right_width: Optional[float] = None
    bottom_width: Optional[float] = None
    left_width: Optional[float] = None
    
    top_color: Optional[Color] = None
    right_color: Optional[Color] = None
    bottom_color: Optional[Color] = None
    left_color: Optional[Color] = None
    
    def __post_init__(self):
        if self.width < 0:
            raise ValueError("Border width must be non-negative")
        if self.radius < 0:
            raise ValueError("Border radius must be non-negative")
        
        # Convert colors if needed
        if not isinstance(self.color, Color):
            self.color = Color(self.color)
        
        for attr in ['top_color', 'right_color', 'bottom_color', 'left_color']:
            value = getattr(self, attr)
            if value is not None and not isinstance(value, Color):
                setattr(self, attr, Color(value))
    
    def get_width(self, side: str) -> float:
        """Get width for specific side."""
        side_width = getattr(self, f"{side}_width", None)
        return side_width if side_width is not None else self.width
    
    def get_color(self, side: str) -> Color:
        """Get color for specific side."""
        side_color = getattr(self, f"{side}_color", None)
        return side_color if side_color is not None else self.color


@dataclass
class BackgroundStyle:
    """Background styling configuration."""
    type: BackgroundType = BackgroundType.NONE
    color: Optional[Color] = None
    
    # Gradient properties
    gradient_stops: List[GradientStop] = field(default_factory=list)
    gradient_angle: float = 0.0  # Degrees for linear gradient
    gradient_center: Tuple[float, float] = (0.5, 0.5)  # Relative center for radial
    
    # Pattern properties
    pattern_type: str = "dots"
    pattern_size: float = 10.0
    pattern_spacing: float = 5.0
    pattern_color: Optional[Color] = None
    
    # Image properties
    image_source: Optional[str] = None
    image_repeat: str = "no-repeat"  # "repeat", "repeat-x", "repeat-y", "no-repeat"
    image_position: Tuple[float, float] = (0.5, 0.5)  # Relative position
    
    def __post_init__(self):
        # Convert colors if needed
        if self.color is not None and not isinstance(self.color, Color):
            self.color = Color(self.color)
        if self.pattern_color is not None and not isinstance(self.pattern_color, Color):
            self.pattern_color = Color(self.pattern_color)
        
        # Validate gradient stops
        for stop in self.gradient_stops:
            if not isinstance(stop, GradientStop):
                raise ValueError("Gradient stops must be GradientStop instances")


@dataclass
class VisualEffect:
    """Visual effect configuration."""
    type: EffectType
    enabled: bool = True
    
    # Shadow/Glow properties
    offset: Tuple[float, float] = (0.0, 0.0)
    blur_radius: float = 0.0
    spread_radius: float = 0.0
    color: Color = field(default_factory=lambda: Color('black'))
    
    # Blur properties
    blur_amount: float = 1.0
    
    # Emboss properties
    depth: float = 1.0
    angle: float = 45.0
    
    # Outline properties
    outline_width: float = 1.0
    
    # Blend mode
    blend_mode: BlendMode = BlendMode.NORMAL
    
    def __post_init__(self):
        if not isinstance(self.color, Color):
            self.color = Color(self.color)
        
        if self.blur_radius < 0:
            raise ValueError("Blur radius must be non-negative")
        if self.spread_radius < 0:
            raise ValueError("Spread radius must be non-negative")
        if self.blur_amount < 0:
            raise ValueError("Blur amount must be non-negative")
        if self.outline_width < 0:
            raise ValueError("Outline width must be non-negative")


class StyleInheritance:
    """Style inheritance and cascading system."""
    
    def __init__(self):
        self._parent_styles: Dict[str, 'WidgetStyle'] = {}
        self._inheritance_rules: Dict[str, List[str]] = {}
        self._lock = threading.RLock()
    
    def register_parent_style(self, name: str, style: 'WidgetStyle') -> None:
        """Register a parent style for inheritance."""
        with self._lock:
            self._parent_styles[name] = style
    
    def set_inheritance_rule(self, child_property: str, parent_properties: List[str]) -> None:
        """Set inheritance rule for a property."""
        with self._lock:
            self._inheritance_rules[child_property] = parent_properties.copy()
    
    def inherit_style(self, child_style: 'WidgetStyle', parent_name: str) -> 'WidgetStyle':
        """Create new style by inheriting from parent."""
        with self._lock:
            if parent_name not in self._parent_styles:
                raise ValueError(f"Parent style '{parent_name}' not found")
            
            parent_style = self._parent_styles[parent_name]
            inherited_style = WidgetStyle()
            
            # Copy parent properties first
            for attr_name in dir(parent_style):
                if not attr_name.startswith('_') and hasattr(inherited_style, attr_name):
                    parent_value = getattr(parent_style, attr_name)
                    if parent_value is not None:
                        setattr(inherited_style, attr_name, parent_value)
            
            # Override with child properties
            for attr_name in dir(child_style):
                if not attr_name.startswith('_') and hasattr(inherited_style, attr_name):
                    child_value = getattr(child_style, attr_name)
                    if child_value is not None:
                        setattr(inherited_style, attr_name, child_value)
            
            return inherited_style


@dataclass
class WidgetStyle:
    """Comprehensive widget styling configuration."""
    
    # Basic properties
    visible: bool = True
    opacity: float = 1.0
    
    # Colors
    foreground_color: Optional[Color] = None
    background: BackgroundStyle = field(default_factory=BackgroundStyle)
    
    # Border
    border: BorderStyle = field(default_factory=BorderStyle)
    
    # Spacing
    margin: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # top, right, bottom, left
    padding: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # top, right, bottom, left
    
    # Visual effects
    effects: List[VisualEffect] = field(default_factory=list)
    
    # Transform properties
    rotation: float = 0.0  # Degrees
    scale: Tuple[float, float] = (1.0, 1.0)  # x, y scale factors
    skew: Tuple[float, float] = (0.0, 0.0)  # x, y skew in degrees
    
    # Animation properties
    transition_duration: float = 0.0  # Seconds
    transition_easing: str = "linear"
    
    # Custom properties for extensibility
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self._validate_style()
    
    def _validate_style(self) -> None:
        """Validate style configuration."""
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError("Opacity must be between 0.0 and 1.0")
        
        if self.foreground_color is not None and not isinstance(self.foreground_color, Color):
            self.foreground_color = Color(self.foreground_color)
        
        if not isinstance(self.background, BackgroundStyle):
            raise ValueError("Background must be BackgroundStyle instance")
        
        if not isinstance(self.border, BorderStyle):
            raise ValueError("Border must be BorderStyle instance")
        
        # Validate spacing tuples
        for spacing_name in ['margin', 'padding']:
            spacing = getattr(self, spacing_name)
            if not (isinstance(spacing, (tuple, list)) and len(spacing) == 4):
                raise ValueError(f"{spacing_name} must be a tuple of 4 values")
            if not all(isinstance(v, (int, float)) and v >= 0 for v in spacing):
                raise ValueError(f"{spacing_name} values must be non-negative numbers")
        
        # Validate scale factors
        if not (isinstance(self.scale, (tuple, list)) and len(self.scale) == 2):
            raise ValueError("Scale must be a tuple of 2 values")
        if not all(isinstance(v, (int, float)) and v > 0 for v in self.scale):
            raise ValueError("Scale factors must be positive numbers")
        
        # Validate effects
        for effect in self.effects:
            if not isinstance(effect, VisualEffect):
                raise ValueError("Effects must be VisualEffect instances")
        
        if self.transition_duration < 0:
            raise ValueError("Transition duration must be non-negative")
    
    def add_effect(self, effect: VisualEffect) -> None:
        """Add visual effect to style."""
        if not isinstance(effect, VisualEffect):
            raise ValueError("Effect must be VisualEffect instance")
        self.effects.append(effect)
    
    def remove_effect(self, effect_type: EffectType) -> bool:
        """Remove visual effect by type."""
        for i, effect in enumerate(self.effects):
            if effect.type == effect_type:
                del self.effects[i]
                return True
        return False
    
    def get_effect(self, effect_type: EffectType) -> Optional[VisualEffect]:
        """Get visual effect by type."""
        for effect in self.effects:
            if effect.type == effect_type:
                return effect
        return None
    
    def set_margin(self, top: float, right: Optional[float] = None, 
                   bottom: Optional[float] = None, left: Optional[float] = None) -> None:
        """Set margin with CSS-like syntax."""
        if right is None:
            right = top
        if bottom is None:
            bottom = top
        if left is None:
            left = right
        
        self.margin = (top, right, bottom, left)
        self._validate_style()
    
    def set_padding(self, top: float, right: Optional[float] = None,
                    bottom: Optional[float] = None, left: Optional[float] = None) -> None:
        """Set padding with CSS-like syntax."""
        if right is None:
            right = top
        if bottom is None:
            bottom = top
        if left is None:
            left = right
        
        self.padding = (top, right, bottom, left)
        self._validate_style()
    
    def clone(self) -> 'WidgetStyle':
        """Create a deep copy of the style."""
        import copy
        # Use copy.copy for shallow copy, then deep copy complex objects
        cloned = copy.copy(self)
        
        # Deep copy complex objects that need it
        cloned.background = copy.deepcopy(self.background)
        cloned.border = copy.deepcopy(self.border)
        cloned.effects = copy.deepcopy(self.effects)
        cloned.custom_properties = copy.deepcopy(self.custom_properties)
        
        return cloned
    
    def merge(self, other: 'WidgetStyle') -> 'WidgetStyle':
        """Merge with another style, other takes precedence."""
        merged = self.clone()
        
        # Create a default style to compare against
        default_style = WidgetStyle()
        
        for attr_name in dir(other):
            if (not attr_name.startswith('_') and 
                hasattr(merged, attr_name) and 
                not callable(getattr(other, attr_name))):  # Skip methods
                
                other_value = getattr(other, attr_name)
                default_value = getattr(default_style, attr_name)
                
                # Only override if the other value is different from default
                # This ensures we only merge explicitly set values
                try:
                    is_different = other_value != default_value
                except Exception as e:
                    # If comparison fails, assume it's different (safer)
                    is_different = True
                
                if is_different:
                    # Special handling for lists and dicts
                    if attr_name == 'effects':
                        merged.effects.extend(other_value)
                    elif attr_name == 'custom_properties':
                        merged.custom_properties.update(other_value)
                    else:
                        setattr(merged, attr_name, other_value)
        
        return merged


class StyleValidator:
    """Style validation and error handling."""
    
    @staticmethod
    def validate_color(color: Any) -> bool:
        """Validate color value."""
        try:
            Color(color)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_spacing(spacing: Any) -> bool:
        """Validate spacing tuple."""
        if not isinstance(spacing, (tuple, list)) or len(spacing) != 4:
            return False
        return all(isinstance(v, (int, float)) and v >= 0 for v in spacing)
    
    @staticmethod
    def validate_style(style: WidgetStyle) -> List[str]:
        """Validate complete style and return list of errors."""
        errors = []
        
        try:
            style._validate_style()
        except ValueError as e:
            errors.append(str(e))
        
        # Additional validation
        if style.foreground_color and not StyleValidator.validate_color(style.foreground_color):
            errors.append("Invalid foreground color")
        
        if not StyleValidator.validate_spacing(style.margin):
            errors.append("Invalid margin values")
        
        if not StyleValidator.validate_spacing(style.padding):
            errors.append("Invalid padding values")
        
        return errors


# Global style inheritance manager
_style_inheritance = StyleInheritance()


def get_style_inheritance() -> StyleInheritance:
    """Get global style inheritance manager."""
    return _style_inheritance


def create_style(**kwargs) -> WidgetStyle:
    """Create widget style with validation."""
    try:
        return WidgetStyle(**kwargs)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid style configuration: {e}")


def parse_color(color: Any) -> Color:
    """Parse color from any supported format."""
    return Color(color)


def create_gradient_background(stops: List[Tuple[float, Any]], 
                             gradient_type: str = "linear",
                             angle: float = 0.0) -> BackgroundStyle:
    """Create gradient background style."""
    gradient_stops = [GradientStop(pos, Color(color)) for pos, color in stops]
    
    bg_type = BackgroundType.LINEAR_GRADIENT if gradient_type == "linear" else BackgroundType.RADIAL_GRADIENT
    
    return BackgroundStyle(
        type=bg_type,
        gradient_stops=gradient_stops,
        gradient_angle=angle
    )


def create_shadow_effect(offset: Tuple[float, float] = (2.0, 2.0),
                        blur: float = 4.0,
                        color: Any = 'black',
                        spread: float = 0.0) -> VisualEffect:
    """Create shadow effect."""
    return VisualEffect(
        type=EffectType.SHADOW,
        offset=offset,
        blur_radius=blur,
        spread_radius=spread,
        color=Color(color)
    )


def create_glow_effect(blur: float = 4.0,
                      color: Any = 'white',
                      spread: float = 0.0) -> VisualEffect:
    """Create glow effect."""
    return VisualEffect(
        type=EffectType.GLOW,
        offset=(0.0, 0.0),
        blur_radius=blur,
        spread_radius=spread,
        color=Color(color)
    ) 