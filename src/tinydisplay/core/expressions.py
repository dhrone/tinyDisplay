"""Safe expression evaluation using asteval for tinyDisplay reactive bindings.

This module provides secure expression evaluation capabilities for reactive
data bindings, with performance optimization and security controls suitable
for embedded devices.
"""

import ast
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Set
from enum import IntEnum

import asteval

try:
    from asteval import Interpreter, make_symbol_table
except ImportError:
    raise ImportError(
        "asteval is required for expression evaluation. "
        "Install it with: pip install asteval"
    )


class ExpressionError(Exception):
    """Base exception for expression evaluation errors."""

    pass


class SecurityError(ExpressionError):
    """Raised when expression violates security constraints."""

    pass


class EvaluationError(ExpressionError):
    """Raised when expression evaluation fails."""

    pass


class TimeoutError(ExpressionError):
    """Raised when expression evaluation times out."""

    pass


class ExpressionComplexity(IntEnum):
    """Expression complexity levels for performance control."""

    SIMPLE = 1  # Basic arithmetic, comparisons
    MODERATE = 2  # Function calls, list comprehensions
    COMPLEX = 3  # Nested operations, loops


@dataclass
class SecurityPolicy:
    """Security policy for expression evaluation."""

    # Allowed built-in functions
    allowed_builtins: Set[str] = field(
        default_factory=lambda: {
            "abs",
            "all",
            "any",
            "bool",
            "dict",
            "float",
            "int",
            "len",
            "list",
            "max",
            "min",
            "round",
            "str",
            "sum",
            "tuple",
            "type",
            "zip",
            "enumerate",
            "range",
            "sorted",
            "reversed",
        }
    )

    # Forbidden names/attributes
    forbidden_names: Set[str] = field(
        default_factory=lambda: {
            "__import__",
            "__builtins__",
            "eval",
            "exec",
            "compile",
            "open",
            "file",
            "input",
            "raw_input",
            "reload",
            "vars",
            "globals",
            "locals",
            "dir",
            "hasattr",
            "getattr",
            "setattr",
            "delattr",
            "__class__",
            "__bases__",
            "__dict__",
            "__module__",
        }
    )

    # Maximum expression length
    max_expression_length: int = 1000

    # Maximum evaluation time (seconds)
    max_evaluation_time: float = 0.1

    # Maximum recursion depth
    max_recursion_depth: int = 10

    # Allow attribute access
    allow_attribute_access: bool = True

    # Allowed modules for import
    allowed_modules: Set[str] = field(
        default_factory=lambda: {"math", "datetime", "time"}
    )


@dataclass
class ExpressionResult:
    """Result of expression evaluation."""

    value: Any
    execution_time: float
    complexity: ExpressionComplexity
    variables_used: Set[str]
    success: bool = True
    error: Optional[str] = None


class ExpressionAnalyzer:
    """Analyzes expressions for security and complexity."""

    def __init__(self, security_policy: SecurityPolicy):
        self.security_policy = security_policy

    def analyze(self, expression: str) -> ExpressionComplexity:
        """Analyze expression complexity and security.

        Args:
            expression: Expression string to analyze

        Returns:
            Expression complexity level

        Raises:
            SecurityError: If expression violates security policy
        """
        # Check expression length
        if len(expression) > self.security_policy.max_expression_length:
            raise SecurityError(
                f"Expression too long: {len(expression)} > {self.security_policy.max_expression_length}"
            )

        # Parse expression to AST
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise SecurityError(f"Invalid syntax: {e}")

        # Analyze AST for security violations and complexity
        complexity = self._analyze_ast(tree)

        return complexity

    def _analyze_ast(self, node: ast.AST) -> ExpressionComplexity:
        """Analyze AST node for security and complexity."""
        complexity = ExpressionComplexity.SIMPLE

        for child in ast.walk(node):
            # Check for forbidden names
            if isinstance(child, ast.Name):
                if child.id in self.security_policy.forbidden_names:
                    raise SecurityError(f"Forbidden name: {child.id}")

            # Check for forbidden attributes
            elif isinstance(child, ast.Attribute):
                if not self.security_policy.allow_attribute_access:
                    raise SecurityError("Attribute access not allowed")
                if child.attr in self.security_policy.forbidden_names:
                    raise SecurityError(f"Forbidden attribute: {child.attr}")

            # Check for imports
            elif isinstance(child, ast.Import) or isinstance(child, ast.ImportFrom):
                raise SecurityError("Import statements not allowed")

            # Analyze complexity
            if isinstance(child, (ast.FunctionDef, ast.ClassDef, ast.For, ast.While)):
                raise SecurityError("Function/class definitions and loops not allowed")

            elif isinstance(child, ast.Call):
                complexity = max(complexity, ExpressionComplexity.MODERATE)

            elif isinstance(
                child, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)
            ):
                complexity = max(complexity, ExpressionComplexity.MODERATE)

            elif isinstance(child, (ast.Lambda, ast.IfExp)):
                complexity = max(complexity, ExpressionComplexity.COMPLEX)

        return complexity


