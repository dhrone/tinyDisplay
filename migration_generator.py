#!/usr/bin/env python3
"""
tinyDisplay Code Generator

Generates new reactive architecture code based on system analysis.
Creates the new Ring Buffer + SQLite + asteval + RxPY system.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from migration_tool import SystemAnalysis, WidgetInfo, DataStreamInfo, DynamicValueInfo

@dataclass
class GenerationConfig:
    """Configuration for code generation"""
    target_fps: int = 60
    max_memory_mb: int = 200
    ring_buffer_default_size: int = 1000
    speculation_workers: int = 3
    enable_predictive_progress: bool = True

class CodeGenerator:
    """Generates new architecture code from analysis"""
    
    def __init__(self, analysis: SystemAnalysis, config: GenerationConfig):
        self.analysis = analysis
        self.config = config
        self.templates = CodeTemplates()
    
    def generate_new_system(self, target_dir: str):
        """Generate complete new system"""
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        
        print(f"🏗️  Generating new tinyDisplay architecture in {target_path}")
        
        # Create directory structure
        self._create_directory_structure(target_path)
        
        # Generate core architecture files
        self._generate_data_layer(target_path)
        self._generate_dynamic_values_engine(target_path)
        self._generate_widget_system(target_path)
        self._generate_rendering_pipeline(target_path)
        
        # Generate migrated content
        self._generate_migrated_widgets(target_path)
        self._generate_data_configuration(target_path)
        self._generate_application_dsl(target_path)
        
        # Generate supporting files
        self._generate_requirements(target_path)
        self._generate_main_application(target_path)
        self._generate_tests(target_path)
        
        print("✅ Code generation complete!")
    
    def _create_directory_structure(self, target_path: Path):
        """Create the new project directory structure"""
        directories = [
            "data",
            "reactive", 
            "widgets",
            "rendering",
            "dsl",
            "tests",
            "examples",
            "config"
        ]
        
        for dir_name in directories:
            (target_path / dir_name).mkdir(exist_ok=True)
            # Create __init__.py files
            (target_path / dir_name / "__init__.py").touch()
    
    def _generate_data_layer(self, target_path: Path):
        """Generate data management layer"""
        
        # Generate ring buffer implementation
        ring_buffer_code = self.templates.generate_ring_buffer()
        (target_path / "data" / "ring_buffer.py").write_text(ring_buffer_code)
        
        # Generate data manager
        data_streams = [ds.key for ds in self.analysis.data_streams]
        data_manager_code = self.templates.generate_data_manager(data_streams)
        (target_path / "data" / "data_manager.py").write_text(data_manager_code)
        
        # Generate SQLite storage
        sqlite_code = self.templates.generate_sqlite_storage()
        (target_path / "data" / "sqlite_storage.py").write_text(sqlite_code)
        
        print("   ✓ Generated data layer")
    
    def _generate_dynamic_values_engine(self, target_path: Path):
        """Generate dynamic values engine with asteval + RxPY"""
        
        # Extract all expressions from analysis
        expressions = [dv.expression for dv in self.analysis.dynamic_values]
        
        # Generate dynamic values engine
        dv_engine_code = self.templates.generate_dynamic_values_engine(expressions)
        (target_path / "reactive" / "dynamic_values.py").write_text(dv_engine_code)
        
        # Generate dependency tracker
        dependency_code = self.templates.generate_dependency_tracker()
        (target_path / "reactive" / "dependency_tracker.py").write_text(dependency_code)
        
        print("   ✓ Generated reactive engine")
    
    def _generate_widget_system(self, target_path: Path):
        """Generate new reactive widget system"""
        
        # Generate base widget classes
        widget_base_code = self.templates.generate_widget_base()
        (target_path / "widgets" / "base.py").write_text(widget_base_code)
        
        # Generate widget manager
        widget_manager_code = self.templates.generate_widget_manager()
        (target_path / "widgets" / "manager.py").write_text(widget_manager_code)
        
        print("   ✓ Generated widget system")
    
    def _generate_rendering_pipeline(self, target_path: Path):
        """Generate rendering pipeline with speculative rendering"""
        
        # Generate render controller
        render_controller_code = self.templates.generate_render_controller(self.config.target_fps)
        (target_path / "rendering" / "controller.py").write_text(render_controller_code)
        
        # Generate speculative renderer
        speculative_code = self.templates.generate_speculative_renderer(self.config.speculation_workers)
        (target_path / "rendering" / "speculative.py").write_text(speculative_code)
        
        # Generate partial screen updater
        partial_update_code = self.templates.generate_partial_updater()
        (target_path / "rendering" / "partial_update.py").write_text(partial_update_code)
        
        print("   ✓ Generated rendering pipeline")
    
    def _generate_migrated_widgets(self, target_path: Path):
        """Generate widgets based on analysis"""
        
        for widget_info in self.analysis.widgets:
            widget_code = self.templates.generate_migrated_widget(widget_info)
            filename = f"{widget_info.name}_widget.py"
            (target_path / "widgets" / filename).write_text(widget_code)
        
        print(f"   ✓ Generated {len(self.analysis.widgets)} migrated widgets")
    
    def _generate_data_configuration(self, target_path: Path):
        """Generate data source configuration"""
        
        config_data = {
            "data_streams": [
                {
                    "key": ds.key,
                    "buffer_size": self.config.ring_buffer_default_size,
                    "data_type": ds.data_type,
                    "is_time_series": ds.is_time_series
                }
                for ds in self.analysis.data_streams
            ],
            "memory_limits": {
                "max_total_mb": self.config.max_memory_mb,
                "ring_buffer_mb": int(self.config.max_memory_mb * 0.6),
                "cache_mb": int(self.config.max_memory_mb * 0.2)
            }
        }
        
        config_code = self.templates.generate_data_config(config_data)
        (target_path / "config" / "data_config.py").write_text(config_code)
        
        print("   ✓ Generated data configuration")
    
    def _generate_application_dsl(self, target_path: Path):
        """Generate application DSL configuration"""
        
        # Create DSL configuration based on analysis
        dsl_config = {
            "dynamic_values": {},
            "widgets": {},
            "display": self.analysis.display_config
        }
        
        # Add dynamic values from analysis
        for i, dv in enumerate(self.analysis.dynamic_values):
            dsl_config["dynamic_values"][f"dv_{i}"] = {
                "expression": dv.expression,
                "dependencies": dv.dependencies
            }
        
        # Add widgets from analysis
        for widget in self.analysis.widgets:
            dsl_config["widgets"][widget.name] = {
                "type": widget.name,
                "position": widget.position or [0, 0],
                "size": widget.size or [100, 20],
                "properties": widget.attributes
            }
        
        dsl_code = self.templates.generate_dsl_config(dsl_config)
        (target_path / "dsl" / "application.py").write_text(dsl_code)
        
        print("   ✓ Generated application DSL")
    
    def _generate_requirements(self, target_path: Path):
        """Generate requirements.txt"""
        
        requirements = [
            "asteval>=0.9.28",
            "rxpy>=4.0.4", 
            "numpy>=1.21.0",
            "scipy>=1.7.0",
            "luma.oled>=3.8.1",
            "luma.lcd>=2.10.0",
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0"
        ]
        
        (target_path / "requirements.txt").write_text("\n".join(requirements))
        print("   ✓ Generated requirements.txt")
    
    def _generate_main_application(self, target_path: Path):
        """Generate main application entry point"""
        
        main_code = self.templates.generate_main_application(
            self.analysis.widgets,
            self.analysis.data_streams
        )
        (target_path / "main.py").write_text(main_code)
        
        print("   ✓ Generated main application")
    
    def _generate_tests(self, target_path: Path):
        """Generate test files"""
        
        # Generate test for each major component
        test_files = [
            ("test_data_manager.py", self.templates.generate_data_manager_tests()),
            ("test_dynamic_values.py", self.templates.generate_dynamic_values_tests()),
            ("test_widgets.py", self.templates.generate_widget_tests(self.analysis.widgets)),
            ("test_rendering.py", self.templates.generate_rendering_tests())
        ]
        
        for filename, content in test_files:
            (target_path / "tests" / filename).write_text(content)
        
        print("   ✓ Generated test suite")

class CodeTemplates:
    """Templates for generating code"""
    
    def generate_ring_buffer(self) -> str:
        return '''"""
