#!/usr/bin/env python3
"""
Widget-Specific Determinism Validation Tests

Tests deterministic behavior for all core widget animation methods to ensure
that widget animations produce identical results across multiple executions.
"""

import pytest
import time
from typing import Dict, Any, List

from src.tinydisplay.animation.determinism import DeterminismValidator, DeterminismTestResult
from src.tinydisplay.animation.tick_based import TickAnimationEngine, TickAnimationDefinition
from src.tinydisplay.widgets.text import TextWidget
from src.tinydisplay.widgets.image import ImageWidget
from src.tinydisplay.widgets.progress import ProgressBarWidget
from src.tinydisplay.widgets.shapes import ShapeWidget, RectangleWidget
from src.tinydisplay.rendering.engine import RenderingEngine


class MockRenderingEngine:
    """Mock rendering engine for testing widget animations."""
    
    def __init__(self):
        self.tick_animation_engine = TickAnimationEngine()
        self.current_tick = 0
        self.frame_count = 0
    
    def advance_tick(self):
        """Advance to next tick."""
        self.tick_animation_engine.advance_tick()
        self.current_tick = self.tick_animation_engine.current_tick
    
    def get_frame_state(self, tick: int) -> Dict[str, Any]:
        """Get frame state at specific tick."""
        return self.tick_animation_engine.compute_frame_state(tick)


class TestTextWidgetDeterminism:
    """Test deterministic behavior of TextWidget animations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = DeterminismValidator()
        self.engine = MockRenderingEngine()
    
    def test_text_fade_in_determinism(self):
        """Test TextWidget fade_in_animated determinism."""
        def create_fade_in_animation():
            widget = TextWidget("test_text", "Hello World")
            # Note: Widgets don't have set_rendering_engine method, they get engine through context
            
            # Start fade in animation
            success = widget.fade_in_animated(duration_ticks=60)
            assert success is True
            
            # Simulate animation execution
            states = {}
            for tick in range(0, 80):
                self.engine.advance_tick()
                widget.update_animations(current_tick=tick)
                
                # Capture widget state
                states[tick] = {
                    'alpha': widget.alpha,
                    'position': widget.position,
                    'visible': widget.visible
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(5):
            self.engine = MockRenderingEngine()  # Fresh engine
            states = create_fade_in_animation()
            execution_states.append(states)
        
        # Validate all executions are identical
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Execution {i} differs from reference"
    
    def test_text_color_animation_determinism(self):
        """Test TextWidget set_text_color_animated determinism."""
        def create_color_animation():
            widget = TextWidget("Color Test")
            widget.set_text_color((255, 0, 0))  # Start with red
            
            # Start color animation to blue
            success = widget.set_text_color_animated((0, 0, 255), duration_ticks=60)
            assert success is True
            
            # Simulate animation execution
            states = {}
            for tick in range(0, 80):
                self.engine.advance_tick()
                widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'text_color': widget.font_style.color,
                    'position': widget.position
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(3):
            self.engine = MockRenderingEngine()
            states = create_color_animation()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Color animation execution {i} differs"
    
    def test_text_typewriter_determinism(self):
        """Test TextWidget typewriter_effect_animated determinism."""
        def create_typewriter_animation():
            widget = TextWidget("test_text", "Typewriter Effect Test")
            
            # Start typewriter animation
            success = widget.typewriter_effect_animated(duration_ticks=120)
            assert success is True
            
            # Simulate animation execution
            states = {}
            for tick in range(0, 140):
                self.engine.advance_tick()
                widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'displayed_text': widget.text,
                    'position': widget.position
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(3):
            self.engine = MockRenderingEngine()
            states = create_typewriter_animation()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Typewriter animation execution {i} differs"


class TestImageWidgetDeterminism:
    """Test deterministic behavior of ImageWidget animations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = DeterminismValidator()
        self.engine = MockRenderingEngine()
    
    def test_image_fade_determinism(self):
        """Test ImageWidget fade animations determinism."""
        def create_fade_animation():
            widget = ImageWidget("test_image", "test.png")
            
            # Start fade out animation
            success = widget.fade_out_animated(duration_ticks=60)
            assert success is True
            
            # Simulate animation execution
            states = {}
            for tick in range(0, 80):
                self.engine.advance_tick()
                widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'alpha': widget.alpha,
                    'opacity': getattr(widget, 'opacity', 1.0),
                    'position': widget.position
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(4):
            self.engine = MockRenderingEngine()
            states = create_fade_animation()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Image fade execution {i} differs"
    
    def test_image_brightness_animation_determinism(self):
        """Test ImageWidget brightness animation determinism."""
        def create_brightness_animation():
            widget = ImageWidget("test_image", "test.png")
            
            # Start brightness animation
            success = widget.set_brightness_animated(0.5, duration_ticks=60)
            assert success is True
            
            # Simulate animation execution
            states = {}
            for tick in range(0, 80):
                self.engine.advance_tick()
                widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'brightness': getattr(widget, 'brightness', 1.0),
                    'position': widget.position
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(3):
            self.engine = MockRenderingEngine()
            states = create_brightness_animation()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Brightness animation execution {i} differs"


