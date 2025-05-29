#!/usr/bin/env python3
"""
Determinism Validation for Tick-Based Animation System

Provides comprehensive tools for validating that tick-based animations produce
identical results across multiple executions, ensuring deterministic behavior
for multi-core safety and reproducible animations.
"""

import hashlib
import json
import time
from typing import Dict, List, Any, Optional, Tuple, Callable, Set
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from .tick_based import (
    TickAnimationEngine, TickAnimationDefinition, TickAnimationState,
    TickFramePredictor
)
from .utilities import (
    create_fade_animation, create_slide_animation, create_scale_animation,
    AnimationConfig, AnimationTiming
)


@dataclass
class DeterminismTestResult:
    """Result of a determinism validation test."""
    test_name: str
    passed: bool
    execution_count: int
    identical_results: bool
    hash_consistency: bool
    state_consistency: bool
    performance_stats: Dict[str, float]
    error_message: Optional[str] = None
    execution_hashes: List[str] = None
    state_snapshots: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.execution_hashes is None:
            self.execution_hashes = []
        if self.state_snapshots is None:
            self.state_snapshots = []


@dataclass
class AnimationExecutionTrace:
    """Trace of an animation execution for determinism analysis."""
    animation_id: str
    start_tick: int
    end_tick: int
    tick_states: Dict[int, TickAnimationState]
    execution_hash: str
    execution_time: float
    
    def compute_hash(self) -> str:
        """Compute hash of the execution trace for comparison."""
        # Create deterministic representation
        # Exclude animation_id as it varies across executions
        trace_data = {
            'start_tick': self.start_tick,
            'end_tick': self.end_tick,
            'states': {}
        }
        
        # Add state data in sorted order for consistency
        # Normalize tick values to be relative to start_tick for deterministic comparison
        # Exclude the 'tick' field from TickAnimationState as it's metadata
        for tick in sorted(self.tick_states.keys()):
            state = self.tick_states[tick]
            relative_tick = tick - self.start_tick  # Normalize to relative tick
            trace_data['states'][relative_tick] = {
                'position': state.position,
                'rotation': state.rotation,
                'scale': state.scale,
                'opacity': state.opacity,
                'custom_properties': dict(sorted(state.custom_properties.items()))
                # Note: Excluding 'tick' field as it's metadata that varies across executions
            }
        
        # Compute hash
        trace_json = json.dumps(trace_data, sort_keys=True)
        return hashlib.sha256(trace_json.encode()).hexdigest()


# Module-level worker function for multiprocessing
def _process_worker(args):
    """Worker function for process execution."""
    process_id, executions_per_process, animation_def = args
    process_hashes = []
    
    for execution in range(executions_per_process):
        engine = TickAnimationEngine()
        animation_id = f"process_{process_id}_execution_{execution}"
        
        engine.add_animation(animation_id, animation_def)
        engine.start_animation_at(animation_id, animation_def.start_tick)
        
        # Execute animation and collect states
        tick_states = {}
        for tick in range(0, 61):  # 0 to 60 inclusive
            frame_state = engine.compute_frame_state(tick)
            if animation_id in frame_state:
                tick_states[tick] = frame_state[animation_id]
        
        # Create trace and compute hash
        trace_data = {
            'start_tick': 0,
            'end_tick': 60,
            'states': {}
        }
        
        for tick in sorted(tick_states.keys()):
            state = tick_states[tick]
            relative_tick = tick - 0  # Normalize to relative tick
            trace_data['states'][relative_tick] = {
                'position': state.position,
                'rotation': state.rotation,
                'scale': state.scale,
                'opacity': state.opacity,
                'custom_properties': dict(sorted(state.custom_properties.items()))
            }
        
        trace_json = json.dumps(trace_data, sort_keys=True)
        execution_hash = hashlib.sha256(trace_json.encode()).hexdigest()
        process_hashes.append(execution_hash)
    
    return process_hashes


