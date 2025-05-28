"""
Tests for expression parsing and validation in the tinyDisplay Marquee Animation DSL.

This test suite focuses on testing various expressions and their parsing/validation,
which is an area with lower coverage in the current test suite.
"""

import sys
import os
from pathlib import Path
import pytest

# Add parent directory to sys.path to allow importing tinyDisplay modules
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from tinyDisplay.dsl.marquee import parse_marquee_dsl, parse_and_validate_marquee_dsl
from tinyDisplay.dsl.marquee.ast import (
    Expression, Literal, Variable, BinaryExpr, PropertyAccess,
    MoveStatement, PauseStatement, Direction
)


def test_numeric_literals():
    """Test parsing of different numeric literal types."""
    source = """
    MOVE(LEFT, 100);      # Positive integer
    MOVE(RIGHT, -50);     # Negative integer
    PAUSE(5);             # Small positive integer
    """
    
    program = parse_marquee_dsl(source)
    
    # Check positive integer
    assert isinstance(program.statements[0], MoveStatement)
    assert program.statements[0].distance.value == 100
    
    # Check negative integer
    assert isinstance(program.statements[1], MoveStatement)
    assert program.statements[1].distance.value == -50
    
    # Check small positive integer
    assert isinstance(program.statements[2], PauseStatement)
    assert program.statements[2].duration.value == 5


def test_variable_expressions():
    """Test parsing of variable references."""
    source = """
    MOVE(LEFT, widget.width);
    PAUSE(current_tick);
    """
    
    program = parse_marquee_dsl(source)
    
    # Check widget.width property access
    assert isinstance(program.statements[0], MoveStatement)
    assert isinstance(program.statements[0].distance, PropertyAccess)
    assert isinstance(program.statements[0].distance.object, Variable)
    assert program.statements[0].distance.object.name == "widget"
    assert program.statements[0].distance.property == "width"
    
    # Check current_tick variable
    assert isinstance(program.statements[1], PauseStatement)
    assert isinstance(program.statements[1].duration, Variable)
    assert program.statements[1].duration.name == "current_tick"


def test_arithmetic_expressions():
    """Test parsing of arithmetic expressions."""
    source = """
    MOVE(LEFT, widget.width * 2);          # Multiplication
    MOVE(RIGHT, container.width / 4);      # Division
    MOVE(UP, widget.height + 10);          # Addition
    MOVE(DOWN, container.height - 20);     # Subtraction
    """
    
    program = parse_marquee_dsl(source)
    
    # Check multiplication
    assert isinstance(program.statements[0], MoveStatement)
    assert isinstance(program.statements[0].distance, BinaryExpr)
    assert program.statements[0].distance.operator == "*"
    
    # Check division
    assert isinstance(program.statements[1], MoveStatement)
    assert isinstance(program.statements[1].distance, BinaryExpr)
    assert program.statements[1].distance.operator == "/"
    
    # Check addition
    assert isinstance(program.statements[2], MoveStatement)
    assert isinstance(program.statements[2].distance, BinaryExpr)
    assert program.statements[2].distance.operator == "+"
    
    # Check subtraction
    assert isinstance(program.statements[3], MoveStatement)
    assert isinstance(program.statements[3].distance, BinaryExpr)
    assert program.statements[3].distance.operator == "-"


def test_complex_nested_expressions():
    """Test parsing of complex nested expressions."""
    source = """
    MOVE(LEFT, (widget.width * 2) + (container.width / 4));
    PAUSE((current_tick % 10) * (5 + 3));
    """
    
    program = parse_marquee_dsl(source)
    
    # Check first complex expression
    assert isinstance(program.statements[0], MoveStatement)
    assert isinstance(program.statements[0].distance, BinaryExpr)
    assert program.statements[0].distance.operator == "+"
    assert isinstance(program.statements[0].distance.left, BinaryExpr)  # (widget.width * 2)
    assert isinstance(program.statements[0].distance.right, BinaryExpr)  # (container.width / 4)
    
    # Check second complex expression
    assert isinstance(program.statements[1], PauseStatement)
    assert isinstance(program.statements[1].duration, BinaryExpr)
    assert program.statements[1].duration.operator == "*"


def test_comparison_expressions():
    """Test parsing of comparison expressions in conditions."""
    source = """
    IF(widget.x > 100) {
        MOVE(LEFT, 10);
    } END;
    
    IF(widget.x < 50) {
        MOVE(RIGHT, 20);
    } END;
    
    IF(widget.x >= container.width) {
        MOVE(UP, 30);
    } END;
    
    IF(widget.x <= container.width / 2) {
        MOVE(DOWN, 40);
    } END;
    
    IF(widget.x == 200) {
        PAUSE(5);
    } END;
    
    IF(widget.x != container.x) {
        PAUSE(10);
    } END;
    """
    
    program = parse_marquee_dsl(source)
    
    # Check all comparison operators
    operators = [">", "<", ">=", "<=", "==", "!="]
    
    for i, op in enumerate(operators):
        assert program.statements[i].condition.operator == op


