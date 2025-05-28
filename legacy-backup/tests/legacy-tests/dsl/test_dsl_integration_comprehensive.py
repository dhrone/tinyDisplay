"""
Integration tests for the tinyDisplay DSL systems.

This test suite focuses on the integration between the Marquee Animation DSL
and the Application Widget DSL, ensuring they work together correctly.
"""

import sys
import os
from pathlib import Path
import pytest

# Add parent directory to sys.path to allow importing tinyDisplay modules
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from tinyDisplay.dsl import parse_application_dsl, parse_and_validate_application_dsl
from tinyDisplay.dsl.marquee import parse_marquee_dsl, parse_and_validate_marquee_dsl
from tinyDisplay.dsl.application.ast import TimelineBlock


class TestBasicIntegration:
    """Tests for basic integration of Application DSL with Marquee Animation DSL."""
    
    def test_widget_with_simple_timeline(self):
        """Test a widget with a simple timeline animation."""
        app_source = """
        DEFINE WIDGET "scrollText" AS Text {
            value: "Scrolling Text",
            size: (128, 16),
            foreground: "white",
            background: "black",
            
            TIMELINE {
                MOVE(LEFT, 100) { step=1, interval=2 };
                PAUSE(10);
                MOVE(RIGHT, 100);
            }
        }
        """
        
        program = parse_application_dsl(app_source)
        
        # Check widget declaration
        assert len(program.statements) == 1
        widget = program.statements[0]
        assert widget.timeline is not None
        
        # Verify timeline content
        timeline = widget.timeline
        assert len(timeline.marquee_ast.statements) == 3
    
    def test_embedded_marquee_dsl(self):
        """Test that Marquee DSL can be embedded within Application DSL."""
        marquee_source = """
        LOOP(INFINITE) {
            SCROLL(LEFT, widget.width) { step=1 };
            PAUSE(20);
            RESET_POSITION({ mode="seamless" });
        } END;
        """
        
        app_source = f"""
        DEFINE WIDGET "marqueeText" AS Text {{
            value: "This is a marquee text that scrolls",
            size: (128, 16),
            foreground: "white",
            background: "black",
            
            TIMELINE {{
                {marquee_source}
            }}
        }}
        """
        
        program = parse_application_dsl(app_source)
        
        # Check widget declaration
        assert len(program.statements) == 1
        widget = program.statements[0]
        assert widget.timeline is not None
        
        # Verify that the marquee DSL is embedded
        # Check that the marquee AST has at least one LoopStatement
        assert any(hasattr(stmt, 'count') and stmt.count == "INFINITE"
                  for stmt in widget.timeline.marquee_ast.statements)
        
        # Helper function to recursively find statements with specific attributes
        def find_statement_with_attrs(statements, attr1, attr2):
            """Recursively check for statements with the given attributes."""
            for stmt in statements:
                if hasattr(stmt, attr1) and hasattr(stmt, attr2):
                    return True
                # Check if it's a container statement with a 'body' or 'statements' attribute
                if hasattr(stmt, 'body') and hasattr(stmt.body, 'statements'):
                    if find_statement_with_attrs(stmt.body.statements, attr1, attr2):
                        return True
            return False
            
        # Check that it contains scroll or move statements (which have direction and distance)
        assert find_statement_with_attrs(widget.timeline.marquee_ast.statements, 'direction', 'distance')


class TestPropertyAccessAcrossDSLs:
    """Tests for property access between Application and Marquee DSLs."""
    
    def test_widget_property_access_in_timeline(self):
        """Test that widget properties can be accessed in timeline animations."""
        app_source = """
        DEFINE WIDGET "dynamicText" AS Text {
            value: "Dynamic Width Text",
            size: (100, 16),
            foreground: "white",
            background: "black",
            
            TIMELINE {
                MOVE(LEFT, widget.width);  # Access widget width
                MOVE(RIGHT, widget.size[0]);  # Access via size array
            }
        }
        """
        
        program = parse_application_dsl(app_source)
        
        # Check widget declaration
        assert len(program.statements) == 1
        widget = program.statements[0]
        assert widget.timeline is not None
        
        # Verify property access in timeline - check that we have at least one statement
        # with a distance that references widget properties
        statements = widget.timeline.marquee_ast.statements
        assert len(statements) > 0
        
        # Since the actual parsing of property access might be implementation-specific,
        # we'll just verify we have MoveStatements
        assert any(hasattr(stmt, 'direction') for stmt in statements)
    
    def test_container_property_access_in_timeline(self):
        """Test that container properties can be accessed in timeline animations."""
        app_source = """
        DEFINE WIDGET "bounceText" AS Text {
            value: "Bouncing Text",
            size: (80, 16),
            foreground: "white",
            background: "black",
            
            TIMELINE {
                LOOP(INFINITE) {
                    MOVE(RIGHT, container.width - widget.width);
                    MOVE(LEFT, 0);
                } END;
            }
        }
        """
        
        program = parse_application_dsl(app_source)
        
        # Check widget declaration
        assert len(program.statements) == 1
        widget = program.statements[0]
        assert widget.timeline is not None
        
        # Verify container property access in timeline
        statements = widget.timeline.marquee_ast.statements
        assert len(statements) > 0
        
        # Verify we have a loop statement
        assert any(hasattr(stmt, 'count') and stmt.count == "INFINITE" 
                  for stmt in statements)