class ExpressionEvaluator:
    """Safe expression evaluator using asteval with security controls."""

    def __init__(self, security_policy: Optional[SecurityPolicy] = None):
        """Initialize expression evaluator.

        Args:
            security_policy: Security policy for evaluation
        """
        self.security_policy = security_policy or SecurityPolicy()
        self.analyzer = ExpressionAnalyzer(self.security_policy)

        # Thread-local storage for interpreters
        self._local = threading.local()

        # Performance tracking
        self._stats = {
            "total_evaluations": 0,
            "successful_evaluations": 0,
            "failed_evaluations": 0,
            "security_violations": 0,
            "timeouts": 0,
            "total_execution_time": 0.0,
        }
        self._stats_lock = threading.Lock()

        # Expression cache for performance
        self._expression_cache: Dict[str, ExpressionResult] = {}
        self._cache_lock = threading.RLock()
        self._max_cache_size = 1000

    def _get_interpreter(self) -> Interpreter:
        """Get thread-local asteval interpreter."""
        if not hasattr(self._local, "interpreter"):
            # Create symbol table with allowed builtins only
            symbol_table = make_symbol_table()

            # Remove forbidden builtins and keep only allowed ones
            for name in list(symbol_table.keys()):
                if name not in self.security_policy.allowed_builtins:
                    del symbol_table[name]

            # Add safe math functions
            import math

            safe_math = {
                "sin",
                "cos",
                "tan",
                "asin",
                "acos",
                "atan",
                "atan2",
                "sinh",
                "cosh",
                "tanh",
                "asinh",
                "acosh",
                "atanh",
                "exp",
                "log",
                "log10",
                "log2",
                "sqrt",
                "pow",
                "ceil",
                "floor",
                "trunc",
                "fabs",
                "degrees",
                "radians",
                "pi",
                "e",
            }

            for name in safe_math:
                if hasattr(math, name):
                    symbol_table[name] = getattr(math, name)

            # Create interpreter with restricted symbol table
            self._local.interpreter = Interpreter(
                symtable=symbol_table,
                use_numpy=False,  # Disable numpy for embedded devices
                max_time=self.security_policy.max_evaluation_time,
                readonly_symbols=list(symbol_table.keys()),
            )

        return self._local.interpreter

    def evaluate(
        self,
        expression: str,
        variables: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> ExpressionResult:
        """Evaluate expression safely.

        Args:
            expression: Expression string to evaluate
            variables: Variables available to expression
            use_cache: Whether to use expression cache

        Returns:
            Expression evaluation result
        """
        variables = variables or {}

        # Check cache first
        cache_key = f"{expression}:{hash(frozenset(variables.items()))}"
        if use_cache:
            with self._cache_lock:
                if cache_key in self._expression_cache:
                    cached_result = self._expression_cache[cache_key]
                    # Return copy to avoid mutation
                    return ExpressionResult(
                        value=cached_result.value,
                        execution_time=cached_result.execution_time,
                        complexity=cached_result.complexity,
                        variables_used=cached_result.variables_used.copy(),
                        success=cached_result.success,
                        error=cached_result.error,
                    )

        start_time = time.perf_counter()

        try:
            # Analyze expression for security and complexity
            complexity = self.analyzer.analyze(expression)

            # Get thread-local interpreter
            interpreter = self._get_interpreter()

            # Set variables in interpreter
            for name, value in variables.items():
                interpreter.symtable[name] = value

            # Track which variables are used
            variables_used = self._extract_variables(expression)

            # Evaluate expression with timeout
            result = interpreter.eval(expression)

            # Check for evaluation errors
            if interpreter.expr is None:
                raise EvaluationError("Expression evaluation failed")

            if hasattr(interpreter, "error") and interpreter.error:
                raise EvaluationError(f"Evaluation error: {interpreter.error}")

            execution_time = time.perf_counter() - start_time

            # Create result
            eval_result = ExpressionResult(
                value=result,
                execution_time=execution_time,
                complexity=complexity,
                variables_used=variables_used,
                success=True,
            )

            # Update stats
            with self._stats_lock:
                self._stats["total_evaluations"] += 1
                self._stats["successful_evaluations"] += 1
                self._stats["total_execution_time"] += execution_time

            # Cache result
            if use_cache:
                self._cache_result(cache_key, eval_result)

            return eval_result

        except SecurityError as e:
            execution_time = time.perf_counter() - start_time
            with self._stats_lock:
                self._stats["total_evaluations"] += 1
                self._stats["failed_evaluations"] += 1
                self._stats["security_violations"] += 1

            return ExpressionResult(
                value=None,
                execution_time=execution_time,
                complexity=ExpressionComplexity.SIMPLE,
                variables_used=set(),
                success=False,
                error=f"Security violation: {e}",
            )

        except Exception as e:
            execution_time = time.perf_counter() - start_time
            with self._stats_lock:
                self._stats["total_evaluations"] += 1
                self._stats["failed_evaluations"] += 1
                if "timeout" in str(e).lower():
                    self._stats["timeouts"] += 1

            return ExpressionResult(
                value=None,
                execution_time=execution_time,
                complexity=ExpressionComplexity.SIMPLE,
                variables_used=set(),
                success=False,
                error=str(e),
            )

    def _extract_variables(self, expression: str) -> Set[str]:
        """Extract variable names from expression."""
        try:
            tree = ast.parse(expression, mode="eval")
            variables = set()

            # Ensure allowed_builtins is a set
            allowed_builtins = getattr(self.security_policy, "allowed_builtins", set())
            if not isinstance(allowed_builtins, set):
                allowed_builtins = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    # Skip built-in functions and constants
                    if node.id not in allowed_builtins:
                        variables.add(node.id)

            return variables
        except Exception:
            return set()

    def _cache_result(self, cache_key: str, result: ExpressionResult) -> None:
        """Cache expression result."""
        with self._cache_lock:
            # Implement LRU-style cache eviction
            if len(self._expression_cache) >= self._max_cache_size:
                # Remove oldest entries (simple FIFO for now)
                keys_to_remove = list(self._expression_cache.keys())[:100]
                for key in keys_to_remove:
                    del self._expression_cache[key]

            self._expression_cache[cache_key] = result

    def validate_expression(self, expression: str) -> bool:
        """Validate expression without evaluating it.

        Args:
            expression: Expression to validate

        Returns:
            True if expression is valid and safe
        """
        try:
            self.analyzer.analyze(expression)
            return True
        except (SecurityError, SyntaxError):
            return False

    def clear_cache(self) -> None:
        """Clear expression cache."""
        with self._cache_lock:
            self._expression_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get evaluation statistics.

        Returns:
            Dictionary of performance and usage statistics
        """
        with self._stats_lock:
            stats = self._stats.copy()

        # Add cache statistics
        with self._cache_lock:
            stats.update(
                {
                    "cache_size": len(self._expression_cache),
                    "max_cache_size": self._max_cache_size,
                }
            )

        # Calculate derived metrics
        if stats["total_evaluations"] > 0:
            stats["success_rate"] = (
                stats["successful_evaluations"] / stats["total_evaluations"]
            )
            stats["average_execution_time"] = (
                stats["total_execution_time"] / stats["total_evaluations"]
            )
        else:
            stats["success_rate"] = 0.0
            stats["average_execution_time"] = 0.0

        return stats

    def reset_stats(self) -> None:
        """Reset evaluation statistics."""
        with self._stats_lock:
            self._stats = {
                "total_evaluations": 0,
                "successful_evaluations": 0,
                "failed_evaluations": 0,
                "security_violations": 0,
                "timeouts": 0,
                "total_execution_time": 0.0,
            }


class ReactiveBinding:
    """Reactive binding that evaluates expressions when variables change."""

    def __init__(
        self,
        expression: str,
        evaluator: ExpressionEvaluator,
        target_callback: Optional[Callable[[Any], None]] = None,
    ):
        """Initialize reactive binding.

        Args:
            expression: Expression to evaluate
            evaluator: Expression evaluator to use
            target_callback: Callback to call with evaluation result
        """
        self.expression = expression
        self.evaluator = evaluator
        self.target_callback = target_callback

        # Track variables this binding depends on
        self.dependencies = self.evaluator._extract_variables(expression)

        # Current state
        self.current_value = None
        self.last_evaluation_time = 0.0
        self.evaluation_count = 0

        # Validation
        if not self.evaluator.validate_expression(expression):
            raise SecurityError(f"Invalid or unsafe expression: {expression}")

    def evaluate(self, variables: Dict[str, Any]) -> Any:
        """Evaluate binding with given variables.

        Args:
            variables: Variables for evaluation

        Returns:
            Evaluation result value
        """
        result = self.evaluator.evaluate(self.expression, variables)

        if result.success:
            self.current_value = result.value
            self.last_evaluation_time = result.execution_time
            self.evaluation_count += 1

            # Call target callback if provided
            if self.target_callback:
                try:
                    self.target_callback(result.value)
                except Exception:
                    pass  # Ignore callback errors

            return result.value
        else:
            raise EvaluationError(f"Binding evaluation failed: {result.error}")

    def depends_on(self, variable_name: str) -> bool:
        """Check if binding depends on a variable.

        Args:
            variable_name: Variable name to check

        Returns:
            True if binding depends on the variable
        """
        return variable_name in self.dependencies


# Convenience functions
def create_evaluator(
    max_time: float = 0.1,
    allow_attribute_access: bool = True,
) -> ExpressionEvaluator:
    """Create expression evaluator with common settings.

    Args:
        max_time: Maximum evaluation time in seconds
        allow_attribute_access: Whether to allow attribute access

    Returns:
        Configured expression evaluator
    """
    policy = SecurityPolicy(
        max_evaluation_time=max_time,
        allow_attribute_access=allow_attribute_access,
    )
    return ExpressionEvaluator(policy)


def evaluate_expression(
    expression: str,
    variables: Optional[Dict[str, Any]] = None,
    evaluator: Optional[ExpressionEvaluator] = None,
) -> Any:
    """Evaluate expression with default settings.

    Args:
        expression: Expression to evaluate
        variables: Variables for evaluation
        evaluator: Custom evaluator (creates default if None)

    Returns:
        Evaluation result value

    Raises:
        EvaluationError: If evaluation fails
    """
    if evaluator is None:
        evaluator = create_evaluator()

    result = evaluator.evaluate(expression, variables)

    if result.success:
        return result.value
    else:
        raise EvaluationError(f"Expression evaluation failed: {result.error}")


def validate_expression(
    expression: str,
    evaluator: Optional[ExpressionEvaluator] = None,
) -> bool:
    """Validate expression with default settings.

    Args:
        expression: Expression to validate
        evaluator: Custom evaluator (creates default if None)

    Returns:
        True if expression is valid and safe
    """
    if evaluator is None:
        evaluator = create_evaluator()

    return evaluator.validate_expression(expression)
