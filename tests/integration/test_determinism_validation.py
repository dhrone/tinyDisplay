#!/usr/bin/env python3
"""
Comprehensive Test Suite for Determinism Validation

Tests the determinism validation system to ensure tick-based animations
produce identical results across multiple executions, threads, and processes.
"""

import pytest
import time
import threading
from typing import Dict, Any

from src.tinydisplay.animation.determinism import (
    DeterminismValidator, DeterminismDebugger, DeterminismTestResult,
    AnimationExecutionTrace, validate_basic_determinism,
    run_comprehensive_determinism_suite
)
from src.tinydisplay.animation.tick_based import (
    TickAnimationEngine, TickAnimationDefinition, TickAnimationState
)
from src.tinydisplay.animation.utilities import (
    create_fade_animation, create_slide_animation, create_scale_animation,
    AnimationConfig, AnimationTiming
)


class TestDeterminismValidator:
    """Test the DeterminismValidator class."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = DeterminismValidator()
        assert validator.tolerance == 1e-10
        assert len(validator.test_results) == 0
        assert len(validator.execution_traces) == 0
        
        # Test custom tolerance
        custom_validator = DeterminismValidator(tolerance=1e-6)
        assert custom_validator.tolerance == 1e-6
    
    def test_basic_animation_determinism(self):
        """Test basic animation determinism validation."""
        validator = DeterminismValidator()
        
        # Create simple fade animation
        fade_anim = create_fade_animation(0.0, 1.0, (10.0, 20.0))
        
        # Validate determinism
        result = validator.validate_animation_determinism(
            fade_anim, "test_fade_basic", execution_count=5
        )
        
        assert isinstance(result, DeterminismTestResult)
        assert result.test_name == "test_fade_basic"
        assert result.execution_count == 5
        assert result.passed is True
        assert result.identical_results is True
        assert result.hash_consistency is True
        assert result.state_consistency is True
        assert len(result.execution_hashes) == 5
        assert len(set(result.execution_hashes)) == 1  # All hashes identical
        
        # Check performance stats
        assert 'total_execution_time' in result.performance_stats
        assert 'average_execution_time' in result.performance_stats
        assert 'executions_per_second' in result.performance_stats
        assert result.performance_stats['executions_per_second'] > 0
    
    def test_slide_animation_determinism(self):
        """Test slide animation determinism."""
        validator = DeterminismValidator()
        
        slide_anim = create_slide_animation((0, 0), (100, 50))
        result = validator.validate_animation_determinism(
            slide_anim, "test_slide_basic", execution_count=3
        )
        
        assert result.passed is True
        assert result.identical_results is True
        assert len(result.execution_hashes) == 3
        assert len(set(result.execution_hashes)) == 1
    
    def test_scale_animation_determinism(self):
        """Test scale animation determinism."""
        validator = DeterminismValidator()
        
        scale_anim = create_scale_animation((0.5, 0.5), (2.0, 2.0), (25.0, 25.0))
        result = validator.validate_animation_determinism(
            scale_anim, "test_scale_basic", execution_count=4
        )
        
        assert result.passed is True
        assert result.identical_results is True
        assert len(result.execution_hashes) == 4
        assert len(set(result.execution_hashes)) == 1
    
    def test_custom_tick_range(self):
        """Test determinism validation with custom tick range."""
        validator = DeterminismValidator()
        
        fade_anim = create_fade_animation(0.0, 1.0)
        result = validator.validate_animation_determinism(
            fade_anim, "test_custom_range", 
            execution_count=3, tick_range=(10, 50)
        )
        
        assert result.passed is True
        assert result.identical_results is True
    
    def test_multi_threaded_determinism(self):
        """Test multi-threaded determinism validation."""
        validator = DeterminismValidator()
        
        fade_anim = create_fade_animation(0.0, 1.0)
        result = validator.validate_multi_threaded_determinism(
            fade_anim, "test_multithreaded", 
            thread_count=3, executions_per_thread=2
        )
        
        assert isinstance(result, DeterminismTestResult)
        assert result.test_name == "test_multithreaded"
        assert result.execution_count == 6  # 3 threads * 2 executions
        assert result.passed is True
        assert result.identical_results is True
        assert result.hash_consistency is True
        assert len(result.execution_hashes) == 6
        assert len(set(result.execution_hashes)) == 1
        
        # Check thread-specific performance stats
        assert 'thread_count' in result.performance_stats
        assert 'executions_per_thread' in result.performance_stats
        assert result.performance_stats['thread_count'] == 3
        assert result.performance_stats['executions_per_thread'] == 2
    
    def test_multi_process_determinism(self):
        """Test multi-process determinism validation."""
        validator = DeterminismValidator()
        
        fade_anim = create_fade_animation(0.0, 1.0)
        result = validator.validate_multi_process_determinism(
            fade_anim, "test_multiprocess",
            process_count=2, executions_per_process=2
        )
        
        assert isinstance(result, DeterminismTestResult)
        assert result.test_name == "test_multiprocess"
        assert result.execution_count == 4  # 2 processes * 2 executions
        assert result.passed is True
        assert result.identical_results is True
        assert result.hash_consistency is True
        assert len(result.execution_hashes) == 4
        assert len(set(result.execution_hashes)) == 1
        
        # Check process-specific performance stats
        assert 'process_count' in result.performance_stats
        assert 'executions_per_process' in result.performance_stats
        assert result.performance_stats['process_count'] == 2
        assert result.performance_stats['executions_per_process'] == 2
    
    def test_animation_performance_benchmark(self):
        """Test animation performance benchmarking."""
        validator = DeterminismValidator()
        
        fade_anim = create_fade_animation(0.0, 1.0)
        stats = validator.benchmark_animation_performance(
            fade_anim, "test_benchmark", tick_count=100, iteration_count=10
        )
        
        assert isinstance(stats, dict)
        assert 'total_time' in stats
        assert 'total_computations' in stats
        assert 'computations_per_second' in stats
        assert 'microseconds_per_computation' in stats
        assert 'fps_capability' in stats
        assert 'iterations' in stats
        assert 'ticks_per_iteration' in stats
        
        assert stats['total_computations'] == 1000  # 100 * 10
        assert stats['iterations'] == 10
        assert stats['ticks_per_iteration'] == 100
        assert stats['computations_per_second'] > 0
        assert stats['fps_capability'] > 0
    
    def test_determinism_report_generation(self):
        """Test determinism report generation."""
        validator = DeterminismValidator()
        
        # Run several tests
        fade_anim = create_fade_animation(0.0, 1.0)
        slide_anim = create_slide_animation((0, 0), (50, 25))
        
        validator.validate_animation_determinism(fade_anim, "test_fade", execution_count=3)
        validator.validate_animation_determinism(slide_anim, "test_slide", execution_count=3)
        validator.validate_multi_threaded_determinism(fade_anim, "test_threaded", thread_count=2, executions_per_thread=2)
        
        # Generate report
        report = validator.generate_determinism_report()
        
        assert isinstance(report, dict)
        assert 'summary' in report
        assert 'test_results' in report
        assert 'performance_summary' in report
        assert 'determinism_analysis' in report
        
        # Check summary
        summary = report['summary']
        assert summary['total_tests'] == 3
        assert summary['passed_tests'] == 3
        assert summary['failed_tests'] == 0
        assert summary['success_rate'] == 1.0
        
        # Check test results
        assert len(report['test_results']) == 3
        for test_result in report['test_results']:
            assert test_result['passed'] is True
            assert test_result['identical_results'] is True
            assert test_result['hash_consistency'] is True
            assert test_result['state_consistency'] is True
        
        # Check determinism analysis
        analysis = report['determinism_analysis']
        assert analysis['hash_consistency_rate'] == 1.0
        assert analysis['state_consistency_rate'] == 1.0
        assert analysis['overall_determinism_rate'] == 1.0
    
    def test_clear_results(self):
        """Test clearing validator results."""
        validator = DeterminismValidator()
        
        # Add some test results
        fade_anim = create_fade_animation(0.0, 1.0)
        validator.validate_animation_determinism(fade_anim, "test_clear", execution_count=2)
        
        assert len(validator.test_results) == 1
        assert len(validator.execution_traces) == 1
        
        # Clear results
        validator.clear_results()
        
        assert len(validator.test_results) == 0
        assert len(validator.execution_traces) == 0


class TestAnimationExecutionTrace:
    """Test the AnimationExecutionTrace class."""
    
    def test_trace_creation(self):
        """Test creation of animation execution trace."""
        # Create mock tick states
        tick_states = {
            0: TickAnimationState(tick=0, position=(0.0, 0.0), opacity=0.0),
            30: TickAnimationState(tick=30, position=(50.0, 25.0), opacity=0.5),
            60: TickAnimationState(tick=60, position=(100.0, 50.0), opacity=1.0)
        }
        
        trace = AnimationExecutionTrace(
            animation_id="test_animation",
            start_tick=0,
            end_tick=60,
            tick_states=tick_states,
            execution_hash="",
            execution_time=0.1
        )
        
        assert trace.animation_id == "test_animation"
        assert trace.start_tick == 0
        assert trace.end_tick == 60
        assert len(trace.tick_states) == 3
        assert trace.execution_time == 0.1
    
    def test_trace_hash_computation(self):
        """Test hash computation for execution traces."""
        # Create two identical traces
        tick_states = {
            0: TickAnimationState(tick=0, position=(0.0, 0.0), opacity=0.0),
            30: TickAnimationState(tick=30, position=(50.0, 25.0), opacity=0.5)
        }
        
        trace1 = AnimationExecutionTrace(
            animation_id="test_animation",
            start_tick=0,
            end_tick=30,
            tick_states=tick_states,
            execution_hash="",
            execution_time=0.1
        )
        
        trace2 = AnimationExecutionTrace(
            animation_id="test_animation",
            start_tick=0,
            end_tick=30,
            tick_states=tick_states,
            execution_hash="",
            execution_time=0.2  # Different execution time
        )
        
        # Compute hashes
        hash1 = trace1.compute_hash()
        hash2 = trace2.compute_hash()
        
        # Hashes should be identical (execution time not included)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest length
    
    def test_trace_hash_differences(self):
        """Test that different traces produce different hashes."""
        tick_states1 = {
            0: TickAnimationState(tick=0, position=(0.0, 0.0), opacity=0.0)
        }
        
        tick_states2 = {
            0: TickAnimationState(tick=0, position=(1.0, 1.0), opacity=0.0)  # Different position
        }
        
        trace1 = AnimationExecutionTrace(
            animation_id="test_animation",
            start_tick=0,
            end_tick=30,
            tick_states=tick_states1,
            execution_hash="",
            execution_time=0.1
        )
        
        trace2 = AnimationExecutionTrace(
            animation_id="test_animation",
            start_tick=0,
            end_tick=30,
            tick_states=tick_states2,
            execution_hash="",
            execution_time=0.1
        )
        
        hash1 = trace1.compute_hash()
        hash2 = trace2.compute_hash()
        
        assert hash1 != hash2


class TestDeterminismDebugger:
    """Test the DeterminismDebugger class."""
    
    def test_debugger_initialization(self):
        """Test debugger initialization."""
        validator = DeterminismValidator()
        debugger = DeterminismDebugger(validator)
        
        assert debugger.validator is validator
    
    def test_analyze_passed_test(self):
        """Test analysis of a passed test."""
        validator = DeterminismValidator()
        debugger = DeterminismDebugger(validator)
        
        # Run a test that should pass
        fade_anim = create_fade_animation(0.0, 1.0)
        validator.validate_animation_determinism(fade_anim, "test_passed", execution_count=3)
        
        # Analyze the test
        analysis = debugger.analyze_failed_test("test_passed")
        
        assert 'message' in analysis
        assert 'passed' in analysis['message']
    
    def test_analyze_nonexistent_test(self):
        """Test analysis of a nonexistent test."""
        validator = DeterminismValidator()
        debugger = DeterminismDebugger(validator)
        
        analysis = debugger.analyze_failed_test("nonexistent_test")
        
        assert 'error' in analysis
        assert 'not found' in analysis['error']
    
    def test_compare_execution_traces(self):
        """Test comparison of execution traces."""
        validator = DeterminismValidator()
        debugger = DeterminismDebugger(validator)
        
        # Run a test to generate traces
        fade_anim = create_fade_animation(0.0, 1.0)
        validator.validate_animation_determinism(fade_anim, "test_compare", execution_count=3)
        
        # Compare traces
        comparison = debugger.compare_execution_traces("test_compare", 0, 1)
        
        assert isinstance(comparison, dict)
        assert 'execution1_hash' in comparison
        assert 'execution2_hash' in comparison
        assert 'hashes_match' in comparison
        assert 'tick_differences' in comparison
        assert 'state_differences' in comparison
        
        # For deterministic animations, hashes should match
        assert comparison['hashes_match'] is True
        assert len(comparison['tick_differences']) == 0
        assert len(comparison['state_differences']) == 0
    
    def test_compare_traces_insufficient_data(self):
        """Test trace comparison with insufficient data."""
        validator = DeterminismValidator()
        debugger = DeterminismDebugger(validator)
        
        # Try to compare without enough traces
        comparison = debugger.compare_execution_traces("nonexistent_test", 0, 1)
        
        assert 'error' in comparison
        assert 'Not enough execution traces' in comparison['error']


class TestConvenienceFunctions:
    """Test convenience functions for determinism validation."""
    
    def test_validate_basic_determinism(self):
        """Test basic determinism validation function."""
        fade_anim = create_fade_animation(0.0, 1.0)
        result = validate_basic_determinism(fade_anim, "test_convenience")
        
        assert isinstance(result, DeterminismTestResult)
        assert result.test_name == "test_convenience"
        assert result.passed is True
        assert result.identical_results is True
        assert result.hash_consistency is True
        assert result.state_consistency is True
    
    def test_comprehensive_determinism_suite(self):
        """Test comprehensive determinism validation suite."""
        report = run_comprehensive_determinism_suite()
        
        assert isinstance(report, dict)
        assert 'summary' in report
        assert 'test_results' in report
        assert 'determinism_analysis' in report
        
        # Should have multiple tests
        assert report['summary']['total_tests'] >= 5
        
        # All tests should pass for basic animations
        assert report['summary']['success_rate'] == 1.0
        assert report['determinism_analysis']['overall_determinism_rate'] == 1.0


class TestDeterminismWithComplexAnimations:
    """Test determinism with more complex animation scenarios."""
    
    def test_complex_easing_determinism(self):
        """Test determinism with complex easing functions."""
        validator = DeterminismValidator()
        
        # Test with different easing functions
        easing_functions = ["linear", "ease_in", "ease_out", "ease_in_out", "bounce", "elastic"]
        
        for easing in easing_functions:
            config = AnimationConfig(
                timing=AnimationTiming(duration_ticks=60),
                easing=easing
            )
            
            fade_anim = create_fade_animation(0.0, 1.0, config=config)
            result = validator.validate_animation_determinism(
                fade_anim, f"test_easing_{easing}", execution_count=3
            )
            
            assert result.passed is True, f"Determinism failed for easing: {easing}"
            assert result.identical_results is True
            assert result.hash_consistency is True
    
    def test_repeat_animation_determinism(self):
        """Test determinism with repeating animations."""
        validator = DeterminismValidator()
        
        config = AnimationConfig(
            timing=AnimationTiming(duration_ticks=30),
            repeat_count=3,
            repeat_mode="restart"
        )
        
        fade_anim = create_fade_animation(0.0, 1.0, config=config)
        result = validator.validate_animation_determinism(
            fade_anim, "test_repeat", execution_count=3, tick_range=(0, 120)
        )
        
        assert result.passed is True
        assert result.identical_results is True
        assert result.hash_consistency is True
    
    def test_mirror_repeat_determinism(self):
        """Test determinism with mirror repeat mode."""
        validator = DeterminismValidator()
        
        config = AnimationConfig(
            timing=AnimationTiming(duration_ticks=30),
            repeat_count=2,
            repeat_mode="mirror"
        )
        
        slide_anim = create_slide_animation((0, 0), (100, 0), config=config)
        result = validator.validate_animation_determinism(
            slide_anim, "test_mirror", execution_count=3, tick_range=(0, 80)
        )
        
        assert result.passed is True
        assert result.identical_results is True
        assert result.hash_consistency is True
    
    def test_custom_properties_determinism(self):
        """Test determinism with custom properties."""
        validator = DeterminismValidator()
        
        # Create animation with custom properties
        start_state = TickAnimationState(
            tick=0,
            position=(0.0, 0.0),
            opacity=1.0,
            custom_properties={'brightness': 0.5, 'contrast': 1.0}
        )
        
        end_state = TickAnimationState(
            tick=60,
            position=(100.0, 50.0),
            opacity=1.0,
            custom_properties={'brightness': 1.5, 'contrast': 1.2}
        )
        
        animation_def = TickAnimationDefinition(
            start_tick=0,
            duration_ticks=60,
            start_state=start_state,
            end_state=end_state,
            easing="linear"
        )
        
        result = validator.validate_animation_determinism(
            animation_def, "test_custom_props", execution_count=3
        )
        
        assert result.passed is True
        assert result.identical_results is True
        assert result.hash_consistency is True


class TestPerformanceBenchmarks:
    """Test performance benchmarking capabilities."""
    
    def test_fade_animation_performance(self):
        """Test fade animation performance benchmarking."""
        validator = DeterminismValidator()
        
        fade_anim = create_fade_animation(0.0, 1.0)
        stats = validator.benchmark_animation_performance(
            fade_anim, "fade_benchmark", tick_count=60, iteration_count=50
        )
        
        # Should be able to compute many states per second
        assert stats['computations_per_second'] > 1000
        assert stats['fps_capability'] > 60  # Should support 60fps easily
        assert stats['microseconds_per_computation'] < 1000  # Less than 1ms per computation
    
    def test_complex_animation_performance(self):
        """Test performance with complex animations."""
        validator = DeterminismValidator()
        
        # Create complex animation with bounce easing
        config = AnimationConfig(
            timing=AnimationTiming(duration_ticks=120),
            easing="bounce",
            repeat_count=2
        )
        
        scale_anim = create_scale_animation((0.0, 0.0), (2.0, 2.0), config=config)
        stats = validator.benchmark_animation_performance(
            scale_anim, "complex_benchmark", tick_count=240, iteration_count=20
        )
        
        # Even complex animations should be performant
        assert stats['computations_per_second'] > 500
        assert stats['fps_capability'] > 30  # Should support at least 30fps
    
    def test_performance_consistency(self):
        """Test that performance is consistent across runs."""
        validator = DeterminismValidator()
        
        fade_anim = create_fade_animation(0.0, 1.0)
        
        # Run benchmark multiple times
        stats_runs = []
        for i in range(3):
            stats = validator.benchmark_animation_performance(
                fade_anim, f"consistency_test_{i}", tick_count=100, iteration_count=10
            )
            stats_runs.append(stats['computations_per_second'])
        
        # Performance should be relatively consistent (within 50% variance)
        avg_performance = sum(stats_runs) / len(stats_runs)
        for performance in stats_runs:
            variance = abs(performance - avg_performance) / avg_performance
            assert variance < 0.5, f"Performance variance too high: {variance}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 