Ring Buffer implementation for high-performance time-series data storage.
"""

import time
from typing import Any, List, Optional, TypeVar, Generic
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class TimestampedValue(Generic[T]):
    """Value with timestamp"""
    timestamp: float
    value: T

class RingBuffer(Generic[T]):
    """High-performance ring buffer for time-series data"""
    
    def __init__(self, size: int):
        self.size = size
        self.buffer: List[Optional[TimestampedValue[T]]] = [None] * size
        self.head = 0
        self.count = 0
        self._lock = threading.RLock()
    
    def append(self, item: TimestampedValue[T]) -> None:
        """Add new value, evicting oldest if full"""
        with self._lock:
            self.buffer[self.head] = item
            self.head = (self.head + 1) % self.size
            if self.count < self.size:
                self.count += 1
    
    def get_latest(self, n: int = 1) -> List[TimestampedValue[T]]:
        """Get most recent N values"""
        with self._lock:
            if self.count == 0:
                return []
            
            result = []
            for i in range(min(n, self.count)):
                idx = (self.head - 1 - i) % self.size
                if self.buffer[idx] is not None:
                    result.append(self.buffer[idx])
            
            return result
    
    def get_range(self, start_time: float, end_time: float) -> List[TimestampedValue[T]]:
        """Get values within time range"""
        with self._lock:
            result = []
            for i in range(self.count):
                idx = (self.head - 1 - i) % self.size
                item = self.buffer[idx]
                if item and start_time <= item.timestamp <= end_time:
                    result.append(item)
            
            return sorted(result, key=lambda x: x.timestamp)
    
    def is_full(self) -> bool:
        """Check if buffer is full"""
        return self.count == self.size
    
    def clear(self) -> None:
        """Clear all data"""
        with self._lock:
            self.buffer = [None] * self.size
            self.head = 0
            self.count = 0

import threading
'''
    
    def generate_data_manager(self, data_streams: List[str]) -> str:
        streams_init = "\\n".join([
            f'        self.register_data_stream("{stream}", DataStreamConfig())'
            for stream in data_streams
        ])
        
        return f'''"""
