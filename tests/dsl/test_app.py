"""
Simple test script for the Application Widget DSL parser.
"""
from tinyDisplay.dsl.application.lexer import Lexer
from tinyDisplay.dsl.application.parser import Parser
from tinyDisplay.dsl.application.validator import Validator

def test_basic_widget():
    """Test the parsing of a basic widget declaration."""
    source = """
    DEFINE WIDGET "title" AS Text {
        value: "Hello World",
        size: (128, 16),
        foreground: "white",
        background: "black",
    }
    """
    
    print("Testing basic widget declaration...")
    
    # Tokenize
    lexer = Lexer(source)
    tokens = lexer.scan_tokens()
    
    # Parse
    parser = Parser(tokens)
    program = parser.parse()
    
    # Print the result
    print(f"Number of statements: {len(program.statements)}")
    for i, stmt in enumerate(program.statements):
        print(f"Statement {i+1}: {type(stmt).__name__}")
        if hasattr(stmt, 'name'):
            print(f"  Name: {stmt.name}")
        if hasattr(stmt, 'properties'):
            print(f"  Properties: {len(stmt.properties)}")
            for prop, value in stmt.properties.items():
                print(f"    {prop}: {value.__class__.__name__}")
        print()

if __name__ == "__main__":
    test_basic_widget() 