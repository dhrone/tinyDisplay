#!/usr/bin/env python3
"""
Complex Legacy tinyDisplay Application
Demonstrates multi-canvas, widget hierarchies, and custom widgets
"""

class Canvas:
    def __init__(self, width=128, height=64):
        self.width = width
        self.height = height
        self.widgets = []
    
    def add(self, widget):
        self.widgets.append(widget)

class CustomGaugeWidget:
    """Custom gauge widget with complex rendering"""
    def __init__(self, min_value=0, max_value=100):
        self.min_value = min_value
        self.max_value = max_value
        self.current_value = 0
        self.color = "blue"
        self.x = 0
        self.y = 0
    
    def update_value(self, value):
        self.current_value = max(self.min_value, min(self.max_value, value))
    
    def set_range(self, min_val, max_val):
        self.min_value = min_val
        self.max_value = max_val
    
    def render_needle(self):
        # Complex needle rendering logic
        pass
    
    def render(self):
        # Custom rendering implementation
        pass

class ComplexChartWidget:
    """Complex chart widget with multiple data series"""
    def __init__(self, chart_type="bar"):
        self.chart_type = chart_type
        self.data_series = []
        self.x = 0
        self.y = 0
        self.width = 200
        self.height = 150
    
    def add_data(self, series_name, data):
        self.data_series.append({"name": series_name, "data": data})
    
    def update_chart(self):
        # Update chart with new data
        pass
    
    def render_axes(self):
        # Render chart axes
        pass
    
    def render_legend(self):
        # Render chart legend
        pass
    
    def animate_bars(self):
        # Animate bar chart
        pass

class ContainerWidget:
    """Container widget for hierarchical layouts"""
    def __init__(self):
        self.children = []
        self.x = 0
        self.y = 0
        self.padding = 10
    
    def add_child(self, widget):
        self.children.append(widget)
    
    def layout_children(self):
        # Layout children with padding
        y_offset = self.y
        for child in self.children:
            child.y = y_offset
            y_offset += child.height + self.padding

# Multi-canvas application setup
main_canvas = Canvas(width=128, height=64)
secondary_canvas = Canvas(width=64, height=32)
status_canvas = Canvas(width=128, height=32)

# Create widgets for main canvas
text_widget_1 = {"type": "text", "content": "System Status", "x": 10, "y": 10}
text_widget_2 = {"type": "text", "content": "CPU Usage", "x": 10, "y": 25}
progress_widget_1 = {"type": "progress", "value": 0.75, "x": 80, "y": 25, "width": 40}

# Create custom widgets
cpu_gauge = CustomGaugeWidget(min_value=0, max_value=100)
cpu_gauge.x = 10
cpu_gauge.y = 40
cpu_gauge.update_value(75)

memory_chart = ComplexChartWidget(chart_type="line")
memory_chart.x = 60
memory_chart.y = 40
memory_chart.add_data("Memory Usage", [45, 50, 55, 60, 58])
memory_chart.add_data("Swap Usage", [10, 12, 15, 18, 16])

# Create widget hierarchy
status_container = ContainerWidget()
status_container.x = 10
status_container.y = 10

status_text = {"type": "text", "content": "Network Status", "x": 0, "y": 0, "height": 15}
network_gauge = CustomGaugeWidget(min_value=0, max_value=1000)
network_gauge.current_value = 250

status_container.add_child(status_text)
status_container.add_child(network_gauge)
status_container.layout_children()

# Add widgets to canvases
main_canvas.add(text_widget_1)
main_canvas.add(text_widget_2)
main_canvas.add(progress_widget_1)
main_canvas.add(cpu_gauge)
main_canvas.add(memory_chart)

secondary_canvas.add({"type": "text", "content": "Alerts", "x": 5, "y": 5})
secondary_canvas.add({"type": "text", "content": "No alerts", "x": 5, "y": 20})

status_canvas.add(status_container)

# Animation patterns
def animate_widgets():
    # Marquee animation for status text
    for i in range(100):
        text_widget_1["x"] = (text_widget_1["x"] + 1) % 128
    
    # Fade animation for alerts
    for widget in secondary_canvas.widgets:
        if widget.get("type") == "text":
            widget["alpha"] = 0.5

# Data binding patterns
def update_data():
    # Dynamic value updates
    import random
    cpu_usage = random.uniform(0.3, 0.9)
    memory_usage = random.uniform(0.4, 0.8)
    
    # Update widgets with new data
    progress_widget_1["value"] = cpu_usage
    cpu_gauge.update_value(cpu_usage * 100)
    
    # Update chart data
    memory_chart.data_series[0]["data"].append(memory_usage * 100)
    if len(memory_chart.data_series[0]["data"]) > 10:
        memory_chart.data_series[0]["data"].pop(0)

def main():
    """Main application loop"""
    while True:
        update_data()
        animate_widgets()
        
        # Render all canvases
        for canvas in [main_canvas, secondary_canvas, status_canvas]:
            for widget in canvas.widgets:
                if hasattr(widget, 'render'):
                    widget.render()

if __name__ == "__main__":
    main() 