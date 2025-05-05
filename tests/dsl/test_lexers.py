"""
Tests for the tinyDisplay DSL lexers (both Application and Marquee).
"""

import sys
import os
from pathlib import Path
import pytest

# Add parent directory to sys.path to allow importing tinyDisplay modules
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from tinyDisplay.dsl.application.lexer import Lexer as AppLexer
from tinyDisplay.dsl.application.tokens import TokenType as AppTokenType, Token as AppToken
from tinyDisplay.dsl.marquee.lexer import Lexer as MarqueeLexer
from tinyDisplay.dsl.marquee.tokens import TokenType as MarqueeTokenType, Token as MarqueeToken


class TestApplicationLexer:
    """Tests for the Application DSL lexer."""
    
    def test_basic_tokens(self):
        """Test lexing of basic tokens."""
        source = """DEFINE WIDGET "title" AS Text {}"""
        lexer = AppLexer(source)
        tokens = lexer.scan_tokens()
        
        # Check token types (excluding EOF)
        expected_types = [
            AppTokenType.DEFINE, AppTokenType.WIDGET, AppTokenType.STRING,
            AppTokenType.AS, AppTokenType.TEXT, AppTokenType.LEFT_BRACE,
            AppTokenType.RIGHT_BRACE, AppTokenType.EOF
        ]
        assert [t.type for t in tokens] == expected_types
        
        # Check string literal
        assert tokens[2].literal == "title"
    
    def test_numeric_literals(self):
        """Test lexing of numeric literals."""
        source = """
        size: (128, 64),
        opacity: 0.5,
        z_index: -10,
        """
        lexer = AppLexer(source)
        tokens = lexer.scan_tokens()
        
        # Find all number tokens
        number_tokens = [t for t in tokens if t.type in [AppTokenType.INTEGER, AppTokenType.FLOAT]]
        assert len(number_tokens) == 4
        
        # Check values
        assert number_tokens[0].literal == 128
        assert number_tokens[1].literal == 64
        assert number_tokens[2].literal == 0.5
        assert number_tokens[3].literal == -10
    
    def test_operators_and_punctuation(self):
        """Test lexing of operators and punctuation marks."""
        source = """
        x + y * (z - 5) / 2;
        a == b != c >= d <= e > f < g;
        """
        lexer = AppLexer(source)
        tokens = lexer.scan_tokens()
        
        # Filter out identifiers, numbers, and EOF
        operators = [t for t in tokens if t.type not in [
            AppTokenType.IDENTIFIER, AppTokenType.INTEGER,
            AppTokenType.FLOAT, AppTokenType.EOF
        ]]
        
        expected_types = [
            AppTokenType.PLUS, AppTokenType.STAR, AppTokenType.LEFT_PAREN,
            AppTokenType.MINUS, AppTokenType.RIGHT_PAREN, AppTokenType.SLASH,
            AppTokenType.SEMICOLON, AppTokenType.EQUALS, AppTokenType.NOT_EQUALS,
            AppTokenType.GREATER_EQUALS, AppTokenType.LESS_EQUALS,
            AppTokenType.GREATER, AppTokenType.LESS, AppTokenType.SEMICOLON
        ]
        assert [t.type for t in operators] == expected_types
    
    def test_keywords(self):
        """Test lexing of keywords."""
        source = """
        DEFINE CANVAS "main" {
            PLACE "widget" AT (10, 20) Z 100;
        }
        
        DEFINE THEME "dark" {
            background: "black",
        }
        
        BIND "{text}" TO "data.value";
        
        IMPORT widget FROM "file.dsl";
        """
        lexer = AppLexer(source)
        tokens = lexer.scan_tokens()
        
        # Extract just the keywords
        keywords = [t for t in tokens if t.type.name.startswith("DEFINE") or 
                                         t.type.name in ["CANVAS", "PLACE", "AT", "Z", 
                                                         "THEME", "BIND", "TO", "IMPORT", "FROM"]]
        
        assert len(keywords) == 10  # DEFINE appears twice
        assert keywords[0].type == AppTokenType.DEFINE
        assert keywords[1].type == AppTokenType.CANVAS
        assert keywords[3].type == AppTokenType.PLACE
        assert keywords[4].type == AppTokenType.AT
        assert keywords[5].type == AppTokenType.Z
    
    def test_comments(self):
        """Test handling of comments."""
        source = """
        DEFINE WIDGET "title" AS Text {
            // This is a line comment
            value: "Hello", /* This is an inline comment */
            /* This is a
               multi-line
               comment */
            size: (128, 16),
        }
        """
        lexer = AppLexer(source)
        tokens = lexer.scan_tokens()
        
        # Comments should be ignored, so we shouldn't see them in tokens
        assert all(t.lexeme.strip() not in ["//", "/*", "*/"] for t in tokens)
        
        # Check we still get all the real tokens
        identifier_tokens = [t for t in tokens if t.type == AppTokenType.IDENTIFIER]
        assert len(identifier_tokens) == 2
        assert [t.lexeme for t in identifier_tokens] == ["value", "size"]
    
    def test_string_literals(self):
        """Test lexing of string literals with escaped characters."""
        source = r"""
        DEFINE WIDGET "complex_string" AS Text {
            value: "Hello \"World\"",
            path: "C:\\Program Files\\App",
            multiline: "Line 1\nLine 2",
        }
        """
        lexer = AppLexer(source)
        tokens = lexer.scan_tokens()
        
        # Extract string literals
        string_tokens = [t for t in tokens if t.type == AppTokenType.STRING]
        assert len(string_tokens) == 4  # widget name + 3 property values
        
        # Check escaped quotes
        assert string_tokens[1].literal == 'Hello "World"'
        
        # Check escaped backslashes
        assert string_tokens[2].literal == r'C:\Program Files\App'
        
        # Check newline escapes
        assert '\n' in string_tokens[3].literal
    
    def test_property_access(self):
        """Test lexing of property access with dot notation."""
        source = """
        foreground: THEME.accent,
        background: widget.properties.color,
        """
        lexer = AppLexer(source)
        tokens = lexer.scan_tokens()
        
        # Find DOT tokens
        dots = [i for i, t in enumerate(tokens) if t.type == AppTokenType.DOT]
        assert len(dots) == 3
        
        # Check the structure around the dots
        assert tokens[dots[0]-1].type == AppTokenType.IDENTIFIER  # THEME
        assert tokens[dots[0]+1].type == AppTokenType.IDENTIFIER  # accent
        
        assert tokens[dots[1]-1].type == AppTokenType.IDENTIFIER  # widget
        assert tokens[dots[1]+1].type == AppTokenType.IDENTIFIER  # properties
    
    def test_error_handling(self):
        """Test lexer error handling for invalid characters."""
        source = """
        DEFINE WIDGET "invalid" AS Text {
            value: "Contains invalid char @",  # @ is not a valid token
        }
        """
        lexer = AppLexer(source)
        with pytest.raises(Exception) as excinfo:
            tokens = lexer.scan_tokens()
        
        # A proper lexer should report an error for the '@' character
        assert "@" in str(excinfo.value)