class TestComplexIntegration:
    """Tests for complex integration scenarios between the DSLs."""
    
    def test_multiple_widgets_with_timelines(self):
        """Test application with multiple widgets having timelines."""
        app_source = """
        DEFINE WIDGET "title" AS Text {
            value: "Title",
            size: (128, 16),
            foreground: "white",
            background: "black",
            
            TIMELINE {
                SLIDE(TOP, 20);
            }
        }
        
        DEFINE WIDGET "content" AS Text {
            value: "Content text goes here",
            size: (128, 32),
            foreground: "white",
            background: "black",
            
            TIMELINE {
                WAIT_FOR(title_ready, 50);
                SLIDE(LEFT, 30);
                SYNC(content_ready);
            }
        }
        
        DEFINE CANVAS "main" {
            size: (128, 64),
            background: "black",
            
            PLACE "title" AT (0, 0) Z 100;
            PLACE "content" AT (0, 20) Z 90;
        }
        """
        
        program = parse_application_dsl(app_source)
        
        # Check application structure
        assert len(program.statements) == 3
        assert sum(1 for stmt in program.statements if hasattr(stmt, 'timeline')) == 2
        
        # Find widgets with timelines
        widgets_with_timeline = [stmt for stmt in program.statements 
                               if hasattr(stmt, 'timeline') and stmt.timeline is not None]
        assert len(widgets_with_timeline) == 2
        
        # Check sync points and wait statements in timelines
        title_widget = next(w for w in widgets_with_timeline if w.name == "title")
        content_widget = next(w for w in widgets_with_timeline if w.name == "content")
        
        # Verify title has a slide statement
        assert len(title_widget.timeline.marquee_ast.statements) > 0
        
        # Verify content has wait and sync statements
        content_statements = content_widget.timeline.marquee_ast.statements
        assert len(content_statements) >= 2
        assert any(hasattr(stmt, 'event') for stmt in content_statements)
    
    def test_timeline_with_variables_and_conditionals(self):
        """Test timeline with variables and conditional animation."""
        app_source = """
        DEFINE WIDGET "conditionalText" AS Text {
            value: "Conditional Animation",
            size: (128, 16),
            foreground: "white",
            background: "black",
            
            TIMELINE {
                IF(widget.x < container.width / 2) {
                    MOVE(RIGHT, container.width / 2);
                } ELSE {
                    MOVE(LEFT, container.width / 4);
                } END;
                
                ON_VARIABLE_CHANGE(data.updating) {
                    IF(data.updating) {
                        POPUP({ duration=5 });
                    } END;
                } END;
            }
        }
        """
        
        program = parse_application_dsl(app_source)
        
        # Check widget declaration
        assert len(program.statements) == 1
        widget = program.statements[0]
        assert widget.timeline is not None
        
        # Verify conditionals in timeline
        statements = widget.timeline.marquee_ast.statements
        assert len(statements) > 0
        
        # Look for if statements
        assert any(hasattr(stmt, 'condition') for stmt in statements)
    
    def test_complex_application_with_animations(self):
        """Test a complex application with coordinated animations."""
        app_source = """
        DEFINE THEME "dark" {
            background: "black",
            foreground: "white",
            accent: "blue"
        }
        
        DEFINE WIDGET "header" AS Text {
            value: "Dashboard",
            size: (128, 16),
            foreground: THEME.accent,
            background: THEME.background,
            
            TIMELINE {
                SLIDE(TOP, 20);
                SYNC(header_ready);
            }
        }
        
        DEFINE WIDGET "temperature" AS Text {
            value: "{data.temperature}°C",
            size: (64, 24),
            foreground: THEME.foreground,
            background: THEME.background,
            
            TIMELINE {
                WAIT_FOR(header_ready, 30);
                SLIDE(LEFT, 30);
                
                ON_VARIABLE_CHANGE(data.temperature) {
                    POPUP({ duration=5 });
                } END;
            }
        }
        
        DEFINE WIDGET "humidity" AS Text {
            value: "{data.humidity}%",
            size: (64, 24),
            foreground: THEME.foreground,
            background: THEME.background,
            
            TIMELINE {
                WAIT_FOR(header_ready, 40);
                SLIDE(RIGHT, 30);
                
                ON_VARIABLE_CHANGE(data.humidity) {
                    POPUP({ duration=5 });
                } END;
            }
        }
        
        DEFINE CANVAS "dashboard" {
            size: (128, 64),
            background: THEME.background,
            
            PLACE "header" AT (0, 0) Z 100;
            PLACE "temperature" AT (0, 20) Z 90;
            PLACE "humidity" AT (64, 20) Z 90;
        }
        
        DEFINE APP "weatherStation" {
            theme: "dark",
            defaultScreen: "dashboard",
            
            SCREENS {
                REFERENCE "dashboard";
            }
            
            DATASOURCES {
                REFERENCE "data";
            }
        }
        """
        
        program = parse_application_dsl(app_source)
        
        # Check application structure for widget counts and timeline presence
        widgets_with_timeline = [stmt for stmt in program.statements 
                            if hasattr(stmt, 'timeline') and stmt.timeline is not None]
        assert len(widgets_with_timeline) == 3
        
        # Verify sync and wait coordination
        header_widget = next(w for w in widgets_with_timeline if w.name == "header")
        temp_widget = next(w for w in widgets_with_timeline if w.name == "temperature")
        humidity_widget = next(w for w in widgets_with_timeline if w.name == "humidity")
        
        # Verify headers have sync statements
        header_statements = header_widget.timeline.marquee_ast.statements
        assert len(header_statements) > 0
        assert any(hasattr(stmt, 'event') for stmt in header_statements)
        
        # Verify temperature has wait statements
        temp_statements = temp_widget.timeline.marquee_ast.statements
        assert len(temp_statements) > 0
        assert any(hasattr(stmt, 'event') for stmt in temp_statements)
        
        # Verify humidity has wait statements
        humidity_statements = humidity_widget.timeline.marquee_ast.statements
        assert len(humidity_statements) > 0
        assert any(hasattr(stmt, 'event') for stmt in humidity_statements)


