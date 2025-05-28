"""
Comprehensive tests for the tinyDisplay Application Widget DSL.

This test suite implements a complete test coverage to ensure the Application Widget DSL
functions correctly for defining widgets, screens, and applications.
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
    AppDeclaration, ResourcesBlock, TimelineBlock, ReferenceStatement, 
    Literal, Variable, BinaryExpression, PropertyAccess, ArrayLiteral
)


class TestWidgetDefinitions:
    """Tests for Widget Definitions in the Application DSL."""
    
    def test_basic_widget_definition(self):
        """Test basic widget definition with simple properties."""
        source = """
        DEFINE WIDGET "title" AS Text {
            value: "Hello World",
            size: (128, 16),
            foreground: "white",
            background: "black"
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], WidgetDeclaration)
        
        widget = program.statements[0]
        assert widget.name == "title"
        assert widget.type == "Text"
        assert len(widget.properties) == 4
        assert "value" in widget.properties
        assert "size" in widget.properties
        assert "foreground" in widget.properties
        assert "background" in widget.properties
    
    def test_widget_with_expressions(self):
        """Test widget definition with complex expressions."""
        source = """
        DEFINE WIDGET "dynamicText" AS Text {
            value: "{data.temperature}°C",
            size: (container.width / 2, 16),
            foreground: data.temperature > 30 ? "red" : "blue",
            background: "black"
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], WidgetDeclaration)
        
        widget = program.statements[0]
        
        # Check that size property contains a binary expression
        size_prop = widget.properties["size"]
        assert isinstance(size_prop, ArrayLiteral)
        assert isinstance(size_prop.elements[0], BinaryExpression)
        assert size_prop.elements[0].operator == "/"
        
        # Check the conditional expression for foreground
        foreground_prop = widget.properties["foreground"]
        assert isinstance(foreground_prop, BinaryExpression)
        assert foreground_prop.operator == "?"
    
    def test_widget_with_timeline(self):
        """Test widget with embedded timeline animation."""
        source = """
        DEFINE WIDGET "animatedText" AS Text {
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
                } END;
            }
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], WidgetDeclaration)
        
        widget = program.statements[0]
        assert widget.timeline is not None
        assert isinstance(widget.timeline, TimelineBlock)
        
        # Check timeline statements
        timeline = widget.timeline
        assert len(timeline.statements) >= 3  # MOVE, PAUSE, LOOP
    
    def test_multiple_widget_types(self):
        """Test various types of widgets."""
        source = """
        DEFINE WIDGET "label" AS Text {
            value: "Label",
            size: (64, 16)
        }
        
        DEFINE WIDGET "icon" AS Image {
            source: "icon.png",
            size: (32, 32)
        }
        
        DEFINE WIDGET "progress" AS ProgressBar {
            value: 75,
            size: (100, 10),
            fill: "green"
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 3
        
        widget_types = ["Text", "Image", "ProgressBar"]
        for i, widget_type in enumerate(widget_types):
            assert isinstance(program.statements[i], WidgetDeclaration)
            assert program.statements[i].type == widget_type


class TestCanvasDefinitions:
    """Tests for Canvas Definitions in the Application DSL."""
    
    def test_basic_canvas(self):
        """Test basic canvas declaration with properties."""
        source = """
        DEFINE CANVAS "main" {
            size: (128, 64),
            background: "black"
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], CanvasDeclaration)
        
        canvas = program.statements[0]
        assert canvas.name == "main"
        assert len(canvas.properties) == 2
        assert "size" in canvas.properties
        assert "background" in canvas.properties
    
    def test_canvas_with_placements(self):
        """Test canvas with widget placements."""
        source = """
        DEFINE CANVAS "home" {
            size: (128, 64),
            background: "black",
            
            PLACE "title" AT (10, 5) Z 100;
            PLACE "status" AT (10, 25) Z 90;
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], CanvasDeclaration)
        
        canvas = program.statements[0]
        assert len(canvas.placements) == 2
        
        # Check first placement
        assert canvas.placements[0].widget_name == "title"
        assert canvas.placements[0].x.value == 10
        assert canvas.placements[0].y.value == 5
        assert canvas.placements[0].z.value == 100
        
        # Check second placement
        assert canvas.placements[1].widget_name == "status"
        assert canvas.placements[1].x.value == 10
        assert canvas.placements[1].y.value == 25
        assert canvas.placements[1].z.value == 90
    
    def test_canvas_with_expressions_in_placements(self):
        """Test canvas with expressions in widget placements."""
        source = """
        DEFINE CANVAS "dynamic" {
            size: (128, 64),
            background: "black",
            
            PLACE "title" AT (canvas.width / 2 - 32, 5) Z 100;
            PLACE "content" AT (10, title.y + title.height + 5) Z 90;
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        canvas = program.statements[0]
        
        # Check first placement with binary expression
        assert canvas.placements[0].widget_name == "title"
        assert isinstance(canvas.placements[0].x, BinaryExpression)
        
        # Check second placement with property access and binary expressions
        assert canvas.placements[1].widget_name == "content"
        assert isinstance(canvas.placements[1].y, BinaryExpression)


class TestThemeDefinitions:
    """Tests for Theme Definitions in the Application DSL."""
    
    def test_basic_theme(self):
        """Test basic theme definition with colors."""
        source = """
        DEFINE THEME "dark" {
            background: "black",
            foreground: "white",
            accent: "blue"
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], ThemeDeclaration)
        
        theme = program.statements[0]
        assert theme.name == "dark"
        assert len(theme.properties) == 3
        assert theme.properties["background"].value == "black"
        assert theme.properties["foreground"].value == "white"
        assert theme.properties["accent"].value == "blue"
    
    def test_theme_with_color_codes(self):
        """Test theme with hex color codes."""
        source = """
        DEFINE THEME "custom" {
            background: "#000000",
            foreground: "#FFFFFF",
            accent: "#FF5500",
            secondary: "#00AAFF"
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], ThemeDeclaration)
        
        theme = program.statements[0]
        assert theme.name == "custom"
        assert len(theme.properties) == 4
        assert theme.properties["background"].value == "#000000"
        assert theme.properties["foreground"].value == "#FFFFFF"
        assert theme.properties["accent"].value == "#FF5500"
        assert theme.properties["secondary"].value == "#00AAFF"