class TestProgressBarWidgetDeterminism:
    """Test deterministic behavior of ProgressBarWidget animations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = DeterminismValidator()
        self.engine = MockRenderingEngine()
    
    def test_progress_animation_determinism(self):
        """Test ProgressBarWidget progress animation determinism."""
        def create_progress_animation():
            widget = ProgressBarWidget(progress=0.0, widget_id="test_progress")
            widget.size = (200, 20)  # Set size after creation
            
            # Start progress animation
            success = widget.set_progress_animated(0.8, duration_ticks=60)
            assert success is True
            
            # Simulate animation execution
            states = {}
            for tick in range(0, 80):
                self.engine.advance_tick()
                widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'progress': widget.progress,
                    'animated_progress': widget.animated_progress,
                    'position': widget.position
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(4):
            self.engine = MockRenderingEngine()
            states = create_progress_animation()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Progress animation execution {i} differs"
    
    def test_progress_pulse_determinism(self):
        """Test ProgressBarWidget pulse animation determinism."""
        def create_pulse_animation():
            widget = ProgressBarWidget(progress=0.5, widget_id="test_progress")
            widget.size = (200, 20)
            
            # Start pulse animation
            success = widget.pulse_animated(duration_ticks=120)
            assert success is True
            
            # Simulate animation execution
            states = {}
            for tick in range(0, 140):
                self.engine.advance_tick()
                widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'progress': widget.progress,
                    'animated_progress': widget.animated_progress,
                    'position': widget.position
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(3):
            self.engine = MockRenderingEngine()
            states = create_pulse_animation()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Pulse animation execution {i} differs"


class TestShapeWidgetDeterminism:
    """Test deterministic behavior of ShapeWidget animations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = DeterminismValidator()
        self.engine = MockRenderingEngine()
    
    def test_shape_fade_determinism(self):
        """Test ShapeWidget fade animation determinism."""
        def create_shape_fade_animation():
            # Fix: RectangleWidget constructor signature - width and height are positional
            widget = RectangleWidget(100, 50)  # width, height
            
            # Start fade animation
            success = widget.fade_out_animated(duration_ticks=60)
            assert success is True
            
            # Simulate animation execution
            states = {}
            for tick in range(0, 80):
                self.engine.advance_tick()
                widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'alpha': widget.alpha,
                    'width': widget.width,
                    'height': widget.height,
                    'position': widget.position
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(4):
            self.engine = MockRenderingEngine()
            states = create_shape_fade_animation()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Shape fade execution {i} differs"
    
    def test_rectangle_size_animation_determinism(self):
        """Test RectangleWidget size animation determinism."""
        def create_size_animation():
            widget = RectangleWidget(50, 25)  # width, height
            
            # Start size animation
            success = widget.set_size_animated(100, 50, duration_ticks=60)
            assert success is True
            
            # Simulate animation execution
            states = {}
            for tick in range(0, 80):
                self.engine.advance_tick()
                widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'width': widget.width,
                    'height': widget.height,
                    'position': widget.position
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(3):
            self.engine = MockRenderingEngine()
            states = create_size_animation()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Size animation execution {i} differs"
    
    def test_shape_color_animation_determinism(self):
        """Test ShapeWidget color animation determinism."""
        def create_color_animation():
            widget = RectangleWidget(100, 50)  # width, height
            widget.set_fill_color((255, 0, 0))  # Start with red
            
            # Start color animation to blue
            success = widget.set_fill_color_animated((0, 0, 255), duration_ticks=60)
            assert success is True
            
            # Simulate animation execution
            states = {}
            for tick in range(0, 80):
                self.engine.advance_tick()
                widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'fill_color': widget.style.fill_color,
                    'position': widget.position
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(3):
            self.engine = MockRenderingEngine()
            states = create_color_animation()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Color animation execution {i} differs"