Data Manager - Central coordination for data streams and storage.
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from collections import defaultdict

from .ring_buffer import RingBuffer, TimestampedValue
from .sqlite_storage import SQLiteStorage

@dataclass
class DataStreamConfig:
    """Configuration for a data stream"""
    buffer_size: int = 1000
    data_type: type = Any
    persistence: bool = True
    compression: bool = False

class DataManager:
    """Central data management system"""
    
    def __init__(self):
        self._ring_buffers: Dict[str, RingBuffer] = {{}}
        self._sqlite_store = SQLiteStorage()
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.RLock()
        
        # Initialize data streams from analysis
{streams_init}
    
    def register_data_stream(self, stream_id: str, config: DataStreamConfig):
        """Register a new data stream"""
        with self._lock:
            self._ring_buffers[stream_id] = RingBuffer(config.buffer_size)
            
            if config.persistence:
                self._sqlite_store.create_stream_table(stream_id, config.data_type)
    
    def update_data(self, stream_id: str, value: Any, timestamp: Optional[float] = None):
        """Update data in stream"""
        if timestamp is None:
            timestamp = time.time()
        
        timestamped_value = TimestampedValue(timestamp, value)
        
        with self._lock:
            # Store in ring buffer
            if stream_id in self._ring_buffers:
                self._ring_buffers[stream_id].append(timestamped_value)
            
            # Store in SQLite (background)
            self._sqlite_store.store_value_async(stream_id, timestamped_value)
            
            # Notify subscribers
            for callback in self._subscribers[stream_id]:
                try:
                    callback(stream_id, value)
                except Exception as e:
                    print(f"Error in subscriber callback: {{e}}")
    
    def get_current_value(self, stream_id: str) -> Any:
        """Get latest value for stream"""
        with self._lock:
            if stream_id in self._ring_buffers:
                latest = self._ring_buffers[stream_id].get_latest(1)
                if latest:
                    return latest[0].value
            return None
    
    def get_history(self, stream_id: str, count: int = 10) -> List[TimestampedValue]:
        """Get recent history for stream"""
        with self._lock:
            if stream_id in self._ring_buffers:
                return self._ring_buffers[stream_id].get_latest(count)
            return []
    
    def subscribe(self, stream_id: str, callback: Callable[[str, Any], None]) -> str:
        """Subscribe to data updates"""
        subscription_id = f"{{stream_id}}_{{len(self._subscribers[stream_id])}}"
        self._subscribers[stream_id].append(callback)
        return subscription_id
    
    def unsubscribe(self, stream_id: str, callback: Callable):
        """Unsubscribe from data updates"""
        if stream_id in self._subscribers:
            try:
                self._subscribers[stream_id].remove(callback)
            except ValueError:
                pass
    
    def get_ring_buffer(self, stream_id: str) -> Optional[RingBuffer]:
        """Get ring buffer for stream"""
        return self._ring_buffers.get(stream_id)
