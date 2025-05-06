"""
Tests for array access in the tinyDisplay Application DSL.
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
    WidgetDeclaration, PropertyAccess, ArrayAccess, Literal, Variable
)


def test_array_access():
    """Test array access in a widget definition."""
    source = """
    DEFINE WIDGET "test" AS Text {
        value: data.items[0]
    }
    """
    
    program = parse_application_dsl(source)
    assert len(program.statements) == 1
    assert isinstance(program.statements[0], WidgetDeclaration)
    
    widget = program.statements[0]
    value_prop = widget.properties["value"]
    
    # Should be an ArrayAccess with a PropertyAccess inside
    assert isinstance(value_prop, ArrayAccess)
    assert isinstance(value_prop.array, PropertyAccess)
    assert value_prop.array.object == "data"
    assert value_prop.array.property == "items"
    assert isinstance(value_prop.index, Literal)
    assert value_prop.index.value == 0


def test_chained_property_after_array_access():
    """Test property access after array access."""
    source = """
    DEFINE WIDGET "test" AS Text {
        value: data.items[0].name
    }
    """
    
    program = parse_application_dsl(source)
    assert len(program.statements) == 1
    assert isinstance(program.statements[0], WidgetDeclaration)
    
    widget = program.statements[0]
    value_prop = widget.properties["value"]
    
    # Should be a PropertyAccess with an ArrayAccess inside
    assert isinstance(value_prop, PropertyAccess)
    assert value_prop.property == "name"
    assert isinstance(value_prop.object, ArrayAccess)
    
    array_access = value_prop.object
    assert isinstance(array_access.array, PropertyAccess)
    assert array_access.array.object == "data"
    assert array_access.array.property == "items"
    assert isinstance(array_access.index, Literal)
    assert array_access.index.value == 0 