class TestAppDefinitions:
    """Tests for App Definitions in the Application DSL."""
    
    def test_basic_app(self):
        """Test basic app definition with properties."""
        source = """
        DEFINE APP "weatherApp" {
            theme: "dark",
            defaultScreen: "home"
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], AppDeclaration)
        
        app = program.statements[0]
        assert app.name == "weatherApp"
        assert len(app.properties) == 2
        assert "theme" in app.properties
        assert "defaultScreen" in app.properties
    
    def test_app_with_screens(self):
        """Test app with screen references."""
        source = """
        DEFINE APP "multiScreenApp" {
            theme: "dark",
            defaultScreen: "home",
            
            SCREENS {
                REFERENCE "home";
                REFERENCE "settings";
                REFERENCE "info";
            }
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], AppDeclaration)
        
        app = program.statements[0]
        assert len(app.screens) == 3
        assert app.screens[0].target_name == "home"
        assert app.screens[1].target_name == "settings"
        assert app.screens[2].target_name == "info"
    
    def test_app_with_datasources(self):
        """Test app with datasource references."""
        source = """
        DEFINE APP "dataDrivenApp" {
            theme: "dark",
            defaultScreen: "home",
            
            SCREENS {
                REFERENCE "home";
            }
            
            DATASOURCES {
                REFERENCE "weather";
                REFERENCE "system";
                REFERENCE "user";
            }
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], AppDeclaration)
        
        app = program.statements[0]
        assert len(app.datasources) == 3
        assert app.datasources[0].target_name == "weather"
        assert app.datasources[1].target_name == "system"
        assert app.datasources[2].target_name == "user"


class TestResourceDefinitions:
    """Tests for Resource Definitions in the Application DSL."""
    
    def test_resources_block(self):
        """Test resources block with various resource types."""
        source = """
        DEFINE RESOURCES {
            fonts: "path/to/fonts/",
            FILE logo: "images/logo.png",
            SEARCH_PATH images: ["dir1/", "dir2/"]
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], ResourcesBlock)
        
        resources = program.statements[0]
        assert len(resources.declarations) == 3
        
        # Check specific declaration types by looking at their string representation
        declarations_str = [str(decl) for decl in resources.declarations]
        assert any("fonts" in decl for decl in declarations_str)
        assert any("logo" in decl for decl in declarations_str)
        assert any("images" in decl for decl in declarations_str)
    
    def test_resource_paths(self):
        """Test resource paths with relative and absolute references."""
        source = """
        DEFINE RESOURCES {
            FILE icon_1: "icons/home.png",
            FILE icon_2: "/absolute/path/to/icon.png"
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        resources = program.statements[0]
        assert len(resources.declarations) == 2
        
        # Validate paths are preserved in the declarations
        declarations_str = [str(decl) for decl in resources.declarations]
        assert any("icons/home.png" in decl for decl in declarations_str)
        assert any("/absolute/path/to/icon.png" in decl for decl in declarations_str)


class TestIntegration:
    """Tests for integrated components in the Application DSL."""
    
    def test_complete_application(self):
        """Test a complete application with all components."""
        source = """
        DEFINE THEME "dark" {
            background: "black",
            foreground: "white",
            accent: "blue"
        }
        
        DEFINE WIDGET "title" AS Text {
            value: "Weather Station",
            size: (128, 16),
            foreground: THEME.accent,
            background: "black"
        }
        
        DEFINE WIDGET "temperature" AS Text {
            value: "{weather.temperature}°C",
            size: (64, 24),
            foreground: "white",
            background: "black",
            
            TIMELINE {
                SLIDE(IN, LEFT, 50);
            }
        }
        
        DEFINE CANVAS "home" {
            size: (128, 64),
            background: "black",
            
            PLACE "title" AT (10, 5) Z 100;
            PLACE "temperature" AT (10, 25) Z 90;
        }
        
        DEFINE RESOURCES {
            fonts: "fonts/",
            FILE logo: "images/logo.png"
        }
        
        DEFINE APP "weatherApp" {
            theme: "dark",
            defaultScreen: "home",
            
            SCREENS {
                REFERENCE "home";
            }
            
            DATASOURCES {
                REFERENCE "weather";
            }
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 6
        
        # Check for each component type
        assert any(isinstance(stmt, ThemeDeclaration) for stmt in program.statements)
        assert sum(1 for stmt in program.statements if isinstance(stmt, WidgetDeclaration)) == 2
        assert any(isinstance(stmt, CanvasDeclaration) for stmt in program.statements)
        assert any(isinstance(stmt, ResourcesBlock) for stmt in program.statements)
        assert any(isinstance(stmt, AppDeclaration) for stmt in program.statements)
    
    def test_theme_reference(self):
        """Test theme property references in widgets."""
        source = """
        DEFINE THEME "custom" {
            background: "black",
            foreground: "white",
            accent: "#FF5500"
        }
        
        DEFINE WIDGET "title" AS Text {
            value: "Title",
            size: (128, 16),
            foreground: THEME.accent,
            background: THEME.background
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 2
        assert isinstance(program.statements[0], ThemeDeclaration)
        assert isinstance(program.statements[1], WidgetDeclaration)
        
        widget = program.statements[1]
        foreground = widget.properties["foreground"]
        background = widget.properties["background"]
        
        # Check for theme property access
        assert isinstance(foreground, PropertyAccess)
        assert foreground.object == "THEME" 
        assert foreground.property == "accent"
        
        assert isinstance(background, PropertyAccess)
        assert background.object == "THEME"
        assert background.property == "background"


class TestErrorHandling:
    """Tests for error handling in the Application DSL parser and validator."""
    
    def test_undefined_widget_reference(self):
        """Test error when referencing undefined widget."""
        source = """
        DEFINE CANVAS "main" {
            size: (128, 64),
            
            PLACE "undefined_widget" AT (10, 10) Z 100;
        }
        """
        
        program, errors = parse_and_validate_application_dsl(source)
        assert len(errors) > 0
        assert any("undefined_widget" in str(error) for error in errors)
    
    def test_undefined_theme_reference(self):
        """Test error when referencing undefined theme."""
        source = """
        DEFINE APP "app" {
            theme: "undefined_theme",
            defaultScreen: "home"
        }
        """
        
        program, errors = parse_and_validate_application_dsl(source)
        assert len(errors) > 0
        assert any("undefined_theme" in str(error) for error in errors)
    
    def test_syntax_errors(self):
        """Test recovery from syntax errors."""
        source = """
        DEFINE WIDGET "broken" AS {  # Missing type
            value: "Test"
        }
        """
        
        program, errors = parse_and_validate_application_dsl(source)
        assert len(errors) > 0
        assert any("syntax error" in str(error).lower() for error in errors)
    
    def test_empty_program(self):
        """Test parsing an empty program."""
        source = ""
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 0
    
    def test_property_type_errors(self):
        """Test type validation in property values."""
        source = """
        DEFINE WIDGET "invalid" AS Text {
            size: "not_a_tuple",  # Should be a tuple
            foreground: 123  # Should be a string
        }
        """
        
        program, errors = parse_and_validate_application_dsl(source)
        assert len(errors) > 0
        assert any("type" in str(error).lower() for error in errors)


class TestCombinedFeatures:
    """Tests for combined features and edge cases in the Application DSL."""
    
    def test_complex_nested_structures(self):
        """Test nested structures with deep property access."""
        source = """
        DEFINE WIDGET "complex" AS Container {
            layout: "vertical",
            children: [
                {
                    type: "Text",
                    properties: {
                        value: data.items[0].name,
                        size: (data.sizes.small.width, data.sizes.small.height)
                    }
                },
                {
                    type: "Image",
                    properties: {
                        source: data.items[current_index].image_url
                    }
                }
            ]
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 1
        assert isinstance(program.statements[0], WidgetDeclaration)
        
        widget = program.statements[0]
        assert widget.name == "complex"
        assert widget.type == "Container"
        assert "children" in widget.properties
    
    def test_multiscreen_app_with_navigation(self):
        """Test multi-screen app with navigation elements."""
        source = """
        DEFINE WIDGET "nav_button" AS Button {
            label: "Navigate",
            size: (80, 20),
            onPress: navigate_to("settings")
        }
        
        DEFINE CANVAS "home" {
            size: (128, 64),
            
            PLACE "nav_button" AT (24, 40) Z 100;
        }
        
        DEFINE CANVAS "settings" {
            size: (128, 64),
            background: "gray"
        }
        
        DEFINE APP "navigationApp" {
            defaultScreen: "home",
            
            SCREENS {
                REFERENCE "home";
                REFERENCE "settings";
            }
        }
        """
        
        program = parse_application_dsl(source)
        assert len(program.statements) == 4
        
        # Check widget with event handler
        widget = next(stmt for stmt in program.statements if isinstance(stmt, WidgetDeclaration))
        assert "onPress" in widget.properties
        
        # Check app with multiple screens
        app = next(stmt for stmt in program.statements if isinstance(stmt, AppDeclaration))
        assert len(app.screens) == 2


if __name__ == "__main__":
    # When run directly, execute the tests
    pytest.main(["-xvs", __file__]) 