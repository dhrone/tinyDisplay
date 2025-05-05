"""
Integration tests for the tinyDisplay DSL framework.

These tests verify that the Application DSL and Marquee DSL work together correctly.
"""

import sys
import os
from pathlib import Path
import pytest

# Add parent directory to sys.path to allow importing tinyDisplay modules
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from tinyDisplay.dsl import (
    parse_application_dsl, parse_marquee_dsl,
    parse_and_validate_application_dsl, parse_and_validate_marquee_dsl
)
from tinyDisplay.dsl.application.ast import TimelineBlock, WidgetDeclaration
from tinyDisplay.dsl.marquee.ast import (
    Program as MarqueeProgram, Block, MoveStatement, 
    PauseStatement, LoopStatement
)


def test_timeline_block_integration():
    """Test integration of Marquee DSL inside Application TIMELINE blocks."""
    source = """
    DEFINE WIDGET "scrolling_text" AS Text {
        value: "This is a scrolling text",
        size: (128, 16),
        foreground: "white",
        background: "black",
        
        TIMELINE {
            LOOP(INFINITE) {
                MOVE(LEFT, 128) { step=1, interval=2 };
                PAUSE(20);
                RESET_POSITION();
            } END;
        }
    }
    """
    program, errors = parse_and_validate_application_dsl(source)
    
    # Verify no errors
    assert len(errors) == 0
    
    # Verify the widget declaration contains a timeline block
    assert len(program.statements) == 1
    widget = program.statements[0]
    assert isinstance(widget, WidgetDeclaration)
    assert widget.timeline is not None
    
    # Verify the marquee AST was correctly parsed
    marquee_ast = widget.timeline.marquee_ast
    assert isinstance(marquee_ast, MarqueeProgram)
    
    # Verify the loop statement exists in the marquee AST
    loop_stmts = [s for s in marquee_ast.statements if isinstance(s, LoopStatement)]
    assert len(loop_stmts) == 1
    
    # Verify the loop contains MOVE, PAUSE, and RESET_POSITION statements
    loop_body = loop_stmts[0].body
    assert len(loop_body.statements) == 3
    assert isinstance(loop_body.statements[0], MoveStatement)
    assert isinstance(loop_body.statements[1], PauseStatement)


def test_complex_application_with_multiple_timelines():
    """Test parsing of a complex application with multiple animated widgets."""
    source = """
    DEFINE THEME "dark" {
        background: "black",
        foreground: "white",
        accent: "blue",
    }
    
    DEFINE WIDGET "title" AS Text {
        value: "Weather Dashboard",
        size: (128, 16),
        foreground: THEME.accent,
        background: THEME.background,
        
        TIMELINE {
            // Fade in animation
            MOVE(IN, 50) { opacity_start=0, opacity_end=1 };
        }
    }
    
    DEFINE WIDGET "temperature" AS Text {
        value: "22°C",
        size: (64, 32),
        foreground: THEME.foreground,
        background: THEME.background,
        
        TIMELINE {
            // Blink animation for emphasis
            LOOP(3) {
                PAUSE(10);
                MOVE(NONE, 5) { opacity_start=1, opacity_end=0 };
                MOVE(NONE, 5) { opacity_start=0, opacity_end=1 };
            } END;
        }
    }
    
    DEFINE CANVAS "main" {
        size: (128, 64),
        background: THEME.background,
        
        PLACE "title" AT (0, 0);
        PLACE "temperature" AT (32, 24);
    }
    
    DEFINE APP "weather_app" {
        theme: "dark",
        defaultScreen: "main",
        
        SCREENS {
            REFERENCE "main";
        }
    }
    """
    program, errors = parse_and_validate_application_dsl(source)
    
    # Verify no errors
    assert len(errors) == 0
    
    # Verify all expected statements exist
    assert len(program.statements) == 5
    
    # Verify the two widgets with timelines
    widgets = [s for s in program.statements if isinstance(s, WidgetDeclaration)]
    assert len(widgets) == 2
    
    # Check both timelines were parsed correctly
    title_widget = next(w for w in widgets if w.name == "title")
    temp_widget = next(w for w in widgets if w.name == "temperature")
    
    assert title_widget.timeline is not None
    assert temp_widget.timeline is not None
    
    # Verify the title widget's timeline has a MOVE statement
    title_marquee = title_widget.timeline.marquee_ast
    assert any(isinstance(s, MoveStatement) for s in title_marquee.statements)
    
    # Verify the temperature widget's timeline has a LOOP statement
    temp_marquee = temp_widget.timeline.marquee_ast
    assert any(isinstance(s, LoopStatement) for s in temp_marquee.statements)


