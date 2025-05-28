"""Code complexity analysis for DSL validation framework.

This module provides comprehensive complexity analysis tools to measure
maintainability, cognitive load, and structural complexity of DSL vs JSON approaches.
"""

import ast
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum


class ComplexityType(Enum):
    """Types of complexity measurements."""

    CYCLOMATIC = "cyclomatic"
    COGNITIVE = "cognitive"
    STRUCTURAL = "structural"
    MAINTAINABILITY = "maintainability"
    READABILITY = "readability"


@dataclass
class ComplexityMetrics:
    """Comprehensive complexity metrics for code analysis."""

    # Basic metrics
    lines_of_code: int
    logical_lines: int
    comment_lines: int
    blank_lines: int

    # Structural complexity
    cyclomatic_complexity: int
    cognitive_complexity: int
    nesting_depth: int

    # Maintainability metrics
    maintainability_index: float
    technical_debt_ratio: float
    code_duplication_ratio: float

    # Readability metrics
    readability_score: float
    average_line_length: float
    identifier_clarity_score: float

    # JSON-specific metrics (when applicable)
    json_depth: Optional[int] = None
    json_key_count: Optional[int] = None
    json_array_count: Optional[int] = None

    # DSL-specific metrics (when applicable)
    function_call_count: Optional[int] = None
    method_chain_length: Optional[int] = None
    variable_usage_count: Optional[int] = None


