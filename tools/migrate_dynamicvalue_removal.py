#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migration script to handle the removal of DynamicValue.

This script scans Python files and modifies any remaining direct usage of
DynamicValue to use the dynamic() function instead.
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Patterns to find and replace
PATTERNS = [
    # Import pattern
    (
        r"from\s+tinyDisplay\.utility\.dynamic\s+import\s+(.*?)\bDynamicValue\b(.*)",
        r"from tinyDisplay.utility.dynamic import \1\2"
    ),
    # Import and as pattern
    (
        r"from\s+tinyDisplay\.utility\s+import\s+(.*?)\bDynamicValue\b(.*)",
        r"from tinyDisplay.utility import \1\2"
    ),
    # Direct usage pattern - replace with dynamic()
    (
        r"(\s*)\bDynamicValue\b\(([^)]*)\)",
        r"\1dynamic(\2)"
    ),
    # Variable pattern in type hints
    (
        r"(\s*:\s*)\bDynamicValue\b",
        r"\1dynamicValue"
    ),
    # List pattern in type hints
    (
        r"List\[\bDynamicValue\b\]",
        r"List[dynamicValue]"
    ),
    # Optional pattern in type hints
    (
        r"Optional\[\bDynamicValue\b\]",
        r"Optional[dynamicValue]"
    ),
    # isinstance checks
    (
        r"isinstance\((.*?),\s*\bDynamicValue\b\)",
        r"isinstance(\1, dynamicValue)"
    ),
    # Expression attribute access
    (
        r"(\.\s*)expression",
        r"\1source"
    ),
    # evaluate method
    (
        r"(\.\s*)evaluate\((.*?)\)",
        r"\1eval()"
    )
]

def process_file(file_path):
    """Process a single file and convert DynamicValue usage."""
    print(f"Processing {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Check for DynamicValue usage
    has_dynamicvalue = 'DynamicValue' in content
    
    if has_dynamicvalue:
        # Add necessary imports if DynamicValue is used
        if 'from tinyDisplay.utility.evaluator import dynamicValue' not in content:
            # Find an appropriate place to add the import
            import_pattern = r'(from\s+tinyDisplay\.utility.*?\n)'
            match = re.search(import_pattern, content)
            if match:
                position = match.end()
                content = (content[:position] + 
                           'from tinyDisplay.utility.evaluator import dynamicValue\n' + 
                           content[position:])
    
    # Apply all patterns
    for pattern, replacement in PATTERNS:
        content = re.sub(pattern, replacement, content)
    
    # Check if content was modified
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file_path}")
        return True
    
    return False

def find_python_files(directory):
    """Find all Python files in the given directory."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                yield os.path.join(root, file)

def main():
    parser = argparse.ArgumentParser(
        description="Convert DynamicValue usage to dynamic() function"
    )
    parser.add_argument(
        "directory", nargs="?", default=".",
        help="Directory to scan for Python files (default: current directory)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", 
        help="Print files that would be modified without changing them"
    )
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists() or not directory.is_dir():
        print(f"Error: {directory} is not a valid directory")
        return 1
    
    modified_count = 0
    
    for file_path in find_python_files(directory):
        if args.dry_run:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file contains DynamicValue
            would_modify = 'DynamicValue' in content
            
            if would_modify:
                print(f"Would modify: {file_path}")
                modified_count += 1
        else:
            if process_file(file_path):
                modified_count += 1
    
    if args.dry_run:
        print(f"\nFound {modified_count} files that would be modified")
    else:
        print(f"\nModified {modified_count} files")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 