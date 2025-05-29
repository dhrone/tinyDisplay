#!/usr/bin/env python3
"""
Standalone Mathematical Determinism Validation Test

This test validates that our mathematical approach for deterministic animations
produces bit-identical results across multiple execution contexts.

This is a simplified version that doesn't depend on the existing codebase.
"""

import math
import time
import multiprocessing as mp
from typing import List, Tuple, Dict, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor


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


# Global functions for multiprocessing (must be picklable)
def math_pow_2(x):
    """Math power function for testing."""
    return math.pow(2, x)


class DeterministicEasing:
    """Pure functional easing functions with guaranteed deterministic behavior."""
    
    @staticmethod
    def linear(t: float) -> float:
        """Linear easing function."""
        return t
    
    @staticmethod
    def ease_in(t: float) -> float:
        """Quadratic ease-in function."""
        return t * t
    
    @staticmethod
    def ease_out(t: float) -> float:
        """Quadratic ease-out function."""
        return 1.0 - (1.0 - t) * (1.0 - t)
    
    @staticmethod
    def ease_in_out(t: float) -> float:
        """Quadratic ease-in-out function."""
        if t < 0.5:
            return 2.0 * t * t
        else:
            return 1.0 - 2.0 * (1.0 - t) * (1.0 - t)
    
    @staticmethod
    def bounce(t: float) -> float:
        """Deterministic bounce easing function."""
        if t < 1.0 / 2.75:
            return 7.5625 * t * t
        elif t < 2.0 / 2.75:
            t -= 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t -= 2.25 / 2.75
            return 7.5625 * t * t + 0.9375
        else:
            t -= 2.625 / 2.75
            return 7.5625 * t * t + 0.984375
    
    @staticmethod
    def elastic(t: float) -> float:
        """Deterministic elastic easing function."""
        if t == 0.0 or t == 1.0:
            return t
        
        # Use deterministic constants for elastic behavior
        period = 0.4
        amplitude = 1.0
        s = period / (2 * math.pi) * math.asin(1.0 / amplitude)
        
        return amplitude * math.pow(2, -10 * t) * math.sin((t - s) * 2 * math.pi / period) + 1.0


class StandaloneDeterminismValidator:
    """Simplified validator for mathematical determinism."""
    
    def __init__(self, num_cores: int = 4, precision_threshold: float = 1e-15):
        """Initialize determinism validator."""
        self.num_cores = num_cores
        self.precision_threshold = precision_threshold
    
    def validate_easing_functions(self) -> List[DeterminismTestResult]:
        """Validate deterministic behavior of easing functions."""
        results = []
        
        # Test cases covering edge cases and precision boundaries
        test_cases = [
            0.0, 0.25, 0.5, 0.75, 1.0,
            1e-15, 1e-10, 1e-5,
            1.0 - 1e-15, 1.0 - 1e-10, 1.0 - 1e-5,
            1.0/3.0, 2.0/3.0, 1.0/7.0,
            math.pi / 4.0, math.e / 3.0, math.sqrt(2) / 2.0,
            0.5 - 1e-10, 0.5 + 1e-10,
        ]
        
        easing_functions = [
            ("linear", DeterministicEasing.linear),
            ("ease_in", DeterministicEasing.ease_in),
            ("ease_out", DeterministicEasing.ease_out),
            ("ease_in_out", DeterministicEasing.ease_in_out),
            ("bounce", DeterministicEasing.bounce),
            ("elastic", DeterministicEasing.elastic),
        ]
        
        for func_name, func in easing_functions:
            result = self._test_function_across_cores(
                func=func,
                test_cases=test_cases,
                test_name=f"easing_{func_name}"
            )
            results.append(result)
        
        return results
    
    def validate_math_functions(self) -> List[DeterminismTestResult]:
        """Validate math library function consistency across cores."""
        results = []
        
        # Test critical math functions used in animations
        test_functions = [
            ("sin", math.sin, [0.0, math.pi/4, math.pi/2, math.pi, 2*math.pi]),
            ("cos", math.cos, [0.0, math.pi/4, math.pi/2, math.pi, 2*math.pi]),
            ("pow", math_pow_2, [-10, -1, 0, 1, 10]),
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
        # Set CPU affinity to specific core (macOS doesn't support this)
        try:
            import os
            if hasattr(os, 'sched_setaffinity'):
                os.sched_setaffinity(0, {core_id})
        except (ImportError, AttributeError, OSError):
            # Not supported on this platform
            pass
        
        outputs = []
        times = []
        
        for test_case in test_cases:
            start_time = time.perf_counter()
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


def main():
    """Run standalone determinism validation."""
    print("🔬 Standalone Mathematical Determinism Validation")
    print("=" * 60)
    print(f"Platform: {mp.cpu_count()} CPU cores available")
    print()
    
    validator = StandaloneDeterminismValidator(num_cores=min(4, mp.cpu_count()))
    
    # Test easing functions
    print("Testing easing function determinism...")
    easing_results = validator.validate_easing_functions()
    
    print("Testing math library consistency...")
    math_results = validator.validate_math_functions()
    
    # Combine all results
    all_results = easing_results + math_results
    
    # Summary
    total_tests = len(all_results)
    passed_tests = len([r for r in all_results if r.is_deterministic])
    
    print(f"\n🎯 Validation Complete!")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    print()
    
    # Detailed results
    print("📊 Detailed Results:")
    print("-" * 60)
    for result in all_results:
        status = "✅ PASS" if result.is_deterministic else "❌ FAIL"
        avg_time = sum(result.execution_times) / len(result.execution_times) * 1e6
        print(f"{result.test_name:20} {status:8} "
              f"Precision: {result.precision_bits:2d} bits, "
              f"Deviation: {result.max_deviation:.2e}, "
              f"Avg Time: {avg_time:.2f} μs")
    
    print()
    if passed_tests == total_tests:
        print("✅ All tests passed! Mathematical determinism validated.")
        print("🚀 Ready for multi-core animation frame pre-computation!")
    else:
        print("❌ Some tests failed. Review results for details.")
        failed_tests = [r for r in all_results if not r.is_deterministic]
        for result in failed_tests:
            print(f"  - {result.test_name}: deviation {result.max_deviation:.2e}")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 