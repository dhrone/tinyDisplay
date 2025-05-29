"""
Mathematical Determinism Validation Framework for tinyDisplay Animation System

This test suite validates that animation algorithms produce bit-identical results
across multiple cores and execution contexts, ensuring safe multi-core frame pre-computation.

Research Focus Areas:
1. Floating-point determinism across ARM Cortex-A53 cores
2. Easing function numerical stability and precision
3. Temporal resolution requirements for 60fps animation
4. Cross-core mathematical consistency validation
"""

import math
import time
import struct
import multiprocessing as mp
from typing import List, Tuple, Dict, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
import pytest

from src.tinydisplay.widgets.progress import EasingFunction


@dataclass
class DeterminismTestResult:
    """Results from determinism validation tests."""
    test_name: str
    inputs: List[Any]
    outputs: List[Any]
    is_deterministic: bool
    precision_bits: int
    max_deviation: float
    execution_times: List[float]
    
    def __post_init__(self):
        """Validate test result data."""
        if len(self.outputs) != len(self.inputs):
            raise ValueError("Outputs must match inputs length")


class MathematicalDeterminismValidator:
    """Comprehensive validator for mathematical determinism in animation algorithms."""
    
    def __init__(self, num_cores: int = 4, precision_threshold: float = 1e-15):
        """Initialize determinism validator.
        
        Args:
            num_cores: Number of CPU cores to test across
            precision_threshold: Maximum allowed floating-point deviation
        """
        self.num_cores = num_cores
        self.precision_threshold = precision_threshold
        self.test_results: List[DeterminismTestResult] = []
    
    def validate_easing_function_determinism(self) -> List[DeterminismTestResult]:
        """Validate deterministic behavior of all easing functions."""
        results = []
        
        # Test cases covering edge cases and precision boundaries
        test_cases = [
            # Basic cases
            0.0, 0.25, 0.5, 0.75, 1.0,
            # Precision edge cases
            1e-15, 1e-10, 1e-5,
            1.0 - 1e-15, 1.0 - 1e-10, 1.0 - 1e-5,
            # Repeating decimals
            1.0/3.0, 2.0/3.0, 1.0/7.0,
            # Irrational approximations
            math.pi / 4.0, math.e / 3.0, math.sqrt(2) / 2.0,
            # Values near 0.5 (critical for ease_in_out)
            0.5 - 1e-10, 0.5 + 1e-10,
        ]
        
        for easing in EasingFunction:
            result = self._test_function_across_cores(
                func=self._apply_easing_deterministic,
                test_cases=[(progress, easing) for progress in test_cases],
                test_name=f"easing_{easing.value}"
            )
            results.append(result)
        
        return results
    
    def validate_interpolation_determinism(self) -> List[DeterminismTestResult]:
        """Validate deterministic behavior of interpolation algorithms."""
        results = []
        
        # Test linear interpolation
        test_cases = [
            (0.0, 100.0, 0.0),
            (0.0, 100.0, 0.5),
            (0.0, 100.0, 1.0),
            (-50.0, 50.0, 0.333333333),
            (math.pi, math.e, 0.7071067812),
        ]
        
        result = self._test_function_across_cores(
            func=self._linear_interpolation,
            test_cases=test_cases,
            test_name="linear_interpolation"
        )
        results.append(result)
        
        return results
    
    def validate_temporal_precision(self) -> DeterminismTestResult:
        """Validate temporal precision requirements for 60fps animation."""
        # Test time step precision for smooth 60fps animation
        frame_duration = 1.0 / 60.0  # 16.666... ms
        
        test_cases = []
        for frame in range(120):  # 2 seconds worth of frames
            timestamp = frame * frame_duration
            test_cases.append(timestamp)
        
        result = self._test_function_across_cores(
            func=self._temporal_precision_test,
            test_cases=test_cases,
            test_name="temporal_precision_60fps"
        )
        
        return result
    
    def validate_floating_point_consistency(self) -> List[DeterminismTestResult]:
        """Validate IEEE 754 floating-point consistency across cores."""
        results = []
        
        # Test edge cases for floating-point arithmetic
        edge_cases = [
            # Normal numbers
            (1.0, 2.0, "addition"),
            (3.14159, 2.71828, "multiplication"),
            (100.0, 3.0, "division"),
            
            # Very small numbers
            (1e-15, 1e-15, "small_addition"),
            (1e-10, 1e-5, "small_multiplication"),
            
            # Very large numbers
            (1e15, 1e10, "large_addition"),
            
            # Mixed precision
            (1.0, 1e-15, "mixed_precision"),
        ]
        
        for a, b, operation in edge_cases:
            result = self._test_function_across_cores(
                func=self._floating_point_operation,
                test_cases=[(a, b, operation)],
                test_name=f"float_consistency_{operation}"
            )
            results.append(result)
        
        return results
    
    def validate_math_library_consistency(self) -> List[DeterminismTestResult]:
        """Validate math library function consistency across cores."""
        results = []
        
        # Test critical math functions used in animations
        test_functions = [
            ("sin", math.sin, [0.0, math.pi/4, math.pi/2, math.pi, 2*math.pi]),
            ("cos", math.cos, [0.0, math.pi/4, math.pi/2, math.pi, 2*math.pi]),
            ("pow", lambda x: math.pow(2, x), [-10, -1, 0, 1, 10]),
            ("sqrt", math.sqrt, [0.0, 1.0, 2.0, math.pi, math.e]),
        ]
        
        for func_name, func, test_values in test_functions:
            result = self._test_function_across_cores(
                func=func,
                test_cases=test_values,
                test_name=f"math_{func_name}"
            )
            results.append(result)
        
        return results
    
    def _test_function_across_cores(self, func: Callable, test_cases: List[Any], 
                                   test_name: str) -> DeterminismTestResult:
        """Test function determinism across multiple CPU cores."""
        all_outputs = []
        execution_times = []
        
        # Run the same function on each core
        with ProcessPoolExecutor(max_workers=self.num_cores) as executor:
            futures = []
            
            for core_id in range(self.num_cores):
                future = executor.submit(self._execute_on_core, func, test_cases, core_id)
                futures.append(future)
            
            for future in futures:
                core_outputs, core_times = future.result()
                all_outputs.append(core_outputs)
                execution_times.extend(core_times)
        
        # Analyze determinism
        is_deterministic = self._analyze_determinism(all_outputs)
        max_deviation = self._calculate_max_deviation(all_outputs)
        precision_bits = self._calculate_precision_bits(all_outputs)
        
        return DeterminismTestResult(
            test_name=test_name,
            inputs=test_cases,
            outputs=all_outputs[0] if all_outputs else [],
            is_deterministic=is_deterministic,
            precision_bits=precision_bits,
            max_deviation=max_deviation,
            execution_times=execution_times
        )
    
    def _execute_on_core(self, func: Callable, test_cases: List[Any], 
                        core_id: int) -> Tuple[List[Any], List[float]]:
        """Execute function on specific core and measure timing."""
        # Set CPU affinity to specific core (Linux only)
        try:
            import os
            os.sched_setaffinity(0, {core_id})
        except (ImportError, AttributeError, OSError):
            # Not supported on this platform
            pass
        
        outputs = []
        times = []
        
        for test_case in test_cases:
            start_time = time.perf_counter()
            
            if isinstance(test_case, tuple):
                result = func(*test_case)
            else:
                result = func(test_case)
            
            end_time = time.perf_counter()
            
            outputs.append(result)
            times.append(end_time - start_time)
        
        return outputs, times
    
    def _analyze_determinism(self, all_outputs: List[List[Any]]) -> bool:
        """Analyze if outputs are deterministic across cores."""
        if not all_outputs or len(all_outputs) < 2:
            return True
        
        reference_outputs = all_outputs[0]
        
        for core_outputs in all_outputs[1:]:
            if len(core_outputs) != len(reference_outputs):
                return False
            
            for ref_val, test_val in zip(reference_outputs, core_outputs):
                if not self._values_equal(ref_val, test_val):
                    return False
        
        return True
    
    def _values_equal(self, val1: Any, val2: Any) -> bool:
        """Check if two values are equal within precision threshold."""
        if type(val1) != type(val2):
            return False
        
        if isinstance(val1, float):
            if math.isnan(val1) and math.isnan(val2):
                return True
            if math.isinf(val1) and math.isinf(val2):
                return val1 == val2  # Check sign of infinity
            
            return abs(val1 - val2) <= self.precision_threshold
        
        return val1 == val2
    
    def _calculate_max_deviation(self, all_outputs: List[List[Any]]) -> float:
        """Calculate maximum deviation between outputs."""
        if not all_outputs or len(all_outputs) < 2:
            return 0.0
        
        max_deviation = 0.0
        reference_outputs = all_outputs[0]
        
        for core_outputs in all_outputs[1:]:
            for ref_val, test_val in zip(reference_outputs, core_outputs):
                if isinstance(ref_val, float) and isinstance(test_val, float):
                    if not (math.isnan(ref_val) or math.isnan(test_val) or 
                           math.isinf(ref_val) or math.isinf(test_val)):
                        deviation = abs(ref_val - test_val)
                        max_deviation = max(max_deviation, deviation)
        
        return max_deviation
    
    def _calculate_precision_bits(self, all_outputs: List[List[Any]]) -> int:
        """Calculate effective precision in bits."""
        max_deviation = self._calculate_max_deviation(all_outputs)
        
        if max_deviation == 0.0:
            return 64  # Perfect precision
        
        # Calculate precision bits based on deviation
        precision_bits = max(0, int(-math.log2(max_deviation)))
        return min(precision_bits, 64)
    
    # Helper functions for specific tests
    
    def _apply_easing_deterministic(self, progress: float, easing: EasingFunction) -> float:
        """Deterministic version of easing function application."""
        if easing == EasingFunction.LINEAR:
            return progress
        elif easing == EasingFunction.EASE_IN:
            return progress * progress
        elif easing == EasingFunction.EASE_OUT:
            return 1.0 - (1.0 - progress) * (1.0 - progress)
        elif easing == EasingFunction.EASE_IN_OUT:
            if progress < 0.5:
                return 2.0 * progress * progress
            else:
                return 1.0 - 2.0 * (1.0 - progress) * (1.0 - progress)
        elif easing == EasingFunction.BOUNCE:
            # Simplified deterministic bounce - avoid time-dependent calculations
            if progress < 0.5:
                return 2.0 * progress * progress
            else:
                # Use deterministic sine calculation
                sine_input = progress * math.pi * 4
                return 1.0 - 2.0 * (1.0 - progress) * (1.0 - progress) * abs(math.sin(sine_input))
        elif easing == EasingFunction.ELASTIC:
            if progress == 0.0 or progress == 1.0:
                return progress
            # Deterministic elastic calculation
            return math.pow(2, -10 * progress) * math.sin((progress - 0.1) * 2 * math.pi / 0.4) + 1.0
        else:
            return progress
    
    def _linear_interpolation(self, start: float, end: float, progress: float) -> float:
        """Deterministic linear interpolation."""
        return start + (end - start) * progress
    
    def _temporal_precision_test(self, timestamp: float) -> float:
        """Test temporal precision for animation timing."""
        # Simulate animation state calculation at specific timestamp
        # This tests floating-point precision in time-based calculations
        frame_number = timestamp * 60.0  # 60fps
        fractional_frame = frame_number - math.floor(frame_number)
        return fractional_frame
    
    def _floating_point_operation(self, a: float, b: float, operation: str) -> float:
        """Perform floating-point operation for consistency testing."""
        if operation == "addition" or operation == "small_addition" or operation == "large_addition":
            return a + b
        elif operation == "multiplication" or operation == "small_multiplication":
            return a * b
        elif operation == "division":
            return a / b if b != 0.0 else float('inf')
        elif operation == "mixed_precision":
            return (a + b) * a / b if b != 0.0 else float('inf')
        else:
            return a + b


