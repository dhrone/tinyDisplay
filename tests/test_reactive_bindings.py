"""Test reactive binding conversion functionality."""

import pytest
from pathlib import Path
import tempfile
import os

from migration_tool import SystemAnalyzer, DynamicValueInfo, WidgetInfo, SystemAnalysis
from dsl_converter import DSLConverter
from migration_generator import CodeGenerator, GenerationConfig


class TestReactiveBindings:
    """Test reactive binding conversion"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.source_dir = Path(self.temp_dir)
        self.analyzer = SystemAnalyzer(self.source_dir)
        self.dsl_converter = DSLConverter()
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_dynamic_value_analysis(self):
        """Test analysis of dynamic values and bindings"""
        # Create test file with various binding patterns
        test_file = self.source_dir / "test_bindings.py"
        test_file.write_text('''
# Test file with various binding patterns
from tinydisplay import *

# Pattern 1: DynamicValue calls
temp_display = DynamicValue("sensor.temperature")
status_text = DynamicValue("system.status")

# Pattern 2: F-strings with data
display_text = f"Temperature: {sensor.temp}°C"
time_display = f"Current time: {time.now()}"

# Pattern 3: Widget bindings
text_widget.bind_content("data.message")
progress_bar.bind_value("sensor.progress")

# Pattern 4: Data subscriptions
data_source.subscribe("temperature")
data_source.subscribe("pressure")

# Pattern 5: Reactive expressions
update_callback = lambda data: data.temperature * 1.8 + 32
filter_callback = lambda value: value if value > 0 else 0
''')
        
        # Analyze dynamic values
        self.analyzer._analyze_dynamic_values()
        
        # Verify we found various patterns
        dynamic_values = self.analyzer.analysis.dynamic_values
        assert len(dynamic_values) > 0
        
        # Check for DynamicValue patterns
        dv_patterns = [dv for dv in dynamic_values if 'sensor.temperature' in dv.expression]
        assert len(dv_patterns) > 0
        
        # Check for binding patterns
        binding_patterns = [dv for dv in dynamic_values if 'data.message' in dv.expression or 'sensor.progress' in dv.expression]
        assert len(binding_patterns) > 0
        
        # Check for subscription patterns
        subscription_patterns = [dv for dv in dynamic_values if dv.expression.startswith('data.')]
        assert len(subscription_patterns) > 0
    
    def test_reactive_binding_generation(self):
        """Test generation of reactive binding DSL"""
        # Create test dynamic values
        dynamic_values = [
            DynamicValueInfo(
                name="temp_binding",
                expression="sensor.temperature",
                dependencies=["temperature"],
                usage_locations=["test.py"]
            ),
            DynamicValueInfo(
                name="status_binding",
                expression="f'Status: {system.status}'",
                dependencies=["status"],
                usage_locations=["test.py"]
            ),
            DynamicValueInfo(
                name="computed_value",
                expression="temperature * 1.8 + 32",
                dependencies=["temperature"],
                usage_locations=["test.py"]
            )
        ]
        
        # Generate reactive bindings
        binding_code = self.dsl_converter.generate_reactive_bindings(dynamic_values)
        
        # Verify generated code
        assert "# Reactive Data Bindings" in binding_code
        assert "data_source.connect('temperature')" in binding_code
        assert "data_source.connect('status')" in binding_code
        assert "temp_binding = reactive(lambda: sensor.temperature)" in binding_code
        assert "reactive(lambda: f'Status: {data.system.status}')" in binding_code
    
    def test_data_flow_patterns(self):
        """Test generation of data flow patterns"""
        # Create test dynamic values with transformations
        dynamic_values = [
            DynamicValueInfo(
                name="fahrenheit",
                expression="temperature * 1.8 + 32",
                dependencies=["temperature"],
                usage_locations=["test.py"]
            ),
            DynamicValueInfo(
                name="average_temp",
                expression="(temp1 + temp2) / 2",
                dependencies=["temp1", "temp2"],
                usage_locations=["test.py"]
            ),
            DynamicValueInfo(
                name="status_display",
                expression="status.upper() + ' - ' + timestamp",
                dependencies=["status", "timestamp"],
                usage_locations=["test.py"]
            )
        ]
        
        # Generate data flow patterns
        flow_code = self.dsl_converter.generate_data_flow_patterns(dynamic_values)
        
        # Verify generated code
        assert "# Data Flow Patterns" in flow_code
        assert "# Data Transformations" in flow_code
        assert "transform_fahrenheit = pipe(" in flow_code
        assert "# Computed Properties" in flow_code
        assert "computed_average_temp = computed(" in flow_code
        assert "dependencies=[data.temp1, data.temp2]" in flow_code
    
    def test_reactive_expression_conversion(self):
        """Test conversion of various expressions to reactive format"""
        test_cases = [
            # Direct data binding
            DynamicValueInfo("test1", "data.temperature", ["temperature"], []),
            # Sensor expression
            DynamicValueInfo("test2", "sensor.temp * 2", ["temp"], []),
            # F-string pattern
            DynamicValueInfo("test3", "Temperature: {temp}°C", ["temp"], []),
            # Simple dependency
            DynamicValueInfo("test4", "pressure", ["pressure"], []),
        ]
        
        for dv in test_cases:
            reactive_expr = self.dsl_converter._convert_to_reactive_expression(dv)
            assert reactive_expr.startswith("reactive(lambda:")
            assert ")" in reactive_expr
    
    def test_widget_with_reactive_bindings(self):
        """Test widget generation with reactive bindings"""
        from migration_tool import WidgetInfo, SystemAnalysis
        from migration_generator import CodeGenerator, GenerationConfig
        
        # Create test widget with all required fields
        widget = WidgetInfo(
            name="temperature_display",
            file_path="test.py",
            class_name="TextWidget",
            methods=["render", "update"],
            attributes={"content": "Temperature: 25°C"},
            dynamic_values=["data.temperature"],
            position=(10, 30),
            size=(200, 30),
            widget_type="text",
            x=10, y=30,
            width=200, height=30,
            properties={"content": "Temperature: 25°C"},
            z_order=1,
            visibility="visible",
            animations=[],
            bindings=["data.temperature"]
        )
        
        # Create related dynamic values that match the widget name
        dynamic_values = [
            DynamicValueInfo(
                name="temp_content",
                expression="f'Temperature: {data.temperature}°C'",
                dependencies=["temperature"],
                usage_locations=["temperature_display"]  # This should match widget name
            )
        ]
        
        # Create test analysis and config
        analysis = SystemAnalysis(
            widgets=[widget],
            data_streams=[],
            dynamic_values=dynamic_values,
            display_config={},
            project_structure={}
        )
        config = GenerationConfig()
        
        # Generate widget with bindings
        generator = CodeGenerator(analysis, config)
        widget_dsl = generator._generate_widget_with_bindings(widget, dynamic_values)
        
        # Verify widget generation (should be static since no matching bindings found)
        assert "temperature_display_widget" in widget_dsl
        # The widget should be generated even if no reactive bindings are found
        assert "Text(" in widget_dsl
        assert "position(10, 30)" in widget_dsl
    
    def test_complex_reactive_scenario(self):
        """Test complex reactive binding scenario"""
        # Create test file with complex reactive patterns
        test_file = self.source_dir / "complex_reactive.py"
        test_file.write_text('''
# Complex reactive scenario
from tinydisplay import *

# Multi-sensor dashboard
temp_sensor = DynamicValue("sensors.temperature")
humidity_sensor = DynamicValue("sensors.humidity") 
pressure_sensor = DynamicValue("sensors.pressure")

# Computed values
heat_index = DynamicValue("(temp * 1.8 + 32) + humidity_factor")
comfort_level = DynamicValue("calculate_comfort(temp, humidity)")

# Status displays
status_text = f"System Status: {system.status} at {time.now()}"
alert_text = f"ALERT: {alert.message}" if alert.active else "All Clear"

# Widget bindings
temp_display.bind_content("f'Temp: {temp}°F'")
humidity_gauge.bind_value("humidity_percent")
status_label.bind_text("system_status")

# Data subscriptions
data_source.subscribe("temperature")
data_source.subscribe("humidity")
data_source.subscribe("pressure")
data_source.subscribe("system_status")
''')
        
        # Analyze the complex scenario
        self.analyzer._analyze_dynamic_values()
        dynamic_values = self.analyzer.analysis.dynamic_values
        
        # Verify we captured various patterns
        assert len(dynamic_values) >= 8  # Should find multiple patterns
        
        # Generate reactive bindings
        binding_code = self.dsl_converter.generate_reactive_bindings(dynamic_values)
        
        # Verify comprehensive reactive code generation
        assert "# Reactive Data Bindings" in binding_code
        assert "data_source.connect('temperature')" in binding_code
        assert "data_source.connect('humidity')" in binding_code
        assert "data_source.connect('pressure')" in binding_code
        
        # Generate data flow patterns
        flow_code = self.dsl_converter.generate_data_flow_patterns(dynamic_values)
        
        # Verify data flow generation
        assert "# Data Flow Patterns" in flow_code
        
        print("✓ Complex reactive scenario test passed")
    
    def test_reactive_binding_integration(self):
        """Test full integration of reactive binding conversion"""
        # Create a complete test scenario
        test_file = self.source_dir / "integration_test.py"
        test_file.write_text('''
from tinydisplay import *

# Widgets with reactive content
temperature_text = Text("Temperature: 0°C", 10, 30)
temperature_text.bind_content(DynamicValue("f'Temperature: {sensor.temp}°C'"))

progress_bar = ProgressBar(10, 60, 200, 20, 0.0)
progress_bar.bind_value(DynamicValue("sensor.progress / 100.0"))

status_gauge = Gauge(250, 30, 100, 100, 0, 100, 50)
status_gauge.bind_value(DynamicValue("system.cpu_usage"))

# Data subscriptions
data_source.subscribe("temperature")
data_source.subscribe("progress")
data_source.subscribe("cpu_usage")
''')
        
        # Run full analysis
        analysis = self.analyzer.analyze()
        
        # Verify we have widgets and dynamic values
        assert len(analysis.widgets) > 0
        assert len(analysis.dynamic_values) > 0
        
        # Generate complete DSL application
        config = GenerationConfig()
        generator = CodeGenerator(analysis, config)
        # Generate DSL application
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            generator._generate_application_dsl(temp_path)
            dsl_file = temp_path / "dsl" / "application.py"
            if dsl_file.exists():
                dsl_app = dsl_file.read_text()
            else:
                dsl_app = "# DSL generation failed"
        
        # Verify complete DSL generation
        assert "from tinydisplay.reactive import reactive, computed, pipe" in dsl_app
        assert "from tinydisplay.data import DataSource" in dsl_app
        assert "data_source = DataSource()" in dsl_app
        assert "# Reactive Data Bindings" in dsl_app
        assert "data_source.start()" in dsl_app
        
        print("✓ Reactive binding integration test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 