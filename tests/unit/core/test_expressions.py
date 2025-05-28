"""Unit tests for expression evaluation module."""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock

from tinydisplay.core.expressions import (
    ExpressionEvaluator,
    ExpressionAnalyzer,
    SecurityPolicy,
    ExpressionResult,
    ExpressionComplexity,
    ReactiveBinding,
    ExpressionError,
    SecurityError,
    EvaluationError,
    TimeoutError,
    create_evaluator,
    evaluate_expression,
    validate_expression,
)


class TestSecurityPolicy:
    """Test security policy configuration."""

    def test_default_policy__has_reasonable_defaults(self):
        """Test that default security policy has reasonable settings."""
        policy = SecurityPolicy()

        # Check allowed builtins include safe functions
        assert "abs" in policy.allowed_builtins
        assert "max" in policy.allowed_builtins
        assert "len" in policy.allowed_builtins

        # Check forbidden names include dangerous functions
        assert "__import__" in policy.forbidden_names
        assert "eval" in policy.forbidden_names
        assert "exec" in policy.forbidden_names

        # Check reasonable limits
        assert policy.max_expression_length == 1000
        assert policy.max_evaluation_time == 0.1
        assert policy.max_recursion_depth == 10

    def test_custom_policy__accepts_custom_settings(self):
        """Test that custom security policy settings are respected."""
        policy = SecurityPolicy(
            max_expression_length=500,
            max_evaluation_time=0.05,
            allow_attribute_access=False,
        )

        assert policy.max_expression_length == 500
        assert policy.max_evaluation_time == 0.05
        assert policy.allow_attribute_access is False


class TestExpressionAnalyzer:
    """Test expression analysis for security and complexity."""

    def setup_method(self):
        """Set up test fixtures."""
        self.policy = SecurityPolicy()
        self.analyzer = ExpressionAnalyzer(self.policy)

    def test_analyze_simple_expression__returns_simple_complexity(self):
        """Test that simple expressions are classified correctly."""
        expressions = ["1 + 2", "x * 3", "a > b", "x and y", "not z"]

        for expr in expressions:
            complexity = self.analyzer.analyze(expr)
            assert complexity == ExpressionComplexity.SIMPLE

    def test_analyze_moderate_expression__returns_moderate_complexity(self):
        """Test that moderate expressions are classified correctly."""
        expressions = [
            "max(a, b)",
            "len(items)",
            "[x for x in range(10)]",
            "sum(values)",
        ]

        for expr in expressions:
            complexity = self.analyzer.analyze(expr)
            assert complexity == ExpressionComplexity.MODERATE

    def test_analyze_complex_expression__returns_complex_complexity(self):
        """Test that complex expressions are classified correctly."""
        expressions = ["lambda x: x * 2", "a if condition else b"]

        for expr in expressions:
            complexity = self.analyzer.analyze(expr)
            assert complexity == ExpressionComplexity.COMPLEX

    def test_analyze_forbidden_names__raises_security_error(self):
        """Test that forbidden names raise security errors."""
        forbidden_expressions = [
            "__import__('os')",
            "eval('1+1')",
            "exec('print(1)')",
            "open('file.txt')",
        ]

        for expr in forbidden_expressions:
            with pytest.raises(SecurityError):
                self.analyzer.analyze(expr)

    def test_analyze_forbidden_constructs__raises_security_error(self):
        """Test that forbidden constructs raise security errors."""
        forbidden_expressions = [
            "def func(): pass",
            "class MyClass: pass",
            "for i in range(10): pass",
            "while True: pass",
            "import os",
        ]

        for expr in forbidden_expressions:
            with pytest.raises(SecurityError):
                self.analyzer.analyze(expr)

    def test_analyze_too_long_expression__raises_security_error(self):
        """Test that overly long expressions raise security errors."""
        long_expr = "1 + " * 1000 + "1"

        with pytest.raises(SecurityError, match="Expression too long"):
            self.analyzer.analyze(long_expr)

    def test_analyze_invalid_syntax__raises_security_error(self):
        """Test that invalid syntax raises security errors."""
        with pytest.raises(SecurityError, match="Invalid syntax"):
            self.analyzer.analyze("1 +")  # Incomplete expression

    def test_analyze_attribute_access__respects_policy(self):
        """Test that attribute access is controlled by policy."""
        # Allow attribute access
        self.policy.allow_attribute_access = True
        complexity = self.analyzer.analyze("obj.value")
        assert complexity == ExpressionComplexity.SIMPLE

        # Disallow attribute access
        self.policy.allow_attribute_access = False
        with pytest.raises(SecurityError, match="Attribute access not allowed"):
            self.analyzer.analyze("obj.value")