'''

    def generate_dynamic_values_engine(self, expressions: List[str]) -> str:
        return '''"""
Dynamic Values Engine with asteval and RxPY integration.
"""

import ast
import time
import asteval
from typing import Dict, Any, Set, List, Optional, Callable
from dataclasses import dataclass
import networkx as nx
from rx import Observable
from rx.subject import Subject

@dataclass
class DynamicValueInfo:
    """Information about a dynamic value"""
    name: str
    expression: str
    dependencies: Set[str]
    compiled_expr: Optional[asteval.Interpreter]
    subscribers: Set[str]
    last_result: Any = None
    last_update: float = 0

class DynamicValuesEngine:
    """Engine for evaluating dynamic expressions with dependency tracking"""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.dynamic_values: Dict[str, DynamicValueInfo] = {}
        self.dependency_graph = nx.DiGraph()
        self.observables: Dict[str, Subject] = {}
        self.expression_cache: Dict[str, asteval.Interpreter] = {}
    
    def create_dynamic_value(self, name: str, expression: str) -> str:
        """Create new dynamic value from expression"""
        
        # Extract dependencies
        dependencies = self._extract_dependencies(expression)
        
        # Create dynamic value info
        dv_info = DynamicValueInfo(
            name=name,
            expression=expression,
            dependencies=dependencies,
            compiled_expr=None,
            subscribers=set()
        )
        
        self.dynamic_values[name] = dv_info
        self.observables[name] = Subject()
        
        # Add to dependency graph
        self.dependency_graph.add_node(name)
        for dep in dependencies:
            self.dependency_graph.add_edge(dep, name)
        
        # Subscribe to data dependencies
        for dep in dependencies:
            self.data_manager.subscribe(dep, self._on_dependency_change)
        
        return name
    
    def get_value(self, name: str, timestamp: Optional[float] = None) -> Any:
        """Get current value of dynamic expression"""
        if name not in self.dynamic_values:
            return None
        
        dv_info = self.dynamic_values[name]
        
        # Check if we need to recompute
        if self._needs_recomputation(dv_info, timestamp):
            result = self._evaluate_expression(dv_info, timestamp)
            dv_info.last_result = result
            dv_info.last_update = timestamp or time.time()
            
            # Notify subscribers
            self.observables[name].on_next(result)
            
            return result
        
        return dv_info.last_result
    
    def subscribe(self, name: str, widget_id: str) -> Observable:
        """Subscribe to dynamic value changes"""
        if name in self.dynamic_values:
            self.dynamic_values[name].subscribers.add(widget_id)
        
        return self.observables.get(name, Subject())
    
    def unsubscribe(self, name: str, widget_id: str):
        """Unsubscribe from dynamic value"""
        if name in self.dynamic_values:
            self.dynamic_values[name].subscribers.discard(widget_id)
    
    def _extract_dependencies(self, expression: str) -> Set[str]:
        """Extract data dependencies from expression using AST"""
        dependencies = set()
        
        try:
            tree = ast.parse(expression, mode='eval')
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    # Handle sensor.temperature, weather.humidity, etc.
                    if isinstance(node.value, ast.Name):
                        dep = f"{node.value.id}.{node.attr}"
                        dependencies.add(dep)
                elif isinstance(node, ast.Subscript):
                    # Handle sensor['temperature'] if key is literal
                    if isinstance(node.value, ast.Name) and isinstance(node.slice, ast.Constant):
                        dep = f"{node.value.id}.{node.slice.value}"
                        dependencies.add(dep)
        
        except SyntaxError:
            # Fallback to simple pattern matching
            import re
            dot_refs = re.findall(r'(\\w+\\.\\w+)', expression)
            dependencies.update(dot_refs)
        
        return dependencies
    
    def _needs_recomputation(self, dv_info: DynamicValueInfo, timestamp: Optional[float]) -> bool:
        """Check if dynamic value needs recomputation"""
        if dv_info.last_result is None:
            return True
        
        # Check if any dependencies have changed
        for dep in dv_info.dependencies:
            latest_data = self.data_manager.get_current_value(dep)
            if latest_data != dv_info.last_result:  # Simplified check
                return True
        
        return False
    
    def _evaluate_expression(self, dv_info: DynamicValueInfo, timestamp: Optional[float]) -> Any:
        """Evaluate dynamic expression"""
        
        # Get or create compiled expression
        if dv_info.compiled_expr is None:
            dv_info.compiled_expr = asteval.Interpreter()
        
        # Build context with current data
        context = {}
        for dep in dv_info.dependencies:
            value = self.data_manager.get_current_value(dep)
            
            # Handle dot notation (sensor.temperature -> context['sensor']['temperature'])
            if '.' in dep:
                parts = dep.split('.')
                if parts[0] not in context:
                    context[parts[0]] = {}
                context[parts[0]][parts[1]] = value
            else:
                context[dep] = value
        
        # Add timestamp if provided
        if timestamp:
            context['timestamp'] = timestamp
            context['time'] = timestamp
        
        try:
            return dv_info.compiled_expr.eval(dv_info.expression, context)
        except Exception as e:
            print(f"Error evaluating expression '{dv_info.expression}': {e}")
            return None
    
    def _on_dependency_change(self, stream_id: str, new_value: Any):
        """Handle dependency data change"""
        
        # Find all dynamic values that depend on this stream
        affected_values = []
        for name, dv_info in self.dynamic_values.items():
            if stream_id in dv_info.dependencies:
                affected_values.append(name)
        
        # Invalidate and potentially recompute affected values
        for name in affected_values:
            if self.dynamic_values[name].subscribers:  # Only if someone is listening
                self.get_value(name)  # This will trigger recomputation
