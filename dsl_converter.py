#!/usr/bin/env python3
"""
DSL Converter Utilities

Converts JSON configurations and legacy patterns to DSL syntax.
Provides utilities for JSON-to-DSL transformation and DSL pattern generation.
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from migration_tool import WidgetInfo, AnimationInfo, DSLPatternInfo, DynamicValueInfo


@dataclass
class DSLGenerationConfig:
    """Configuration for DSL generation"""
    indent_size: int = 4
    max_line_length: int = 88
    use_method_chaining: bool = True
    generate_comments: bool = True
    validate_syntax: bool = True


class DSLConverter:
    """Converts legacy patterns and JSON to DSL syntax"""
    
    def __init__(self, config: DSLGenerationConfig = None):
        self.config = config or DSLGenerationConfig()
        self.widget_templates = self._init_widget_templates()
        self.animation_templates = self._init_animation_templates()
    
    def _init_widget_templates(self) -> Dict[str, str]:
        """Initialize widget DSL templates"""
        return {
            'text': 'Text("{content}").position({x}, {y}).z_order({z})',
            'progress': 'ProgressBar(value={value}).position({x}, {y}).size({width}, {height})',
            'progressbar': 'ProgressBar(value={value}).position({x}, {y}).size({width}, {height})',
            'image': 'Image("{path}").position({x}, {y}).size({width}, {height})',
            'button': 'Button("{text}").position({x}, {y}).on_click({callback})',
            'label': 'Label("{text}").position({x}, {y}).font_size({size})',
            'canvas': 'Canvas(width={width}, height={height})',
            'gauge': 'Gauge(value={value}, min_val={min_val}, max_val={max_val}).position({x}, {y}).size({width}, {height})',
            'chart': 'Chart(data={data}, chart_type="{chart_type}").position({x}, {y}).size({width}, {height})',
            'slider': 'Slider(value={value}, min_val={min_val}, max_val={max_val}).position({x}, {y}).size({width}, {height})',
            'checkbox': 'Checkbox(checked={checked}, label="{label}").position({x}, {y})',
            'radio': 'RadioButton(selected={selected}, label="{label}", group="{group}").position({x}, {y})',
            'textbox': 'TextBox(text="{text}", placeholder="{placeholder}").position({x}, {y}).size({width}, {height})',
            'list': 'ListView(items={items}).position({x}, {y}).size({width}, {height})',
            'grid': 'GridView(data={data}, columns={columns}).position({x}, {y}).size({width}, {height})',
            # Reactive binding templates
            'reactive_text': 'Text().bind_content({content_binding}).position({x}, {y}).z_order({z})',
            'reactive_progress': 'ProgressBar().bind_value({value_binding}).position({x}, {y}).size({width}, {height})',
            'reactive_gauge': 'Gauge().bind_value({value_binding}).position({x}, {y}).size({width}, {height})',
        }
    
    def _init_animation_templates(self) -> Dict[str, str]:
        """Initialize animation DSL templates"""
        return {
            'scroll': 'animate.scroll(direction="{direction}", speed={speed}, distance={distance})',
            'marquee': 'animate.marquee(direction="{direction}", speed={speed}, loop={loop})',
            'fade': 'animate.fade(duration={duration}, from_alpha={from_alpha}, to_alpha={to_alpha})',
            'fade_in': 'animate.fade_in(duration={duration})',
            'fade_out': 'animate.fade_out(duration={duration})',
            'slide': 'animate.slide(direction="{direction}", distance={distance}, duration={duration})',
            'slide_in': 'animate.slide_in(direction="{direction}", duration={duration})',
            'slide_out': 'animate.slide_out(direction="{direction}", duration={duration})',
            'transition': 'animate.transition(property="{property}", duration={duration}, timing="{timing}")',
            'bounce': 'animate.bounce(amplitude={amplitude}, frequency={frequency}, duration={duration})',
            'pulse': 'animate.pulse(scale_factor={scale_factor}, duration={duration})',
            'rotate': 'animate.rotate(angle={angle}, duration={duration})',
            'scale': 'animate.scale(factor={scale_factor}, duration={duration})',
            'blink': 'animate.blink(interval={interval}, count={count})',
            # Coordination patterns
            'sync': 'sync("{group_name}")',
            'sequence': 'then({next_animation})',
            'parallel': 'parallel({animations})',
            'barrier': 'barrier("{barrier_name}").then({next_animation})',
            'delay': 'delay({delay_ms})',
            'repeat': 'repeat({count})',
            'loop': 'loop()',
        }
    
    def convert_json_to_dsl(self, json_config: Dict[str, Any]) -> str:
        """Convert JSON configuration to DSL syntax"""
        dsl_lines = []
        
        if self.config.generate_comments:
            dsl_lines.append("# Generated DSL from JSON configuration")
            dsl_lines.append("")
        
        # Convert canvas configuration
        if 'canvas' in json_config:
            canvas_dsl = self._convert_canvas_json(json_config['canvas'])
            dsl_lines.append(canvas_dsl)
            dsl_lines.append("")
        
        # Convert widgets
        if 'widgets' in json_config:
            widgets_dsl = self._convert_widgets_json(json_config['widgets'])
            dsl_lines.extend(widgets_dsl)
            dsl_lines.append("")
        
        # Convert animations
        if 'animations' in json_config:
            animations_dsl = self._convert_animations_json(json_config['animations'])
            dsl_lines.extend(animations_dsl)
        
        return '\n'.join(dsl_lines)
    
    def _convert_canvas_json(self, canvas_config: Dict[str, Any]) -> str:
        """Convert canvas JSON to DSL"""
        width = canvas_config.get('width', 128)
        height = canvas_config.get('height', 64)
        
        canvas_dsl = f"canvas = Canvas(width={width}, height={height})"
        
        # Add widgets to canvas if present
        if 'widgets' in canvas_config:
            widget_calls = []
            for widget in canvas_config['widgets']:
                widget_dsl = self._convert_widget_json(widget)
                widget_calls.append(f"    {widget_dsl}")
            
            if widget_calls:
                canvas_dsl += "\ncanvas.add(\n" + ",\n".join(widget_calls) + "\n)"
        
        return canvas_dsl
    
    def _convert_widgets_json(self, widgets_config: List[Dict[str, Any]]) -> List[str]:
        """Convert widgets JSON to DSL"""
        widget_lines = []
        
        for i, widget in enumerate(widgets_config):
            widget_dsl = self._convert_widget_json(widget, variable_name=f"widget_{i}")
            widget_lines.append(widget_dsl)
        
        return widget_lines
    
    def _convert_widget_json(self, widget_config: Dict[str, Any], variable_name: str = None) -> str:
        """Convert single widget JSON to DSL"""
        widget_type = widget_config.get('type', 'text')
        template = self.widget_templates.get(widget_type, self.widget_templates['text'])
        
        # Extract common properties
        x = widget_config.get('position', {}).get('x', 0)
        y = widget_config.get('position', {}).get('y', 0)
        z = widget_config.get('z_order', 1)
        width = widget_config.get('size', {}).get('width', 100)
        height = widget_config.get('size', {}).get('height', 20)
        
        # Widget-specific properties
        widget_props = {
            'x': x, 'y': y, 'z': z, 'width': width, 'height': height,
            'content': widget_config.get('content', 'Text'),
            'text': widget_config.get('text', 'Button'),
            'value': widget_config.get('value', 'data.value'),
            'path': widget_config.get('path', 'image.png'),
            'callback': widget_config.get('callback', 'on_click_handler'),
            'size': widget_config.get('font_size', 12),
            # Enhanced properties for different widget types
            'min_val': widget_config.get('min_value', widget_config.get('min', 0)),
            'max_val': widget_config.get('max_value', widget_config.get('max', 100)),
            'chart_type': widget_config.get('chart_type', 'line'),
            'data': widget_config.get('data', 'data.values'),
            'checked': widget_config.get('checked', False),
            'selected': widget_config.get('selected', False),
            'label': widget_config.get('label', widget_config.get('content', 'Text')),
            'group': widget_config.get('group', 'default'),
            'placeholder': widget_config.get('placeholder', 'Enter text...'),
            'items': widget_config.get('items', 'data.items'),
            'columns': widget_config.get('columns', 'data.columns'),
        }
        
        # Format template with properties
        try:
            widget_dsl = template.format(**widget_props)
        except KeyError as e:
            # Fallback for missing properties
            widget_dsl = f"Widget(type='{widget_type}').position({x}, {y})"
        
        # Add variable assignment if requested
        if variable_name:
            widget_dsl = f"{variable_name} = {widget_dsl}"
        
        return widget_dsl
    
    def _convert_animations_json(self, animations_config: List[Dict[str, Any]]) -> List[str]:
        """Convert animations JSON to DSL"""
        animation_lines = []
        
        for i, animation in enumerate(animations_config):
            animation_dsl = self._convert_animation_json(animation, target=f"widget_{i}")
            animation_lines.append(animation_dsl)
        
        return animation_lines
    
    def _convert_animation_json(self, animation_config: Dict[str, Any], target: str = "widget") -> str:
        """Convert single animation JSON to DSL"""
        animation_type = animation_config.get('type', 'fade')
        template = self.animation_templates.get(animation_type, self.animation_templates['fade'])
        
        # Animation properties
        animation_props = {
            'direction': animation_config.get('direction', 'left'),
            'speed': animation_config.get('speed', 1.0),
            'duration': animation_config.get('duration', 1000),
            'from_alpha': animation_config.get('from_alpha', 0.0),
            'to_alpha': animation_config.get('to_alpha', 1.0),
            'distance': animation_config.get('distance', 100),
            'property': animation_config.get('property', 'opacity'),
            'timing': animation_config.get('timing', 'ease-in'),
        }
        
        # Format template
        try:
            animation_dsl = template.format(**animation_props)
        except KeyError:
            animation_dsl = f"animate.{animation_type}()"
        
        # Add sync group if present
        if 'sync_group' in animation_config:
            sync_template = self.animation_templates['sync']
            sync_dsl = sync_template.format(group_name=animation_config['sync_group'])
            animation_dsl += f".{sync_dsl}"
        
        return f"{target}.{animation_dsl}"
    
    def convert_widget_info_to_dsl(self, widget_info: WidgetInfo) -> str:
        """Convert WidgetInfo object to DSL syntax"""
        widget_type = widget_info.name.lower()
        
        # Map widget names to template types
        type_mapping = {
            'progress_bar': 'progress',
            'progressbar': 'progress',
            'progress': 'progress',
            'text': 'text',
            'label': 'label',
            'image': 'image',
            'button': 'button',
            'gauge': 'gauge',
            'chart': 'chart',
            'graph': 'chart',
            'slider': 'slider',
            'checkbox': 'checkbox',
            'check': 'checkbox',
            'radio': 'radio',
            'radiobutton': 'radio',
            'textbox': 'textbox',
            'input': 'textbox',
            'list': 'list',
            'listview': 'list',
            'grid': 'grid',
            'gridview': 'grid',
            'table': 'grid'
        }
        
        template_type = type_mapping.get(widget_type, 'text')
        template = self.widget_templates.get(template_type, self.widget_templates['text'])
        
        # Extract properties from widget_info
        x, y = widget_info.position or (0, 0)
        width, height = widget_info.size or (100, 20)
        z = widget_info.z_order or 1
        
        # Get content from attributes
        content = widget_info.attributes.get('text', widget_info.attributes.get('content', 'Widget'))
        
        widget_props = {
            'x': x, 'y': y, 'z': z, 'width': width, 'height': height,
            'content': content, 'text': content,
            'value': widget_info.attributes.get('value', 'data.value'),
            'path': widget_info.attributes.get('path', widget_info.attributes.get('image_path', 'image.png')),
            'callback': widget_info.attributes.get('callback', 'on_click_handler'),
            'size': widget_info.attributes.get('font_size', 12),
            # Enhanced properties for different widget types
            'min_val': widget_info.attributes.get('min_value', widget_info.attributes.get('min', 0)),
            'max_val': widget_info.attributes.get('max_value', widget_info.attributes.get('max', 100)),
            'chart_type': widget_info.attributes.get('chart_type', 'line'),
            'data': widget_info.attributes.get('data', 'data.values'),
            'checked': widget_info.attributes.get('checked', False),
            'selected': widget_info.attributes.get('selected', False),
            'label': widget_info.attributes.get('label', content),
            'group': widget_info.attributes.get('group', 'default'),
            'placeholder': widget_info.attributes.get('placeholder', 'Enter text...'),
            'items': widget_info.attributes.get('items', 'data.items'),
            'columns': widget_info.attributes.get('columns', 'data.columns'),
        }
        
        try:
            widget_dsl = template.format(**widget_props)
        except KeyError:
            widget_dsl = f"{widget_info.class_name}().position({x}, {y})"
        
        # Add data bindings if present
        if widget_info.bindings:
            for binding in widget_info.bindings:
                widget_dsl += f".bind_value({binding})"
        
        return widget_dsl
    
    def convert_animation_info_to_dsl(self, animation_info: AnimationInfo, target: str = "widget") -> str:
        """Convert AnimationInfo object to DSL syntax"""
        template = self.animation_templates.get(animation_info.animation_type, 
                                               self.animation_templates['fade'])
        
        animation_props = {
            'direction': animation_info.direction or 'left',
            'speed': 1.0,
            'distance': 100,
            'duration': animation_info.duration or 1000,
            'from_alpha': 0.0, 'to_alpha': 1.0,
            'property': 'opacity',
            'timing': animation_info.timing or 'ease-in',
            # Enhanced animation properties
            'loop': True,
            'amplitude': 10,
            'frequency': 2,
            'scale_factor': 1.2,
            'angle': 360,
            'interval': 500,
            'count': 3,
            'delay_ms': 0,
            'animations': '[]',
        }
        
        try:
            animation_dsl = template.format(**animation_props)
        except KeyError:
            animation_dsl = f"animate.{animation_info.animation_type}()"
        
        # Add sync group if present
        if animation_info.sync_group:
            sync_template = self.animation_templates['sync']
            sync_dsl = sync_template.format(group_name=animation_info.sync_group)
            animation_dsl += f".{sync_dsl}"
        
        return f"{target}.{animation_dsl}"
    
    def validate_dsl_syntax(self, dsl_code: str) -> tuple[bool, List[str]]:
        """Validate DSL syntax and return errors if any"""
        errors = []
        
        try:
            # Basic syntax validation
            lines = dsl_code.split('\n')
            open_parens = 0
            open_quotes = 0
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Count parentheses across multiple lines
                open_parens += line.count('(') - line.count(')')
                
                # Count quotes (should be even within complete statements)
                quote_count = line.count('"')
                if quote_count % 2 != 0:
                    open_quotes = 1 - open_quotes
                
                # Check for invalid method chaining patterns
                if '.(' in line and not any(pattern in line for pattern in ['canvas.add(', '.position(', '.size(', '.z_order(']):
                    errors.append(f"Line {i}: Invalid method chaining syntax")
            
            # Check final balance
            if open_parens != 0:
                errors.append("Unbalanced parentheses in complete code")
            
            if open_quotes != 0:
                errors.append("Unmatched quotes in complete code")
        
        except Exception as e:
            errors.append(f"Syntax validation error: {str(e)}")
        
        return len(errors) == 0, errors
    
    def format_dsl_code(self, dsl_code: str) -> str:
        """Format DSL code according to configuration"""
        lines = dsl_code.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Apply indentation
            if line.strip():
                # Basic indentation logic
                indent_level = 0
                if '.add(' in line or 'canvas.add(' in line:
                    indent_level = 1
                elif line.strip().startswith(')'):
                    indent_level = 0
                elif '    ' in line:
                    indent_level = 1
                
                formatted_line = ' ' * (indent_level * self.config.indent_size) + line.strip()
                formatted_lines.append(formatted_line)
            else:
                formatted_lines.append('')
        
        return '\n'.join(formatted_lines)
    
    def generate_reactive_bindings(self, dynamic_values: List[DynamicValueInfo]) -> str:
        """Generate reactive binding DSL code from dynamic values"""
        if not dynamic_values:
            return ""
        
        binding_code = []
        binding_code.append("# Reactive Data Bindings")
        binding_code.append("")
        
        # Group bindings by data source
        data_sources = {}
        for dv in dynamic_values:
            for dep in dv.dependencies:
                if dep not in data_sources:
                    data_sources[dep] = []
                data_sources[dep].append(dv)
        
        # Generate data source connections
        if data_sources:
            binding_code.append("# Data Source Connections")
            for source in data_sources.keys():
                binding_code.append(f"data_source.connect('{source}')")
            binding_code.append("")
        
        # Generate reactive expressions
        binding_code.append("# Reactive Expressions")
        for dv in dynamic_values:
            reactive_expr = self._convert_to_reactive_expression(dv)
            if reactive_expr:
                binding_code.append(f"{dv.name} = {reactive_expr}")
        
        binding_code.append("")
        return "\n".join(binding_code)
    
    def _convert_to_reactive_expression(self, dv: DynamicValueInfo) -> str:
        """Convert a dynamic value to a reactive expression"""
        expr = dv.expression
        
        # Handle different types of expressions
        if expr.startswith('data.'):
            # Direct data binding
            return f"reactive(lambda: {expr})"
        elif any(dep in expr for dep in ['sensor', 'temp', 'time']):
            # Sensor or time-based binding
            return f"reactive(lambda: {expr})"
        elif '{' in expr and '}' in expr:
            # F-string pattern - convert to reactive format
            import re
            variables = re.findall(r'\{([^}]+)\}', expr)
            if variables:
                # Handle f-string expressions like "f'Status: {system.status}'"
                if expr.startswith("f'") and expr.endswith("'"):
                    # Extract the f-string content
                    f_content = expr[2:-1]  # Remove f' and '
                    formatted_expr = f_content
                    for var in variables:
                        if '.' in var:
                            # Convert system.status to data.system.status
                            formatted_expr = formatted_expr.replace(f'{{{var}}}', f'{{data.{var}}}')
                        else:
                            # Simple variable
                            formatted_expr = formatted_expr.replace(f'{{{var}}}', f'{{data.{var}}}')
                    return f"reactive(lambda: f'{formatted_expr}')"
                else:
                    # Regular string with variables
                    formatted_expr = expr
                    for var in variables:
                        formatted_expr = formatted_expr.replace(f'{{{var}}}', f'{{data.{var}}}')
                    return f"reactive(lambda: f'{formatted_expr}')"
        elif expr in dv.dependencies:
            # Simple dependency reference
            return f"reactive(lambda: data.{expr})"
        
        # Default reactive wrapper
        return f"reactive(lambda: {expr})"
    
    def generate_data_flow_patterns(self, dynamic_values: List[DynamicValueInfo]) -> str:
        """Generate data flow and transformation patterns"""
        if not dynamic_values:
            return ""
        
        flow_code = []
        flow_code.append("# Data Flow Patterns")
        flow_code.append("")
        
        # Identify transformation patterns
        transformations = []
        for dv in dynamic_values:
            if any(op in dv.expression for op in ['+', '-', '*', '/', '%']):
                transformations.append(dv)
        
        if transformations:
            flow_code.append("# Data Transformations")
            for transform in transformations:
                flow_code.append(f"# Transform: {transform.expression}")
                flow_code.append(f"transform_{transform.name} = pipe(")
                flow_code.append(f"    source=data.{transform.dependencies[0] if transform.dependencies else 'input'},")
                flow_code.append(f"    transform=lambda x: {transform.expression.replace(transform.dependencies[0] if transform.dependencies else 'x', 'x')},")
                flow_code.append(f"    target='{transform.name}'")
                flow_code.append(")")
                flow_code.append("")
        
        # Generate computed properties
        computed_props = [dv for dv in dynamic_values if len(dv.dependencies) > 1]
        if computed_props:
            flow_code.append("# Computed Properties")
            for prop in computed_props:
                deps_str = ', '.join(f"data.{dep}" for dep in prop.dependencies)
                flow_code.append(f"computed_{prop.name} = computed(")
                flow_code.append(f"    dependencies=[{deps_str}],")
                flow_code.append(f"    compute=lambda {', '.join(prop.dependencies)}: {prop.expression}")
                flow_code.append(")")
                flow_code.append("")
        
        return "\n".join(flow_code)
    
    def generate_widget_dsl(self, widget: WidgetInfo) -> str:
        """Generate DSL code for a single widget"""
        widget_type = widget.widget_type or 'text'
        template = self.widget_templates.get(widget_type, self.widget_templates['text'])
        
        # Prepare template parameters
        params = {
            'x': widget.x,
            'y': widget.y,
            'width': widget.width or 100,
            'height': widget.height or 20,
            'z': widget.z_order or 0,
            'content': widget.properties.get('content', 'Text'),
            'text': widget.properties.get('text', widget.properties.get('content', 'Text')),
            'value': widget.properties.get('value', 0.5),
            'path': widget.properties.get('path', 'image.png'),
            'callback': widget.properties.get('callback', 'on_click'),
            'size': widget.properties.get('font_size', 12),
            'min_val': widget.properties.get('min_val', 0),
            'max_val': widget.properties.get('max_val', 100),
            'data': widget.properties.get('data', '[]'),
            'chart_type': widget.properties.get('chart_type', 'line'),
            'checked': widget.properties.get('checked', False),
            'label': widget.properties.get('label', 'Label'),
            'selected': widget.properties.get('selected', False),
            'group': widget.properties.get('group', 'group1'),
            'placeholder': widget.properties.get('placeholder', 'Enter text'),
            'items': widget.properties.get('items', '[]'),
            'columns': widget.properties.get('columns', 1)
        }
        
        try:
            widget_dsl = template.format(**params)
            return f"widget_{widget.name.lower().replace(' ', '_')} = {widget_dsl}"
        except KeyError as e:
            # Fallback for missing parameters
            return f"widget_{widget.name.lower().replace(' ', '_')} = Text('{widget.name}').position({widget.x}, {widget.y})"


class JSONToDSLConverter:
    """Specialized converter for JSON configuration files"""
    
    def __init__(self):
        self.dsl_converter = DSLConverter()
        self.validation_errors = []
        self.conversion_warnings = []
    
    def convert_file(self, json_file_path: str, output_file_path: str = None) -> str:
        """Convert JSON file to DSL file"""
        try:
            with open(json_file_path, 'r') as f:
                json_config = json.load(f)
        except json.JSONDecodeError as e:
            self.validation_errors.append(f"Invalid JSON in {json_file_path}: {e}")
            return ""
        except FileNotFoundError:
            self.validation_errors.append(f"File not found: {json_file_path}")
            return ""
        
        dsl_code = self.convert_config(json_config)
        
        if output_file_path:
            try:
                with open(output_file_path, 'w') as f:
                    f.write(dsl_code)
            except IOError as e:
                self.validation_errors.append(f"Could not write to {output_file_path}: {e}")
        
        return dsl_code
    
    def convert_string(self, json_string: str) -> str:
        """Convert JSON string to DSL string"""
        try:
            json_config = json.loads(json_string)
            return self.convert_config(json_config)
        except json.JSONDecodeError as e:
            self.validation_errors.append(f"Invalid JSON string: {e}")
            return ""
    
    def convert_config(self, json_config: Dict[str, Any]) -> str:
        """Convert JSON configuration to DSL with enhanced validation"""
        self.validation_errors.clear()
        self.conversion_warnings.clear()
        
        # Validate JSON structure
        if not self._validate_json_structure(json_config):
            return ""
        
        # Convert to DSL
        dsl_code = self.dsl_converter.convert_json_to_dsl(json_config)
        formatted_dsl = self.dsl_converter.format_dsl_code(dsl_code)
        
        # Validate generated DSL
        is_valid, errors = self.dsl_converter.validate_dsl_syntax(formatted_dsl)
        if not is_valid:
            self.validation_errors.extend(errors)
        
        return formatted_dsl
    
    def _validate_json_structure(self, json_config: Dict[str, Any]) -> bool:
        """Validate JSON configuration structure"""
        required_sections = ['canvas', 'widgets']
        optional_sections = ['animations', 'data_sources', 'reactive_bindings']
        
        # Check for required sections
        for section in required_sections:
            if section not in json_config:
                self.validation_errors.append(f"Missing required section: {section}")
        
        # Validate canvas configuration
        if 'canvas' in json_config:
            canvas = json_config['canvas']
            if not isinstance(canvas, dict):
                self.validation_errors.append("Canvas configuration must be an object")
            else:
                if 'width' not in canvas or 'height' not in canvas:
                    self.conversion_warnings.append("Canvas missing width or height, using defaults")
        
        # Validate widgets
        if 'widgets' in json_config:
            widgets = json_config['widgets']
            if not isinstance(widgets, list):
                self.validation_errors.append("Widgets must be an array")
            else:
                for i, widget in enumerate(widgets):
                    if not self._validate_widget(widget, i):
                        return False
        
        # Validate animations if present
        if 'animations' in json_config:
            animations = json_config['animations']
            if not isinstance(animations, list):
                self.validation_errors.append("Animations must be an array")
            else:
                for i, animation in enumerate(animations):
                    self._validate_animation(animation, i)
        
        return len(self.validation_errors) == 0
    
    def _validate_widget(self, widget: Dict[str, Any], index: int) -> bool:
        """Validate individual widget configuration"""
        required_fields = ['type']
        recommended_fields = ['position', 'size']
        
        # Check required fields
        for field in required_fields:
            if field not in widget:
                self.validation_errors.append(f"Widget {index}: Missing required field '{field}'")
                return False
        
        # Check widget type
        valid_types = ['text', 'progress', 'progressbar', 'image', 'button', 'label', 'gauge', 'chart', 'slider', 'checkbox', 'radio', 'textbox', 'list', 'grid']
        if widget['type'] not in valid_types:
            self.conversion_warnings.append(f"Widget {index}: Unknown widget type '{widget['type']}', will use fallback")
        
        # Check recommended fields
        for field in recommended_fields:
            if field not in widget:
                self.conversion_warnings.append(f"Widget {index}: Missing recommended field '{field}'")
        
        # Validate position
        if 'position' in widget:
            pos = widget['position']
            if not isinstance(pos, dict) or 'x' not in pos or 'y' not in pos:
                self.validation_errors.append(f"Widget {index}: Position must have x and y coordinates")
                return False
        
        # Validate size
        if 'size' in widget:
            size = widget['size']
            if not isinstance(size, dict) or 'width' not in size or 'height' not in size:
                self.validation_errors.append(f"Widget {index}: Size must have width and height")
                return False
        
        return True
    
    def _validate_animation(self, animation: Dict[str, Any], index: int) -> bool:
        """Validate individual animation configuration"""
        required_fields = ['type']
        valid_types = ['scroll', 'marquee', 'fade', 'fade_in', 'fade_out', 'slide', 'slide_in', 'slide_out', 'transition', 'bounce', 'pulse', 'rotate', 'scale', 'blink']
        
        # Check required fields
        for field in required_fields:
            if field not in animation:
                self.validation_errors.append(f"Animation {index}: Missing required field '{field}'")
                return False
        
        # Check animation type
        if animation['type'] not in valid_types:
            self.conversion_warnings.append(f"Animation {index}: Unknown animation type '{animation['type']}', will use fallback")
        
        return True
    
    def convert_legacy_json_patterns(self, json_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert legacy JSON patterns to modern DSL-compatible format"""
        converted = json_config.copy()
        
        # Convert legacy widget definitions
        if 'widgets' in converted:
            for widget in converted['widgets']:
                # Convert legacy position format
                if 'x' in widget and 'y' in widget:
                    widget['position'] = {'x': widget.pop('x'), 'y': widget.pop('y')}
                
                # Convert legacy size format
                if 'width' in widget and 'height' in widget:
                    widget['size'] = {'width': widget.pop('width'), 'height': widget.pop('height')}
                
                # Convert legacy content field
                if 'content' in widget and widget.get('type') == 'text':
                    widget['text'] = widget.pop('content')
                
                # Convert legacy value field for progress bars
                if 'value' in widget and widget.get('type') in ['progress', 'progressbar']:
                    if isinstance(widget['value'], str) and widget['value'].startswith('data.'):
                        # This is a reactive binding
                        widget['reactive_value'] = widget.pop('value')
        
        # Convert legacy animation definitions
        if 'animations' in converted:
            for animation in converted['animations']:
                # Convert legacy timing format
                if 'speed' in animation:
                    # Convert speed to duration (inverse relationship)
                    speed = animation.pop('speed')
                    if speed > 0:
                        animation['duration'] = int(1000 / speed)  # Convert to milliseconds
                
                # Convert legacy direction format
                if 'direction' in animation and animation['direction'] in ['left', 'right', 'up', 'down']:
                    # Already in correct format
                    pass
        
        return converted
    
    def batch_convert_directory(self, input_dir: str, output_dir: str, pattern: str = "*.json") -> List[str]:
        """Convert all JSON files in a directory to DSL files"""
        from pathlib import Path
        import glob
        
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        converted_files = []
        json_files = glob.glob(str(input_path / pattern))
        
        for json_file in json_files:
            json_path = Path(json_file)
            dsl_filename = json_path.stem + '.py'
            dsl_path = output_path / dsl_filename
            
            try:
                dsl_code = self.convert_file(str(json_path), str(dsl_path))
                if dsl_code:  # Only count successful conversions
                    converted_files.append(str(dsl_path))
            except Exception as e:
                self.validation_errors.append(f"Error converting {json_file}: {e}")
        
        return converted_files
    
    def get_conversion_report(self) -> Dict[str, Any]:
        """Get detailed conversion report"""
        return {
            'errors': self.validation_errors,
            'warnings': self.conversion_warnings,
            'error_count': len(self.validation_errors),
            'warning_count': len(self.conversion_warnings),
            'success': len(self.validation_errors) == 0
        }


if __name__ == "__main__":
    # Example usage
    converter = DSLConverter()
    
    # Example JSON configuration
    example_json = {
        "canvas": {
            "width": 128,
            "height": 64,
            "widgets": [
                {
                    "type": "text",
                    "content": "Hello World",
                    "position": {"x": 10, "y": 10},
                    "z_order": 1
                },
                {
                    "type": "progress",
                    "value": "data.cpu_usage",
                    "position": {"x": 10, "y": 30},
                    "size": {"width": 100, "height": 10},
                    "z_order": 2
                }
            ]
        },
        "animations": [
            {
                "type": "slide",
                "direction": "left",
                "duration": 1000,
                "sync_group": "startup"
            }
        ]
    }
    
    dsl_code = converter.convert_json_to_dsl(example_json)
    print("Generated DSL:")
    print(dsl_code)
    
    # Validate syntax
    is_valid, errors = converter.validate_dsl_syntax(dsl_code)
    print(f"\nSyntax valid: {is_valid}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}") 