def test_modulo_operator():
    """Test parsing of modulo operator in expressions."""
    source = """
    IF(current_tick % 10 == 0) {
        MOVE(LEFT, 5);
    } END;
    """
    
    program = parse_marquee_dsl(source)
    
    # Check modulo in the left side of condition
    assert program.statements[0].condition.left.operator == "%"
    assert isinstance(program.statements[0].condition.left.left, Variable)
    assert program.statements[0].condition.left.left.name == "current_tick"
    assert program.statements[0].condition.left.right.value == 10


def test_parenthesized_expressions():
    """Test parsing of expressions with parentheses."""
    source = """
    MOVE(LEFT, (widget.width + 10) * 2);
    MOVE(RIGHT, container.width - (20 + 5));
    """
    
    program = parse_marquee_dsl(source)
    
    # Check first expression with parentheses
    assert isinstance(program.statements[0], MoveStatement)
    assert isinstance(program.statements[0].distance, BinaryExpr)
    assert program.statements[0].distance.operator == "*"
    assert isinstance(program.statements[0].distance.left, BinaryExpr)  # (widget.width + 10)
    
    # Check second expression with parentheses
    assert isinstance(program.statements[1], MoveStatement)
    assert isinstance(program.statements[1].distance, BinaryExpr)
    assert program.statements[1].distance.operator == "-"
    assert isinstance(program.statements[1].distance.right, BinaryExpr)  # (20 + 5)


def test_expression_in_options():
    """Test parsing of expressions in statement options."""
    source = """
    MOVE(LEFT, 100) { 
        step=widget.width / 10,
        interval=current_tick % 5 + 1
    };
    """
    
    program = parse_marquee_dsl(source)
    
    # Check expression in step option
    assert isinstance(program.statements[0], MoveStatement)
    step_expr = program.statements[0].options["step"]
    assert isinstance(step_expr, BinaryExpr)
    assert step_expr.operator == "/"
    
    # Check expression in interval option
    interval_expr = program.statements[0].options["interval"]
    assert isinstance(interval_expr, BinaryExpr)
    assert interval_expr.operator == "+"
    assert isinstance(interval_expr.left, BinaryExpr)  # current_tick % 5
    assert interval_expr.left.operator == "%"


def test_string_literals():
    """Test parsing of string literals in options."""
    source = """
    RESET_POSITION({ mode="seamless" });
    RESET_POSITION({ mode="instant" });
    RESET_POSITION({ mode="fade" });
    """
    
    program = parse_marquee_dsl(source)
    
    # Check string literals in mode option
    for i, mode in enumerate(["seamless", "instant", "fade"]):
        assert isinstance(program.statements[i].options["mode"], Literal)
        assert program.statements[i].options["mode"].value == mode


def test_operator_precedence():
    """Test operator precedence in expressions."""
    source = """
    MOVE(LEFT, 2 + 3 * 4);  # Should be 2 + (3 * 4) = 14, not (2 + 3) * 4 = 20
    MOVE(RIGHT, 10 - 6 / 2);  # Should be 10 - (6 / 2) = 7, not (10 - 6) / 2 = 2
    """
    
    program = parse_marquee_dsl(source)
    
    # Check first expression (testing * has higher precedence than +)
    first_expr = program.statements[0].distance
    assert isinstance(first_expr, BinaryExpr)
    assert first_expr.operator == "+"
    assert first_expr.left.value == 2
    assert isinstance(first_expr.right, BinaryExpr)  # 3 * 4
    
    # Check second expression (testing / has higher precedence than -)
    second_expr = program.statements[1].distance
    assert isinstance(second_expr, BinaryExpr)
    assert second_expr.operator == "-"
    assert second_expr.left.value == 10
    assert isinstance(second_expr.right, BinaryExpr)  # 6 / 2


if __name__ == "__main__":
    # When run directly, execute tests and print results
    test_numeric_literals()
    print("✓ test_numeric_literals passed")
    
    test_variable_expressions()
    print("✓ test_variable_expressions passed")
    
    test_arithmetic_expressions()
    print("✓ test_arithmetic_expressions passed")
    
    test_complex_nested_expressions()
    print("✓ test_complex_nested_expressions passed")
    
    test_comparison_expressions()
    print("✓ test_comparison_expressions passed")
    
    test_modulo_operator()
    print("✓ test_modulo_operator passed")
    
    test_parenthesized_expressions()
    print("✓ test_parenthesized_expressions passed")
    
    test_expression_in_options()
    print("✓ test_expression_in_options passed")
    
    test_string_literals()
    print("✓ test_string_literals passed")
    
    test_operator_precedence()
    print("✓ test_operator_precedence passed")
    
    print("All tests passed!") 