class TestMarqueeLexer:
    """Tests for the Marquee DSL lexer."""
    
    def test_basic_tokens(self):
        """Test lexing of basic Marquee tokens."""
        source = """MOVE(LEFT, 100) { step=1 };"""
        lexer = MarqueeLexer(source)
        tokens = lexer.scan_tokens()
        
        # Check token types
        expected_types = [
            MarqueeTokenType.MOVE, MarqueeTokenType.LEFT_PAREN, 
            MarqueeTokenType.LEFT, MarqueeTokenType.COMMA, 
            MarqueeTokenType.INTEGER, MarqueeTokenType.RIGHT_PAREN,
            MarqueeTokenType.LEFT_BRACE, MarqueeTokenType.IDENTIFIER,
            MarqueeTokenType.EQUALS, MarqueeTokenType.INTEGER,
            MarqueeTokenType.RIGHT_BRACE, MarqueeTokenType.SEMICOLON,
            MarqueeTokenType.EOF
        ]
        assert [t.type for t in tokens] == expected_types
    
    def test_direction_constants(self):
        """Test lexing of direction constants."""
        source = """
        MOVE(LEFT, 10);
        MOVE(RIGHT, 20);
        MOVE(UP, 30);
        MOVE(DOWN, 40);
        """
        lexer = MarqueeLexer(source)
        tokens = lexer.scan_tokens()
        
        # Extract direction tokens
        directions = [t for t in tokens if t.type in [
            MarqueeTokenType.LEFT, MarqueeTokenType.RIGHT,
            MarqueeTokenType.UP, MarqueeTokenType.DOWN
        ]]
        
        assert len(directions) == 4
        assert [d.type for d in directions] == [
            MarqueeTokenType.LEFT, MarqueeTokenType.RIGHT,
            MarqueeTokenType.UP, MarqueeTokenType.DOWN
        ]
    
    def test_loop_and_control_keywords(self):
        """Test lexing of loop and control flow keywords."""
        source = """
        LOOP(INFINITE) {
            IF(widget.x > 100) {
                BREAK;
            } ELSE {
                CONTINUE;
            } END;
        } END;
        """
        lexer = MarqueeLexer(source)
        tokens = lexer.scan_tokens()
        
        # Extract control flow keywords
        keywords = [t for t in tokens if t.type in [
            MarqueeTokenType.LOOP, MarqueeTokenType.INFINITE,
            MarqueeTokenType.IF, MarqueeTokenType.ELSE,
            MarqueeTokenType.BREAK, MarqueeTokenType.CONTINUE,
            MarqueeTokenType.END
        ]]
        
        assert len(keywords) == 7
        assert [k.type for k in keywords] == [
            MarqueeTokenType.LOOP, MarqueeTokenType.INFINITE,
            MarqueeTokenType.IF, MarqueeTokenType.ELSE,
            MarqueeTokenType.CONTINUE, MarqueeTokenType.END,
            MarqueeTokenType.END
        ]
    
    def test_easing_functions(self):
        """Test lexing of easing function names."""
        source = """
        MOVE(LEFT, 100) { 
            easing=linear 
        };
        MOVE(RIGHT, 100) { 
            easing=ease_in 
        };
        MOVE(UP, 100) { 
            easing=cubic_bezier(0.42, 0, 0.58, 1) 
        };
        """
        lexer = MarqueeLexer(source)
        tokens = lexer.scan_tokens()
        
        # Find easing function names
        easing_tokens = []
        for i, t in enumerate(tokens):
            if t.type == MarqueeTokenType.IDENTIFIER and t.lexeme == "easing":
                # The next token after EQUALS should be the easing name
                easing_tokens.append(tokens[i+2])
        
        assert len(easing_tokens) == 3
        assert easing_tokens[0].lexeme == "linear"
        assert easing_tokens[1].lexeme == "ease_in"
        assert easing_tokens[2].lexeme == "cubic_bezier"
    
    def test_timeline_optimization_keywords(self):
        """Test lexing of timeline optimization keywords."""
        source = """
        PERIOD(50);
        START_AT(10);
        SEGMENT(intro, 0, 20) {
            MOVE(RIGHT, 50);
        } END;
        POSITION_AT(t) => {
            x = 100 - t;
        } END;
        """
        lexer = MarqueeLexer(source)
        tokens = lexer.scan_tokens()
        
        # Extract timeline optimization keywords
        keywords = [t for t in tokens if t.type in [
            MarqueeTokenType.PERIOD, MarqueeTokenType.START_AT,
            MarqueeTokenType.SEGMENT, MarqueeTokenType.POSITION_AT
        ]]
        
        assert len(keywords) == 4
        assert [k.type for k in keywords] == [
            MarqueeTokenType.PERIOD, MarqueeTokenType.START_AT,
            MarqueeTokenType.SEGMENT, MarqueeTokenType.POSITION_AT
        ]
    
    def test_widget_state_access(self):
        """Test lexing of widget state access expressions."""
        source = """
        IF(widget.x > container.width) {
            MOVE(LEFT, widget.width);
        } END;
        """
        lexer = MarqueeLexer(source)
        tokens = lexer.scan_tokens()
        
        # Extract identifiers
        identifiers = [t.lexeme for t in tokens if t.type == MarqueeTokenType.IDENTIFIER]
        assert "widget" in identifiers
        assert "container" in identifiers
        
        # Find DOT tokens and check the structure
        dots = [i for i, t in enumerate(tokens) if t.type == MarqueeTokenType.DOT]
        assert len(dots) == 3
        
        # Check property access structure
        assert tokens[dots[0]-1].lexeme == "widget"
        assert tokens[dots[0]+1].lexeme == "x"
        
        assert tokens[dots[1]-1].lexeme == "container"
        assert tokens[dots[1]+1].lexeme == "width"
        
        assert tokens[dots[2]-1].lexeme == "widget"
        assert tokens[dots[2]+1].lexeme == "width"
    
    def test_high_level_commands(self):
        """Test lexing of high-level commands."""
        source = """
        SCROLL(LEFT, widget.width) { step=2, gap=5 };
        SLIDE(IN_OUT, RIGHT, 100) { pause=30 };
        POPUP({ top_delay=20 });
        """
        lexer = MarqueeLexer(source)
        tokens = lexer.scan_tokens()
        
        # Extract high-level command tokens
        commands = [t for t in tokens if t.type in [
            MarqueeTokenType.SCROLL, MarqueeTokenType.SLIDE, MarqueeTokenType.POPUP
        ]]
        
        assert len(commands) == 3
        assert [c.type for c in commands] == [
            MarqueeTokenType.SCROLL, MarqueeTokenType.SLIDE, MarqueeTokenType.POPUP
        ]
        
        # Check for slide action constant
        slide_action = [t for t in tokens if t.lexeme == "IN_OUT"]
        assert len(slide_action) == 1 