"""Test JSON-to-DSL conversion utilities."""

import pytest
import json
import tempfile
import os
from pathlib import Path

from dsl_converter import JSONToDSLConverter


class TestJSONToDSLConverter:
    """Test JSON-to-DSL conversion utilities"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.converter = JSONToDSLConverter()
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_basic_json_to_dsl_conversion(self):
        """Test basic JSON to DSL conversion"""
        json_config = {
            "canvas": {
                "width": 128,
                "height": 64
            },
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
        }
        
        dsl_code = self.converter.convert_config(json_config)
        
        # Verify DSL generation
        assert "Canvas(width=128, height=64)" in dsl_code
        assert "Text(" in dsl_code
        assert "ProgressBar(" in dsl_code
        assert "position(10, 10)" in dsl_code
        assert "position(10, 30)" in dsl_code
        
        # Verify no errors
        report = self.converter.get_conversion_report()
        assert report['success'] == True
        assert report['error_count'] == 0
    
    def test_json_validation(self):
        """Test JSON structure validation"""
        # Test missing required sections
        invalid_json = {"canvas": {"width": 128, "height": 64}}  # Missing widgets
        
        dsl_code = self.converter.convert_config(invalid_json)
        report = self.converter.get_conversion_report()
        
        assert report['success'] == False
        assert report['error_count'] > 0
        assert any("Missing required section: widgets" in error for error in report['errors'])
    
    def test_widget_validation(self):
        """Test widget validation"""
        json_config = {
            "canvas": {"width": 128, "height": 64},
            "widgets": [
                {
                    # Missing required 'type' field
                    "content": "Invalid Widget",
                    "position": {"x": 10, "y": 10}
                },
                {
                    "type": "text",
                    "content": "Valid Widget",
                    "position": {"x": 20, "y": 20}
                }
            ]
        }
        
        dsl_code = self.converter.convert_config(json_config)
        report = self.converter.get_conversion_report()
        
        assert report['success'] == False
        assert any("Missing required field 'type'" in error for error in report['errors'])
    
    def test_animation_validation(self):
        """Test animation validation"""
        json_config = {
            "canvas": {"width": 128, "height": 64},
            "widgets": [
                {
                    "type": "text",
                    "content": "Test",
                    "position": {"x": 10, "y": 10}
                }
            ],
            "animations": [
                {
                    "type": "fade",
                    "duration": 1000
                },
                {
                    # Missing required 'type' field
                    "duration": 500
                }
            ]
        }
        
        dsl_code = self.converter.convert_config(json_config)
        report = self.converter.get_conversion_report()
        
        assert report['success'] == False
        assert any("Missing required field 'type'" in error for error in report['errors'])
    
    def test_legacy_json_pattern_conversion(self):
        """Test conversion of legacy JSON patterns"""
        legacy_json = {
            "canvas": {"width": 128, "height": 64},
            "widgets": [
                {
                    "type": "text",
                    "content": "Legacy Text",
                    "x": 10,  # Legacy position format
                    "y": 20,
                    "width": 100,  # Legacy size format
                    "height": 30
                },
                {
                    "type": "progress",
                    "value": "data.progress",  # Reactive binding
                    "x": 10,
                    "y": 60,
                    "width": 200,
                    "height": 20
                }
            ],
            "animations": [
                {
                    "type": "scroll",
                    "speed": 2.0,  # Legacy speed format
                    "direction": "left"
                }
            ]
        }
        
        # Convert legacy patterns
        converted = self.converter.convert_legacy_json_patterns(legacy_json)
        
        # Verify conversion
        text_widget = converted['widgets'][0]
        assert 'position' in text_widget
        assert text_widget['position'] == {'x': 10, 'y': 20}
        assert 'size' in text_widget
        assert text_widget['size'] == {'width': 100, 'height': 30}
        assert 'x' not in text_widget  # Legacy fields removed
        assert 'y' not in text_widget
        
        progress_widget = converted['widgets'][1]
        assert 'reactive_value' in progress_widget
        assert progress_widget['reactive_value'] == 'data.progress'
        
        animation = converted['animations'][0]
        assert 'duration' in animation
        assert animation['duration'] == 500  # 1000 / 2.0
        assert 'speed' not in animation  # Legacy field removed
    
    def test_file_conversion(self):
        """Test file-based conversion"""
        # Create test JSON file
        json_config = {
            "canvas": {"width": 128, "height": 64},
            "widgets": [
                {
                    "type": "text",
                    "content": "File Test",
                    "position": {"x": 10, "y": 10}
                }
            ]
        }
        
        json_file = Path(self.temp_dir) / "test_config.json"
        dsl_file = Path(self.temp_dir) / "test_config.py"
        
        # Write JSON file
        with open(json_file, 'w') as f:
            json.dump(json_config, f)
        
        # Convert file
        dsl_code = self.converter.convert_file(str(json_file), str(dsl_file))
        
        # Verify conversion
        assert dsl_code != ""
        assert dsl_file.exists()
        
        # Verify file content
        with open(dsl_file, 'r') as f:
            file_content = f.read()
        
        assert "Canvas(width=128, height=64)" in file_content
        assert "Text(" in file_content
    
    def test_string_conversion(self):
        """Test string-based conversion"""
        json_string = '''
        {
            "canvas": {"width": 128, "height": 64},
            "widgets": [
                {
                    "type": "text",
                    "content": "String Test",
                    "position": {"x": 10, "y": 10}
                }
            ]
        }
        '''
        
        dsl_code = self.converter.convert_string(json_string)
        
        assert dsl_code != ""
        assert "Canvas(width=128, height=64)" in dsl_code
        assert "Text(" in dsl_code
    
    def test_batch_directory_conversion(self):
        """Test batch conversion of directory"""
        # Create multiple JSON files
        configs = [
            {
                "canvas": {"width": 128, "height": 64},
                "widgets": [{"type": "text", "content": "Config 1", "position": {"x": 10, "y": 10}}]
            },
            {
                "canvas": {"width": 256, "height": 128},
                "widgets": [{"type": "progress", "value": 0.5, "position": {"x": 20, "y": 20}, "size": {"width": 100, "height": 20}}]
            },
            {
                "canvas": {"width": 64, "height": 32},
                "widgets": [{"type": "image", "path": "test.png", "position": {"x": 0, "y": 0}, "size": {"width": 64, "height": 32}}]
            }
        ]
        
        input_dir = Path(self.temp_dir) / "input"
        output_dir = Path(self.temp_dir) / "output"
        input_dir.mkdir()
        
        # Write JSON files
        for i, config in enumerate(configs):
            json_file = input_dir / f"config_{i}.json"
            with open(json_file, 'w') as f:
                json.dump(config, f)
        
        # Batch convert
        converted_files = self.converter.batch_convert_directory(str(input_dir), str(output_dir))
        
        # Verify conversion
        assert len(converted_files) == 3
        assert output_dir.exists()
        
        # Check each converted file
        for converted_file in converted_files:
            assert Path(converted_file).exists()
            assert converted_file.endswith('.py')
    
    def test_error_handling(self):
        """Test error handling for invalid inputs"""
        # Test invalid JSON string
        invalid_json = '{"invalid": json}'
        dsl_code = self.converter.convert_string(invalid_json)
        
        assert dsl_code == ""
        report = self.converter.get_conversion_report()
        assert report['success'] == False
        assert report['error_count'] > 0
        
        # Test non-existent file
        dsl_code = self.converter.convert_file("non_existent_file.json")
        
        assert dsl_code == ""
        report = self.converter.get_conversion_report()
        assert report['success'] == False
        assert any("File not found" in error for error in report['errors'])
    
    def test_complex_json_conversion(self):
        """Test conversion of complex JSON configuration"""
        complex_json = {
            "canvas": {
                "width": 800,
                "height": 600,
                "background": "#000000"
            },
            "widgets": [
                {
                    "type": "text",
                    "content": "Dashboard Title",
                    "position": {"x": 10, "y": 10},
                    "size": {"width": 200, "height": 30},
                    "z_order": 1,
                    "font_size": 16,
                    "color": "#FFFFFF"
                },
                {
                    "type": "gauge",
                    "value": "data.cpu_usage",
                    "position": {"x": 50, "y": 50},
                    "size": {"width": 150, "height": 150},
                    "min_value": 0,
                    "max_value": 100,
                    "z_order": 2
                },
                {
                    "type": "chart",
                    "data": "data.temperature_history",
                    "chart_type": "line",
                    "position": {"x": 250, "y": 50},
                    "size": {"width": 300, "height": 200},
                    "z_order": 3
                },
                {
                    "type": "slider",
                    "value": "data.brightness",
                    "min_value": 0,
                    "max_value": 255,
                    "position": {"x": 50, "y": 250},
                    "size": {"width": 200, "height": 30},
                    "z_order": 4
                }
            ],
            "animations": [
                {
                    "type": "fade_in",
                    "duration": 1000,
                    "target": "dashboard_title"
                },
                {
                    "type": "pulse",
                    "duration": 2000,
                    "target": "cpu_gauge",
                    "sync_group": "dashboard_startup"
                }
            ],
            "data_sources": [
                {
                    "name": "cpu_usage",
                    "type": "sensor",
                    "update_interval": 1000
                },
                {
                    "name": "temperature_history",
                    "type": "time_series",
                    "buffer_size": 100
                }
            ]
        }
        
        dsl_code = self.converter.convert_config(complex_json)
        
        # Verify complex conversion
        assert "Canvas(width=800, height=600)" in dsl_code
        assert "Text(" in dsl_code
        assert "Gauge(" in dsl_code
        assert "Chart(" in dsl_code
        assert "Slider(" in dsl_code
        
        # Verify no errors for valid complex configuration
        report = self.converter.get_conversion_report()
        assert report['success'] == True
        assert report['error_count'] == 0
        
        print("✓ Complex JSON conversion test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 