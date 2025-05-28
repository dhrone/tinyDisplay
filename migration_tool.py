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
    # Enhanced for DSL generation
    animations: List[str] = None
    bindings: List[str] = None
    z_order: Optional[int] = None
    visibility: Optional[str] = None
    # Additional properties for DSL conversion
    widget_type: Optional[str] = None
    x: int = 0
    y: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    properties: Dict[str, Any] = None

    def __post_init__(self):
        if self.animations is None:
            self.animations = []
        if self.bindings is None:
            self.bindings = []
        if self.properties is None:
            self.properties = {}
        # Extract widget type from class name if not set
        if self.widget_type is None:
            self.widget_type = self.name.lower().replace('widget', '')
        # Extract position if available
        if self.position and len(self.position) >= 2:
            self.x, self.y = self.position[0], self.position[1]
        # Extract size if available
        if self.size and len(self.size) >= 2:
            self.width, self.height = self.size[0], self.size[1]

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
class AnimationInfo:
    """Information about animation patterns"""
    name: str
    animation_type: str  # 'scroll', 'fade', 'slide', 'transition'
    duration: Optional[float] = None
    direction: Optional[str] = None  # 'left', 'right', 'up', 'down'
    timing: Optional[str] = None  # 'linear', 'ease-in', 'ease-out'
    sync_group: Optional[str] = None
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class DSLPatternInfo:
    """Information about DSL conversion patterns"""
    pattern_type: str  # 'widget_composition', 'animation_coordination', 'data_binding'
    legacy_pattern: str
    dsl_pattern: str
    complexity_score: int  # 1-10, higher = more complex
    conversion_confidence: float  # 0.0-1.0, higher = more confident

@dataclass
class CanvasInfo:
    """Information about canvas configurations"""
    name: str
    width: int
    height: int
    widgets: List[str]  # Widget names on this canvas
    z_layers: Dict[int, List[str]]  # Z-order layers
    file_path: str
    is_primary: bool = False

@dataclass
class WidgetHierarchy:
    """Information about widget parent-child relationships"""
    parent: str
    children: List[str]
    hierarchy_type: str  # 'container', 'group', 'layout'
    layout_properties: Dict[str, Any]

@dataclass
class CustomWidgetInfo:
    """Information about custom widget types"""
    name: str
    base_class: str
    custom_methods: List[str]
    custom_properties: Dict[str, Any]
    rendering_complexity: int  # 1-10 scale
    migration_strategy: str  # 'direct', 'composite', 'custom'

@dataclass
class ApplicationComplexity:
    """Analysis of application complexity"""
    widget_count: int
    canvas_count: int
    hierarchy_depth: int
    custom_widget_count: int
    data_binding_count: int
    animation_count: int
    complexity_score: int  # 1-100 scale
    migration_strategy: str  # 'simple', 'modular', 'phased'