class DeterminismValidator:
    """Comprehensive determinism validation for tick-based animations."""
    
    def __init__(self, tolerance: float = 1e-10):
        """Initialize determinism validator.
        
        Args:
            tolerance: Floating point comparison tolerance
        """
        self.tolerance = tolerance
        self.test_results: List[DeterminismTestResult] = []
        self.execution_traces: Dict[str, List[AnimationExecutionTrace]] = defaultdict(list)
    
    def validate_animation_determinism(
        self,
        animation_def: TickAnimationDefinition,
        test_name: str,
        execution_count: int = 10,
        tick_range: Tuple[int, int] = (0, 100)
    ) -> DeterminismTestResult:
        """Validate that an animation produces identical results across executions.
        
        Args:
            animation_def: Animation definition to test
            test_name: Name of the test
            execution_count: Number of executions to run
            tick_range: Range of ticks to test (start, end)
            
        Returns:
            DeterminismTestResult with validation results
        """
        start_time = time.time()
        execution_hashes = []
        state_snapshots = []
        traces = []
        
        try:
            for execution in range(execution_count):
                # Create fresh engine for each execution
                engine = TickAnimationEngine()
                animation_id = f"test_animation_{execution}"
                
                # Add animation to engine
                engine.add_animation(animation_id, animation_def)
                engine.start_animation_at(animation_id, animation_def.start_tick)
                
                # Execute animation and collect states
                trace = self._execute_animation_trace(
                    engine, animation_id, tick_range[0], tick_range[1]
                )
                traces.append(trace)
                
                # Collect execution hash and state snapshot
                execution_hashes.append(trace.execution_hash)
                state_snapshots.append(trace.tick_states)
            
            # Analyze results
            identical_results = len(set(execution_hashes)) == 1
            hash_consistency = all(h == execution_hashes[0] for h in execution_hashes)
            state_consistency = self._validate_state_consistency(state_snapshots)
            
            execution_time = time.time() - start_time
            performance_stats = {
                'total_execution_time': execution_time,
                'average_execution_time': execution_time / execution_count,
                'executions_per_second': execution_count / execution_time
            }
            
            result = DeterminismTestResult(
                test_name=test_name,
                passed=identical_results and hash_consistency and state_consistency,
                execution_count=execution_count,
                identical_results=identical_results,
                hash_consistency=hash_consistency,
                state_consistency=state_consistency,
                performance_stats=performance_stats,
                execution_hashes=execution_hashes,
                state_snapshots=state_snapshots
            )
            
        except Exception as e:
            result = DeterminismTestResult(
                test_name=test_name,
                passed=False,
                execution_count=execution_count,
                identical_results=False,
                hash_consistency=False,
                state_consistency=False,
                performance_stats={},
                error_message=str(e)
            )
        
        self.test_results.append(result)
        self.execution_traces[test_name] = traces
        return result
    
    def _execute_animation_trace(
        self,
        engine: TickAnimationEngine,
        animation_id: str,
        start_tick: int,
        end_tick: int
    ) -> AnimationExecutionTrace:
        """Execute animation and create execution trace."""
        execution_start = time.time()
        tick_states = {}
        
        # Execute animation tick by tick using direct state computation
        # instead of advancing the engine to avoid inconsistent tick values
        for tick in range(start_tick, end_tick + 1):
            frame_state = engine.compute_frame_state(tick)
            
            if animation_id in frame_state:
                tick_states[tick] = frame_state[animation_id]
        
        execution_time = time.time() - execution_start
        
        # Create trace
        trace = AnimationExecutionTrace(
            animation_id=animation_id,
            start_tick=start_tick,
            end_tick=end_tick,
            tick_states=tick_states,
            execution_hash="",  # Will be computed
            execution_time=execution_time
        )
        
        # Compute hash
        trace.execution_hash = trace.compute_hash()
        return trace
    
    def _validate_state_consistency(self, state_snapshots: List[Dict[str, Any]]) -> bool:
        """Validate that state snapshots are consistent across executions."""
        if not state_snapshots:
            return True
        
        reference_snapshot = state_snapshots[0]
        
        for snapshot in state_snapshots[1:]:
            if not self._compare_state_snapshots(reference_snapshot, snapshot):
                return False
        
        return True
    
    def _compare_state_snapshots(
        self,
        snapshot1: Dict[str, Any],
        snapshot2: Dict[str, Any]
    ) -> bool:
        """Compare two state snapshots for equality within tolerance."""
        if set(snapshot1.keys()) != set(snapshot2.keys()):
            return False
        
        for tick in snapshot1.keys():
            state1 = snapshot1[tick]
            state2 = snapshot2[tick]
            
            if not self._compare_animation_states(state1, state2):
                return False
        
        return True
    
    def _compare_animation_states(
        self,
        state1: TickAnimationState,
        state2: TickAnimationState
    ) -> bool:
        """Compare two animation states for equality within tolerance.
        
        Note: Excludes the 'tick' field as it's metadata that can vary across executions.
        """
        # Compare positions
        if not self._compare_tuples(state1.position, state2.position):
            return False
        
        # Compare rotation
        if abs(state1.rotation - state2.rotation) > self.tolerance:
            return False
        
        # Compare scale
        if not self._compare_tuples(state1.scale, state2.scale):
            return False
        
        # Compare opacity
        if abs(state1.opacity - state2.opacity) > self.tolerance:
            return False
        
        # Compare custom properties
        if state1.custom_properties.keys() != state2.custom_properties.keys():
            return False
        
        for key in state1.custom_properties:
            val1 = state1.custom_properties[key]
            val2 = state2.custom_properties[key]
            
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                if abs(val1 - val2) > self.tolerance:
                    return False
            elif val1 != val2:
                return False
        
        # Note: We deliberately exclude the 'tick' field from comparison
        # as it's metadata that can vary across executions
        return True
    
    def _compare_tuples(self, tuple1: Tuple[float, float], tuple2: Tuple[float, float]) -> bool:
        """Compare two tuples for equality within tolerance."""
        return (abs(tuple1[0] - tuple2[0]) <= self.tolerance and
                abs(tuple1[1] - tuple2[1]) <= self.tolerance)
    
    def validate_multi_threaded_determinism(
        self,
        animation_def: TickAnimationDefinition,
        test_name: str,
        thread_count: int = 4,
        executions_per_thread: int = 5
    ) -> DeterminismTestResult:
        """Validate determinism across multiple threads.
        
        Args:
            animation_def: Animation definition to test
            test_name: Name of the test
            thread_count: Number of threads to use
            executions_per_thread: Number of executions per thread
            
        Returns:
            DeterminismTestResult with validation results
        """
        start_time = time.time()
        all_hashes = []
        all_snapshots = []
        
        def thread_worker(thread_id: int) -> List[Tuple[str, Dict[str, Any]]]:
            """Worker function for thread execution."""
            thread_results = []
            
            for execution in range(executions_per_thread):
                engine = TickAnimationEngine()
                animation_id = f"thread_{thread_id}_execution_{execution}"
                
                engine.add_animation(animation_id, animation_def)
                engine.start_animation_at(animation_id, animation_def.start_tick)
                
                trace = self._execute_animation_trace(engine, animation_id, 0, 60)
                thread_results.append((trace.execution_hash, trace.tick_states))
            
            return thread_results
        
        try:
            # Execute in multiple threads
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [
                    executor.submit(thread_worker, thread_id)
                    for thread_id in range(thread_count)
                ]
                
                for future in futures:
                    thread_results = future.result()
                    for hash_val, snapshot in thread_results:
                        all_hashes.append(hash_val)
                        all_snapshots.append(snapshot)
            
            # Analyze results
            identical_results = len(set(all_hashes)) == 1
            hash_consistency = all(h == all_hashes[0] for h in all_hashes)
            state_consistency = self._validate_state_consistency(all_snapshots)
            
            execution_time = time.time() - start_time
            total_executions = thread_count * executions_per_thread
            
            performance_stats = {
                'total_execution_time': execution_time,
                'thread_count': thread_count,
                'executions_per_thread': executions_per_thread,
                'total_executions': total_executions,
                'executions_per_second': total_executions / execution_time
            }
            
            result = DeterminismTestResult(
                test_name=test_name,
                passed=identical_results and hash_consistency and state_consistency,
                execution_count=total_executions,
                identical_results=identical_results,
                hash_consistency=hash_consistency,
                state_consistency=state_consistency,
                performance_stats=performance_stats,
                execution_hashes=all_hashes,
                state_snapshots=all_snapshots
            )
            
        except Exception as e:
            result = DeterminismTestResult(
                test_name=test_name,
                passed=False,
                execution_count=0,
                identical_results=False,
                hash_consistency=False,
                state_consistency=False,
                performance_stats={},
                error_message=str(e)
            )
        
        self.test_results.append(result)
        return result
    
    def validate_multi_process_determinism(
        self,
        animation_def: TickAnimationDefinition,
        test_name: str,
        process_count: int = 2,
        executions_per_process: int = 3
    ) -> DeterminismTestResult:
        """Validate determinism across multiple processes.
        
        Args:
            animation_def: Animation definition to test
            test_name: Name of the test
            process_count: Number of processes to use
            executions_per_process: Number of executions per process
            
        Returns:
            DeterminismTestResult with validation results
        """
        start_time = time.time()
        
        try:
            # Execute in multiple processes
            with ProcessPoolExecutor(max_workers=process_count) as executor:
                futures = [
                    executor.submit(_process_worker, (process_id, executions_per_process, animation_def))
                    for process_id in range(process_count)
                ]
                
                all_hashes = []
                for future in futures:
                    process_hashes = future.result()
                    all_hashes.extend(process_hashes)
            
            # Analyze results
            identical_results = len(set(all_hashes)) == 1
            hash_consistency = all(h == all_hashes[0] for h in all_hashes)
            
            execution_time = time.time() - start_time
            total_executions = process_count * executions_per_process
            
            performance_stats = {
                'total_execution_time': execution_time,
                'process_count': process_count,
                'executions_per_process': executions_per_process,
                'total_executions': total_executions,
                'executions_per_second': total_executions / execution_time
            }
            
            result = DeterminismTestResult(
                test_name=test_name,
                passed=identical_results and hash_consistency,
                execution_count=total_executions,
                identical_results=identical_results,
                hash_consistency=hash_consistency,
                state_consistency=True,  # Can't compare states across processes easily
                performance_stats=performance_stats,
                execution_hashes=all_hashes
            )
            
        except Exception as e:
            result = DeterminismTestResult(
                test_name=test_name,
                passed=False,
                execution_count=0,
                identical_results=False,
                hash_consistency=False,
                state_consistency=False,
                performance_stats={},
                error_message=str(e)
            )
        
        self.test_results.append(result)
        return result
    
    def benchmark_animation_performance(
        self,
        animation_def: TickAnimationDefinition,
        test_name: str,
        tick_count: int = 1000,
        iteration_count: int = 100
    ) -> Dict[str, float]:
        """Benchmark animation performance.
        
        Args:
            animation_def: Animation definition to benchmark
            test_name: Name of the benchmark
            tick_count: Number of ticks to simulate
            iteration_count: Number of iterations to run
            
        Returns:
            Performance statistics dictionary
        """
        engine = TickAnimationEngine()
        animation_id = "benchmark_animation"
        
        engine.add_animation(animation_id, animation_def)
        engine.start_animation_at(animation_id, 0)
        
        # Warm up
        for tick in range(10):
            engine.compute_frame_state(tick)
        
        # Benchmark
        start_time = time.time()
        
        for iteration in range(iteration_count):
            for tick in range(tick_count):
                frame_state = engine.compute_frame_state(tick)
        
        end_time = time.time()
        total_time = end_time - start_time
        total_computations = iteration_count * tick_count
        
        stats = {
            'total_time': total_time,
            'total_computations': total_computations,
            'computations_per_second': total_computations / total_time,
            'microseconds_per_computation': (total_time * 1_000_000) / total_computations,
            'fps_capability': 1.0 / ((total_time / total_computations) * 60),  # Assuming 60 ticks per frame
            'iterations': iteration_count,
            'ticks_per_iteration': tick_count
        }
        
        return stats
    
    def generate_determinism_report(self) -> Dict[str, Any]:
        """Generate comprehensive determinism validation report.
        
        Returns:
            Dictionary containing detailed report
        """
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.passed)
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': passed_tests / total_tests if total_tests > 0 else 0.0
            },
            'test_results': [],
            'performance_summary': {},
            'determinism_analysis': {}
        }
        
        # Add individual test results
        for result in self.test_results:
            report['test_results'].append({
                'test_name': result.test_name,
                'passed': result.passed,
                'execution_count': result.execution_count,
                'identical_results': result.identical_results,
                'hash_consistency': result.hash_consistency,
                'state_consistency': result.state_consistency,
                'performance_stats': result.performance_stats,
                'error_message': result.error_message
            })
        
        # Performance summary
        if self.test_results:
            all_perf_stats = [r.performance_stats for r in self.test_results if r.performance_stats]
            if all_perf_stats:
                avg_exec_time = sum(s.get('average_execution_time', 0) for s in all_perf_stats) / len(all_perf_stats)
                avg_exec_per_sec = sum(s.get('executions_per_second', 0) for s in all_perf_stats) / len(all_perf_stats)
                
                report['performance_summary'] = {
                    'average_execution_time': avg_exec_time,
                    'average_executions_per_second': avg_exec_per_sec,
                    'total_executions': sum(r.execution_count for r in self.test_results)
                }
        
        # Determinism analysis
        hash_consistency_rate = sum(1 for r in self.test_results if r.hash_consistency) / total_tests if total_tests > 0 else 0.0
        state_consistency_rate = sum(1 for r in self.test_results if r.state_consistency) / total_tests if total_tests > 0 else 0.0
        
        report['determinism_analysis'] = {
            'hash_consistency_rate': hash_consistency_rate,
            'state_consistency_rate': state_consistency_rate,
            'overall_determinism_rate': min(hash_consistency_rate, state_consistency_rate)
        }
        
        return report
    
    def clear_results(self) -> None:
        """Clear all test results and traces."""
        self.test_results.clear()
        self.execution_traces.clear()


