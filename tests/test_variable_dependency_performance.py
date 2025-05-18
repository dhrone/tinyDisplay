#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Performance benchmark for the variable dependency tracking system.

This test compares the performance of dynamic variable evaluation with and without
dependency tracking to demonstrate the efficiency gains.
"""
import time
import unittest

from tinyDisplay.utility import dataset
from tinyDisplay.utility.evaluator import evaluator, dynamicValue
from tinyDisplay.utility.dynamic import dynamic
from tinyDisplay.utility.variable_dependencies import variable_registry

class PerformanceBenchmark(unittest.TestCase):
    """Performance benchmarks for variable dependency tracking."""
    
    def setUp(self):
        # Create a large dataset with many values
        self.data = dataset()
        self.data.add('stats', {
            'value1': 10,
            'value2': 20,
            'value3': 30,
            'value4': 40,
            'value5': 50,
            'unused1': 100,
            'unused2': 200,
            'unused3': 300,
            'unused4': 400,
            'unused5': 500,
        })
        
        # Create an evaluator
        self.eval = evaluator(self.data)
        
        # Create a large number of dynamic values
        # Some dependent on value1
        self.value1_deps = []
        for i in range(50):
            dv = self.eval.compile(f"stats['value1'] * {i}", name=f"val1_dep_{i}", dynamic=True)
            self.value1_deps.append(dv)
        
        # Some dependent on value2
        self.value2_deps = []
        for i in range(50):
            dv = self.eval.compile(f"stats['value2'] * {i}", name=f"val2_dep_{i}", dynamic=True)
            self.value2_deps.append(dv)
        
        # Some dependent on value3
        self.value3_deps = []
        for i in range(50):
            dv = self.eval.compile(f"stats['value3'] * {i}", name=f"val3_dep_{i}", dynamic=True)
            self.value3_deps.append(dv)
        
        # Some with mixed dependencies
        self.mixed_deps = []
        for i in range(50):
            expr = f"stats['value{(i % 3) + 1}'] * {i}"
            dv = self.eval.compile(expr, name=f"mixed_dep_{i}", dynamic=True)
            self.mixed_deps.append(dv)
        
        # Force initial evaluation of all variables
        self.eval.evalAll()
    
    def test_performance_with_dependency_tracking(self):
        """Benchmark performance with dependency tracking enabled."""
        # Update value1 and measure time to evaluate all variables
        start_time = time.time()
        
        # Update value1
        self.data.update('stats', {'value1': 15})
        
        # Evaluate all variables
        self.eval.evalAll()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\nWith dependency tracking: {execution_time:.6f} seconds")
        print(f"Affected variables count: {len(variable_registry.get_all_affected_variables('stats[\"value1\"]'))}")
        
        # Keep the result for comparison
        self.dependency_tracking_time = execution_time
    
    def test_performance_without_dependency_tracking(self):
        """Simulate performance without dependency tracking (evaluating all variables)."""
        # Update value1 and measure time to force evaluation of all variables
        start_time = time.time()
        
        # Update value1
        self.data.update('stats', {'value1': 20})
        
        # Force evaluation of ALL variables regardless of dependencies
        for dv in self.value1_deps + self.value2_deps + self.value3_deps + self.mixed_deps:
            dv.mark_for_update()  # Mark all as needing update
            dv.eval()  # Evaluate each one
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"Without dependency tracking: {execution_time:.6f} seconds")
        print(f"Total variables count: {len(self.value1_deps + self.value2_deps + self.value3_deps + self.mixed_deps)}")
        
        # Keep the result for comparison
        self.no_dependency_tracking_time = execution_time
    
    def test_compare_performance(self):
        """Compare the performance with and without dependency tracking."""
        self.test_performance_with_dependency_tracking()
        self.test_performance_without_dependency_tracking()
        
        # Calculate improvement factor
        improvement_factor = self.no_dependency_tracking_time / self.dependency_tracking_time
        
        print(f"\nPerformance improvement factor: {improvement_factor:.2f}x faster with dependency tracking")
        print(f"With dependency tracking: {self.dependency_tracking_time:.6f} seconds")
        print(f"Without dependency tracking: {self.no_dependency_tracking_time:.6f} seconds")
        
        # The test should show an improvement with dependency tracking
        self.assertGreater(improvement_factor, 1.0, 
                          "Dependency tracking should improve performance")

class RealWorldScenarioBenchmark(unittest.TestCase):
    """Benchmark realistic scenarios with complex dependencies."""
    
    def setUp(self):
        # Create a dataset mimicking a real application
        self.data = dataset()
        self.data.add('user', {
            'name': 'John Doe',
            'preferences': {'theme': 'dark', 'lang': 'en'},
            'is_admin': False
        })
        self.data.add('system', {
            'status': 'running',
            'cpu': 32,
            'memory': 84,
            'disk': 55,
            'network': 12
        })
        self.data.add('content', {
            'title': 'Dashboard',
            'items': 25,
            'last_updated': '2023-05-01'
        })
        
        # Create evaluator
        self.eval = evaluator(self.data)
        
        # Create variables with realistic dependencies
        # Header section variables
        self.header_vars = []
        self.header_vars.append(self.eval.compile("f\"Welcome, {user['name']}\"", name="welcome_msg", dynamic=True))
        self.header_vars.append(self.eval.compile("user['preferences']['theme']", name="theme", dynamic=True))
        self.header_vars.append(self.eval.compile("user['preferences']['lang']", name="lang", dynamic=True))
        
        # System stats variables
        self.system_vars = []
        self.system_vars.append(self.eval.compile("f\"CPU: {system['cpu']}%\"", name="cpu_display", dynamic=True))
        self.system_vars.append(self.eval.compile("f\"Memory: {system['memory']}%\"", name="memory_display", dynamic=True))
        self.system_vars.append(self.eval.compile("f\"Disk: {system['disk']}%\"", name="disk_display", dynamic=True))
        self.system_vars.append(self.eval.compile("f\"Network: {system['network']}%\"", name="network_display", dynamic=True))
        self.system_vars.append(self.eval.compile("'red' if system['cpu'] > 80 else 'green'", name="cpu_color", dynamic=True))
        self.system_vars.append(self.eval.compile("'red' if system['memory'] > 80 else 'green'", name="memory_color", dynamic=True))
        
        # Content variables
        self.content_vars = []
        self.content_vars.append(self.eval.compile("content['title']", name="content_title", dynamic=True))
        self.content_vars.append(self.eval.compile("f\"{content['items']} items\"", name="item_count", dynamic=True))
        self.content_vars.append(self.eval.compile("f\"Last updated: {content['last_updated']}\"", name="update_info", dynamic=True))
        
        # Complex variables that depend on multiple sources
        self.complex_vars = []
        self.complex_vars.append(self.eval.compile(
            "f\"Memory usage {'critical' if system['memory'] > 80 else 'acceptable'} for {user['name']}\"", 
            name="status_message", dynamic=True))
        self.complex_vars.append(self.eval.compile(
            "'Admin Dashboard' if user['is_admin'] else content['title']", 
            name="display_title", dynamic=True))
        
        # Force initial evaluation
        self.eval.evalAll()
    
    def test_realistic_user_change(self):
        """Test performance when changing user preferences."""
        # Set up counters
        self.eval_count = 0
        original_eval = dynamicValue.eval
        
        # Replace eval with counting version
        def counting_eval(self_):
            self.eval_count += 1
            return original_eval(self_)
        
        dynamicValue.eval = counting_eval
        
        try:
            # Update user preferences
            self.data.update('user', {'preferences': {'theme': 'light', 'lang': 'fr'}})
            
            # Evaluate all variables
            self.eval.evalAll()
            
            # Count how many variables were evaluated
            total_vars = len(self.header_vars + self.system_vars + self.content_vars + self.complex_vars)
            
            print(f"\nRealistic scenario - User preference change:")
            print(f"Total variables: {total_vars}")
            print(f"Variables evaluated: {self.eval_count}")
            print(f"Efficiency: {(total_vars - self.eval_count) / total_vars * 100:.1f}% of evaluations avoided")
            
            # Only user-related variables should be evaluated
            self.assertLess(self.eval_count, total_vars, 
                           "With dependency tracking, not all variables should be evaluated")
        finally:
            # Restore original eval method
            dynamicValue.eval = original_eval
    
    def test_realistic_system_change(self):
        """Test performance when changing system metrics."""
        # Set up counters
        self.eval_count = 0
        original_eval = dynamicValue.eval
        
        # Replace eval with counting version
        def counting_eval(self_):
            self.eval_count += 1
            return original_eval(self_)
        
        dynamicValue.eval = counting_eval
        
        try:
            # Update system metrics - critical CPU
            self.data.update('system', {'cpu': 95})
            
            # Evaluate all variables
            self.eval.evalAll()
            
            # Count how many variables were evaluated
            total_vars = len(self.header_vars + self.system_vars + self.content_vars + self.complex_vars)
            
            print(f"\nRealistic scenario - System metric change:")
            print(f"Total variables: {total_vars}")
            print(f"Variables evaluated: {self.eval_count}")
            print(f"Efficiency: {(total_vars - self.eval_count) / total_vars * 100:.1f}% of evaluations avoided")
            
            # Only system-related variables should be evaluated
            self.assertLess(self.eval_count, total_vars, 
                           "With dependency tracking, not all variables should be evaluated")
        finally:
            # Restore original eval method
            dynamicValue.eval = original_eval

if __name__ == "__main__":
    unittest.main() 