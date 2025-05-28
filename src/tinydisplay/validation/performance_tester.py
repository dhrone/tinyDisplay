"""Performance testing framework for DSL validation.

This module provides tools to measure and compare performance characteristics
of DSL and JSON approaches including parsing speed, memory usage, and execution time.
"""

import gc
import json
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import ast


class PerformanceTestType(Enum):
    """Types of performance tests."""

    PARSING_SPEED = "parsing_speed"
    MEMORY_USAGE = "memory_usage"
    EXECUTION_TIME = "execution_time"
    SCALABILITY = "scalability"


@dataclass
class PerformanceMetrics:
    """Performance metrics for code analysis."""

    # Parsing performance
    parse_time_ms: float
    parse_memory_kb: float
    parse_success: bool

    # Execution performance
    execution_time_ms: float
    execution_memory_kb: float
    execution_success: bool

    # Scalability metrics
    complexity_scaling_factor: float
    memory_scaling_factor: float

    # Comparative metrics
    performance_score: float
    efficiency_rating: str

    # Error information
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class PerformanceTester:
    """Performance testing framework for DSL vs JSON comparison."""

    def __init__(self):
        """Initialize the performance tester."""
        self.test_results: List[PerformanceMetrics] = []
        self.baseline_metrics: Optional[PerformanceMetrics] = None

    def measure_parsing_performance(
        self, code: str, code_type: str, iterations: int = 100
    ) -> PerformanceMetrics:
        """Measure parsing performance for code.

        Args:
            code: Source code to parse
            code_type: "dsl" or "json"
            iterations: Number of iterations for averaging

        Returns:
            PerformanceMetrics with parsing performance data
        """
        parse_times = []
        memory_usage = []
        parse_success = True
        error_message = None

        # Warm up
        for _ in range(5):
            try:
                if code_type == "dsl":
                    ast.parse(code)
                elif code_type == "json":
                    json.loads(code)
            except Exception:
                pass

        # Measure parsing performance
        for _ in range(iterations):
            # Start memory tracking
            tracemalloc.start()
            gc.collect()

            start_time = time.perf_counter()

            try:
                if code_type == "dsl":
                    ast.parse(code)
                elif code_type == "json":
                    json.loads(code)
                else:
                    raise ValueError(f"Unknown code type: {code_type}")

                end_time = time.perf_counter()
                parse_times.append((end_time - start_time) * 1000)  # Convert to ms

            except Exception as e:
                parse_success = False
                error_message = str(e)
                parse_times.append(float("inf"))

            # Measure memory usage
            current, peak = tracemalloc.get_traced_memory()
            memory_usage.append(peak / 1024)  # Convert to KB
            tracemalloc.stop()

        # Calculate averages
        avg_parse_time = sum(parse_times) / len(parse_times) if parse_times else 0
        avg_memory = sum(memory_usage) / len(memory_usage) if memory_usage else 0

        # Calculate performance score (lower is better for time and memory)
        performance_score = self._calculate_performance_score(
            avg_parse_time, avg_memory
        )
        efficiency_rating = self._get_efficiency_rating(performance_score)

        metrics = PerformanceMetrics(
            parse_time_ms=avg_parse_time,
            parse_memory_kb=avg_memory,
            parse_success=parse_success,
            execution_time_ms=0.0,  # Not measured in this test
            execution_memory_kb=0.0,
            execution_success=True,
            complexity_scaling_factor=1.0,
            memory_scaling_factor=1.0,
            performance_score=performance_score,
            efficiency_rating=efficiency_rating,
            error_message=error_message,
        )

        self.test_results.append(metrics)
        return metrics

    def measure_execution_performance(
        self,
        code: str,
        code_type: str,
        execution_func: Callable[[Any], Any],
        iterations: int = 50,
    ) -> PerformanceMetrics:
        """Measure execution performance for processed code.

        Args:
            code: Source code to process
            code_type: "dsl" or "json"
            execution_func: Function to execute the parsed code
            iterations: Number of iterations for averaging

        Returns:
            PerformanceMetrics with execution performance data
        """
        execution_times = []
        memory_usage = []
        execution_success = True
        error_message = None

        # Parse code first
        try:
            if code_type == "dsl":
                parsed_code = ast.parse(code)
            elif code_type == "json":
                parsed_code = json.loads(code)
            else:
                raise ValueError(f"Unknown code type: {code_type}")
        except Exception as e:
            return PerformanceMetrics(
                parse_time_ms=0.0,
                parse_memory_kb=0.0,
                parse_success=False,
                execution_time_ms=float("inf"),
                execution_memory_kb=0.0,
                execution_success=False,
                complexity_scaling_factor=1.0,
                memory_scaling_factor=1.0,
                performance_score=0.0,
                efficiency_rating="Failed",
                error_message=str(e),
            )

        # Measure execution performance
        for _ in range(iterations):
            tracemalloc.start()
            gc.collect()

            start_time = time.perf_counter()

            try:
                execution_func(parsed_code)
                end_time = time.perf_counter()
                execution_times.append((end_time - start_time) * 1000)  # Convert to ms

            except Exception as e:
                execution_success = False
                error_message = str(e)
                execution_times.append(float("inf"))

            # Measure memory usage
            current, peak = tracemalloc.get_traced_memory()
            memory_usage.append(peak / 1024)  # Convert to KB
            tracemalloc.stop()

        # Calculate averages
        avg_execution_time = (
            sum(execution_times) / len(execution_times) if execution_times else 0
        )
        avg_memory = sum(memory_usage) / len(memory_usage) if memory_usage else 0

        # Calculate performance score
        performance_score = self._calculate_performance_score(
            avg_execution_time, avg_memory
        )
        efficiency_rating = self._get_efficiency_rating(performance_score)

        metrics = PerformanceMetrics(
            parse_time_ms=0.0,  # Not measured in this test
            parse_memory_kb=0.0,
            parse_success=True,
            execution_time_ms=avg_execution_time,
            execution_memory_kb=avg_memory,
            execution_success=execution_success,
            complexity_scaling_factor=1.0,
            memory_scaling_factor=1.0,
            performance_score=performance_score,
            efficiency_rating=efficiency_rating,
            error_message=error_message,
        )

        self.test_results.append(metrics)
        return metrics

    def measure_scalability(
        self,
        base_code: str,
        code_type: str,
        scale_factors: List[int] = [1, 2, 5, 10, 20],
    ) -> Dict[str, Any]:
        """Measure scalability characteristics as code complexity increases.

        Args:
            base_code: Base code to scale up
            code_type: "dsl" or "json"
            scale_factors: List of scaling factors to test

        Returns:
            Dictionary with scalability analysis
        """
        scalability_results = {}

        for factor in scale_factors:
            scaled_code = self._scale_code(base_code, code_type, factor)

            # Measure parsing performance for scaled code
            metrics = self.measure_parsing_performance(
                scaled_code, code_type, iterations=20
            )

            scalability_results[f"scale_{factor}x"] = {
                "parse_time_ms": metrics.parse_time_ms,
                "memory_kb": metrics.parse_memory_kb,
                "success": metrics.parse_success,
                "code_size": len(scaled_code),
            }

        # Calculate scaling factors
        base_metrics = scalability_results["scale_1x"]
        max_metrics = scalability_results[f"scale_{max(scale_factors)}x"]

        if base_metrics["parse_time_ms"] > 0:
            time_scaling = max_metrics["parse_time_ms"] / base_metrics["parse_time_ms"]
        else:
            time_scaling = 1.0

        if base_metrics["memory_kb"] > 0:
            memory_scaling = max_metrics["memory_kb"] / base_metrics["memory_kb"]
        else:
            memory_scaling = 1.0

        return {
            "results": scalability_results,
            "analysis": {
                "time_scaling_factor": time_scaling,
                "memory_scaling_factor": memory_scaling,
                "scalability_rating": self._get_scalability_rating(
                    time_scaling, memory_scaling
                ),
                "linear_scaling": time_scaling
                <= max(scale_factors) * 1.2,  # Within 20% of linear
                "memory_efficient": memory_scaling
                <= max(scale_factors) * 1.5,  # Within 50% of linear
            },
        }

    def _scale_code(self, code: str, code_type: str, factor: int) -> str:
        """Scale code by the given factor."""
        if code_type == "json":
            try:
                data = json.loads(code)
                scaled_data = self._scale_json_data(data, factor)
                return json.dumps(scaled_data, indent=2)
            except json.JSONDecodeError:
                # If JSON parsing fails, just repeat the string
                return code * factor

        elif code_type == "dsl":
            # For DSL, we can repeat certain patterns or add complexity
            lines = code.strip().split("\n")
            scaled_lines = []

            for line in lines:
                scaled_lines.append(line)
                # Add variations for scaling
                if "canvas.add(" in line or "Text(" in line or "ProgressBar(" in line:
                    for i in range(factor - 1):
                        # Create variations of the line
                        scaled_line = line.replace("10,", f"{10 + i * 20},")
                        scaled_line = scaled_line.replace("30,", f"{30 + i * 20},")
                        scaled_lines.append(scaled_line)

            return "\n".join(scaled_lines)

        return code * factor

    def _scale_json_data(self, data: Any, factor: int) -> Any:
        """Scale JSON data structure by the given factor."""
        if isinstance(data, dict):
            if "widgets" in data:
                # Scale widgets array
                original_widgets = data["widgets"]
                scaled_widgets = []

                for i in range(factor):
                    for widget in original_widgets:
                        scaled_widget = widget.copy()
                        if "position" in scaled_widget:
                            if "y" in scaled_widget["position"]:
                                scaled_widget["position"]["y"] += i * 25
                        scaled_widgets.append(scaled_widget)

                scaled_data = data.copy()
                scaled_data["widgets"] = scaled_widgets
                return scaled_data
            else:
                return {k: self._scale_json_data(v, factor) for k, v in data.items()}

        elif isinstance(data, list):
            scaled_list = []
            for i in range(factor):
                for item in data:
                    scaled_list.append(self._scale_json_data(item, 1))
            return scaled_list

        return data

    def _calculate_performance_score(self, time_ms: float, memory_kb: float) -> float:
        """Calculate overall performance score (higher is better)."""
        if time_ms == float("inf") or memory_kb == float("inf"):
            return 0.0

        # Normalize metrics (assuming reasonable baselines)
        time_score = max(0, 100 - time_ms)  # 100ms baseline
        memory_score = max(0, 100 - memory_kb / 10)  # 1MB baseline

        # Weighted average (time is more important than memory for parsing)
        return time_score * 0.7 + memory_score * 0.3

    def _get_efficiency_rating(self, score: float) -> str:
        """Get efficiency rating based on performance score."""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 50:
            return "Moderate"
        elif score >= 25:
            return "Poor"
        else:
            return "Critical"

    def _get_scalability_rating(
        self, time_scaling: float, memory_scaling: float
    ) -> str:
        """Get scalability rating based on scaling factors."""
        avg_scaling = (time_scaling + memory_scaling) / 2

        if avg_scaling <= 1.2:
            return "Excellent"
        elif avg_scaling <= 2.0:
            return "Good"
        elif avg_scaling <= 5.0:
            return "Moderate"
        elif avg_scaling <= 10.0:
            return "Poor"
        else:
            return "Critical"

    def compare_performance(
        self, dsl_code: str, json_code: str, iterations: int = 100
    ) -> Dict[str, Any]:
        """Compare performance between DSL and JSON approaches.

        Args:
            dsl_code: DSL source code
            json_code: JSON configuration
            iterations: Number of test iterations

        Returns:
            Dictionary with comparative performance analysis
        """
        # Measure DSL performance
        dsl_metrics = self.measure_parsing_performance(dsl_code, "dsl", iterations)

        # Measure JSON performance
        json_metrics = self.measure_parsing_performance(json_code, "json", iterations)

        # Calculate comparative metrics
        if json_metrics.parse_time_ms > 0:
            time_advantage_dsl = (
                json_metrics.parse_time_ms - dsl_metrics.parse_time_ms
            ) / json_metrics.parse_time_ms
        else:
            time_advantage_dsl = 0.0

        if json_metrics.parse_memory_kb > 0:
            memory_advantage_dsl = (
                json_metrics.parse_memory_kb - dsl_metrics.parse_memory_kb
            ) / json_metrics.parse_memory_kb
        else:
            memory_advantage_dsl = 0.0

        return {
            "dsl_metrics": dsl_metrics,
            "json_metrics": json_metrics,
            "comparison": {
                "parsing_time_advantage_dsl": time_advantage_dsl,
                "memory_usage_advantage_dsl": memory_advantage_dsl,
                "performance_score_advantage_dsl": dsl_metrics.performance_score
                - json_metrics.performance_score,
                "overall_performance_winner": (
                    "dsl"
                    if dsl_metrics.performance_score > json_metrics.performance_score
                    else "json"
                ),
                "speed_ratio_dsl_to_json": json_metrics.parse_time_ms
                / max(dsl_metrics.parse_time_ms, 0.001),
                "memory_ratio_dsl_to_json": json_metrics.parse_memory_kb
                / max(dsl_metrics.parse_memory_kb, 0.001),
            },
        }

    def run_comprehensive_performance_test(
        self, dsl_code: str, json_code: str
    ) -> Dict[str, Any]:
        """Run comprehensive performance testing suite.

        Args:
            dsl_code: DSL source code
            json_code: JSON configuration

        Returns:
            Dictionary with comprehensive performance analysis
        """
        results = {}

        # Basic parsing performance
        results["parsing_performance"] = self.compare_performance(dsl_code, json_code)

        # Scalability testing
        results["dsl_scalability"] = self.measure_scalability(dsl_code, "dsl")
        results["json_scalability"] = self.measure_scalability(json_code, "json")

        # Performance summary
        dsl_score = results["parsing_performance"]["dsl_metrics"].performance_score
        json_score = results["parsing_performance"]["json_metrics"].performance_score

        dsl_scalability = results["dsl_scalability"]["analysis"]["scalability_rating"]
        json_scalability = results["json_scalability"]["analysis"]["scalability_rating"]

        results["summary"] = {
            "overall_performance_winner": "dsl" if dsl_score > json_score else "json",
            "performance_advantage": abs(dsl_score - json_score),
            "scalability_winner": self._compare_scalability_ratings(
                dsl_scalability, json_scalability
            ),
            "recommendation": self._generate_performance_recommendation(
                dsl_score, json_score, dsl_scalability, json_scalability
            ),
        }

        return results

    def _compare_scalability_ratings(self, dsl_rating: str, json_rating: str) -> str:
        """Compare scalability ratings and determine winner."""
        rating_scores = {
            "Excellent": 5,
            "Good": 4,
            "Moderate": 3,
            "Poor": 2,
            "Critical": 1,
        }

        dsl_score = rating_scores.get(dsl_rating, 0)
        json_score = rating_scores.get(json_rating, 0)

        if dsl_score > json_score:
            return "dsl"
        elif json_score > dsl_score:
            return "json"
        else:
            return "tie"

    def _generate_performance_recommendation(
        self,
        dsl_score: float,
        json_score: float,
        dsl_scalability: str,
        json_scalability: str,
    ) -> str:
        """Generate performance-based recommendation."""
        if dsl_score > json_score + 10:
            return "DSL shows significant performance advantage"
        elif json_score > dsl_score + 10:
            return "JSON shows significant performance advantage"
        elif dsl_scalability in ["Excellent", "Good"] and json_scalability in [
            "Poor",
            "Critical",
        ]:
            return "DSL recommended for scalable applications"
        elif json_scalability in ["Excellent", "Good"] and dsl_scalability in [
            "Poor",
            "Critical",
        ]:
            return "JSON recommended for scalable applications"
        else:
            return "Performance characteristics are comparable"

    def set_baseline_metrics(self, metrics: PerformanceMetrics) -> None:
        """Set baseline metrics for comparative analysis."""
        self.baseline_metrics = metrics

    def clear_results(self) -> None:
        """Clear all test results."""
        self.test_results.clear()
        self.baseline_metrics = None