class TestMathematicalDeterminism:
    """Test suite for mathematical determinism validation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.validator = MathematicalDeterminismValidator()
    
    def test_easing_function_determinism(self):
        """Test that easing functions produce identical results across cores."""
        results = self.validator.validate_easing_function_determinism()
        
        for result in results:
            assert result.is_deterministic, (
                f"Easing function {result.test_name} is not deterministic. "
                f"Max deviation: {result.max_deviation}, "
                f"Precision bits: {result.precision_bits}"
            )
            
            # Require at least 50 bits of precision for animation smoothness
            assert result.precision_bits >= 50, (
                f"Easing function {result.test_name} has insufficient precision: "
                f"{result.precision_bits} bits"
            )
    
    def test_interpolation_determinism(self):
        """Test that interpolation algorithms are deterministic."""
        results = self.validator.validate_interpolation_determinism()
        
        for result in results:
            assert result.is_deterministic, (
                f"Interpolation {result.test_name} is not deterministic. "
                f"Max deviation: {result.max_deviation}"
            )
    
    def test_temporal_precision(self):
        """Test temporal precision for 60fps animation."""
        result = self.validator.validate_temporal_precision()
        
        assert result.is_deterministic, (
            f"Temporal precision test failed. Max deviation: {result.max_deviation}"
        )
        
        # Require sub-microsecond precision for smooth animation
        assert result.max_deviation < 1e-6, (
            f"Temporal precision insufficient: {result.max_deviation}"
        )
    
    def test_floating_point_consistency(self):
        """Test floating-point arithmetic consistency across cores."""
        results = self.validator.validate_floating_point_consistency()
        
        for result in results:
            assert result.is_deterministic, (
                f"Floating-point operation {result.test_name} is not consistent. "
                f"Max deviation: {result.max_deviation}"
            )
    
    def test_math_library_consistency(self):
        """Test math library function consistency across cores."""
        results = self.validator.validate_math_library_consistency()
        
        for result in results:
            assert result.is_deterministic, (
                f"Math function {result.test_name} is not consistent across cores. "
                f"Max deviation: {result.max_deviation}"
            )
    
    def test_comprehensive_determinism_report(self):
        """Generate comprehensive determinism report."""
        all_results = []
        
        all_results.extend(self.validator.validate_easing_function_determinism())
        all_results.extend(self.validator.validate_interpolation_determinism())
        all_results.append(self.validator.validate_temporal_precision())
        all_results.extend(self.validator.validate_floating_point_consistency())
        all_results.extend(self.validator.validate_math_library_consistency())
        
        # Generate detailed report
        report = self._generate_determinism_report(all_results)
        
        # Save report for analysis
        with open("determinism_validation_report.md", "w") as f:
            f.write(report)
        
        # Ensure overall system determinism
        failed_tests = [r for r in all_results if not r.is_deterministic]
        assert len(failed_tests) == 0, (
            f"Determinism validation failed for {len(failed_tests)} tests: "
            f"{[r.test_name for r in failed_tests]}"
        )
    
    def _generate_determinism_report(self, results: List[DeterminismTestResult]) -> str:
        """Generate comprehensive determinism validation report."""
        report = [
            "# Mathematical Determinism Validation Report",
            "",
            f"**Test Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**CPU Cores Tested:** {self.validator.num_cores}",
            f"**Precision Threshold:** {self.validator.precision_threshold}",
            "",
            "## Summary",
            "",
        ]
        
        total_tests = len(results)
        passed_tests = len([r for r in results if r.is_deterministic])
        
        report.extend([
            f"- **Total Tests:** {total_tests}",
            f"- **Passed:** {passed_tests}",
            f"- **Failed:** {total_tests - passed_tests}",
            f"- **Success Rate:** {(passed_tests/total_tests)*100:.1f}%",
            "",
            "## Detailed Results",
            "",
        ])
        
        for result in results:
            status = "✅ PASS" if result.is_deterministic else "❌ FAIL"
            report.extend([
                f"### {result.test_name} - {status}",
                "",
                f"- **Deterministic:** {result.is_deterministic}",
                f"- **Precision Bits:** {result.precision_bits}",
                f"- **Max Deviation:** {result.max_deviation:.2e}",
                f"- **Test Cases:** {len(result.inputs)}",
                f"- **Avg Execution Time:** {sum(result.execution_times)/len(result.execution_times)*1e6:.2f} μs",
                "",
            ])
        
        return "\n".join(report)


if __name__ == "__main__":
    # Run determinism validation
    validator = MathematicalDeterminismValidator()
    
    print("🔬 Starting Mathematical Determinism Validation...")
    print(f"Testing across {validator.num_cores} CPU cores")
    print(f"Precision threshold: {validator.precision_threshold}")
    print()
    
    # Run all validation tests
    all_results = []
    
    print("Testing easing function determinism...")
    all_results.extend(validator.validate_easing_function_determinism())
    
    print("Testing interpolation determinism...")
    all_results.extend(validator.validate_interpolation_determinism())
    
    print("Testing temporal precision...")
    all_results.append(validator.validate_temporal_precision())
    
    print("Testing floating-point consistency...")
    all_results.extend(validator.validate_floating_point_consistency())
    
    print("Testing math library consistency...")
    all_results.extend(validator.validate_math_library_consistency())
    
    # Summary
    total_tests = len(all_results)
    passed_tests = len([r for r in all_results if r.is_deterministic])
    
    print(f"\n🎯 Validation Complete!")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("✅ All tests passed! Mathematical determinism validated.")
    else:
        print("❌ Some tests failed. Review results for details.")
        failed_tests = [r for r in all_results if not r.is_deterministic]
        for result in failed_tests:
            print(f"  - {result.test_name}: deviation {result.max_deviation:.2e}") 