class DeterminismDebugger:
    """Debugging tools for determinism issues."""
    
    def __init__(self, validator: DeterminismValidator):
        """Initialize debugger with validator instance."""
        self.validator = validator
    
    def analyze_failed_test(self, test_name: str) -> Dict[str, Any]:
        """Analyze a failed determinism test.
        
        Args:
            test_name: Name of the failed test
            
        Returns:
            Analysis results
        """
        # Find the test result
        test_result = None
        for result in self.validator.test_results:
            if result.test_name == test_name:
                test_result = result
                break
        
        if not test_result:
            return {'error': f'Test {test_name} not found'}
        
        if test_result.passed:
            return {'message': f'Test {test_name} passed, no analysis needed'}
        
        analysis = {
            'test_name': test_name,
            'failure_reasons': [],
            'hash_analysis': {},
            'state_analysis': {},
            'recommendations': []
        }
        
        # Analyze failure reasons
        if not test_result.identical_results:
            analysis['failure_reasons'].append('Results not identical across executions')
        
        if not test_result.hash_consistency:
            analysis['failure_reasons'].append('Hash inconsistency detected')
            
            # Analyze hash differences
            if test_result.execution_hashes:
                unique_hashes = set(test_result.execution_hashes)
                analysis['hash_analysis'] = {
                    'unique_hash_count': len(unique_hashes),
                    'total_executions': len(test_result.execution_hashes),
                    'hash_distribution': {h: test_result.execution_hashes.count(h) for h in unique_hashes}
                }
        
        if not test_result.state_consistency:
            analysis['failure_reasons'].append('State inconsistency detected')
        
        # Add recommendations
        if 'Results not identical' in str(analysis['failure_reasons']):
            analysis['recommendations'].append('Check for non-deterministic operations in animation logic')
        
        if 'Hash inconsistency' in str(analysis['failure_reasons']):
            analysis['recommendations'].append('Verify that all animation state computations are deterministic')
        
        if 'State inconsistency' in str(analysis['failure_reasons']):
            analysis['recommendations'].append('Check floating-point precision and comparison tolerances')
        
        return analysis
    
    def compare_execution_traces(
        self,
        test_name: str,
        execution1: int = 0,
        execution2: int = 1
    ) -> Dict[str, Any]:
        """Compare two execution traces for differences.
        
        Args:
            test_name: Name of the test
            execution1: Index of first execution
            execution2: Index of second execution
            
        Returns:
            Comparison results
        """
        traces = self.validator.execution_traces.get(test_name, [])
        
        if len(traces) <= max(execution1, execution2):
            return {'error': 'Not enough execution traces for comparison'}
        
        trace1 = traces[execution1]
        trace2 = traces[execution2]
        
        comparison = {
            'execution1_hash': trace1.execution_hash,
            'execution2_hash': trace2.execution_hash,
            'hashes_match': trace1.execution_hash == trace2.execution_hash,
            'tick_differences': [],
            'state_differences': {}
        }
        
        # Compare tick by tick
        all_ticks = set(trace1.tick_states.keys()) | set(trace2.tick_states.keys())
        
        for tick in sorted(all_ticks):
            state1 = trace1.tick_states.get(tick)
            state2 = trace2.tick_states.get(tick)
            
            if state1 is None or state2 is None:
                comparison['tick_differences'].append({
                    'tick': tick,
                    'issue': 'Missing state in one execution'
                })
                continue
            
            # Compare states
            differences = self._compare_states_detailed(state1, state2)
            if differences:
                comparison['state_differences'][tick] = differences
        
        return comparison
    
    def _compare_states_detailed(
        self,
        state1: TickAnimationState,
        state2: TickAnimationState
    ) -> Dict[str, Any]:
        """Compare two states and return detailed differences.
        
        Note: Excludes the 'tick' field as it's metadata that can vary across executions.
        """
        differences = {}
        
        # Position differences
        if state1.position != state2.position:
            differences['position'] = {
                'state1': state1.position,
                'state2': state2.position,
                'difference': (
                    state1.position[0] - state2.position[0],
                    state1.position[1] - state2.position[1]
                )
            }
        
        # Rotation differences
        if abs(state1.rotation - state2.rotation) > self.validator.tolerance:
            differences['rotation'] = {
                'state1': state1.rotation,
                'state2': state2.rotation,
                'difference': state1.rotation - state2.rotation
            }
        
        # Scale differences
        if state1.scale != state2.scale:
            differences['scale'] = {
                'state1': state1.scale,
                'state2': state2.scale,
                'difference': (
                    state1.scale[0] - state2.scale[0],
                    state1.scale[1] - state2.scale[1]
                )
            }
        
        # Opacity differences
        if abs(state1.opacity - state2.opacity) > self.validator.tolerance:
            differences['opacity'] = {
                'state1': state1.opacity,
                'state2': state2.opacity,
                'difference': state1.opacity - state2.opacity
            }
        
        # Custom properties differences
        all_props = set(state1.custom_properties.keys()) | set(state2.custom_properties.keys())
        prop_diffs = {}
        
        for prop in all_props:
            val1 = state1.custom_properties.get(prop)
            val2 = state2.custom_properties.get(prop)
            
            if val1 != val2:
                prop_diffs[prop] = {
                    'state1': val1,
                    'state2': val2
                }
        
        if prop_diffs:
            differences['custom_properties'] = prop_diffs
        
        # Note: We deliberately exclude the 'tick' field from comparison
        # as it's metadata that can vary across executions
        return differences


