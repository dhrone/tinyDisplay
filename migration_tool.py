#!/usr/bin/env python3
"""
tinyDisplay Migration Tool

Analyzes existing tinyDisplay codebase and generates new reactive architecture.
This tool automates the migration from the current system to the new 
Ring Buffer + SQLite + asteval + RxPY architecture.
"""

import os
import sys
import ast
import glob
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import importlib.util

@dataclass
class WidgetInfo:
    """Information about an existing widget"""
    name: str
    file_path: str
    class_name: str
    methods: List[str]
    attributes: Dict[str, Any]
    dynamic_values: List[str]
    position: Optional[tuple] = None
    size: Optional[tuple] = None

@dataclass
class DataStreamInfo:
    """Information about a data stream"""
    key: str
    data_type: str
    sample_values: List[Any]
    usage_count: int
    is_time_series: bool

@dataclass
class DynamicValueInfo:
    """Information about a dynamic value expression"""
    name: str
    expression: str
    dependencies: List[str]
    usage_locations: List[str]

@dataclass
class SystemAnalysis:
    """Complete analysis of existing system"""
    widgets: List[WidgetInfo]
    data_streams: List[DataStreamInfo]
    dynamic_values: List[DynamicValueInfo]
    display_config: Dict[str, Any]
    project_structure: Dict[str, List[str]]