class TestCrossWidgetDeterminism:
    """Test deterministic behavior across multiple widgets."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = DeterminismValidator()
        self.engine = MockRenderingEngine()
    
    def test_multiple_widget_animations_determinism(self):
        """Test multiple widget animations running simultaneously."""
        def create_multi_widget_animation():
            # Create multiple widgets with corrected constructors
            text_widget = TextWidget("Test Text")
            progress_widget = ProgressBarWidget(progress=0.0, widget_id="progress")
            progress_widget.size = (200, 20)
            rect_widget = RectangleWidget(50, 25)  # width, height
            
            # Start animations on all widgets
            text_widget.fade_in_animated(duration_ticks=60)
            progress_widget.set_progress_animated(1.0, duration_ticks=60)
            rect_widget.set_size_animated(100, 50, duration_ticks=60)
            
            # Simulate animation execution
            states = {}
            for tick in range(0, 80):
                self.engine.advance_tick()
                
                # Update all widgets
                text_widget.update_animations(current_tick=tick)
                progress_widget.update_animations(current_tick=tick)
                rect_widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'text_alpha': text_widget.alpha,
                    'progress_value': progress_widget.progress,
                    'rect_width': rect_widget.width,
                    'rect_height': rect_widget.height
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(3):
            self.engine = MockRenderingEngine()
            states = create_multi_widget_animation()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Multi-widget execution {i} differs"
    
    def test_sequential_widget_animations_determinism(self):
        """Test sequential widget animations determinism."""
        def create_sequential_animation():
            text_widget = TextWidget("text", "Sequential Test")
            rect_widget = RectangleWidget(50, 25)  # width, height
            
            # Start first animation
            text_widget.fade_in_animated(duration_ticks=30)
            
            # Simulate first part
            states = {}
            for tick in range(0, 40):
                self.engine.advance_tick()
                text_widget.update_animations(current_tick=tick)
                
                # Start second animation at tick 30
                if tick == 30:
                    rect_widget.set_size_animated(100, 50, duration_ticks=30)
                
                if tick >= 30:
                    rect_widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'text_alpha': text_widget.alpha,
                    'rect_width': rect_widget.width,
                    'rect_height': rect_widget.height
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(3):
            self.engine = MockRenderingEngine()
            states = create_sequential_animation()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Sequential animation execution {i} differs"


class TestWidgetAnimationPerformance:
    """Test widget animation performance consistency."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = DeterminismValidator()
        self.engine = MockRenderingEngine()
    
    def test_widget_animation_performance_consistency(self):
        """Test widget animation performance is consistent across runs."""
        def benchmark_widget_animation():
            widget = TextWidget("test_text", "Performance Test")
            
            start_time = time.time()
            
            # Start animation
            widget.fade_in_animated(duration_ticks=60)
            
            # Simulate animation execution
            for tick in range(0, 80):
                self.engine.advance_tick()
                widget.update_animations(current_tick=tick)
            
            return time.time() - start_time
        
        # Run multiple performance tests
        execution_times = []
        for i in range(5):
            self.engine = MockRenderingEngine()
            exec_time = benchmark_widget_animation()
            execution_times.append(exec_time)
        
        # Validate performance consistency (within 50% variance)
        avg_time = sum(execution_times) / len(execution_times)
        for i, exec_time in enumerate(execution_times):
            variance = abs(exec_time - avg_time) / avg_time
            assert variance < 0.5, f"Performance execution {i} variance too high: {variance:.2%}"
    
    def test_multiple_widget_performance(self):
        """Test multiple widget animation performance consistency."""
        def benchmark_multiple_widgets():
            widgets = []
            for i in range(10):
                widget = TextWidget(f"widget_{i}", f"Text {i}")
                widgets.append(widget)
            
            start_time = time.time()
            
            # Start animations on all widgets
            for widget in widgets:
                widget.fade_in_animated(duration_ticks=60)
            
            # Simulate animation execution
            for tick in range(0, 80):
                self.engine.advance_tick()
                for widget in widgets:
                    widget.update_animations(current_tick=tick)
            
            return time.time() - start_time
        
        # Run multiple performance tests
        execution_times = []
        for i in range(3):
            self.engine = MockRenderingEngine()
            exec_time = benchmark_multiple_widgets()
            execution_times.append(exec_time)
        
        # Validate performance consistency
        avg_time = sum(execution_times) / len(execution_times)
        for i, exec_time in enumerate(execution_times):
            variance = abs(exec_time - avg_time) / avg_time
            assert variance < 0.5, f"Multi-widget performance execution {i} variance too high: {variance:.2%}"