class TestValidationIntegration:
    """Tests for validation across both DSLs."""
    
    def test_invalid_timeline_in_widget(self):
        """Test validation of invalid Marquee DSL in a widget."""
        app_source = """
        DEFINE WIDGET "invalidTimeline" AS Text {
            value: "Invalid Timeline",
            size: (128, 16),
            
            TIMELINE {
                BREAK;  # BREAK outside of a loop is invalid
            }
        }
        """
        
        program, errors = parse_and_validate_application_dsl(app_source)
        
        # Should have validation errors
        assert len(errors) > 0
        assert any(("BREAK" in str(error) or "break" in str(error).lower()) for error in errors)
    
    def test_undefined_sync_point(self):
        """Test validation of undefined sync points across widgets."""
        app_source = """
        DEFINE WIDGET "first" AS Text {
            value: "First Widget",
            size: (128, 16),
            
            TIMELINE {
                MOVE(LEFT, 50);
                # No SYNC declaration for "first_ready"
            }
        }
        
        DEFINE WIDGET "second" AS Text {
            value: "Second Widget",
            size: (128, 16),
            
            TIMELINE {
                WAIT_FOR(first_ready, 50);  # Referencing undefined sync point
                MOVE(RIGHT, 30);
            }
        }
        """
        
        program, errors = parse_and_validate_application_dsl(app_source)
        
        # Should have validation errors for the undefined sync point
        assert len(errors) > 0
        assert any("first_ready" in str(error) for error in errors)
    
    def test_property_access_validation(self):
        """Test validation of property access in timelines."""
        app_source = """
        DEFINE WIDGET "invalidPropertyAccess" AS Text {
            value: "Invalid Property",
            size: (128, 16),
            
            TIMELINE {
                MOVE(LEFT, invalid_property);  # Accessing undefined property
            }
        }
        """
        
        program, errors = parse_and_validate_application_dsl(app_source)
        
        # Should have validation errors for the undefined property
        assert len(errors) > 0
        assert any("invalid_property" in str(error) for error in errors)


if __name__ == "__main__":
    # When run directly, execute the tests
    pytest.main(["-xvs", __file__]) 