class SystemAnalyzer:
    """Analyzes existing tinyDisplay codebase"""
    
    def __init__(self, source_dir: str):
        self.source_dir = Path(source_dir)
        self.analysis = SystemAnalysis(
            widgets=[],
            data_streams=[],
            dynamic_values=[],
            display_config={},
            project_structure={}
        )
    
    def analyze(self) -> SystemAnalysis:
        """Perform complete system analysis"""
        print("🔍 Analyzing existing tinyDisplay system...")
        
        # Analyze project structure
        self._analyze_project_structure()
        
        # Analyze widgets
        self._analyze_widgets()
        
        # Analyze data usage
        self._analyze_data_usage()
        
        # Analyze dynamic values
        self._analyze_dynamic_values()
        
        # Analyze display configuration
        self._analyze_display_config()
        
        print(f"✅ Analysis complete:")
        print(f"   - Found {len(self.analysis.widgets)} widgets")
        print(f"   - Found {len(self.analysis.data_streams)} data streams")
        print(f"   - Found {len(self.analysis.dynamic_values)} dynamic values")
        
        return self.analysis
    
    def _analyze_project_structure(self):
        """Analyze the project directory structure"""
        for root, dirs, files in os.walk(self.source_dir):
            rel_path = os.path.relpath(root, self.source_dir)
            python_files = [f for f in files if f.endswith('.py')]
            if python_files:
                self.analysis.project_structure[rel_path] = python_files
    
    def _analyze_widgets(self):
        """Analyze widget classes and their properties"""
        widget_files = list(self.source_dir.glob("**/widget*.py")) + \
                      list(self.source_dir.glob("**/render/*.py"))
        
        for file_path in widget_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                widgets = self._extract_widgets_from_ast(tree, file_path)
                self.analysis.widgets.extend(widgets)
                
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze {file_path}: {e}")
    
    def _extract_widgets_from_ast(self, tree: ast.AST, file_path: Path) -> List[WidgetInfo]:
        """Extract widget information from AST"""
        widgets = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._is_widget_class(node):
                    widget_info = WidgetInfo(
                        name=node.name.lower().replace('widget', ''),
                        file_path=str(file_path),
                        class_name=node.name,
                        methods=[m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                        attributes=self._extract_class_attributes(node),
                        dynamic_values=self._extract_dynamic_values_from_class(node),
                        position=self._extract_position(node),
                        size=self._extract_size(node)
                    )
                    widgets.append(widget_info)
        
        return widgets
    
    def _is_widget_class(self, node: ast.ClassDef) -> bool:
        """Determine if a class is a widget"""
        # Check class name patterns
        if 'widget' in node.name.lower():
            return True
        
        # Check if it inherits from a widget base class
        for base in node.bases:
            if isinstance(base, ast.Name) and 'widget' in base.id.lower():
                return True
        
        # Check for widget-like methods
        methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
        widget_methods = {'render', 'update', 'draw', 'display'}
        if any(method in widget_methods for method in methods):
            return True
        
        return False
    
    def _extract_class_attributes(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Extract class attributes and their default values"""
        attributes = {}
        
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        try:
                            # Try to evaluate simple literals
                            value = ast.literal_eval(item.value)
                            attributes[target.id] = value
                        except (ValueError, TypeError):
                            # Store as string representation for complex expressions
                            attributes[target.id] = ast.unparse(item.value)
        
        return attributes
    
    def _extract_dynamic_values_from_class(self, node: ast.ClassDef) -> List[str]:
        """Extract dynamic value expressions from widget class"""
        dynamic_values = []
        
        # Look for DynamicValue instantiations
        for item in ast.walk(node):
            if isinstance(item, ast.Call):
                if isinstance(item.func, ast.Name) and 'dynamic' in item.func.id.lower():
                    if item.args:
                        try:
                            expr = ast.literal_eval(item.args[0])
                            dynamic_values.append(expr)
                        except:
                            pass
        
        return dynamic_values
    
    def _extract_position(self, node: ast.ClassDef) -> Optional[tuple]:
        """Extract position from widget class"""
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id in ['position', 'pos', 'location']:
                        try:
                            return ast.literal_eval(item.value)
                        except:
                            pass
        return None
    
    def _extract_size(self, node: ast.ClassDef) -> Optional[tuple]:
        """Extract size from widget class"""
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id in ['size', 'dimensions', 'width_height']:
                        try:
                            return ast.literal_eval(item.value)
                        except:
                            pass
        return None
    
    def _analyze_data_usage(self):
        """Analyze how data is used throughout the codebase"""
        # Look for dataset usage patterns
        all_files = list(self.source_dir.glob("**/*.py"))
        data_usage = {}
        
        for file_path in all_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Look for dataset.get() calls
                import re
                get_calls = re.findall(r'dataset\.get\(["\']([^"\']+)["\']', content)
                for key in get_calls:
                    if key not in data_usage:
                        data_usage[key] = {
                            'usage_count': 0,
                            'files': [],
                            'sample_values': []
                        }
                    data_usage[key]['usage_count'] += 1
                    data_usage[key]['files'].append(str(file_path))
                
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze data usage in {file_path}: {e}")
        
        # Convert to DataStreamInfo objects
        for key, info in data_usage.items():
            self.analysis.data_streams.append(DataStreamInfo(
                key=key,
                data_type="Any",  # Will be refined during actual migration
                sample_values=[],
                usage_count=info['usage_count'],
                is_time_series=True  # Assume time-series for now
            ))
    
    def _analyze_dynamic_values(self):
        """Analyze dynamic value expressions throughout codebase"""
        all_files = list(self.source_dir.glob("**/*.py"))
        
        for file_path in all_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Look for dynamic value patterns
                import re
                
                # Pattern 1: DynamicValue("expression")
                dv_calls = re.findall(r'DynamicValue\(["\']([^"\']+)["\']', content)
                for expr in dv_calls:
                    self.analysis.dynamic_values.append(DynamicValueInfo(
                        name=f"dv_{len(self.analysis.dynamic_values)}",
                        expression=expr,
                        dependencies=self._extract_dependencies_from_expression(expr),
                        usage_locations=[str(file_path)]
                    ))
                
                # Pattern 2: f-strings and format strings that might be dynamic
                f_strings = re.findall(r'f["\']([^"\']*\{[^}]+\}[^"\']*)["\']', content)
                for f_str in f_strings:
                    if any(keyword in f_str for keyword in ['sensor', 'data', 'temp', 'time']):
                        self.analysis.dynamic_values.append(DynamicValueInfo(
                            name=f"f_string_{len(self.analysis.dynamic_values)}",
                            expression=f_str,
                            dependencies=self._extract_dependencies_from_expression(f_str),
                            usage_locations=[str(file_path)]
                        ))
                
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze dynamic values in {file_path}: {e}")
    
    def _extract_dependencies_from_expression(self, expression: str) -> List[str]:
        """Extract data dependencies from an expression"""
        dependencies = []
        
        # Simple pattern matching for common dependency patterns
        import re
        
        # Pattern: dataset.get('key') or similar
        dataset_refs = re.findall(r'dataset\.get\(["\']([^"\']+)["\']', expression)
        dependencies.extend(dataset_refs)
        
        # Pattern: sensor.temperature or similar dot notation
        dot_refs = re.findall(r'(\w+\.\w+)', expression)
        dependencies.extend(dot_refs)
        
        # Pattern: variables that look like data keys
        var_refs = re.findall(r'\{(\w+)\}', expression)  # f-string variables
        dependencies.extend(var_refs)
        
        return list(set(dependencies))  # Remove duplicates
    
    def _analyze_display_config(self):
        """Analyze display configuration"""
        # Look for display-related configuration
        config_files = list(self.source_dir.glob("**/config*.py")) + \
                      list(self.source_dir.glob("**/settings*.py"))
        
        for file_path in config_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                # Extract configuration variables
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                name = target.id.lower()
                                if any(keyword in name for keyword in ['display', 'screen', 'width', 'height', 'fps']):
                                    try:
                                        value = ast.literal_eval(node.value)
                                        self.analysis.display_config[target.id] = value
                                    except:
                                        pass
                                        
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze config in {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Migrate tinyDisplay to new reactive architecture')
    parser.add_argument('--source', '-s', required=True, help='Source directory (existing tinyDisplay)')
    parser.add_argument('--target', '-t', required=True, help='Target directory (new architecture)')
    parser.add_argument('--analysis-only', action='store_true', help='Only perform analysis, don\'t generate code')
    parser.add_argument('--output-analysis', '-o', help='Save analysis to JSON file')
    
    args = parser.parse_args()
    
    # Validate source directory
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"❌ Source directory {source_path} does not exist")
        sys.exit(1)
    
    # Analyze existing system
    analyzer = SystemAnalyzer(args.source)
    analysis = analyzer.analyze()
    
    # Save analysis if requested
    if args.output_analysis:
        with open(args.output_analysis, 'w') as f:
            json.dump(asdict(analysis), f, indent=2, default=str)
        print(f"📄 Analysis saved to {args.output_analysis}")
    
    if args.analysis_only:
        print("🔍 Analysis complete. Use --output-analysis to save results.")
        return
    
    # Generate new system
    from migration_generator import CodeGenerator, GenerationConfig
    
    config = GenerationConfig(
        target_fps=60,
        max_memory_mb=200,
        ring_buffer_default_size=1000,
        speculation_workers=3,
        enable_predictive_progress=True
    )
    
    generator = CodeGenerator(analysis, config)
    generator.generate_new_system(args.target)

if __name__ == "__main__":
    main() 