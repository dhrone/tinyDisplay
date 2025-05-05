"""
Advanced tests for the tinyDisplay Application Widget DSL parser.
"""

import sys
import os
from pathlib import Path
import pytest

# Add parent directory to sys.path to allow importing tinyDisplay modules
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from tinyDisplay.dsl import parse_application_dsl
from tinyDisplay.dsl.application.ast import (
    WidgetDeclaration, CanvasDeclaration, ThemeDeclaration, PlacementStatement,
    AppDeclaration, ResourcesBlock, TimelineBlock, EnvBlock, EnvDeclaration, 
    MacroDeclaration, DisplayDeclaration, ObjectLiteral, ArrayLiteral,
    PropertyAccess, ImportStatement, SearchPathDeclaration, DirDeclaration,
    FileDeclaration
)
from tinyDisplay.dsl.application.parser import ParseError


def test_parser_error_recovery():
    """Test parser's ability to recover from syntax errors."""
    source = """
    DEFINE WIDGET "error" AS Text {
        value: "Missing comma"
        size: (128, 16),  # Error: missing comma after previous value
    }
    
    DEFINE CANVAS "main" {  # This should still be parsed
        size: (128, 64),
    }
    """
    program = parse_application_dsl(source)
    
    # Despite the error, the parser should recover and parse the canvas
    assert len(program.statements) >= 1
    assert any(isinstance(stmt, CanvasDeclaration) for stmt in program.statements)


def test_complex_nested_expressions():
    """Test parsing of complex and nested expressions."""
    source = """
    DEFINE WIDGET "complex" AS Text {
        value: "Complex",
        position: (10 + 5 * 2, 20 / 2),  # Arithmetic expressions
        nested: {
            x: 10,
            y: {
                baseline: 20,
                offset: -5,
            },
            colors: ["red", "green", "blue"],
        },
    }
    """
    program = parse_application_dsl(source)
    
    assert len(program.statements) == 1
    assert isinstance(program.statements[0], WidgetDeclaration)
    widget = program.statements[0]
    
    # Check for complex properties
    assert "position" in widget.properties
    assert "nested" in widget.properties
    assert isinstance(widget.properties["nested"], ObjectLiteral)
    
    # Verify nesting depth
    nested = widget.properties["nested"]
    assert "y" in nested.properties
    assert isinstance(nested.properties["y"], ObjectLiteral)
    assert "colors" in nested.properties
    assert isinstance(nested.properties["colors"], ArrayLiteral)


def test_env_block():
    """Test parsing of ENV block with multiple declarations."""
    source = """
    DEFINE ENV {
        APP_HOME: "/home/user/app";
        DEBUG_MODE: "true";
        API_URL: "https://api.example.com";
    }
    """
    program = parse_application_dsl(source)
    
    assert len(program.statements) == 1
    assert isinstance(program.statements[0], EnvBlock)
    
    env_block = program.statements[0]
    assert len(env_block.declarations) == 3
    
    # Check specific declarations
    assert any(isinstance(decl, EnvDeclaration) and decl.name == "APP_HOME" for decl in env_block.declarations)
    assert any(isinstance(decl, EnvDeclaration) and decl.name == "DEBUG_MODE" for decl in env_block.declarations)
    assert any(isinstance(decl, EnvDeclaration) and decl.name == "API_URL" for decl in env_block.declarations)


def test_macro_declarations():
    """Test parsing of macro declarations with parameters."""
    source = """
    DEFINE MACRO SCREEN_WIDTH 128;
    DEFINE MACRO CENTER_X(width) (SCREEN_WIDTH - width) / 2;
    DEFINE MACRO CENTER_POS(width, height) {
        x: (SCREEN_WIDTH - width) / 2,
        y: 10,
    };
    """
    program = parse_application_dsl(source)
    
    assert len(program.statements) == 3
    assert all(isinstance(stmt, MacroDeclaration) for stmt in program.statements)
    
    # Simple macro
    assert program.statements[0].name == "SCREEN_WIDTH"
    assert len(program.statements[0].parameters) == 0
    
    # Single parameter macro
    assert program.statements[1].name == "CENTER_X"
    assert len(program.statements[1].parameters) == 1
    assert program.statements[1].parameters[0] == "width"
    
    # Multi-parameter macro with object literal
    assert program.statements[2].name == "CENTER_POS"
    assert len(program.statements[2].parameters) == 2
    assert "width" in program.statements[2].parameters
    assert "height" in program.statements[2].parameters
    assert isinstance(program.statements[2].value, ObjectLiteral)