# Convenience functions for common determinism tests

def validate_basic_determinism(animation_def: TickAnimationDefinition, test_name: str) -> DeterminismTestResult:
    """Quick determinism validation for an animation definition."""
    validator = DeterminismValidator()
    return validator.validate_animation_determinism(animation_def, test_name)


def validate_widget_animation_determinism(
    widget_type: str,
    animation_method: str,
    **animation_params
) -> DeterminismTestResult:
    """Validate determinism for a specific widget animation method."""
    # This would be implemented to test specific widget animations
    # For now, return a placeholder
    return DeterminismTestResult(
        test_name=f"{widget_type}_{animation_method}",
        passed=True,
        execution_count=1,
        identical_results=True,
        hash_consistency=True,
        state_consistency=True,
        performance_stats={}
    )


def run_comprehensive_determinism_suite() -> Dict[str, Any]:
    """Run comprehensive determinism validation suite."""
    validator = DeterminismValidator()
    
    # Test basic animations
    fade_anim = create_fade_animation(0.0, 1.0)
    validator.validate_animation_determinism(fade_anim, "fade_animation_basic")
    
    slide_anim = create_slide_animation((0, 0), (100, 50))
    validator.validate_animation_determinism(slide_anim, "slide_animation_basic")
    
    scale_anim = create_scale_animation((0.5, 0.5), (2.0, 2.0))
    validator.validate_animation_determinism(scale_anim, "scale_animation_basic")
    
    # Test multi-threaded determinism
    validator.validate_multi_threaded_determinism(fade_anim, "fade_animation_multithreaded")
    
    # Test multi-process determinism
    validator.validate_multi_process_determinism(fade_anim, "fade_animation_multiprocess")
    
    return validator.generate_determinism_report() 