@dataclass
class SystemAnalysis:
    """Complete analysis of existing system"""
    widgets: List[WidgetInfo]
    data_streams: List[DataStreamInfo]
    dynamic_values: List[DynamicValueInfo]
    display_config: Dict[str, Any]
    project_structure: Dict[str, List[str]]
    # Enhanced for DSL generation
    animations: List[AnimationInfo] = None
    dsl_patterns: List[DSLPatternInfo] = None
    # Enhanced for complex scenarios (Task 7)
    canvases: List[CanvasInfo] = None
    widget_hierarchies: List[WidgetHierarchy] = None
    custom_widgets: List[CustomWidgetInfo] = None
    application_complexity: ApplicationComplexity = None

    def __post_init__(self):
        if self.animations is None:
            self.animations = []
        if self.dsl_patterns is None:
            self.dsl_patterns = []
        if self.canvases is None:
            self.canvases = []
        if self.widget_hierarchies is None:
            self.widget_hierarchies = []
        if self.custom_widgets is None:
            self.custom_widgets = []
        if self.application_complexity is None:
            self.application_complexity = ApplicationComplexity(
                widget_count=0, canvas_count=0, hierarchy_depth=0,
                custom_widget_count=0, data_binding_count=0, animation_count=0,
                complexity_score=0, migration_strategy='simple'
            )

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
        
        # Enhanced for DSL generation
        self._analyze_animations()
        self._analyze_dsl_patterns()
        
        # Enhanced for complex scenarios (Task 7)
        self._analyze_canvases()
        self._analyze_widget_hierarchies()
        self._analyze_custom_widgets()
        self._analyze_application_complexity()
        
        print(f"✅ Analysis complete:")
        print(f"   - Found {len(self.analysis.widgets)} widgets")
        print(f"   - Found {len(self.analysis.data_streams)} data streams")
        print(f"   - Found {len(self.analysis.dynamic_values)} dynamic values")
        print(f"   - Found {len(self.analysis.animations)} animations")
        print(f"   - Identified {len(self.analysis.dsl_patterns)} DSL patterns")
        print(f"   - Found {len(self.analysis.canvases)} canvases")
        print(f"   - Found {len(self.analysis.widget_hierarchies)} widget hierarchies")
        print(f"   - Found {len(self.analysis.custom_widgets)} custom widgets")
        print(f"   - Application complexity: {self.analysis.application_complexity.complexity_score}/100")
        
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
                      list(self.source_dir.glob("**/render/*.py")) + \
                      list(self.source_dir.glob("**/*.py"))  # Include all Python files
        
        for file_path in widget_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    
                # Extract widget classes
                widgets = self._extract_widgets_from_ast(tree, file_path)
                self.analysis.widgets.extend(widgets)
                
                # Also extract widget instantiations
                widget_instances = self._extract_widget_instances_from_ast(tree, file_path)
                self.analysis.widgets.extend(widget_instances)
                
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
                        size=self._extract_size(node),
                        # Enhanced for DSL generation
                        animations=self._extract_animations_from_class(node),
                        bindings=self._extract_bindings_from_class(node),
                        z_order=self._extract_z_order(node),
                        visibility=self._extract_visibility(node)
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
    
    def _extract_animations_from_class(self, node: ast.ClassDef) -> List[str]:
        """Extract animations from widget class"""
        animations = []
        
        # Look for animation-related methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if 'animate' in item.name.lower():
                    animations.append(item.name)
        
        return animations
    
    def _extract_bindings_from_class(self, node: ast.ClassDef) -> List[str]:
        """Extract bindings from widget class"""
        bindings = []
        
        # Look for binding-related methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if 'bind' in item.name.lower():
                    bindings.append(item.name)
        
        return bindings
    
    def _extract_z_order(self, node: ast.ClassDef) -> Optional[int]:
        """Extract z-order from widget class"""
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id in ['z_order', 'order']:
                        try:
                            return ast.literal_eval(item.value)
                        except:
                            pass
        return None
    
    def _extract_visibility(self, node: ast.ClassDef) -> Optional[str]:
        """Extract visibility from widget class"""
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id in ['visibility', 'visible']:
                        try:
                            return ast.literal_eval(item.value)
                        except:
                            pass
        return None
    
    def _extract_widget_instances_from_ast(self, tree: ast.AST, file_path: Path) -> List[WidgetInfo]:
        """Extract widget instances from AST (e.g., Text(), ProgressBar(), etc.)"""
        widgets = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Look for assignments like: text_widget = Text("Hello", 10, 30)
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                        if isinstance(node.value.func, ast.Name):
                            widget_type = node.value.func.id.lower()
                            if widget_type in ['text', 'progressbar', 'gauge', 'button', 'label', 'image']:
                                # Extract position and properties from arguments
                                args = node.value.args
                                x, y = 0, 0
                                width, height = None, None
                                properties = {}
                                
                                if widget_type == 'text' and len(args) >= 3:
                                    if isinstance(args[1], ast.Constant):
                                        x = args[1].value
                                    if isinstance(args[2], ast.Constant):
                                        y = args[2].value
                                    if isinstance(args[0], ast.Constant):
                                        properties['content'] = args[0].value
                                elif widget_type == 'progressbar' and len(args) >= 5:
                                    if isinstance(args[0], ast.Constant):
                                        x = args[0].value
                                    if isinstance(args[1], ast.Constant):
                                        y = args[1].value
                                    if isinstance(args[2], ast.Constant):
                                        width = args[2].value
                                    if isinstance(args[3], ast.Constant):
                                        height = args[3].value
                                    if isinstance(args[4], ast.Constant):
                                        properties['value'] = args[4].value
                                elif widget_type == 'gauge' and len(args) >= 7:
                                    if isinstance(args[0], ast.Constant):
                                        x = args[0].value
                                    if isinstance(args[1], ast.Constant):
                                        y = args[1].value
                                    if isinstance(args[2], ast.Constant):
                                        width = args[2].value
                                    if isinstance(args[3], ast.Constant):
                                        height = args[3].value
                                
                                widget_info = WidgetInfo(
                                    name=target.id,
                                    file_path=str(file_path),
                                    class_name=node.value.func.id,
                                    methods=[],
                                    attributes={},
                                    dynamic_values=[],
                                    position=(x, y) if x or y else None,
                                    size=(width, height) if width and height else None,
                                    widget_type=widget_type,
                                    x=x, y=y,
                                    width=width, height=height,
                                    properties=properties
                                )
                                widgets.append(widget_info)
        
        return widgets
    
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
                
                # Pattern 3: Widget property bindings (enhanced for reactive patterns)
                binding_patterns = re.findall(r'\.bind\w*\(["\']?([^"\']+)["\']?\)', content)
                for binding in binding_patterns:
                    self.analysis.dynamic_values.append(DynamicValueInfo(
                        name=f"binding_{len(self.analysis.dynamic_values)}",
                        expression=binding,
                        dependencies=self._extract_dependencies_from_expression(binding),
                        usage_locations=[str(file_path)]
                    ))
                
                # Pattern 4: Data source subscriptions
                subscription_patterns = re.findall(r'subscribe\(["\']([^"\']+)["\']', content)
                for subscription in subscription_patterns:
                    self.analysis.dynamic_values.append(DynamicValueInfo(
                        name=f"subscription_{len(self.analysis.dynamic_values)}",
                        expression=f"data.{subscription}",
                        dependencies=[subscription],
                        usage_locations=[str(file_path)]
                    ))
                
                # Pattern 5: Reactive expressions with lambda/callback patterns
                reactive_patterns = re.findall(r'lambda\s+\w+:\s*([^,\)]+)', content)
                for reactive_expr in reactive_patterns:
                    if any(keyword in reactive_expr for keyword in ['data', 'sensor', 'value']):
                        self.analysis.dynamic_values.append(DynamicValueInfo(
                            name=f"reactive_{len(self.analysis.dynamic_values)}",
                            expression=reactive_expr.strip(),
                            dependencies=self._extract_dependencies_from_expression(reactive_expr),
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

    def _analyze_animations(self):
        """Analyze animation patterns in the codebase"""
        all_files = list(self.source_dir.glob("**/*.py"))
        
        for file_path in all_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Look for animation patterns
                import re
                
                # Pattern 1: Marquee animations (most common in legacy displays)
                marquee_patterns = re.findall(r'marquee|scroll|slide', content, re.IGNORECASE)
                for pattern in marquee_patterns:
                    # Extract direction and speed if possible
                    direction_match = re.search(r'direction["\s]*[:=]["\s]*(["\']?)(\w+)\1', content, re.IGNORECASE)
                    speed_match = re.search(r'speed["\s]*[:=]["\s]*(["\']?)(\d+\.?\d*)\1', content, re.IGNORECASE)
                    
                    direction = direction_match.group(2) if direction_match else "left"
                    speed = float(speed_match.group(2)) if speed_match else 1.0
                    
                    self.analysis.animations.append(AnimationInfo(
                        name=f"marquee_{len(self.analysis.animations)}",
                        animation_type="marquee",
                        direction=direction,
                        timing="linear",
                        sync_group=None,
                        duration=None  # Marquee typically loops indefinitely
                    ))
                
                # Pattern 2: Fade animations
                fade_patterns = re.findall(r'fade|opacity|alpha', content, re.IGNORECASE)
                for pattern in fade_patterns:
                    # Determine fade type
                    if 'in' in pattern.lower():
                        animation_type = "fade_in"
                    elif 'out' in pattern.lower():
                        animation_type = "fade_out"
                    else:
                        animation_type = "fade"
                    
                    # Extract duration if possible
                    duration_match = re.search(r'duration["\s]*[:=]["\s]*(["\']?)(\d+)\1', content, re.IGNORECASE)
                    duration = float(duration_match.group(2)) if duration_match else 1000
                    
                    self.analysis.animations.append(AnimationInfo(
                        name=f"fade_{len(self.analysis.animations)}",
                        animation_type=animation_type,
                        timing="ease-in",
                        sync_group=None,
                        duration=duration
                    ))
                
                # Pattern 3: Slide animations
                slide_patterns = re.findall(r'slide|move|translate', content, re.IGNORECASE)
                for pattern in slide_patterns:
                    # Determine slide direction
                    direction_match = re.search(r'(left|right|up|down)', content, re.IGNORECASE)
                    direction = direction_match.group(1) if direction_match else "left"
                    
                    self.analysis.animations.append(AnimationInfo(
                        name=f"slide_{len(self.analysis.animations)}",
                        animation_type="slide",
                        direction=direction,
                        timing="ease-out",
                        sync_group=None,
                        duration=800
                    ))
                
                # Pattern 4: Pulse/Blink animations
                pulse_patterns = re.findall(r'pulse|blink|flash', content, re.IGNORECASE)
                for pattern in pulse_patterns:
                    animation_type = "pulse" if "pulse" in pattern.lower() else "blink"
                    
                    self.analysis.animations.append(AnimationInfo(
                        name=f"{animation_type}_{len(self.analysis.animations)}",
                        animation_type=animation_type,
                        timing="linear",
                        sync_group=None,
                        duration=500
                    ))
                
                # Pattern 5: Rotation animations
                rotate_patterns = re.findall(r'rotate|spin|turn', content, re.IGNORECASE)
                for pattern in rotate_patterns:
                    self.analysis.animations.append(AnimationInfo(
                        name=f"rotate_{len(self.analysis.animations)}",
                        animation_type="rotate",
                        timing="linear",
                        sync_group=None,
                        duration=2000
                    ))
                
                # Pattern 6: Animation coordination (sync groups)
                sync_patterns = re.findall(r'sync["\s]*[:=]["\s]*(["\']?)(\w+)\1', content, re.IGNORECASE)
                for match in sync_patterns:
                    sync_group = match[1]
                    # Update existing animations with sync group
                    if self.analysis.animations:
                        self.analysis.animations[-1].sync_group = sync_group
                    
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze animations in {file_path}: {e}")

    def _analyze_dsl_patterns(self):
        """Analyze and identify DSL conversion patterns"""
        # Widget composition patterns
        for widget in self.analysis.widgets:
            if widget.position and widget.size:
                legacy_pattern = f"Widget with position {widget.position} and size {widget.size}"
                dsl_pattern = f"{widget.class_name}().position({widget.position[0]}, {widget.position[1]}).size({widget.size[0]}, {widget.size[1]})"
                
                self.analysis.dsl_patterns.append(DSLPatternInfo(
                    pattern_type="widget_composition",
                    legacy_pattern=legacy_pattern,
                    dsl_pattern=dsl_pattern,
                    complexity_score=3,
                    conversion_confidence=0.9
                ))
        
        # Animation coordination patterns
        for animation in self.analysis.animations:
            legacy_pattern = f"{animation.animation_type} animation"
            dsl_pattern = f"widget.animate.{animation.animation_type}()"
            if animation.sync_group:
                dsl_pattern += f".sync('{animation.sync_group}')"
            
            self.analysis.dsl_patterns.append(DSLPatternInfo(
                pattern_type="animation_coordination",
                legacy_pattern=legacy_pattern,
                dsl_pattern=dsl_pattern,
                complexity_score=5,
                conversion_confidence=0.8
            ))
        
        # Data binding patterns
        for dv in self.analysis.dynamic_values:
            legacy_pattern = f"DynamicValue('{dv.expression}')"
            dsl_pattern = f"widget.bind_value(data.{dv.dependencies[0] if dv.dependencies else 'unknown'})"
            
            self.analysis.dsl_patterns.append(DSLPatternInfo(
                pattern_type="data_binding",
                legacy_pattern=legacy_pattern,
                dsl_pattern=dsl_pattern,
                complexity_score=4,
                conversion_confidence=0.7
            ))

    def _analyze_canvases(self):
        """Analyze canvases in the codebase"""
        all_files = list(self.source_dir.glob("**/*.py"))
        canvas_dict = {}
        
        for file_path in all_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    tree = ast.parse(content)
                
                # Look for canvas creation and widget assignments
                for node in ast.walk(tree):
                    # Look for Canvas() instantiation
                    if isinstance(node, ast.Assign):
                        if isinstance(node.value, ast.Call):
                            if hasattr(node.value.func, 'id') and node.value.func.id == 'Canvas':
                                canvas_name = node.targets[0].id if hasattr(node.targets[0], 'id') else 'canvas'
                                width = 128  # Default
                                height = 64  # Default
                                
                                # Extract width and height from arguments
                                for keyword in node.value.keywords:
                                    if keyword.arg == 'width' and isinstance(keyword.value, ast.Constant):
                                        width = keyword.value.value
                                    elif keyword.arg == 'height' and isinstance(keyword.value, ast.Constant):
                                        height = keyword.value.value
                                
                                canvas_dict[canvas_name] = CanvasInfo(
                                    name=canvas_name,
                                    width=width,
                                    height=height,
                                    widgets=[],
                                    z_layers={},
                                    file_path=str(file_path),
                                    is_primary=(canvas_name == 'canvas' or canvas_name == 'main_canvas')
                                )
                    
                    # Look for canvas.add() calls
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Attribute) and node.func.attr == 'add':
                            if hasattr(node.func.value, 'id'):
                                canvas_name = node.func.value.id
                                if canvas_name in canvas_dict:
                                    # Extract widget names from arguments
                                    for arg in node.args:
                                        if hasattr(arg, 'id'):
                                            widget_name = arg.id
                                            canvas_dict[canvas_name].widgets.append(widget_name)
                
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze canvases in {file_path}: {e}")
        
        # Convert dictionary to list
        self.analysis.canvases = list(canvas_dict.values())
        
        # If no canvases found, create a default one
        if not self.analysis.canvases and self.analysis.widgets:
            self.analysis.canvases.append(CanvasInfo(
                name='main_canvas',
                width=128,
                height=64,
                widgets=[w.name for w in self.analysis.widgets],
                z_layers={},
                file_path='generated',
                is_primary=True
            ))

    def _analyze_widget_hierarchies(self):
        """Analyze widget hierarchies in the codebase"""
        all_files = list(self.source_dir.glob("**/*.py"))
        hierarchy_dict = {}
        
        for file_path in all_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    tree = ast.parse(content)
                
                # Look for widget hierarchy patterns
                for node in ast.walk(tree):
                    # Look for parent.add_child(child) patterns
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Attribute):
                            if node.func.attr in ['add_child', 'add_widget', 'add']:
                                if hasattr(node.func.value, 'id'):
                                    parent_name = node.func.value.id
                                    hierarchy_type = 'container'
                                    
                                    # Determine hierarchy type from method name
                                    if 'group' in node.func.attr.lower():
                                        hierarchy_type = 'group'
                                    elif 'layout' in node.func.attr.lower():
                                        hierarchy_type = 'layout'
                                    
                                    # Extract child widgets from arguments
                                    children = []
                                    for arg in node.args:
                                        if hasattr(arg, 'id'):
                                            children.append(arg.id)
                                    
                                    if parent_name not in hierarchy_dict:
                                        hierarchy_dict[parent_name] = WidgetHierarchy(
                                            parent=parent_name,
                                            children=children,
                                            hierarchy_type=hierarchy_type,
                                            layout_properties={}
                                        )
                                    else:
                                        hierarchy_dict[parent_name].children.extend(children)
                
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze widget hierarchies in {file_path}: {e}")
        
        # Convert dictionary to list
        self.analysis.widget_hierarchies = list(hierarchy_dict.values())

    def _analyze_custom_widgets(self):
        """Analyze custom widget types in the codebase"""
        all_files = list(self.source_dir.glob("**/*.py"))
        
        for file_path in all_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    tree = ast.parse(content)
                
                # Look for custom widget class definitions
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Check if it's a custom widget (not a standard widget type)
                        standard_widgets = {'Text', 'ProgressBar', 'Image', 'Button', 'Gauge', 'Chart'}
                        if node.name not in standard_widgets and 'Widget' in node.name:
                            # Extract base classes
                            base_classes = []
                            for base in node.bases:
                                if hasattr(base, 'id'):
                                    base_classes.append(base.id)
                            
                            # Extract custom methods
                            custom_methods = []
                            custom_properties = {}
                            
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    if not item.name.startswith('__'):  # Skip magic methods
                                        custom_methods.append(item.name)
                                elif isinstance(item, ast.Assign):
                                    # Extract custom properties
                                    for target in item.targets:
                                        if hasattr(target, 'id'):
                                            prop_name = target.id
                                            prop_value = 'unknown'
                                            if isinstance(item.value, ast.Constant):
                                                prop_value = item.value.value
                                            custom_properties[prop_name] = prop_value
                            
                            # Determine migration strategy based on complexity
                            migration_strategy = 'direct'
                            if len(custom_methods) > 5:
                                migration_strategy = 'composite'
                            elif len(custom_methods) > 10:
                                migration_strategy = 'custom'
                            
                            self.analysis.custom_widgets.append(CustomWidgetInfo(
                                name=node.name,
                                base_class=base_classes[0] if base_classes else 'Widget',
                                custom_methods=custom_methods,
                                custom_properties=custom_properties,
                                rendering_complexity=min(len(custom_methods), 10),
                                migration_strategy=migration_strategy
                            ))
                
            except Exception as e:
                print(f"⚠️  Warning: Could not analyze custom widgets in {file_path}: {e}")

    def _analyze_application_complexity(self):
        """Analyze application complexity"""
        # Calculate complexity scores
        self.analysis.application_complexity.widget_count = len(self.analysis.widgets)
        self.analysis.application_complexity.canvas_count = len(self.analysis.canvases)
        self.analysis.application_complexity.hierarchy_depth = max(len(hierarchy.children) for hierarchy in self.analysis.widget_hierarchies) if self.analysis.widget_hierarchies else 0
        self.analysis.application_complexity.custom_widget_count = len(self.analysis.custom_widgets)
        self.analysis.application_complexity.data_binding_count = len(self.analysis.dynamic_values)
        self.analysis.application_complexity.animation_count = len(self.analysis.animations)
        
        # Calculate complexity score
        complexity_score = 0
        complexity_score += self.analysis.application_complexity.widget_count * 0.2
        complexity_score += self.analysis.application_complexity.canvas_count * 0.2
        complexity_score += self.analysis.application_complexity.hierarchy_depth * 0.1
        complexity_score += self.analysis.application_complexity.custom_widget_count * 0.1
        complexity_score += self.analysis.application_complexity.data_binding_count * 0.1
        complexity_score += self.analysis.application_complexity.animation_count * 0.1
        complexity_score += self.analysis.application_complexity.hierarchy_depth * 0.1
        
        self.analysis.application_complexity.complexity_score = int(complexity_score)

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