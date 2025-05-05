"""
Simple test file for the tinyDisplay Marquee Animation DSL parser and validator.
"""

import sys
import os
from pathlib import Path

# Add parent directory to sys.path to allow importing tinyDisplay modules
parent_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(parent_dir))

from tinyDisplay.dsl.marquee import parse_and_validate_marquee_dsl


def test_basic_marquee():
    """Test a basic marquee animation."""
    source = """
    MOVE(LEFT, 100);
    PAUSE(10);
    """
    
    program, errors = parse_and_validate_marquee_dsl(source)
    
    print(f"Parsed program with {len(program.statements)} statements")
    
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  {error}")
    else:
        print("Validation successful!")
    
    # Print the AST structure
    print("\nAST Structure:")
    print_ast(program)


def test_comprehensive_example():
    """Test a more comprehensive example."""
    source = """
    SCROLL(LEFT, widget.width) { step=1, interval=1, gap=10 };
    """
    
    program, errors = parse_and_validate_marquee_dsl(source)
    
    print(f"Parsed program with {len(program.statements)} statements")
    
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  {error}")
    else:
        print("Validation successful!")


def print_ast(node, indent=0):
    """Print a simple representation of the AST."""
    indent_str = "  " * indent
    
    if node is None:
        print(f"{indent_str}None")
        return
    
    node_type = type(node).__name__
    
    if hasattr(node, "statements") and node.statements:
        print(f"{indent_str}{node_type}:")
        for stmt in node.statements:
            print_ast(stmt, indent + 1)
    elif hasattr(node, "body") and node.body:
        print(f"{indent_str}{node_type}:")
        print_ast(node.body, indent + 1)
    elif hasattr(node, "then_branch") and node.then_branch:
        print(f"{indent_str}{node_type}:")
        print(f"{indent_str}  Then:")
        print_ast(node.then_branch, indent + 2)
        
        if hasattr(node, "else_branch") and node.else_branch:
            print(f"{indent_str}  Else:")
            print_ast(node.else_branch, indent + 2)
    else:
        if hasattr(node, "value"):
            print(f"{indent_str}{node_type}: {node.value}")
        elif hasattr(node, "name"):
            print(f"{indent_str}{node_type}: {node.name}")
        elif hasattr(node, "direction") and node.direction:
            print(f"{indent_str}{node_type}: {node.direction.name}")
        else:
            print(f"{indent_str}{node_type}")


if __name__ == "__main__":
    print("\n=== Basic Marquee Test ===\n")
    test_basic_marquee()
    
    print("\n=== Comprehensive Example Test ===\n")
    test_comprehensive_example() 