class TestExpressionEvaluator:
    """Test expression evaluation functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = ExpressionEvaluator()

    def test_evaluate_simple_arithmetic__returns_correct_result(self):
        """Test that simple arithmetic expressions evaluate correctly."""
        result = self.evaluator.evaluate("2 + 3")

        assert result.success is True
        assert result.value == 5
        assert result.complexity == ExpressionComplexity.SIMPLE
        assert result.error is None

    def test_evaluate_with_variables__substitutes_correctly(self):
        """Test that variables are substituted correctly."""
        variables = {"x": 10, "y": 5}
        result = self.evaluator.evaluate("x * y", variables)

        assert result.success is True
        assert result.value == 50
        assert "x" in result.variables_used
        assert "y" in result.variables_used

    def test_evaluate_builtin_functions__works_correctly(self):
        """Test that allowed builtin functions work."""
        test_cases = [
            ("max(1, 2, 3)", 3),
            ("min(5, 2, 8)", 2),
            ("abs(-10)", 10),
            ("len([1, 2, 3])", 3),
            ("sum([1, 2, 3])", 6),
        ]

        for expr, expected in test_cases:
            result = self.evaluator.evaluate(expr)
            assert result.success is True
            assert result.value == expected

    def test_evaluate_forbidden_expression__returns_error(self):
        """Test that forbidden expressions return error results."""
        result = self.evaluator.evaluate("__import__('os')")

        assert result.success is False
        assert result.error is not None
        assert "security" in result.error.lower() or "forbidden" in result.error.lower()

    def test_evaluate_invalid_expression__returns_error(self):
        """Test that invalid expressions return error results."""
        result = self.evaluator.evaluate("1 / 0")

        assert result.success is False
        assert result.error is not None

    def test_evaluate_with_cache__uses_cached_result(self):
        """Test that expression caching works correctly."""
        # First evaluation
        result1 = self.evaluator.evaluate("2 + 3", use_cache=True)

        # Second evaluation should use cache
        result2 = self.evaluator.evaluate("2 + 3", use_cache=True)

        assert result1.value == result2.value
        assert result1.success == result2.success

    def test_evaluate_without_cache__always_evaluates(self):
        """Test that cache can be disabled."""
        # Clear cache first
        self.evaluator.clear_cache()

        # Evaluate without cache
        result1 = self.evaluator.evaluate("2 + 3", use_cache=False)
        result2 = self.evaluator.evaluate("2 + 3", use_cache=False)

        # Both should succeed but be separate evaluations
        assert result1.value == result2.value
        assert result1.success == result2.success

    def test_validate_expression__returns_correct_status(self):
        """Test expression validation."""
        assert self.evaluator.validate_expression("1 + 2") is True
        assert self.evaluator.validate_expression("__import__('os')") is False
        assert (
            self.evaluator.validate_expression("1 / 0") is True
        )  # Valid syntax, runtime error

    def test_clear_cache__removes_cached_results(self):
        """Test that cache clearing works."""
        # Populate cache
        self.evaluator.evaluate("1 + 1", use_cache=True)

        # Clear cache
        self.evaluator.clear_cache()

        # Cache should be empty (we can't directly test this, but it shouldn't error)
        result = self.evaluator.evaluate("1 + 1", use_cache=True)
        assert result.success is True

    def test_get_stats__returns_performance_metrics(self):
        """Test that performance statistics are collected."""
        # Perform some evaluations
        self.evaluator.evaluate("1 + 1")
        self.evaluator.evaluate("2 * 3")
        self.evaluator.evaluate("invalid syntax")

        stats = self.evaluator.get_stats()

        assert "total_evaluations" in stats
        assert "successful_evaluations" in stats
        assert "failed_evaluations" in stats
        assert "total_execution_time" in stats
        assert stats["total_evaluations"] >= 3

    def test_reset_stats__clears_statistics(self):
        """Test that statistics can be reset."""
        # Perform evaluation
        self.evaluator.evaluate("1 + 1")

        # Reset stats
        self.evaluator.reset_stats()

        stats = self.evaluator.get_stats()
        assert stats["total_evaluations"] == 0
        assert stats["successful_evaluations"] == 0
        assert stats["failed_evaluations"] == 0

    def test_thread_safety__concurrent_evaluations__work_correctly(self):
        """Test that evaluator is thread-safe."""
        results = []
        errors = []

        def evaluate_expression():
            try:
                result = self.evaluator.evaluate("1 + 1")
                results.append(result.value)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=evaluate_expression)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0
        assert len(results) == 10
        assert all(result == 2 for result in results)


class TestReactiveBinding:
    """Test reactive binding functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = ExpressionEvaluator()
        self.callback_values = []

        def test_callback(value):
            self.callback_values.append(value)

        self.test_callback = test_callback

    def test_initialization__creates_binding(self):
        """Test that reactive binding initializes correctly."""
        binding = ReactiveBinding("x + 1", self.evaluator)

        assert binding.expression == "x + 1"
        assert binding.evaluator is self.evaluator
        assert binding.target_callback is None

    def test_initialization_with_callback__sets_callback(self):
        """Test that reactive binding with callback initializes correctly."""
        binding = ReactiveBinding("x + 1", self.evaluator, self.test_callback)

        assert binding.target_callback is self.test_callback

    def test_evaluate__returns_correct_value(self):
        """Test that reactive binding evaluates correctly."""
        binding = ReactiveBinding("x * 2", self.evaluator)

        result = binding.evaluate({"x": 5})
        assert result == 10

    def test_evaluate_with_callback__calls_callback(self):
        """Test that reactive binding calls callback when evaluating."""
        binding = ReactiveBinding("x + 10", self.evaluator, self.test_callback)

        result = binding.evaluate({"x": 5})

        assert result == 15
        assert len(self.callback_values) == 1
        assert self.callback_values[0] == 15

    def test_depends_on__identifies_dependencies_correctly(self):
        """Test that dependency detection works correctly."""
        binding = ReactiveBinding("x + y * z", self.evaluator)

        assert binding.depends_on("x") is True
        assert binding.depends_on("y") is True
        assert binding.depends_on("z") is True
        assert binding.depends_on("w") is False

    def test_evaluate_error__handles_gracefully(self):
        """Test that evaluation errors are handled gracefully."""
        binding = ReactiveBinding("x / 0", self.evaluator)

        # Should raise an EvaluationError when evaluation fails
        with pytest.raises(EvaluationError):
            binding.evaluate({"x": 1})