'''

    def generate_widget_base(self) -> str:
        return '''"""
Base widget classes for the new reactive architecture.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Set, Optional, Tuple
from dataclasses import dataclass

@dataclass
class RenderResult:
    """Result of widget rendering"""
    content: Any
    position: Tuple[int, int]
    size: Tuple[int, int]
    changed: bool = True
    render_time: float = 0

@dataclass
class RenderContext:
    """Context provided to widgets during rendering"""
    timestamp: float
    data_manager: Any
    dynamic_values_engine: Any
    display_config: Dict[str, Any]

class ReactiveWidget(ABC):
    """Base class for reactive widgets"""
    
    def __init__(self, widget_id: str, config: Dict[str, Any]):
        self.widget_id = widget_id
        self.config = config
        self.subscriptions: Set[str] = set()
        self.is_dirty = True
        self.last_render_time = 0
        self.render_cache: Optional[RenderResult] = None
        self.position = config.get('position', (0, 0))
        self.size = config.get('size', (100, 20))
        self.visible = config.get('visible', True)
    
    def subscribe_to_data(self, data_path: str) -> None:
        """Subscribe to data changes"""
        if data_path not in self.subscriptions:
            self.subscriptions.add(data_path)
    
    def subscribe_to_dynamic_value(self, dv_name: str) -> None:
        """Subscribe to dynamic value changes"""
        if dv_name not in self.subscriptions:
            self.subscriptions.add(f"dv:{dv_name}")
    
    def invalidate(self) -> None:
        """Mark widget as needing re-render"""
        self.is_dirty = True
        self.render_cache = None
    
    def is_visible(self) -> bool:
        """Check if widget is visible"""
        return self.visible
    
    @abstractmethod
    def render(self, context: RenderContext, timestamp: float) -> RenderResult:
        """Render widget content"""
        pass
    
    def cleanup(self) -> None:
        """Cleanup subscriptions"""
        self.subscriptions.clear()

class TextWidget(ReactiveWidget):
    """Text display widget"""
    
    def __init__(self, widget_id: str, config: Dict[str, Any]):
        super().__init__(widget_id, config)
        self.text_source = config.get('text_source')
        self.font_size = config.get('font_size', 12)
        self.color = config.get('color', 'white')
        
        if self.text_source:
            self.subscribe_to_dynamic_value(self.text_source)
    
    def render(self, context: RenderContext, timestamp: float) -> RenderResult:
        """Render text widget"""
        
        # Get text from dynamic value
        text = ""
        if self.text_source:
            text = context.dynamic_values_engine.get_value(self.text_source, timestamp)
        
        result = RenderResult(
            content={'text': str(text), 'font_size': self.font_size, 'color': self.color},
            position=self.position,
            size=self.size,
            changed=self.is_dirty,
            render_time=timestamp
        )
        
        self.is_dirty = False
        self.last_render_time = timestamp
        self.render_cache = result
        
        return result

class ImageWidget(ReactiveWidget):
    """Image display widget"""
    
    def __init__(self, widget_id: str, config: Dict[str, Any]):
        super().__init__(widget_id, config)
        self.image_source = config.get('image_source')
        
        if self.image_source:
            self.subscribe_to_dynamic_value(self.image_source)
    
    def render(self, context: RenderContext, timestamp: float) -> RenderResult:
        """Render image widget"""
        
        # Get image path from dynamic value
        image_path = ""
        if self.image_source:
            image_path = context.dynamic_values_engine.get_value(self.image_source, timestamp)
        
        result = RenderResult(
            content={'image_path': str(image_path)},
            position=self.position,
            size=self.size,
            changed=self.is_dirty,
            render_time=timestamp
        )
        
        self.is_dirty = False
        self.last_render_time = timestamp
        self.render_cache = result
        
        return result
'''

    def generate_migrated_widget(self, widget_info: WidgetInfo) -> str:
        # Determine widget type based on analysis
        if 'text' in widget_info.name.lower():
            base_class = "TextWidget"
        elif 'image' in widget_info.name.lower():
            base_class = "ImageWidget"
        else:
            base_class = "ReactiveWidget"
        
        # Generate dynamic value subscriptions
        subscriptions = ""
        for dv in widget_info.dynamic_values:
            subscriptions += f'        self.subscribe_to_dynamic_value("{dv}")\\n'
        
        return f'''"""