def test_display_declaration():
    """Test parsing of display declaration with interface block."""
    source = """
    DEFINE DISPLAY "main" {
        width: 128,
        height: 64,
        color_mode: "1",
        
        INTERFACE {
            type: "spi",
            bus: 0,
            device: 0,
            reset_pin: 25,
        }
    }
    """
    program = parse_application_dsl(source)
    
    assert len(program.statements) == 1
    assert isinstance(program.statements[0], DisplayDeclaration)
    
    display = program.statements[0]
    assert display.name == "main"
    assert len(display.properties) == 3
    assert display.interface is not None
    assert len(display.interface) == 4
    assert display.interface["type"].value == "spi"


def test_complex_timeline_block():
    """Test parsing widget with complex timeline block."""
    source = """
    DEFINE WIDGET "animated" AS Rectangle {
        size: (128, 64),
        background: "black",
        
        TIMELINE {
            LOOP(INFINITE) {
                MOVE(LEFT, 100) { step=1, interval=2 };
                PAUSE(10);
                IF(widget.x <= 0) {
                    RESET_POSITION();
                } END;
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
    # Timeline content is parsed as Marquee DSL AST, so we just check it exists
    assert widget.timeline.marquee_ast is not None


def test_theme_property_access():
    """Test parsing of property access expressions."""
    source = """
    DEFINE THEME "dark" {
        background: "black",
        foreground: "white",
        accent: "blue",
    }
    
    DEFINE WIDGET "title" AS Text {
        value: "Hello",
        foreground: THEME.accent,
        background: THEME.background,
    }
    """
    program = parse_application_dsl(source)
    
    assert len(program.statements) == 2
    assert isinstance(program.statements[0], ThemeDeclaration)
    assert isinstance(program.statements[1], WidgetDeclaration)
    
    widget = program.statements[1]
    assert isinstance(widget.properties["foreground"], PropertyAccess)
    assert widget.properties["foreground"].object == "THEME"
    assert widget.properties["foreground"].property == "accent"
    
    assert isinstance(widget.properties["background"], PropertyAccess)
    assert widget.properties["background"].object == "THEME"
    assert widget.properties["background"].property == "background"


def test_import_statement():
    """Test parsing of import statements."""
    source = """
    IMPORT widget1, widget2 FROM "common.dsl";
    IMPORT * FROM "/absolute/path/to/utils.dsl";
    """
    program = parse_application_dsl(source)
    
    assert len(program.statements) == 2
    assert all(isinstance(stmt, ImportStatement) for stmt in program.statements)
    
    # First import with specific items
    assert len(program.statements[0].imports) == 2
    assert "widget1" in program.statements[0].imports
    assert "widget2" in program.statements[0].imports
    assert program.statements[0].source == "common.dsl"
    
    # Second import with wildcard
    assert len(program.statements[1].imports) == 1
    assert program.statements[1].imports[0] == "*"
    assert program.statements[1].source == "/absolute/path/to/utils.dsl"


def test_resources_block():
    """Test parsing of resources block with different declaration types."""
    source = """
    DEFINE RESOURCES {
        fonts: "path/to/fonts/",
        images: "path/to/images/",
        FILE logo: "images/logo.png",
        FILE icon: "images/icon.svg",
        SEARCH_PATH themes: ["theme1/", "theme2/", "theme3/"],
    }
    """
    program = parse_application_dsl(source)
    
    assert len(program.statements) == 1
    assert isinstance(program.statements[0], ResourcesBlock)
    
    resources = program.statements[0]
    assert len(resources.declarations) == 5
    
    # Check for directory declarations
    dir_decls = [d for d in resources.declarations if isinstance(d, DirDeclaration)]
    assert len(dir_decls) == 2
    assert any(d.path_type == "fonts" for d in dir_decls)
    assert any(d.path_type == "images" for d in dir_decls)
    
    # Check for file declarations
    file_decls = [f for f in resources.declarations if isinstance(f, FileDeclaration)]
    assert len(file_decls) == 2
    assert any(f.name == "logo" for f in file_decls)
    assert any(f.name == "icon" for f in file_decls)
    
    # Check for search path declaration
    search_path_decls = [s for s in resources.declarations if isinstance(s, SearchPathDeclaration)]
    assert len(search_path_decls) == 1
    assert search_path_decls[0].path_type == "themes"
    assert len(search_path_decls[0].paths) == 3 