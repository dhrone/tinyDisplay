#!/usr/bin/env python3
"""
Test script to demonstrate the migration tool functionality.
"""

import os
import tempfile
from pathlib import Path

def create_sample_tinydisplay_project(temp_dir: Path):
    """Create a sample tinyDisplay project for testing migration"""
    
    # Create directory structure
    (temp_dir / "render").mkdir()
    (temp_dir / "utility").mkdir()
    
    # Create sample widget.py
    widget_code = '''
class TemperatureWidget:
    """Sample temperature display widget"""
    
    def __init__(self):
        self.position = (10, 20)
        self.size = (100, 30)
        self.font_size = 14
        self.temp_value = DynamicValue("f'{sensor.temperature}°F'")
        self.color_value = DynamicValue("'red' if sensor.temperature > 80 else 'blue'")
    
    def render(self):
        # Render temperature display
        pass
    
    def update(self):
        # Update widget content
        pass

class ClockWidget:
    """Sample clock widget"""
    
    def __init__(self):
        self.position = (200, 10)
        self.size = (80, 20)
        self.time_format = "%H:%M:%S"
        self.time_value = DynamicValue("time.strftime('%H:%M:%S')")
    
    def render(self):
        # Render clock
        pass
'''
    
    (temp_dir / "render" / "widget.py").write_text(widget_code)
    
    # Create sample dataset.py
    dataset_code = '''
class Dataset:
    """Sample dataset implementation"""
    
    def __init__(self):
        self.data = {}
        self.history = {}
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def set(self, key, value):
        self.data[key] = value
        if key not in self.history:
            self.history[key] = []
        self.history[key].append((time.time(), value))
    
    def get_history(self, key, count=10):
        return self.history.get(key, [])[-count:]
    
    def get_all_keys(self):
        return list(self.data.keys())

# Sample usage
dataset = Dataset()
dataset.set('sensor.temperature', 72.5)
dataset.set('sensor.humidity', 45.0)
dataset.set('weather.condition', 'sunny')
'''
    
    (temp_dir / "utility" / "dataset.py").write_text(dataset_code)
    
    # Create sample config
    config_code = '''
# Display configuration
DISPLAY_WIDTH = 256
DISPLAY_HEIGHT = 128
TARGET_FPS = 60
MEMORY_LIMIT_MB = 200
'''
    
    (temp_dir / "config.py").write_text(config_code)
    
    # Create sample main.py with dynamic values
    main_code = '''
import time
from render.widget import TemperatureWidget, ClockWidget
from utility.dataset import dataset

class DynamicValue:
    def __init__(self, expression):
        self.expression = expression

def main():
    # Sample application using dataset
    temp_widget = TemperatureWidget()
    clock_widget = ClockWidget()
    
    # Sample data access patterns
    current_temp = dataset.get('sensor.temperature')
    humidity = dataset.get('sensor.humidity')
    
    # Sample f-string usage
    status_text = f"Temp: {current_temp}°F, Humidity: {humidity}%"
    
    print("Sample tinyDisplay application running...")

if __name__ == "__main__":
    main()
'''
    
    (temp_dir / "main.py").write_text(main_code)

def test_migration_tool():
    """Test the migration tool end-to-end"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_dir = temp_path / "old_tinydisplay"
        target_dir = temp_path / "new_tinydisplay"
        
        # Create sample project
        source_dir.mkdir()
        create_sample_tinydisplay_project(source_dir)
        
        print(f"📁 Created sample project in {source_dir}")
        
        # Test analysis only
        print("\\n🔍 Testing analysis phase...")
        os.system(f"python migration_tool.py --source {source_dir} --analysis-only --output-analysis {temp_path}/analysis.json")
        
        # Check if analysis file was created
        analysis_file = temp_path / "analysis.json"
        if analysis_file.exists():
            print(f"✅ Analysis completed successfully: {analysis_file}")
            
            # Show analysis results
            import json
            with open(analysis_file) as f:
                analysis = json.load(f)
            
            print(f"   - Found {len(analysis['widgets'])} widgets")
            print(f"   - Found {len(analysis['data_streams'])} data streams")
            print(f"   - Found {len(analysis['dynamic_values'])} dynamic values")
            
            # Show widget details
            for widget in analysis['widgets']:
                print(f"   - Widget: {widget['name']} ({widget['class_name']})")
            
            # Show data streams
            for stream in analysis['data_streams']:
                print(f"   - Data stream: {stream['key']} (used {stream['usage_count']} times)")
        
        # Test full migration
        print("\\n🏗️  Testing full migration...")
        os.system(f"python migration_tool.py --source {source_dir} --target {target_dir}")
        
        # Check if new system was generated
        if target_dir.exists():
            print(f"✅ Migration completed successfully: {target_dir}")
            
            # Show generated structure
            print("\\n📂 Generated project structure:")
            for root, dirs, files in os.walk(target_dir):
                level = root.replace(str(target_dir), '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    print(f"{subindent}{file}")
        
        print("\\n🎉 Migration tool test completed!")

if __name__ == "__main__":
    test_migration_tool() 