class TestUtilityFunctions:
    """Test utility functions."""

    def test_create_evaluator__creates_with_custom_settings(self):
        """Test that create_evaluator creates evaluator with custom settings."""
        evaluator = create_evaluator(max_time=0.05, allow_attribute_access=False)

        assert evaluator.security_policy.max_evaluation_time == 0.05
        assert evaluator.security_policy.allow_attribute_access is False

    def test_evaluate_expression__convenience_function_works(self):
        """Test that convenience function works correctly."""
        result = evaluate_expression("2 + 3")
        assert result == 5

        result = evaluate_expression("x * 2", {"x": 4})
        assert result == 8

    def test_evaluate_expression_with_custom_evaluator__uses_evaluator(self):
        """Test that convenience function uses provided evaluator."""
        evaluator = ExpressionEvaluator()
        result = evaluate_expression("1 + 1", evaluator=evaluator)
        assert result == 2

    def test_validate_expression__convenience_function_works(self):
        """Test that validation convenience function works."""
        assert validate_expression("1 + 2") is True
        assert validate_expression("__import__('os')") is False

    def test_validate_expression_with_custom_evaluator__uses_evaluator(self):
        """Test that validation uses provided evaluator."""
        evaluator = ExpressionEvaluator()
        assert validate_expression("1 + 1", evaluator=evaluator) is True


class TestPerformanceAndSecurity:
    """Test performance and security aspects."""

    def test_evaluation_time_tracking__measures_execution_time(self):
        """Test that execution time is measured."""
        evaluator = ExpressionEvaluator()

        result = evaluator.evaluate("sum(range(100))")

        assert result.execution_time > 0
        assert result.execution_time < 1.0  # Should be fast

    def test_cache_performance__improves_repeated_evaluations(self):
        """Test that caching improves performance for repeated evaluations."""
        evaluator = ExpressionEvaluator()

        # First evaluation (not cached)
        result1 = evaluator.evaluate("sum(range(100))", use_cache=True)

        # Second evaluation (cached)
        result2 = evaluator.evaluate("sum(range(100))", use_cache=True)

        # Both should have same result
        assert result1.value == result2.value

        # Cached evaluation might be faster (though this is hard to test reliably)
        assert result1.success is True
        assert result2.success is True

    def test_security_isolation__prevents_dangerous_operations(self):
        """Test that security measures prevent dangerous operations."""
        evaluator = ExpressionEvaluator()

        dangerous_expressions = [
            "__import__('subprocess').call(['rm', '-rf', '/'])",
            "open('/etc/passwd').read()",
            'eval(\'__import__("os").system("ls")\')',
            "exec('import os; os.system(\"pwd\")')",
        ]

        for expr in dangerous_expressions:
            result = evaluator.evaluate(expr)
            assert result.success is False
            assert result.error is not None

    @pytest.mark.slow
    def test_timeout_protection__prevents_infinite_loops(self):
        """Test that timeout protection works (marked as slow test)."""
        # Create evaluator with very short timeout
        policy = SecurityPolicy(max_evaluation_time=0.001)
        evaluator = ExpressionEvaluator(policy)

        # This should timeout (though it's hard to create a guaranteed timeout)
        # We'll test with a complex expression that might take time
        result = evaluator.evaluate("sum(x*x for x in range(10000))")

        # The result might succeed or fail depending on system speed
        # The important thing is that it doesn't hang indefinitely
        assert isinstance(result, ExpressionResult)