Migrated {widget_info.class_name} - Generated from existing widget
Original file: {widget_info.file_path}
"""

from .base import {base_class}, RenderContext, RenderResult

class {widget_info.class_name}({base_class}):
    """Migrated {widget_info.name} widget"""
    
    def __init__(self, widget_id: str, config: dict):
        super().__init__(widget_id, config)
        
        # Migrated attributes
{self._generate_attributes(widget_info.attributes)}
        
        # Set up subscriptions
{subscriptions}
    
    def render(self, context: RenderContext, timestamp: float) -> RenderResult:
        """Render migrated widget"""
        
        # TODO: Implement specific rendering logic based on original widget
        # This is a template - customize based on original widget behavior
        
        content = {{
            'type': '{widget_info.name}',
            'timestamp': timestamp
        }}
        
        result = RenderResult(
            content=content,
            position=self.position,
            size=self.size,
            changed=self.is_dirty,
            render_time=timestamp
        )
        
        self.is_dirty = False
        self.last_render_time = timestamp
        
        return result
'''

    def _generate_attributes(self, attributes: Dict[str, Any]) -> str:
        lines = []
        for name, value in attributes.items():
            if isinstance(value, str):
                lines.append(f'        self.{name} = "{value}"')
            else:
                lines.append(f'        self.{name} = {value}')
        return "\\n".join(lines) if lines else "        pass"

    def generate_main_application(self, widgets: List[WidgetInfo], data_streams: List[DataStreamInfo]) -> str:
        return '''"""
