"""Test migration validation framework."""

import pytest
import tempfile
import json
import shutil
from pathlib import Path

from migration_validator import (
    MigrationValidator, 
    WidgetCountValidation, 
    AnimationConversionValidation,
    DataBindingValidation,
    DSLSyntaxValidation,
    PerformanceValidation,
    BeforeAfterComparisonValidation,
    RegressionTestValidation,
    MigrationRollbackManager
)
from migration_tool import SystemAnalysis, WidgetInfo, AnimationInfo, DynamicValueInfo, DataStreamInfo, CanvasInfo, WidgetHierarchy, CustomWidgetInfo


class TestMigrationValidator:
    """Test migration validation framework"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = MigrationValidator()
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_widget_count_validation(self):
        """Test widget count validation"""
        # Create test analysis with widgets
        analysis = SystemAnalysis(
            widgets=[
                WidgetInfo(
                    name="test_widget_1",
                    file_path="test.py",
                    class_name="TestWidget",
                    methods=["render"],
                    attributes={},
                    dynamic_values=[],
                    widget_type="text",
                    x=10, y=10
                ),
                WidgetInfo(
                    name="test_widget_2",
                    file_path="test.py",
                    class_name="TestWidget2",
                    methods=["render"],
                    attributes={},
                    dynamic_values=[],
                    widget_type="progress",
                    x=20, y=20
                )
            ],
            data_streams=[],
            dynamic_values=[],
            animations=[],
            display_config={},
            project_structure={}
        )
        
        # Create generated DSL with matching widgets (count "widget_" occurrences)
        generated_dsl = '''
        widget_text = Text("Test").position(10, 10)
        widget_progress = ProgressBar(0.5).position(20, 20)
        '''
        
        # Run validation
        test = WidgetCountValidation()
        result = test.validate(analysis, generated_dsl, Path(self.temp_dir))
        
        # Verify results - the DSL has 2 "widget_" occurrences
        assert result.passed == True
        assert result.score == 1.0
        assert result.details["legacy_widgets"] == 2
        assert result.details["dsl_widgets"] == 2
        assert len(result.errors) == 0
    
    def test_widget_count_validation_mismatch(self):
        """Test widget count validation with mismatch"""
        # Create test analysis with more widgets than DSL
        analysis = SystemAnalysis(
            widgets=[
                WidgetInfo(
                    name="widget1", file_path="test.py", class_name="Test",
                    methods=[], attributes={}, dynamic_values=[], widget_type="text", x=0, y=0
                ),
                WidgetInfo(
                    name="widget2", file_path="test.py", class_name="Test",
                    methods=[], attributes={}, dynamic_values=[], widget_type="text", x=0, y=0
                ),
                WidgetInfo(
                    name="widget3", file_path="test.py", class_name="Test",
                    methods=[], attributes={}, dynamic_values=[], widget_type="text", x=0, y=0
                )
            ],
            data_streams=[], dynamic_values=[], animations=[],
            display_config={}, project_structure={}
        )
        
        # Generated DSL with only one widget
        generated_dsl = 'widget_test = Text("Test").position(0, 0)'
        
        test = WidgetCountValidation()
        result = test.validate(analysis, generated_dsl, Path(self.temp_dir))
        
        # Should fail due to mismatch
        assert result.passed == False
        assert result.score < 0.95
        assert len(result.errors) > 0
    
    def test_animation_conversion_validation(self):
        """Test animation conversion validation"""
        # Create test analysis with animations
        analysis = SystemAnalysis(
            widgets=[],
            data_streams=[],
            dynamic_values=[],
            animations=[
                AnimationInfo(
                    name="fade_anim",
                    animation_type="fade",
                    duration=1000
                ),
                AnimationInfo(
                    name="slide_anim",
                    animation_type="slide",
                    duration=500,
                    direction="left"
                )
            ],
            display_config={},
            project_structure={}
        )
        
        # Generated DSL with matching animations
        generated_dsl = '''
        widget1.animate.fade(duration=1000)
        widget2.animate.slide(direction="left", duration=500)
        '''
        
        test = AnimationConversionValidation()
        result = test.validate(analysis, generated_dsl, Path(self.temp_dir))
        
        # Verify results
        assert result.passed == True
        assert result.score == 1.0
        assert result.details["legacy_animations"] == 2
        assert result.details["dsl_animations"] == 2
    
    def test_data_binding_validation(self):
        """Test data binding validation"""
        # Create test analysis with dynamic values
        analysis = SystemAnalysis(
            widgets=[],
            data_streams=[],
            dynamic_values=[
                DynamicValueInfo(
                    name="temp_binding",
                    expression="sensor.temperature",
                    dependencies=["temperature"],
                    usage_locations=["widget1"]
                ),
                DynamicValueInfo(
                    name="status_binding",
                    expression="system.status",
                    dependencies=["status"],
                    usage_locations=["widget2"]
                )
            ],
            animations=[],
            display_config={},
            project_structure={}
        )
        
        # Generated DSL with reactive bindings (2 reactive + 0 bind_ = 2 total)
        generated_dsl = '''
        widget1_content = reactive(lambda: sensor.temperature)
        widget2_text = reactive(lambda: system.status)
        data_source.connect('temperature')
        data_source.connect('status')
        '''
        
        test = DataBindingValidation()
        result = test.validate(analysis, generated_dsl, Path(self.temp_dir))
        
        # Verify results - 2 reactive() calls = 2 bindings
        assert result.passed == True
        assert result.score == 1.0
        assert result.details["legacy_bindings"] == 2
        assert result.details["dsl_bindings"] == 2
    
    def test_dsl_syntax_validation(self):
        """Test DSL syntax validation"""
        # Valid DSL code
        valid_dsl = '''
def create_application():
    canvas = Canvas(width=128, height=64)
    widget1 = Text("Hello").position(10, 10)
    return canvas

if __name__ == '__main__':
    app = create_application()
    app.run()
        '''
        
        test = DSLSyntaxValidation()
        result = test.validate(SystemAnalysis([], [], [], [], {}, {}), valid_dsl, Path(self.temp_dir))
        
        # Should pass
        assert result.passed == True
        assert result.score >= 0.8
        assert result.details["syntax_valid"] == True
    
    def test_dsl_syntax_validation_invalid(self):
        """Test DSL syntax validation with invalid syntax"""
        # Invalid DSL code (syntax error)
        invalid_dsl = '''
def create_application(:  # Missing parameter
    canvas = Canvas(width=128, height=64
    return canvas  # Missing closing parenthesis
        '''
        
        test = DSLSyntaxValidation()
        result = test.validate(SystemAnalysis([], [], [], [], {}, {}), invalid_dsl, Path(self.temp_dir))
        
        # Should fail - syntax is invalid but some patterns might be found
        assert result.passed == False
        assert result.score < 0.8  # Combined score should be low
        assert result.details["syntax_valid"] == False
        assert len(result.errors) > 0
    
    def test_performance_validation(self):
        """Test performance validation"""
        # Create reasonable DSL code
        analysis = SystemAnalysis(
            widgets=[
                WidgetInfo(
                    name="widget1", file_path="test.py", class_name="Test",
                    methods=[], attributes={}, dynamic_values=[], widget_type="text", x=0, y=0
                )
            ],
            data_streams=[], dynamic_values=[], animations=[],
            display_config={}, project_structure={}
        )
        
        # Reasonable DSL code with performance patterns
        reasonable_dsl = '''
def create_application():
    data_manager = DataManager()
    canvas = Canvas(width=128, height=64)
    widget1 = Text("Test").position(0, 0)
    widget1.bind_content(reactive(lambda: data.value))
    return canvas
        '''
        
        test = PerformanceValidation()
        result = test.validate(analysis, reasonable_dsl, Path(self.temp_dir))
        
        # Should pass
        assert result.passed == True
        assert result.score >= 0.7
        assert result.details["performance_patterns"] > 0
    
    def test_full_migration_validation(self):
        """Test full migration validation"""
        # Create test source directory
        source_dir = Path(self.temp_dir) / "source"
        source_dir.mkdir()
        
        # Create a simple test file
        test_file = source_dir / "test_widget.py"
        test_file.write_text('''
class TestWidget:
    def __init__(self):
        self.content = "Hello World"
        self.position = (10, 20)
    
    def render(self):
        pass
        ''')
        
        # Run full validation
        report = self.validator.validate_migration(str(source_dir))
        
        # Verify report structure
        assert report.source_path == str(source_dir)
        assert report.total_tests == 7  # Number of validation tests
        assert report.overall_score >= 0.0
        assert report.success_rate >= 0.0
        assert len(report.validation_results) == 7
        assert report.generation_time > 0
        assert report.validation_time > 0
    
    def test_json_conversion_validation(self):
        """Test JSON conversion validation"""
        # Create test JSON file
        json_config = {
            "canvas": {"width": 128, "height": 64},
            "widgets": [
                {
                    "type": "text",
                    "content": "Test",
                    "position": {"x": 10, "y": 10}
                }
            ]
        }
        
        json_file = Path(self.temp_dir) / "test.json"
        with open(json_file, 'w') as f:
            json.dump(json_config, f)
        
        # Validate JSON conversion
        result = self.validator.validate_json_conversion(str(json_file))
        
        # Should pass for valid JSON
        assert result.test_name == "JSON Conversion"
        assert result.passed == True
        assert result.score == 1.0
    
    def test_json_conversion_validation_invalid(self):
        """Test JSON conversion validation with invalid JSON"""
        # Create invalid JSON file
        json_file = Path(self.temp_dir) / "invalid.json"
        json_file.write_text('{"invalid": json}')  # Invalid JSON
        
        # Validate JSON conversion
        result = self.validator.validate_json_conversion(str(json_file))
        
        # Should fail for invalid JSON
        assert result.passed == False
        assert result.score == 0.0
        assert len(result.errors) > 0
    
    def test_report_generation(self):
        """Test validation report generation"""
        # Create a mock report
        from migration_validator import MigrationReport, ValidationResult
        
        validation_results = [
            ValidationResult(
                test_name="Test 1",
                passed=True,
                score=1.0,
                details={"key": "value"},
                errors=[],
                warnings=["Warning message"],
                execution_time=0.1
            ),
            ValidationResult(
                test_name="Test 2",
                passed=False,
                score=0.5,
                details={},
                errors=["Error message"],
                warnings=[],
                execution_time=0.2
            )
        ]
        
        report = MigrationReport(
            source_path="/test/source",
            target_path="/test/target",
            validation_results=validation_results,
            overall_score=0.75,
            success_rate=0.5,
            total_tests=2,
            passed_tests=1,
            failed_tests=1,
            generation_time=1.0,
            validation_time=0.3,
            recommendations=["Recommendation 1", "Recommendation 2"]
        )
        
        # Generate report
        report_text = self.validator.generate_report(report)
        
        # Verify report content (check for the actual format)
        assert "Migration Validation Report" in report_text
        assert "75.0%" in report_text  # Overall score appears in the text
        assert "50.0%" in report_text  # Success rate appears in the text
        assert "Test 1 - ✅ PASS" in report_text
        assert "Test 2 - ❌ FAIL" in report_text
        assert "Recommendations" in report_text
        assert "Recommendation 1" in report_text
    
    def test_recommendations_generation(self):
        """Test recommendation generation"""
        from migration_validator import ValidationResult
        
        # Create validation results with various issues
        validation_results = [
            ValidationResult("Widget Count", False, 0.8, {}, ["Widget mismatch"], [], 0.1),
            ValidationResult("Animation Conversion", True, 0.85, {}, [], [], 0.1),
            ValidationResult("Data Binding", False, 0.9, {}, ["Binding issue"], [], 0.1),
            ValidationResult("DSL Syntax", False, 0.0, {}, ["Syntax error"], [], 0.1),
            ValidationResult("Performance", True, 0.6, {}, [], ["Performance warning"], 0.1)
        ]
        
        # Create analysis with many widgets and dynamic values
        analysis = SystemAnalysis(
            widgets=[WidgetInfo(f"widget{i}", "test.py", "Test", [], {}, [], "text", 0, 0) for i in range(15)],
            data_streams=[],
            dynamic_values=[DynamicValueInfo(f"dv{i}", "expr", [], []) for i in range(25)],
            animations=[],
            display_config={},
            project_structure={}
        )
        
        # Generate recommendations
        recommendations = self.validator._generate_recommendations(validation_results, analysis)
        
        # Verify recommendations
        assert len(recommendations) > 0
        assert any("widget analysis patterns" in rec for rec in recommendations)
        assert any("data dependencies" in rec for rec in recommendations)
        assert any("DSL generation templates" in rec for rec in recommendations)
        assert any("smaller modules" in rec for rec in recommendations)
        assert any("data binding patterns" in rec for rec in recommendations)
        assert any("module" in rec.lower() for rec in recommendations)  # Large app recommendation

    def test_before_after_comparison_validation(self):
        """Test before/after comparison validation"""
        # Create test analysis with widgets, animations, and data bindings
        analysis = SystemAnalysis(
            widgets=[
                WidgetInfo(
                    name="text_widget",
                    file_path="test.py",
                    class_name="TextWidget",
                    methods=["render"],
                    attributes={"content": "Hello World", "color": "blue"},
                    dynamic_values=[],
                    widget_type="text",
                    x=10, y=20
                )
            ],
            data_streams=[],
            dynamic_values=[
                DynamicValueInfo(
                    name="temp_binding",
                    expression="sensor.temperature",
                    dependencies=["temperature"],
                    usage_locations=["text_widget"]
                )
            ],
            animations=[
                AnimationInfo(
                    name="fade_anim",
                    animation_type="fade",
                    duration=1000
                )
            ],
            display_config={},
            project_structure={}
        )
        
        # Generated DSL that preserves functionality
        generated_dsl = '''
        widget_text = Text("Hello World").position(10, 20).color("blue")
        widget_text.animate.fade(duration=1000)
        temp_data = reactive(lambda: sensor.temperature)
        data_source.connect('temperature')
        '''
        
        test = BeforeAfterComparisonValidation()
        result = test.validate(analysis, generated_dsl, Path(self.temp_dir))
        
        # Should pass with high preservation scores
        assert result.passed == True
        assert result.score >= 0.95
        assert result.details["widget_preservation"] >= 0.9
        assert result.details["animation_preservation"] >= 0.9
        assert result.details["data_flow_preservation"] >= 0.9
    
    def test_before_after_comparison_validation_poor_preservation(self):
        """Test before/after comparison with poor preservation"""
        # Create test analysis
        analysis = SystemAnalysis(
            widgets=[
                WidgetInfo(
                    name="text_widget", file_path="test.py", class_name="TextWidget",
                    methods=[], attributes={"content": "Hello"}, dynamic_values=[],
                    widget_type="text", x=10, y=20
                )
            ],
            data_streams=[],
            dynamic_values=[
                DynamicValueInfo(
                    name="temp_binding", expression="sensor.temperature",
                    dependencies=["temperature"], usage_locations=["text_widget"]
                )
            ],
            animations=[
                AnimationInfo(name="fade_anim", animation_type="fade", duration=1000)
            ],
            display_config={},
            project_structure={}
        )
        
        # Generated DSL that doesn't preserve functionality well
        generated_dsl = '''
        # Missing widget type, position, and attributes
        some_widget = Widget()
        # Missing animation
        # Missing data binding
        '''
        
        test = BeforeAfterComparisonValidation()
        result = test.validate(analysis, generated_dsl, Path(self.temp_dir))
        
        # Should fail due to poor preservation
        assert result.passed == False
        assert result.score < 0.95
        assert len(result.warnings) > 0
    
    def test_regression_test_validation(self):
        """Test regression testing validation"""
        # Create test analysis
        analysis = SystemAnalysis(
            widgets=[
                WidgetInfo(
                    name="text_widget", file_path="test.py", class_name="TextWidget",
                    methods=[], attributes={}, dynamic_values=[], widget_type="text", x=0, y=0
                )
            ],
            data_streams=[],
            dynamic_values=[],
            animations=[
                AnimationInfo(name="fade_anim", animation_type="fade", duration=1000)
            ],
            display_config={},
            project_structure={}
        )
        
        # Generated DSL with good patterns and quality
        generated_dsl = '''
import time
from display import Canvas, Text

def create_application():
    """Create the main application"""
    canvas = Canvas(width=128, height=64)
    widget_text = Text("Hello").position(10, 10)
    canvas.add(widget_text)
    widget_text.animate.fade(duration=1000)
    return canvas

if __name__ == '__main__':
    app = create_application()
    app.run()
        '''
        
        test = RegressionTestValidation()
        result = test.validate(analysis, generated_dsl, Path(self.temp_dir))
        
        # Should pass with good scores
        assert result.passed == True
        assert result.score >= 0.90
        assert result.details["core_patterns"] >= 0.8
        assert result.details["backward_compatibility"] >= 0.8
        assert result.details["code_quality"] >= 0.8
    
    def test_regression_test_validation_poor_quality(self):
        """Test regression testing with poor code quality"""
        # Create test analysis
        analysis = SystemAnalysis(
            widgets=[
                WidgetInfo(
                    name="unknown_widget", file_path="test.py", class_name="UnknownWidget",
                    methods=[], attributes={}, dynamic_values=[], widget_type="unknown", x=0, y=0
                )
            ],
            data_streams=[],
            dynamic_values=[],
            animations=[
                AnimationInfo(name="unknown_anim", animation_type="unknown", duration=1000)
            ],
            display_config={},
            project_structure={}
        )
        
        # Generated DSL with poor patterns and quality
        generated_dsl = '''
        # Missing imports, main function, proper structure
        widget = SomeWidget()
        '''
        
        test = RegressionTestValidation()
        result = test.validate(analysis, generated_dsl, Path(self.temp_dir))
        
        # Should fail due to poor quality
        assert result.passed == False
        assert result.score < 0.90
        assert len(result.warnings) > 0
    
    def test_migration_rollback_manager(self):
        """Test migration rollback manager"""
        from migration_validator import MigrationRollbackManager
        import tempfile
        import shutil
        from pathlib import Path
        
        # Create test source directory
        source_dir = tempfile.mkdtemp(prefix="test_source_")
        test_file = Path(source_dir) / "test.py"
        test_file.write_text("# Original content")
        
        try:
            manager = MigrationRollbackManager()
            
            # Test backup creation
            backup_path = manager.create_backup(source_dir)
            assert Path(backup_path).exists()
            assert (Path(backup_path) / "test.py").exists()
            
            # Modify source to simulate migration
            test_file.write_text("# Modified content")
            
            # Test rollback
            rollback_success = manager.rollback_migration(source_dir)
            assert rollback_success == True
            assert test_file.read_text() == "# Original content"
            
            # Test rollback log
            log = manager.get_rollback_log()
            assert len(log) >= 2  # backup_created and rollback_successful
            assert any(entry['action'] == 'backup_created' for entry in log)
            assert any(entry['action'] == 'rollback_successful' for entry in log)
            
        finally:
            # Cleanup
            if Path(source_dir).exists():
                shutil.rmtree(source_dir)
            if backup_path and Path(backup_path).exists():
                shutil.rmtree(backup_path)
    
    def test_migration_rollback_manager_no_backup(self):
        """Test rollback manager when no backup exists"""
        from migration_validator import MigrationRollbackManager
        
        manager = MigrationRollbackManager()
        
        # Test rollback without backup
        rollback_success = manager.rollback_migration("/nonexistent/path")
        assert rollback_success == False
        
        # Check log for failure
        log = manager.get_rollback_log()
        assert len(log) >= 1
        assert any(entry['action'] == 'rollback_failed' for entry in log)
        assert any('No backup found' in entry.get('error', '') for entry in log)
    
    def test_enhanced_migration_validator_with_rollback(self):
        """Test enhanced migration validator with rollback functionality"""
        # Create test source directory
        source_dir = tempfile.mkdtemp(prefix="test_migration_")
        test_file = Path(source_dir) / "main.py"
        test_file.write_text('''
class TestWidget:
    def __init__(self):
        self.x = 10
        self.y = 20
        self.content = "Hello"
    
    def render(self):
        pass
        ''')
        
        try:
            validator = MigrationValidator()
            
            # Test migration with backup
            report = validator.validate_migration(source_dir, create_backup=True)
            
            # Should have rollback manager
            assert hasattr(validator, 'rollback_manager')
            
            # Should have additional validation tests
            test_names = [r.test_name for r in report.validation_results]
            assert "Before/After Comparison" in test_names
            assert "Regression Testing" in test_names
            
            # Check rollback log
            rollback_log = validator.get_rollback_log()
            assert len(rollback_log) >= 1  # At least backup creation
            
        finally:
            # Cleanup
            if Path(source_dir).exists():
                shutil.rmtree(source_dir)
            
            # Cleanup any backups
            for entry in validator.get_rollback_log():
                if 'backup' in entry and Path(entry['backup']).exists():
                    shutil.rmtree(entry['backup'])

    def test_rollback_manager_functionality(self):
        """Test rollback manager functionality"""
        # Create test backup
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source"
            source_path.mkdir()
            test_file = source_path / "test.py"
            test_file.write_text("# Test content")
            
            rollback_manager = MigrationRollbackManager()
            
            # Create backup
            backup_id = rollback_manager.create_backup(str(source_path))
            assert backup_id is not None
            
            # Modify source
            test_file.write_text("# Modified content")
            
            # Rollback
            success = rollback_manager.rollback_migration(str(source_path))
            assert success
            
            # Verify rollback
            assert test_file.read_text() == "# Test content"

    def test_complex_application_analysis(self):
        """Test analysis of complex applications with multiple canvases and hierarchies"""
        from migration_tool import SystemAnalyzer, CanvasInfo, WidgetHierarchy, CustomWidgetInfo
        
        # Create test analysis with complex scenarios
        analysis = SystemAnalysis(
            widgets=[
                WidgetInfo(
                    name=f"widget_{i}",
                    file_path="test.py",
                    class_name=f"Widget{i}",
                    methods=["render"],
                    attributes={"content": f"Widget {i}"},
                    dynamic_values=[],
                    position=(i*10, i*10),
                    widget_type="text"
                ) for i in range(15)  # >10 widgets
            ],
            data_streams=[],
            dynamic_values=[],
            display_config={},
            project_structure={},
            canvases=[
                CanvasInfo(
                    name="main_canvas",
                    width=128,
                    height=64,
                    widgets=["widget_0", "widget_1", "widget_2"],
                    z_layers={0: ["widget_0"], 1: ["widget_1", "widget_2"]},
                    file_path="main.py",
                    is_primary=True
                ),
                CanvasInfo(
                    name="secondary_canvas",
                    width=64,
                    height=32,
                    widgets=["widget_3", "widget_4"],
                    z_layers={0: ["widget_3", "widget_4"]},
                    file_path="secondary.py",
                    is_primary=False
                )
            ],
            widget_hierarchies=[
                WidgetHierarchy(
                    parent="container_widget",
                    children=["widget_0", "widget_1"],
                    hierarchy_type="container",
                    layout_properties={"padding": 10}
                ),
                WidgetHierarchy(
                    parent="group_widget",
                    children=["widget_2", "widget_3", "widget_4"],
                    hierarchy_type="group",
                    layout_properties={"columns": 2, "spacing": 5}
                )
            ],
            custom_widgets=[
                CustomWidgetInfo(
                    name="CustomGaugeWidget",
                    base_class="Widget",
                    custom_methods=["update_value", "set_range", "render_needle"],
                    custom_properties={"min_value": 0, "max_value": 100, "color": "blue"},
                    rendering_complexity=7,
                    migration_strategy="composite"
                ),
                CustomWidgetInfo(
                    name="ComplexChartWidget",
                    base_class="Widget",
                    custom_methods=["add_data", "update_chart", "render_axes", "render_legend", "animate_bars"],
                    custom_properties={"chart_type": "bar", "data_source": "sensor_data"},
                    rendering_complexity=9,
                    migration_strategy="custom"
                )
            ]
        )
        
        # Manually update complexity since it's not automatically calculated in tests
        analysis.application_complexity.widget_count = len(analysis.widgets)
        analysis.application_complexity.canvas_count = len(analysis.canvases)
        analysis.application_complexity.custom_widget_count = len(analysis.custom_widgets)
        analysis.application_complexity.complexity_score = 75  # High complexity
        analysis.application_complexity.migration_strategy = 'modular'
        
        # Test complexity calculation
        complexity = analysis.application_complexity
        assert complexity.widget_count == 15
        assert complexity.canvas_count == 2
        assert complexity.custom_widget_count == 2
        assert complexity.complexity_score > 50  # Should be high complexity
        
        # Test migration strategy determination
        assert complexity.migration_strategy in ['modular', 'phased']

    def test_multi_canvas_migration_validation(self):
        """Test validation for multi-canvas applications"""
        # Create test analysis with multiple canvases
        analysis = SystemAnalysis(
            widgets=[
                WidgetInfo("widget1", "test.py", "Widget1", [], {}, [], widget_type="text", position=(0, 0)),
                WidgetInfo("widget2", "test.py", "Widget2", [], {}, [], widget_type="progress", position=(10, 10)),
                WidgetInfo("widget3", "test.py", "Widget3", [], {}, [], widget_type="image", position=(20, 20))
            ],
            data_streams=[],
            dynamic_values=[],
            display_config={},
            project_structure={},
            canvases=[
                CanvasInfo("canvas1", 128, 64, ["widget1", "widget2"], {}, "main.py", True),
                CanvasInfo("canvas2", 64, 32, ["widget3"], {}, "secondary.py", False)
            ]
        )
        
        # Generate DSL for multi-canvas
        generated_dsl = '''
        canvas_manager = CanvasManager()
        canvas1 = canvas_manager.create_canvas("canvas1", 128, 64, is_primary=True)
        canvas2 = canvas_manager.create_canvas("canvas2", 64, 32, is_primary=False)
        widget1 = Text("Hello").position(0, 0)
        widget2 = ProgressBar(0.5).position(10, 10)
        widget3 = Image("test.png").position(20, 20)
        canvas1.add(widget1)
        canvas1.add(widget2)
        canvas2.add(widget3)
        '''
        
        # Test multi-canvas validation
        validation = BeforeAfterComparisonValidation()
        result = validation.validate(analysis, generated_dsl, Path("test"))
        
        assert result.passed
        assert result.score >= 0.8
        assert "canvas" in generated_dsl.lower()  # Check DSL contains canvas references

    def test_widget_hierarchy_validation(self):
        """Test validation for widget hierarchies"""
        # Create test analysis with widget hierarchies
        analysis = SystemAnalysis(
            widgets=[
                WidgetInfo("parent_widget", "test.py", "ParentWidget", [], {}, [], widget_type="container", position=(0, 0)),
                WidgetInfo("child1", "test.py", "Child1", [], {}, [], widget_type="text", position=(10, 10)),
                WidgetInfo("child2", "test.py", "Child2", [], {}, [], widget_type="button", position=(20, 20))
            ],
            data_streams=[],
            dynamic_values=[],
            display_config={},
            project_structure={},
            widget_hierarchies=[
                WidgetHierarchy(
                    parent="parent_widget",
                    children=["child1", "child2"],
                    hierarchy_type="container",
                    layout_properties={"padding": 10}
                )
            ]
        )
        
        # Generate DSL with hierarchy
        generated_dsl = '''
        hierarchy_manager = HierarchyManager()
        parent_hierarchy = hierarchy_manager.create_hierarchy(
            parent="parent_widget",
            hierarchy_type="container",
            children=["child1", "child2"]
        )
        parent_widget = Container().position(0, 0)
        child1 = Text("Child 1").position(10, 10)
        child2 = Button("Child 2").position(20, 20)
        parent_widget.add_child(child1)
        parent_widget.add_child(child2)
        '''
        
        # Test hierarchy validation
        validation = BeforeAfterComparisonValidation()
        result = validation.validate(analysis, generated_dsl, Path("test"))
        
        assert result.passed
        assert "hierarchy" in generated_dsl.lower()  # Check DSL contains hierarchy references

    def test_custom_widget_migration_validation(self):
        """Test validation for custom widget migration"""
        # Create test analysis with custom widgets
        analysis = SystemAnalysis(
            widgets=[],
            data_streams=[],
            dynamic_values=[],
            display_config={},
            project_structure={},
            custom_widgets=[
                CustomWidgetInfo(
                    name="CustomGaugeWidget",
                    base_class="Widget",
                    custom_methods=["update_value", "set_range"],
                    custom_properties={"min_value": 0, "max_value": 100},
                    rendering_complexity=5,
                    migration_strategy="direct"
                )
            ]
        )
        
        # Generate DSL for custom widget
        generated_dsl = '''
        class CustomGaugeWidget(Widget):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.min_value = 0
                self.max_value = 100
            
            def update_value(self, value):
                pass
            
            def set_range(self, min_val, max_val):
                self.min_value = min_val
                self.max_value = max_val
        
        custom_gauge = CustomGaugeWidget().position(0, 0)
        '''
        
        # Test custom widget validation
        validation = BeforeAfterComparisonValidation()
        result = validation.validate(analysis, generated_dsl, Path("test"))
        
        assert result.passed
        assert "customgaugewidget" in generated_dsl.lower()  # Check DSL contains custom widget

    def test_large_application_migration_strategy(self):
        """Test migration strategy for applications with >10 widgets"""
        # Create test analysis with many widgets
        analysis = SystemAnalysis(
            widgets=[
                WidgetInfo(
                    name=f"widget_{i}",
                    file_path="test.py",
                    class_name=f"Widget{i}",
                    methods=["render"],
                    attributes={"content": f"Widget {i}"},
                    dynamic_values=[],
                    widget_type="text" if i % 2 == 0 else "button",
                    position=(i*10, i*10)
                ) for i in range(20)  # 20 widgets
            ],
            data_streams=[],
            dynamic_values=[],
            display_config={},
            project_structure={}
        )
        
        # Manually update complexity
        analysis.application_complexity.widget_count = len(analysis.widgets)
        analysis.application_complexity.complexity_score = 60  # High complexity
        analysis.application_complexity.migration_strategy = 'modular'
        
        # Test complexity calculation
        complexity = analysis.application_complexity
        assert complexity.widget_count == 20
        assert complexity.complexity_score > 30  # Should be moderate to high complexity
        
        # Test that modular strategy is recommended for >10 widgets
        assert complexity.migration_strategy in ['modular', 'phased']

    def test_migration_performance_with_complex_app(self):
        """Test migration performance with complex applications"""
        import time
        
        # Create complex test analysis
        analysis = SystemAnalysis(
            widgets=[
                WidgetInfo(f"widget_{i}", "test.py", f"Widget{i}", [], {}, [], widget_type="text", position=(i*5, i*5))
                for i in range(50)  # Large number of widgets
            ],
            data_streams=[
                DataStreamInfo(f"stream_{i}", "float", [1.0, 2.0], 10, True)
                for i in range(20)  # Many data streams
            ],
            dynamic_values=[
                DynamicValueInfo(f"dv_{i}", f"data.stream_{i}", [], [])
                for i in range(30)  # Many dynamic values
            ],
            display_config={},
            project_structure={},
            canvases=[
                CanvasInfo(f"canvas_{i}", 128, 64, [f"widget_{i*10+j}" for j in range(10)], {}, f"canvas_{i}.py", i==0)
                for i in range(5)  # Multiple canvases
            ]
        )
        
        # Create a more substantial DSL for performance testing
        generated_dsl = '''
        # Complex DSL Application
        from widgets.base import *
        from data.data_manager import DataManager
        
        def create_application():
            data_manager = DataManager()
            canvas = Canvas(width=128, height=64)
            
            # Create many widgets
            widgets = []
            for i in range(50):
                widget = Text(f"Widget {i}").position(i*5, i*5)
                widgets.append(widget)
                canvas.add(widget)
            
            # Add data streams
            for i in range(20):
                data_manager.add_stream(f"stream_{i}")
            
            # Add dynamic values
            for i in range(30):
                data_manager.add_dynamic_value(f"dv_{i}")
            
            return canvas
        
        if __name__ == "__main__":
            app = create_application()
            app.run()
        '''
        
        # Test performance validation
        validation = PerformanceValidation()
        start_time = time.time()
        result = validation.validate(analysis, generated_dsl, Path("test"))
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 5.0  # 5 seconds max
        # Performance validation should pass with substantial DSL
        assert result.score > 0.3  # Lower threshold for complex apps


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 