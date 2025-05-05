"""
Tests for the tinyDisplay Application Widget DSL validator.
"""

import sys
import os
from pathlib import Path
import pytest

# Add parent directory to sys.path to allow importing tinyDisplay modules
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from tinyDisplay.dsl import parse_application_dsl, parse_and_validate_application_dsl
from tinyDisplay.dsl.application.ast import (
    WidgetDeclaration, CanvasDeclaration, ThemeDeclaration, PlacementStatement,
    AppDeclaration, ResourcesBlock, TimelineBlock
)
from tinyDisplay.dsl.application.validator import Validator, ValidationError


def test_validator_duplicate_widget_definitions():
    """Test validation detects duplicate widget definitions."""
    source = """
    DEFINE WIDGET "title" AS Text {
        value: "Hello",
    }
    
    DEFINE WIDGET "title" AS Text {  # Same name as above
        value: "World",
    }
    """
    _, errors = parse_and_validate_application_dsl(source)
    assert any("already defined" in str(error) for error in errors)


def test_validator_missing_required_properties():
    """Test validation of required widget properties."""
    source = """
    DEFINE WIDGET "title" AS Text {
        # Missing required 'value' property
        size: (128, 16),
        foreground: "white",
        background: "black",
    }
    
    DEFINE WIDGET "icon" AS Image {
        # Missing required 'source' property
        size: (64, 64),
    }
    """
    _, errors = parse_and_validate_application_dsl(source)
    assert any("must have a 'value' property" in str(error) for error in errors)
    assert any("must have a 'source' property" in str(error) for error in errors)


def test_validator_invalid_widget_references():
    """Test validation of references to non-existent widgets."""
    source = """
    DEFINE CANVAS "main" {
        size: (128, 64),
        background: "black",
        
        PLACE "title" AT (10, 10) Z 100;  # Widget "title" doesn't exist
        PLACE "status" AT (10, 30) Z 50;  # Widget "status" doesn't exist
    }
    
    DEFINE STACK "header" {
        orientation: "horizontal",
        
        APPEND "logo";  # Widget "logo" doesn't exist
    }
    """
    _, errors = parse_and_validate_application_dsl(source)
    assert len([e for e in errors if "is not defined" in str(e)]) == 3


def test_validator_invalid_theme_reference():
    """Test validation of theme references."""
    source = """
    DEFINE APP "myApp" {
        theme: "dark",  # Theme "dark" doesn't exist
        defaultScreen: "home",
    }
    """
    _, errors = parse_and_validate_application_dsl(source)
    assert any("Theme 'dark' is not defined" in str(error) for error in errors)


def test_validator_theme_property_access():
    """Test validation of theme property access."""
    source = """
    DEFINE THEME "dark" {
        background: "black",
        foreground: "white",
        accent: "blue",
    }
    
    DEFINE WIDGET "title" AS Text {
        value: "Hello",
        foreground: THEME.accent,     # Valid
        background: THEME.invalid,    # Invalid property
    }
    """
    _, errors = parse_and_validate_application_dsl(source)
    assert any("Unknown theme property: 'invalid'" in str(error) for error in errors)


def test_validator_invalid_canvas_references():
    """Test validation of references to non-existent canvases."""
    source = """
    DEFINE APP "myApp" {
        theme: "dark",
        defaultScreen: "home",
        
        SCREENS {
            REFERENCE "home";       # Canvas "home" doesn't exist
            REFERENCE "settings";   # Canvas "settings" doesn't exist
        }
    }
    """
    _, errors = parse_and_validate_application_dsl(source)
    assert len([e for e in errors if "Canvas or sequence" in str(e) and "is not defined" in str(e)]) == 2


def test_validator_invalid_datasource_references():
    """Test validation of references to non-existent data sources."""
    source = """
    DEFINE APP "myApp" {
        theme: "dark",
        defaultScreen: "home",
        
        DATASOURCES {
            REFERENCE "weather";   # DataSource "weather" doesn't exist
            REFERENCE "system";    # DataSource "system" doesn't exist
        }
    }
    """
    _, errors = parse_and_validate_application_dsl(source)
    assert len([e for e in errors if "DataSource" in str(e) and "is not defined" in str(e)]) == 2


def test_validator_invalid_binding():
    """Test validation of invalid binding statements."""
    source = """
    DEFINE STATE "count" AS NUMBER DEFAULT 0;
    
    BIND "{value}" TO "invalid";           # Invalid format (no dot)
    BIND "{value}" TO "nonexistent.prop";  # Non-existent source
    """
    _, errors = parse_and_validate_application_dsl(source)
    assert any("Invalid binding target" in str(error) for error in errors)
    assert any("is not defined as a DataSource or State" in str(error) for error in errors)


def test_validator_unreferenced_widgets():
    """Test validation detects widgets that are never used."""
    source = """
    DEFINE WIDGET "title" AS Text {
        value: "Hello World",
    }
    
    DEFINE WIDGET "status" AS Text {
        value: "Status: OK",
    }
    
    DEFINE CANVAS "main" {
        size: (128, 64),
        
        # Only using "title", "status" is unreferenced
        PLACE "title" AT (10, 10);
    }
    """
    _, errors = parse_and_validate_application_dsl(source)
    assert any("Widget 'status' is defined but never used" in str(error) for error in errors)


def test_validator_missing_stack_orientation():
    """Test validation requires orientation for stacks."""
    source = """
    DEFINE WIDGET "title" AS Text {
        value: "Hello World",
    }
    
    DEFINE STACK "header" {
        # Missing required 'orientation' property
        APPEND "title";
    }
    """
    _, errors = parse_and_validate_application_dsl(source)
    assert any("must have an 'orientation' property" in str(error) for error in errors)


def test_validator_complex_expressions():
    """Test validation of complex expressions."""
    source = """
    DEFINE THEME "dark" {
        background: "black",
        foreground: "white",
        accent: "blue",
    }
    
    DEFINE WIDGET "complex" AS Text {
        value: "Test",
        size: (100 + 28, 8 * 2),  # Arithmetic expressions
        position: {
            x: 10,
            y: 20,
        },                        # Object literal
        colors: ["red", "green", "blue"],  # Array literal
        theme_color: THEME.accent,  # Property access
    }
    """
    _, errors = parse_and_validate_application_dsl(source)
    assert len(errors) == 0  # All expressions should be valid


def test_validator_array_literal_elements():
    """Test validation of array literal elements."""
    source = """
    DEFINE WIDGET "test" AS Text {
        value: "Test",
        colors: ["red", THEME.accent, "blue"],  # Reference to theme in array
    }
    """
    _, errors = parse_and_validate_application_dsl(source)
    assert any("Unknown theme property: 'accent'" in str(error) for error in errors) 