class ComplexityAnalyzer:
    """Analyzer for measuring code complexity across different dimensions."""

    def __init__(self):
        """Initialize the complexity analyzer."""
        self.analysis_cache: Dict[str, ComplexityMetrics] = {}

    def analyze_code(self, code: str, code_type: str = "auto") -> ComplexityMetrics:
        """Analyze code complexity comprehensively.

        Args:
            code: Source code to analyze
            code_type: "dsl", "json", or "auto" for automatic detection

        Returns:
            ComplexityMetrics with comprehensive analysis
        """
        # Cache key for performance
        cache_key = f"{hash(code)}_{code_type}"
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]

        # Auto-detect code type if needed
        if code_type == "auto":
            code_type = self._detect_code_type(code)

        # Basic line analysis
        lines = code.split("\n")
        logical_lines = [line.strip() for line in lines if line.strip()]
        comment_lines = [
            line for line in logical_lines if self._is_comment_line(line, code_type)
        ]
        blank_lines = [line for line in lines if not line.strip()]

        # Initialize metrics
        metrics = ComplexityMetrics(
            lines_of_code=len(lines),
            logical_lines=len(logical_lines),
            comment_lines=len(comment_lines),
            blank_lines=len(blank_lines),
            cyclomatic_complexity=0,
            cognitive_complexity=0,
            nesting_depth=0,
            maintainability_index=0.0,
            technical_debt_ratio=0.0,
            code_duplication_ratio=0.0,
            readability_score=0.0,
            average_line_length=0.0,
            identifier_clarity_score=0.0,
        )

        # Calculate average line length
        if logical_lines:
            metrics.average_line_length = sum(
                len(line) for line in logical_lines
            ) / len(logical_lines)

        # Type-specific analysis
        if code_type == "dsl":
            self._analyze_dsl_complexity(code, metrics)
        elif code_type == "json":
            self._analyze_json_complexity(code, metrics)

        # Calculate derived metrics
        self._calculate_maintainability_index(metrics)
        self._calculate_readability_score(metrics, code_type)
        self._calculate_technical_debt_ratio(metrics)

        # Cache and return
        self.analysis_cache[cache_key] = metrics
        return metrics

    def _detect_code_type(self, code: str) -> str:
        """Auto-detect whether code is DSL (Python) or JSON."""
        code = code.strip()

        # Try parsing as JSON first
        try:
            json.loads(code)
            return "json"
        except json.JSONDecodeError:
            pass

        # Try parsing as Python AST
        try:
            ast.parse(code)
            return "dsl"
        except SyntaxError:
            pass

        # Fallback heuristics
        if code.startswith("{") or code.startswith("["):
            return "json"
        else:
            return "dsl"

    def _is_comment_line(self, line: str, code_type: str) -> bool:
        """Check if a line is a comment."""
        line = line.strip()
        if code_type == "dsl":
            return line.startswith("#")
        elif code_type == "json":
            return line.startswith("//") or (
                line.startswith("/*") and line.endswith("*/")
            )
        return False

    def _analyze_dsl_complexity(self, code: str, metrics: ComplexityMetrics) -> None:
        """Analyze DSL (Python) specific complexity metrics."""
        try:
            tree = ast.parse(code)

            # Cyclomatic complexity
            metrics.cyclomatic_complexity = self._calculate_cyclomatic_complexity(tree)

            # Cognitive complexity
            metrics.cognitive_complexity = self._calculate_cognitive_complexity(tree)

            # Nesting depth
            metrics.nesting_depth = self._calculate_nesting_depth(tree)

            # DSL-specific metrics
            metrics.function_call_count = len(
                [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
            )
            metrics.method_chain_length = self._calculate_method_chain_length(tree)
            metrics.variable_usage_count = len(
                [node for node in ast.walk(tree) if isinstance(node, ast.Name)]
            )

            # Identifier clarity
            metrics.identifier_clarity_score = self._calculate_identifier_clarity(tree)

        except SyntaxError:
            # Handle syntax errors gracefully
            metrics.cyclomatic_complexity = float("inf")
            metrics.cognitive_complexity = float("inf")

    def _analyze_json_complexity(self, code: str, metrics: ComplexityMetrics) -> None:
        """Analyze JSON specific complexity metrics."""
        try:
            data = json.loads(code)

            # JSON-specific metrics
            metrics.json_depth = self._calculate_json_depth(data)
            metrics.json_key_count = self._count_json_keys(data)
            metrics.json_array_count = self._count_json_arrays(data)

            # Structural complexity (adapted for JSON)
            metrics.structural_complexity = self._calculate_json_structural_complexity(
                data
            )
            metrics.nesting_depth = metrics.json_depth

            # Cognitive complexity for JSON (based on structure)
            metrics.cognitive_complexity = self._calculate_json_cognitive_complexity(
                data
            )

        except json.JSONDecodeError:
            # Handle JSON errors gracefully
            metrics.json_depth = float("inf")
            metrics.cognitive_complexity = float("inf")

    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity of Python AST."""
        complexity = 1  # Base complexity

        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.If, ast.While, ast.For, ast.AsyncFor, ast.With, ast.AsyncWith),
            ):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, (ast.ExceptHandler,)):
                complexity += 1
            elif isinstance(node, ast.comprehension):
                complexity += 1

        return complexity

    def _calculate_cognitive_complexity(self, tree: ast.AST) -> int:
        """Calculate cognitive complexity of Python AST."""
        complexity = 0
        nesting_level = 0

        def visit_node(node, level):
            nonlocal complexity

            if isinstance(node, (ast.If, ast.While, ast.For)):
                complexity += 1 + level
                level += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            elif isinstance(node, (ast.Try, ast.ExceptHandler)):
                complexity += 1 + level

            for child in ast.iter_child_nodes(node):
                visit_node(child, level)

        visit_node(tree, 0)
        return complexity

    def _calculate_nesting_depth(self, tree: ast.AST) -> int:
        """Calculate maximum nesting depth of Python AST."""

        def get_depth(node, current_depth=0):
            max_depth = current_depth

            if isinstance(
                node,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.With,
                    ast.Try,
                    ast.FunctionDef,
                    ast.ClassDef,
                ),
            ):
                current_depth += 1

            for child in ast.iter_child_nodes(node):
                child_depth = get_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)

            return max_depth

        return get_depth(tree)

    def _calculate_method_chain_length(self, tree: ast.AST) -> int:
        """Calculate maximum method chain length in Python AST."""
        max_chain_length = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                chain_length = 1
                current = node.value

                while isinstance(current, ast.Attribute):
                    chain_length += 1
                    current = current.value

                max_chain_length = max(max_chain_length, chain_length)

        return max_chain_length

    def _calculate_identifier_clarity(self, tree: ast.AST) -> float:
        """Calculate identifier clarity score based on naming conventions."""
        identifiers = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.append(node.id)
            elif isinstance(node, ast.FunctionDef):
                identifiers.append(node.name)
            elif isinstance(node, ast.ClassDef):
                identifiers.append(node.name)

        if not identifiers:
            return 5.0

        clarity_score = 0.0
        for identifier in identifiers:
            # Score based on length and descriptiveness
            if len(identifier) >= 3:
                clarity_score += 1.0
            if "_" in identifier or identifier.islower():  # Snake case or lowercase
                clarity_score += 0.5
            if not identifier.startswith("_"):  # Not private
                clarity_score += 0.5
            if len(identifier) <= 20:  # Not too long
                clarity_score += 0.5

        return min(5.0, (clarity_score / len(identifiers)) * 2)

    def _calculate_json_depth(self, obj: Any, depth: int = 0) -> int:
        """Calculate maximum nesting depth of JSON object."""
        if isinstance(obj, dict):
            if not obj:
                return depth
            return max(self._calculate_json_depth(v, depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return depth
            return max(self._calculate_json_depth(item, depth + 1) for item in obj)
        else:
            return depth

    def _count_json_keys(self, obj: Any) -> int:
        """Count total number of keys in JSON object."""
        if isinstance(obj, dict):
            return len(obj) + sum(self._count_json_keys(v) for v in obj.values())
        elif isinstance(obj, list):
            return sum(self._count_json_keys(item) for item in obj)
        else:
            return 0

    def _count_json_arrays(self, obj: Any) -> int:
        """Count number of arrays in JSON object."""
        count = 0
        if isinstance(obj, dict):
            count += sum(self._count_json_arrays(v) for v in obj.values())
        elif isinstance(obj, list):
            count = 1 + sum(self._count_json_arrays(item) for item in obj)
        return count

    def _calculate_json_structural_complexity(self, obj: Any, depth: int = 0) -> int:
        """Calculate structural complexity of JSON object."""
        complexity = 0

        if isinstance(obj, dict):
            complexity += len(obj) * (depth + 1)
            for value in obj.values():
                complexity += self._calculate_json_structural_complexity(
                    value, depth + 1
                )
        elif isinstance(obj, list):
            complexity += len(obj) * (depth + 1)
            for item in obj:
                complexity += self._calculate_json_structural_complexity(
                    item, depth + 1
                )

        return complexity

    def _calculate_json_cognitive_complexity(self, obj: Any, depth: int = 0) -> int:
        """Calculate cognitive complexity for JSON structures."""
        complexity = 0

        if isinstance(obj, dict):
            # Each nested object adds cognitive load
            complexity += depth
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    complexity += self._calculate_json_cognitive_complexity(
                        value, depth + 1
                    )
        elif isinstance(obj, list):
            # Arrays add complexity, especially nested ones
            complexity += depth
            for item in obj:
                if isinstance(item, (dict, list)):
                    complexity += self._calculate_json_cognitive_complexity(
                        item, depth + 1
                    )

        return complexity

    def _calculate_maintainability_index(self, metrics: ComplexityMetrics) -> None:
        """Calculate maintainability index based on various metrics."""
        # Simplified maintainability index calculation
        # Based on Halstead volume, cyclomatic complexity, and lines of code

        if metrics.logical_lines == 0:
            metrics.maintainability_index = 100.0
            return

        # Normalize cyclomatic complexity
        cc_factor = max(1, metrics.cyclomatic_complexity)

        # Calculate maintainability index (0-100 scale)
        mi = (
            171
            - 5.2 * (cc_factor**0.23)
            - 0.23 * cc_factor
            - 16.2 * (metrics.logical_lines**0.5)
        )

        # Adjust for comment ratio
        comment_ratio = metrics.comment_lines / max(1, metrics.logical_lines)
        mi += comment_ratio * 10

        # Adjust for average line length (penalize very long lines)
        if metrics.average_line_length > 80:
            mi -= (metrics.average_line_length - 80) * 0.1

        metrics.maintainability_index = max(0.0, min(100.0, mi))

    def _calculate_readability_score(
        self, metrics: ComplexityMetrics, code_type: str
    ) -> None:
        """Calculate readability score based on various factors."""
        score = 5.0  # Start with perfect score

        # Penalize high nesting depth
        if metrics.nesting_depth > 3:
            score -= (metrics.nesting_depth - 3) * 0.5

        # Penalize long lines
        if metrics.average_line_length > 80:
            score -= (metrics.average_line_length - 80) / 40

        # Penalize high cognitive complexity
        if metrics.cognitive_complexity > 10:
            score -= (metrics.cognitive_complexity - 10) * 0.1

        # Reward comments
        if metrics.logical_lines > 0:
            comment_ratio = metrics.comment_lines / metrics.logical_lines
            score += comment_ratio * 1.0

        # Code type specific adjustments
        if code_type == "dsl" and metrics.identifier_clarity_score:
            score = (score + metrics.identifier_clarity_score) / 2

        metrics.readability_score = max(0.0, min(5.0, score))

    def _calculate_technical_debt_ratio(self, metrics: ComplexityMetrics) -> None:
        """Calculate technical debt ratio based on complexity metrics."""
        # Technical debt increases with complexity and decreases with maintainability

        debt_factors = []

        # High cyclomatic complexity increases debt
        if metrics.cyclomatic_complexity > 10:
            debt_factors.append((metrics.cyclomatic_complexity - 10) * 0.05)

        # High cognitive complexity increases debt
        if metrics.cognitive_complexity > 15:
            debt_factors.append((metrics.cognitive_complexity - 15) * 0.03)

        # Deep nesting increases debt
        if metrics.nesting_depth > 4:
            debt_factors.append((metrics.nesting_depth - 4) * 0.1)

        # Low maintainability increases debt
        if metrics.maintainability_index < 70:
            debt_factors.append((70 - metrics.maintainability_index) * 0.01)

        # Calculate total debt ratio
        total_debt = sum(debt_factors)
        metrics.technical_debt_ratio = min(1.0, total_debt)

    def compare_complexity(self, dsl_code: str, json_code: str) -> Dict[str, Any]:
        """Compare complexity between DSL and JSON approaches.

        Args:
            dsl_code: DSL source code
            json_code: JSON configuration

        Returns:
            Dictionary with comparative complexity analysis
        """
        dsl_metrics = self.analyze_code(dsl_code, "dsl")
        json_metrics = self.analyze_code(json_code, "json")

        return {
            "dsl_metrics": dsl_metrics,
            "json_metrics": json_metrics,
            "comparison": {
                "maintainability_advantage_dsl": dsl_metrics.maintainability_index
                - json_metrics.maintainability_index,
                "readability_advantage_dsl": dsl_metrics.readability_score
                - json_metrics.readability_score,
                "complexity_advantage_dsl": json_metrics.cognitive_complexity
                - dsl_metrics.cognitive_complexity,
                "technical_debt_advantage_dsl": json_metrics.technical_debt_ratio
                - dsl_metrics.technical_debt_ratio,
                "lines_of_code_ratio": dsl_metrics.logical_lines
                / max(1, json_metrics.logical_lines),
                "overall_complexity_score_dsl": (
                    dsl_metrics.maintainability_index / 100
                    + dsl_metrics.readability_score / 5
                    + (1 - dsl_metrics.technical_debt_ratio)
                )
                / 3,
                "overall_complexity_score_json": (
                    json_metrics.maintainability_index / 100
                    + json_metrics.readability_score / 5
                    + (1 - json_metrics.technical_debt_ratio)
                )
                / 3,
            },
        }

    def generate_complexity_report(
        self, metrics: ComplexityMetrics, code_type: str
    ) -> Dict[str, Any]:
        """Generate a comprehensive complexity report.

        Args:
            metrics: ComplexityMetrics to report on
            code_type: "dsl" or "json"

        Returns:
            Dictionary with formatted complexity report
        """
        report = {
            "summary": {
                "code_type": code_type,
                "lines_of_code": metrics.lines_of_code,
                "logical_lines": metrics.logical_lines,
                "maintainability_index": round(metrics.maintainability_index, 2),
                "readability_score": round(metrics.readability_score, 2),
                "technical_debt_ratio": round(metrics.technical_debt_ratio, 3),
            },
            "complexity_metrics": {
                "cyclomatic_complexity": metrics.cyclomatic_complexity,
                "cognitive_complexity": metrics.cognitive_complexity,
                "nesting_depth": metrics.nesting_depth,
                "average_line_length": round(metrics.average_line_length, 1),
            },
            "quality_indicators": {
                "maintainability_level": self._get_maintainability_level(
                    metrics.maintainability_index
                ),
                "readability_level": self._get_readability_level(
                    metrics.readability_score
                ),
                "complexity_level": self._get_complexity_level(
                    metrics.cognitive_complexity
                ),
                "technical_debt_level": self._get_debt_level(
                    metrics.technical_debt_ratio
                ),
            },
        }

        # Add type-specific metrics
        if code_type == "dsl" and metrics.function_call_count is not None:
            report["dsl_specific"] = {
                "function_calls": metrics.function_call_count,
                "method_chain_length": metrics.method_chain_length,
                "variable_usage": metrics.variable_usage_count,
                "identifier_clarity": round(metrics.identifier_clarity_score, 2),
            }
        elif code_type == "json" and metrics.json_depth is not None:
            report["json_specific"] = {
                "nesting_depth": metrics.json_depth,
                "total_keys": metrics.json_key_count,
                "array_count": metrics.json_array_count,
            }

        return report

    def _get_maintainability_level(self, index: float) -> str:
        """Get maintainability level description."""
        if index >= 85:
            return "Excellent"
        elif index >= 70:
            return "Good"
        elif index >= 50:
            return "Moderate"
        elif index >= 25:
            return "Poor"
        else:
            return "Critical"

    def _get_readability_level(self, score: float) -> str:
        """Get readability level description."""
        if score >= 4.5:
            return "Excellent"
        elif score >= 3.5:
            return "Good"
        elif score >= 2.5:
            return "Moderate"
        elif score >= 1.5:
            return "Poor"
        else:
            return "Critical"

    def _get_complexity_level(self, complexity: int) -> str:
        """Get complexity level description."""
        if complexity <= 5:
            return "Low"
        elif complexity <= 10:
            return "Moderate"
        elif complexity <= 20:
            return "High"
        else:
            return "Very High"

    def _get_debt_level(self, ratio: float) -> str:
        """Get technical debt level description."""
        if ratio <= 0.1:
            return "Low"
        elif ratio <= 0.3:
            return "Moderate"
        elif ratio <= 0.6:
            return "High"
        else:
            return "Critical"

    def clear_cache(self) -> None:
        """Clear the analysis cache."""
        self.analysis_cache.clear()