Main application entry point for new tinyDisplay architecture.
"""

import time
import asyncio
from pathlib import Path

from data.data_manager import DataManager
from reactive.dynamic_values import DynamicValuesEngine
from widgets.manager import WidgetManager
from rendering.controller import RenderController
from rendering.speculative import SpeculativeRenderer
from dsl.application import load_application_config

class TinyDisplayApp:
    """Main tinyDisplay application"""
    
    def __init__(self, config_path: str = "dsl/application.yaml"):
        self.config_path = config_path
        
        # Initialize core components
        self.data_manager = DataManager()
        self.dynamic_values_engine = DynamicValuesEngine(self.data_manager)
        self.widget_manager = WidgetManager(self.dynamic_values_engine)
        self.render_controller = RenderController(target_fps=60)
        self.speculative_renderer = SpeculativeRenderer(num_workers=3)
        
        # Load application configuration
        self.config = load_application_config(config_path)
        
    async def initialize(self):
        """Initialize the application"""
        print("🚀 Initializing tinyDisplay...")
        
        # Set up data streams
        await self._setup_data_streams()
        
        # Create dynamic values
        await self._setup_dynamic_values()
        
        # Create widgets
        await self._setup_widgets()
        
        # Start background services
        self.speculative_renderer.start_background_rendering()
        
        print("✅ tinyDisplay initialized successfully")
    
    async def run(self):
        """Run the main application loop"""
        print("🎬 Starting tinyDisplay main loop...")
        
        try:
            while True:
                current_time = time.time()
                
                # Process frame
                if self.render_controller.should_render_frame(current_time):
                    render_results = self.render_controller.process_frame(current_time)
                    
                    # Send to display hardware
                    await self._update_display(render_results)
                
                # Small sleep to prevent CPU spinning
                await asyncio.sleep(0.001)  # 1ms
                
        except KeyboardInterrupt:
            print("\\n🛑 Shutting down tinyDisplay...")
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the application"""
        self.speculative_renderer.stop()
        print("👋 tinyDisplay shutdown complete")
    
    async def _setup_data_streams(self):
        """Set up data streams from configuration"""
        for stream_config in self.config.get('data_streams', []):
            self.data_manager.register_data_stream(
                stream_config['key'],
                stream_config
            )
    
    async def _setup_dynamic_values(self):
        """Set up dynamic values from configuration"""
        for name, dv_config in self.config.get('dynamic_values', {}).items():
            self.dynamic_values_engine.create_dynamic_value(
                name,
                dv_config['expression']
            )
    
    async def _setup_widgets(self):
        """Set up widgets from configuration"""
        for name, widget_config in self.config.get('widgets', {}).items():
            self.widget_manager.create_widget(
                widget_id=name,
                widget_type=widget_config['type'],
                config=widget_config
            )
    
    async def _update_display(self, render_results):
        """Update physical display with render results"""
        # TODO: Integrate with luma.oled/luma.lcd
        # This is where you'd send the rendered content to the actual display
        pass

async def main():
    """Main entry point"""
    app = TinyDisplayApp()
    
    await app.initialize()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
'''

    # Additional template methods would go here...
    def generate_sqlite_storage(self) -> str:
        return "# SQLite storage implementation\\n# TODO: Implement SQLite backend"
    
    def generate_widget_manager(self) -> str:
        return "# Widget manager implementation\\n# TODO: Implement widget lifecycle management"
    
    def generate_render_controller(self, target_fps: int) -> str:
        return f"# Render controller implementation\\n# Target FPS: {target_fps}\\n# TODO: Implement frame scheduling"
    
    def generate_speculative_renderer(self, workers: int) -> str:
        return f"# Speculative renderer implementation\\n# Workers: {workers}\\n# TODO: Implement background rendering"
    
    def generate_partial_updater(self) -> str:
        return "# Partial screen updater implementation\\n# TODO: Implement dirty region tracking"
    
    def generate_dependency_tracker(self) -> str:
        return "# Dependency tracker implementation\\n# TODO: Implement RxPY integration"
    
    def generate_dsl_config(self, config: Dict[str, Any]) -> str:
        return f"# Application DSL configuration\\n# Config: {config}\\n# TODO: Implement DSL parser"
    
    def generate_data_config(self, config: Dict[str, Any]) -> str:
        return f"# Data configuration\\n# Config: {config}\\n# TODO: Implement data stream setup"
    
    def generate_data_manager_tests(self) -> str:
        return "# Data manager tests\\n# TODO: Implement test cases"
    
    def generate_dynamic_values_tests(self) -> str:
        return "# Dynamic values tests\\n# TODO: Implement test cases"
    
    def generate_widget_tests(self, widgets: List[WidgetInfo]) -> str:
        return f"# Widget tests\\n# Widgets: {len(widgets)}\\n# TODO: Implement test cases"
    
    def generate_rendering_tests(self) -> str:
        return "# Rendering tests\\n# TODO: Implement test cases" 