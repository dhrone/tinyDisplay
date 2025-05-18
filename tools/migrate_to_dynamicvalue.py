#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migration script to convert DynamicValue to dynamicValue.

This script scans Python files and modifies direct usage of DynamicValue 
to use dynamicValue from tinyDisplay.utility.evaluator instead.
from tinyDisplay.utility.evaluator import dynamicValue
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
        r"from tinyDisplay.utility.dynamic import \1dynamic\2"
    ),
    # Direct usage pattern
    (
        r"(\s*)\bDynamicValue\b\(([^)]*)\)",
        r"\1dynamic(\2)"
    ),
    # Type annotation pattern
    (
        r"(\s*:.+?)\bDynamicValue\b", 
        r"\1dynamicValue"
    ),
    # Variable type hint pattern
    (
        r"(:\s*)\bDynamicValue\b",
        r"\1dynamicValue"
    ),
]

def process_file(file_path):
    """Process a single file and fix DynamicValue usages."""
    print(f"Processing {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
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
        description="Convert DynamicValue usage to dynamicValue"
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
            
            # Check if any pattern matches
            would_modify = any(
                re.search(pattern, content) 
                for pattern, _ in PATTERNS
            )
            
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