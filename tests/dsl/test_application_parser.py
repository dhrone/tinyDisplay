"""
Tests for the tinyDisplay Application Widget DSL parser and validator.
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


def test_widget_declaration():
    """Test parsing of a widget declaration."""
    source = """
    DEFINE WIDGET "title" AS Text {
        value: "Hello World",
        size: (128, 16),
        foreground: "white",
        background: "black",
    }
    """
    
    program = parse_application_dsl(source)
    
    # Assertions to verify results
    assert len(program.statements) == 1, "Expected 1 statement in the program"
    assert isinstance(program.statements[0], WidgetDeclaration), "Expected a WidgetDeclaration"
    
    widget = program.statements[0]
    assert widget.name == "title", "Expected widget name to be 'title'"
    assert widget.type == "Text", "Expected widget type to be 'Text'"
    assert len(widget.properties) == 4, "Expected 4 properties"
    assert "value" in widget.properties, "Expected 'value' property"
    assert "size" in widget.properties, "Expected 'size' property"
    assert "foreground" in widget.properties, "Expected 'foreground' property"
    assert "background" in widget.properties, "Expected 'background' property"


def test_canvas_with_placements():
    """Test parsing of a canvas with placements."""
    source = """
    DEFINE CANVAS "main" {
        size: (128, 64),
        background: "black",
        
        PLACE "title" AT (10, 10) Z 100;
        PLACE "status" AT (10, 30) Z 50;
    }
    """
    
    program = parse_application_dsl(source)
    
    # Assertions to verify results
    assert len(program.statements) == 1, "Expected 1 statement in the program"
    assert isinstance(program.statements[0], CanvasDeclaration), "Expected a CanvasDeclaration"
    
    canvas = program.statements[0]
    assert canvas.name == "main", "Expected canvas name to be 'main'"
    assert len(canvas.properties) == 2, "Expected 2 properties"
    assert len(canvas.placements) == 2, "Expected 2 placements"
    assert canvas.placements[0].widget_name == "title", "Expected first placement widget to be 'title'"
    assert canvas.placements[1].widget_name == "status", "Expected second placement widget to be 'status'"


def test_theme_declaration():
    """Test parsing of a theme declaration."""
    source = """
    DEFINE THEME "dark" {
        background: "black",
        foreground: "white",
        accent: "blue",
    }
    """
    
    program = parse_application_dsl(source)
    
    # Assertions to verify results
    assert len(program.statements) == 1, "Expected 1 statement in the program"
    assert isinstance(program.statements[0], ThemeDeclaration), "Expected a ThemeDeclaration"
    
    theme = program.statements[0]
    assert theme.name == "dark", "Expected theme name to be 'dark'"
    assert len(theme.properties) == 3, "Expected 3 properties"
    assert "background" in theme.properties, "Expected 'background' property"
    assert "foreground" in theme.properties, "Expected 'foreground' property"
    assert "accent" in theme.properties, "Expected 'accent' property"


def test_app_declaration():
    """Test parsing of an app declaration."""
    source = """
    DEFINE APP "weatherStation" {
        theme: "dark",
        defaultScreen: "home",
        
        SCREENS {
            REFERENCE "home";
            REFERENCE "settings";
        }
        
        DATASOURCES {
            REFERENCE "weather";
            REFERENCE "system";
        }
    }
    """
    
    program = parse_application_dsl(source)
    
    # Assertions to verify results
    assert len(program.statements) == 1, "Expected 1 statement in the program"
    assert isinstance(program.statements[0], AppDeclaration), "Expected an AppDeclaration"
    
    app = program.statements[0]
    assert app.name == "weatherStation", "Expected app name to be 'weatherStation'"
    assert len(app.properties) == 2, "Expected 2 properties"
    assert len(app.screens) == 2, "Expected 2 screens"
    assert len(app.datasources) == 2, "Expected 2 datasources"
    assert app.screens[0].target_name == "home", "Expected first screen to be 'home'"
    assert app.screens[1].target_name == "settings", "Expected second screen to be 'settings'"
    assert app.datasources[0].target_name == "weather", "Expected first datasource to be 'weather'"
    assert app.datasources[1].target_name == "system", "Expected second datasource to be 'system'"


def test_resources_block():
    """Test parsing of a resources block."""
    source = """
    DEFINE RESOURCES {
        fonts: "path/to/fonts/",
        FILE logo: "images/logo.png",
        SEARCH_PATH images: ["dir1/", "dir2/"],
    }
    """
    
    program = parse_application_dsl(source)
    
    # Assertions to verify results
    assert len(program.statements) == 1, "Expected 1 statement in the program"
    assert isinstance(program.statements[0], ResourcesBlock), "Expected a ResourcesBlock"
    
    resources = program.statements[0]
    assert len(resources.declarations) == 3, "Expected 3 declarations"


def test_widget_with_timeline():
    """Test parsing of a widget with a timeline."""
    source = """
    DEFINE WIDGET "scrollingText" AS Text {
        value: "Scrolling Message",
        size: (128, 16),
        foreground: "white",
        background: "black",
        
        TIMELINE {
            MOVE(LEFT, 100) { step=1, interval=2 };
            PAUSE(10);
            LOOP {
                MOVE(RIGHT, 100);
                PAUSE(5);
                MOVE(LEFT, 100);
                PAUSE(5);
            }
        }
    }
    """
    
    program = parse_application_dsl(source)
    
    # Assertions to verify results
    assert len(program.statements) == 1, "Expected 1 statement in the program"
    assert isinstance(program.statements[0], WidgetDeclaration), "Expected a WidgetDeclaration"
    
    widget = program.statements[0]
    assert widget.name == "scrollingText", "Expected widget name to be 'scrollingText'"
    assert widget.timeline is not None, "Expected timeline to be present"
    assert isinstance(widget.timeline, TimelineBlock), "Expected a TimelineBlock"


def test_validation_errors():
    """Test validation of undefined references."""
    source = """
    DEFINE CANVAS "main" {
        size: (128, 64),
        background: "black",
        
        PLACE "undefined_widget" AT (10, 10) Z 100;
    }
    """
    
    program, errors = parse_and_validate_application_dsl(source)
    
    # Assertions to verify results
    assert len(errors) > 0, "Expected validation errors"
    assert any("is not defined" in str(error) for error in errors), "Expected 'not defined' error"


def test_complete_application():
    """Test parsing of a complete application with multiple declarations."""
    source = """
    DEFINE THEME "dark" {
        background: "black",
        foreground: "white",
        accent: "blue",
    }
    
    DEFINE WIDGET "title" AS Text {
        value: "Weather Station",
        size: (128, 16),
        foreground: THEME.accent,
        background: "black",
    }
    
    DEFINE WIDGET "temperature" AS Text {
        value: "{weather.temperature}°C",
        size: (64, 24),
        foreground: "white",
        background: "black",
    }
    
    DEFINE CANVAS "home" {
        size: (128, 64),
        background: "black",
        
        PLACE "title" AT (10, 5) Z 100;
        PLACE "temperature" AT (10, 25) Z 90;
    }
    
    DEFINE APP "weatherApp" {
        theme: "dark",
        defaultScreen: "home",
        
        SCREENS {
            REFERENCE "home";
        }
    }
    """
    
    program = parse_application_dsl(source)
    
    # Assertions to verify results
    assert len(program.statements) == 4, "Expected 4 statements in the program"
    assert any(isinstance(stmt, ThemeDeclaration) for stmt in program.statements), "Expected a ThemeDeclaration"
    assert sum(1 for stmt in program.statements if isinstance(stmt, WidgetDeclaration)) == 2, "Expected 2 WidgetDeclarations"
    assert any(isinstance(stmt, CanvasDeclaration) for stmt in program.statements), "Expected a CanvasDeclaration"
    assert any(isinstance(stmt, AppDeclaration) for stmt in program.statements), "Expected an AppDeclaration" 