class TestWidgetAnimationEdgeCases:
    """Test widget animation edge cases for determinism."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = DeterminismValidator()
        self.engine = MockRenderingEngine()
    
    def test_zero_duration_animation_determinism(self):
        """Test zero duration animation determinism."""
        def create_zero_duration_animation():
            widget = TextWidget("test_text", "Zero Duration Test")
            
            # Start zero duration animation (should complete immediately)
            success = widget.fade_in_animated(duration_ticks=0)
            assert success is True
            
            # Simulate animation execution
            states = {}
            for tick in range(0, 10):
                self.engine.advance_tick()
                widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'alpha': widget.alpha,
                    'position': widget.position
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(3):
            self.engine = MockRenderingEngine()
            states = create_zero_duration_animation()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Zero duration execution {i} differs"
    
    def test_overlapping_animations_determinism(self):
        """Test overlapping animations determinism."""
        def create_overlapping_animations():
            widget = TextWidget("test_text", "Overlapping Test")
            
            # Start first animation
            widget.fade_in_animated(duration_ticks=60)
            
            # Simulate animation execution with overlapping animation
            states = {}
            for tick in range(0, 100):
                self.engine.advance_tick()
                
                # Start second animation at tick 30 (overlapping)
                if tick == 30:
                    widget.set_alpha_animated(0.5, duration=1.0)  # Time-based for variety
                
                widget.update_animations(current_tick=tick)
                
                states[tick] = {
                    'alpha': widget.alpha,
                    'position': widget.position
                }
            
            return states
        
        # Run multiple executions
        execution_states = []
        for i in range(3):
            self.engine = MockRenderingEngine()
            states = create_overlapping_animations()
            execution_states.append(states)
        
        # Validate determinism
        reference_states = execution_states[0]
        for i, states in enumerate(execution_states[1:], 1):
            assert states == reference_states, f"Overlapping animation execution {i} differs"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 