def test_marquee_within_application_validation():
    """Test validation of marquee code within application DSL."""
    source = """
    DEFINE WIDGET "invalid_animation" AS Text {
        value: "Invalid Animation",
        
        TIMELINE {
            MOVE(INVALID_DIRECTION, 100);  // Invalid direction
            BREAK;  // BREAK outside of loop
        }
    }
    """
    program, errors = parse_and_validate_application_dsl(source)
    
    # Verify errors were detected in the embedded marquee code
    assert len(errors) > 0
    marquee_errors = [e for e in errors if "TIMELINE" in str(e)]
    assert len(marquee_errors) > 0


def test_widget_reference_in_timeline():
    """Test that marquee code can reference its parent widget."""
    source = """
    DEFINE WIDGET "self_aware" AS Text {
        value: "Self-aware widget",
        size: (128, 16),
        
        TIMELINE {
            LOOP(INFINITE) {
                IF(widget.x <= 0) {
                    MOVE(RIGHT, widget.width);
                } ELSEIF(widget.x >= container.width - widget.width) {
                    MOVE(LEFT, widget.width);
                } END;
            } END;
        }
    }
    """
    program, errors = parse_and_validate_application_dsl(source)
    
    # Verify no errors
    assert len(errors) == 0
    
    # Verify the widget declaration
    assert len(program.statements) == 1
    widget = program.statements[0]
    assert isinstance(widget, WidgetDeclaration)
    
    # Verify the timeline contains references to the widget properties
    timeline = widget.timeline
    assert timeline is not None
    assert "widget.x" in timeline.source
    assert "widget.width" in timeline.source
    assert "container.width" in timeline.source


def test_application_embed_standalone_marquee():
    """Test embedding a standalone marquee animation into an application."""
    # First, define a standalone marquee animation
    marquee_source = """
    LOOP(INFINITE) {
        MOVE(LEFT, 128) { step=1 };
        PAUSE(20);
        RESET_POSITION();
    } END;
    """
    marquee_program, marquee_errors = parse_and_validate_marquee_dsl(marquee_source)
    assert len(marquee_errors) == 0
    
    # Now embed it in an application widget
    app_source = f"""
    DEFINE WIDGET "embedded" AS Text {{
        value: "Embedded animation",
        size: (128, 16),
        
        TIMELINE {{
            {marquee_source}
        }}
    }}
    """
    app_program, app_errors = parse_and_validate_application_dsl(app_source)
    
    # Verify no errors
    assert len(app_errors) == 0
    
    # Verify the widget declaration contains a timeline block
    assert len(app_program.statements) == 1
    widget = app_program.statements[0]
    assert isinstance(widget, WidgetDeclaration)
    assert widget.timeline is not None
    
    # Verify the marquee AST was correctly parsed
    marquee_ast = widget.timeline.marquee_ast
    assert isinstance(marquee_ast, MarqueeProgram)
    
    # Verify the timeline has the same structure as the standalone marquee
    assert len(marquee_ast.statements) == len(marquee_program.statements)
    assert isinstance(marquee_ast.statements[0], LoopStatement)


def test_mixed_dsl_file():
    """Test parsing a file with both DSL syntaxes interleaved."""
    source = """
    // Application DSL part
    DEFINE THEME "dark" {
        background: "black",
        foreground: "white",
    }
    
    DEFINE WIDGET "animated" AS Text {
        value: "Mixed DSL test",
        background: THEME.background,
        foreground: THEME.foreground,
        
        // Marquee DSL embedded in TIMELINE block
        TIMELINE {
            // This is Marquee DSL syntax
            PERIOD(100);
            SEGMENT(intro, 0, 50) {
                MOVE(IN, 50) { opacity_start=0, opacity_end=1 };
            } END;
            
            SEGMENT(main, 51, 150) {
                LOOP(3) {
                    MOVE(LEFT, 20);
                    MOVE(RIGHT, 20);
                } END;
            } END;
        }
    }
    
    // Back to Application DSL
    DEFINE CANVAS "main" {
        size: (128, 64),
        background: THEME.background,
        
        PLACE "animated" AT (0, 24);
    }
    """
    program, errors = parse_and_validate_application_dsl(source)
    
    # Verify no errors
    assert len(errors) == 0
    
    # Check overall structure
    assert len(program.statements) == 3
    
    # Verify the widget with timeline
    widget = next(s for s in program.statements if isinstance(s, WidgetDeclaration))
    assert widget.timeline is not None
    
    # Verify the marquee segments
    marquee_ast = widget.timeline.marquee_ast
    segment_strs = [s for s in widget.timeline.source.split('\n') if "SEGMENT" in s]
    assert len(segment_strs) == 2  # Two segments defined
    assert "intro" in widget.timeline.source
    assert "main" in widget.timeline.source 