#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migration script to convert d-prefixed parameters to dynamic() function calls.

Usage:
    python migrate_dynamic.py <file_or_directory>

This script will scan Python files for widget creation with d-prefixed parameters
and convert them to use the dynamic() function approach.
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Regular expression to find d-prefixed parameters
D_PREFIX_PATTERN = re.compile(r"(\s*)(d[a-zA-Z0-9_]+)(\s*=\s*)(['\"])(.+?)\4", re.DOTALL)

# Pattern to check if dynamic function is already imported
IMPORT_PATTERN = re.compile(r"from\s+tinyDisplay\.utility\.dynamic\s+import\s+dynamic")

def process_file(file_path):
    """Process a single Python file to convert d-prefixed parameters."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if there are any d-prefixed parameters to convert
    matches = D_PREFIX_PATTERN.findall(content)
    if not matches:
        print(f"No d-prefixed parameters found in {file_path}")
        return 0
    
    # Check if the dynamic import already exists
    needs_import = not IMPORT_PATTERN.search(content)
    
    # Add import if needed
    if needs_import:
        # Find where to add the import
        import_line = "from tinyDisplay.utility.dynamic import dynamic\n"
        
        # Look for other tinyDisplay imports to add it nearby
        td_import_match = re.search(r"(from tinyDisplay.*import .*\n)", content)
        if td_import_match:
            # Add after the last tinyDisplay import
            all_td_imports = re.finditer(r"from tinyDisplay.*import .*\n", content)
            last_pos = 0
            for match in all_td_imports:
                last_pos = match.end()
            
            content = content[:last_pos] + import_line + content[last_pos:]
        else:
            # Add at the top of the file after any module docstring
            doc_end = re.search(r'""".*?"""\n', content, re.DOTALL)
            if doc_end:
                pos = doc_end.end()
                content = content[:pos] + "\n" + import_line + content[pos:]
            else:
                # Just add after any shebang and encoding lines
                encoding_match = re.search(r'# -\*- coding:.*-\*-\n', content)
                if encoding_match:
                    pos = encoding_match.end()
                    content = content[:pos] + "\n" + import_line + content[pos:]
                else:
                    content = import_line + content
    
    # Replace d-prefixed parameters with dynamic function calls
    def replacement(match):
        whitespace, param, equals, quote, value = match.groups()
        # Remove the 'd' prefix from parameter name
        param_name = param[1:]
        # Replace with dynamic function call
        return f"{whitespace}{param_name}{equals}{quote}dynamic({quote}{value}{quote}){quote}"
    
    # This approach doesn't work well due to the complexity of matching balanced quotes
    # Instead, we'll modify the content line by line
    new_lines = []
    lines = content.splitlines()
    
    for line in lines:
        # Only process lines that look like they have d-prefixed parameters
        if re.search(r'\bd[a-zA-Z0-9_]+\s*=\s*[\'"]', line):
            # Replace d-prefixed parameters
            modified_line = D_PREFIX_PATTERN.sub(
                lambda m: f"{m.group(1)}{m.group(2)[1:]}{m.group(3)}dynamic({m.group(4)}{m.group(5)}{m.group(4)})",
                line
            )
            new_lines.append(modified_line)
        else:
            new_lines.append(line)
    
    # Save back the modified content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"Converted {len(matches)} d-prefixed parameters in {file_path}")
    if needs_import:
        print(f"Added dynamic import to {file_path}")
    
    return len(matches)

def process_directory(directory):
    """Process all Python files in a directory recursively."""
    total_changes = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                total_changes += process_file(file_path)
    return total_changes

def main():
    parser = argparse.ArgumentParser(
        description="Convert d-prefixed parameters to dynamic() function calls"
    )
    parser.add_argument(
        "path", 
        help="File or directory to process"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Only report changes without modifying files"
    )
    args = parser.parse_args()
    
    path = Path(args.path)
    
    if not path.exists():
        print(f"Error: Path {path} does not exist")
        return 1
    
    if args.dry_run:
        print("Dry run mode: No files will be modified")
    
    if path.is_file():
        if not path.name.endswith('.py'):
            print(f"Error: {path} is not a Python file")
            return 1
        if args.dry_run:
            print(f"Would process file: {path}")
        else:
            changes = process_file(path)
            print(f"Made {changes} changes to {path}")
    elif path.is_dir():
        if args.dry_run:
            print(f"Would process directory: {path}")
        else:
            changes = process_directory(path)
            print(f"Made a total of {changes} changes in directory {path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 