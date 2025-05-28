"""Core DSL vs JSON comparison framework for tinyDisplay validation.

This module provides the foundation for comparing DSL and JSON approaches
across widget composition, animation coordination, and developer experience metrics.
"""

import ast
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum


class ComparisonType(Enum):
    """Types of comparisons supported by the framework."""

    WIDGET_COMPOSITION = "widget_composition"
    ANIMATION_COORDINATION = "animation_coordination"
    DATA_BINDING = "data_binding"
    ERROR_HANDLING = "error_handling"


@dataclass
class ComparisonResult:
    """Result of a DSL vs JSON comparison."""

    comparison_type: ComparisonType
    dsl_code: str
    json_config: str
    dsl_metrics: Dict[str, Any]
    json_metrics: Dict[str, Any]
    performance_data: Dict[str, float]
    readability_scores: Dict[str, float]
    complexity_analysis: Dict[str, Any]
    success: bool = True
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class ComparisonFramework:
    """Framework for comparing DSL and JSON approaches systematically."""

    def __init__(self):
        """Initialize the comparison framework with predefined examples."""
        self.results: List[ComparisonResult] = []
        self._comparison_results: List[Dict[str, Any]] = []

        # Initialize predefined examples
        self._dsl_examples: Dict[ComparisonType, Dict[str, str]] = {}
        self._json_examples: Dict[ComparisonType, Dict[str, str]] = {}

        self._initialize_examples()

    def _initialize_examples(self) -> None:
        """Set up predefined DSL and JSON examples for comparison."""
        # Widget Composition Examples
        self._dsl_examples[ComparisonType.WIDGET_COMPOSITION] = {
            "simple_text_progress": """
# DSL Approach - Simple Text + Progress Bar
canvas = Canvas(width=128, height=64)
canvas.add(
    Text("CPU Usage").position(10, 10).z_order(1),
    ProgressBar(value=data.cpu_usage).position(10, 30).z_order(2)
)
""",
            "complex_dashboard": """
# DSL Approach - Complex Dashboard
dashboard = Canvas(width=256, height=128)
dashboard.add(
    Text("System Monitor").position(10, 5).font_size(14).z_order(1),
    ProgressBar(value=data.cpu_usage, label="CPU").position(10, 25).z_order(2),
    ProgressBar(value=data.memory_usage, label="RAM").position(10, 45).z_order(2),
    Text(f"Temp: {data.temperature}°C").position(10, 70).z_order(1),
    Image("status_icon.png").position(200, 10).z_order(3)
)
dashboard.animate.slide_in().sync('startup_sequence')
""",
        }

        self._json_examples[ComparisonType.WIDGET_COMPOSITION] = {
            "simple_text_progress": """
{
  "canvas": {
    "width": 128,
    "height": 64,
    "widgets": [
      {
        "type": "text",
        "content": "CPU Usage",
        "position": {"x": 10, "y": 10},
        "z_order": 1
      },
      {
        "type": "progress_bar",
        "value": "data.cpu_usage",
        "position": {"x": 10, "y": 30},
        "z_order": 2
      }
    ]
  }
}
""",
            "complex_dashboard": """
{
  "canvas": {
    "width": 256,
    "height": 128,
    "widgets": [
      {
        "type": "text",
        "content": "System Monitor",
        "position": {"x": 10, "y": 5},
        "font_size": 14,
        "z_order": 1
      },
      {
        "type": "progress_bar",
        "value": "data.cpu_usage",
        "label": "CPU",
        "position": {"x": 10, "y": 25},
        "z_order": 2
      },
      {
        "type": "progress_bar", 
        "value": "data.memory_usage",
        "label": "RAM",
        "position": {"x": 10, "y": 45},
        "z_order": 2
      },
      {
        "type": "text",
        "content": "Temp: ${data.temperature}°C",
        "position": {"x": 10, "y": 70},
        "z_order": 1
      },
      {
        "type": "image",
        "source": "status_icon.png",
        "position": {"x": 200, "y": 10},
        "z_order": 3
      }
    ],
    "animations": [
      {
        "type": "slide_in",
        "sync_group": "startup_sequence"
      }
    ]
  }
}
""",
        }

        # Animation Coordination Examples
        self._dsl_examples[ComparisonType.ANIMATION_COORDINATION] = {
            "sync_coordination": """
# DSL Approach - Sync Coordination
text1.animate.scroll().sync('group_a')
text2.animate.scroll().sync('group_a')
progress1.animate.fill().sync('group_a')
""",
            "sequential_coordination": """
# DSL Approach - Sequential Coordination
progress1.animate.fill().then(
    progress2.animate.fill()
).then(
    text1.animate.fade_in()
).wait_for('data_ready')
""",
            "barrier_coordination": """
# DSL Approach - Barrier Coordination
animation_group.barrier('all_ready').then(
    canvas.animate.fade_in()
)
""",
        }

        self._json_examples[ComparisonType.ANIMATION_COORDINATION] = {
            "sync_coordination": """
{
  "animations": [
    {
      "target": "text1",
      "type": "scroll",
      "sync_group": "group_a"
    },
    {
      "target": "text2", 
      "type": "scroll",
      "sync_group": "group_a"
    },
    {
      "target": "progress1",
      "type": "fill",
      "sync_group": "group_a"
    }
  ]
}
""",
            "sequential_coordination": """
{
  "animation_sequence": [
    {
      "target": "progress1",
      "type": "fill",
      "wait_for_completion": true
    },
    {
      "target": "progress2",
      "type": "fill", 
      "wait_for_completion": true
    },
    {
      "target": "text1",
      "type": "fade_in",
      "wait_for_event": "data_ready"
    }
  ]
}
""",
            "barrier_coordination": """
{
  "animation_barriers": [
    {
      "barrier_id": "all_ready",
      "wait_for": ["animation1", "animation2", "animation3"]
    }
  ],
  "animations": [
    {
      "target": "canvas",
      "type": "fade_in",
      "wait_for_barrier": "all_ready"
    }
  ]
}
""",
        }

        # Data binding examples
        self._dsl_examples[ComparisonType.DATA_BINDING] = {
            "simple_binding": """
# DSL Approach - Simple Data Binding
text = Text(content=data.status).position(10, 10)
progress = ProgressBar(value=data.progress).position(10, 30)
canvas.add(text, progress)
""",
            "complex_binding": """
# DSL Approach - Complex Data Binding
dashboard = Canvas(256, 128)
dashboard.add(
    Text(content=f"Status: {data.status}").position(10, 5).bind('status_text'),
    ProgressBar(value=data.cpu_usage, max=100).position(10, 25).bind('cpu_bar'),
    Text(content=f"Memory: {data.memory_usage:.1f}%").position(10, 45).bind('memory_text'),
    Image(src=data.status_icon).position(200, 10).bind('status_icon')
)
""",
        }

        self._json_examples[ComparisonType.DATA_BINDING] = {
            "simple_binding": """{
  "canvas": {
    "widgets": [
      {
        "type": "text",
        "content": {"binding": "data.status"},
        "position": {"x": 10, "y": 10}
      },
      {
        "type": "progress_bar",
        "value": {"binding": "data.progress"},
        "position": {"x": 10, "y": 30}
      }
    ]
  }
}""",
            "complex_binding": """{
  "canvas": {
    "width": 256,
    "height": 128,
    "widgets": [
      {
        "type": "text",
        "content": {"binding": "data.status", "template": "Status: {value}"},
        "position": {"x": 10, "y": 5},
        "id": "status_text"
      },
      {
        "type": "progress_bar",
        "value": {"binding": "data.cpu_usage"},
        "max": 100,
        "position": {"x": 10, "y": 25},
        "id": "cpu_bar"
      },
      {
        "type": "text",
        "content": {"binding": "data.memory_usage", "template": "Memory: {value:.1f}%"},
        "position": {"x": 10, "y": 45},
        "id": "memory_text"
      },
      {
        "type": "image",
        "src": {"binding": "data.status_icon"},
        "position": {"x": 200, "y": 10},
        "id": "status_icon"
      }
    ]
  }
}""",
        }

        # Error handling examples
        self._dsl_examples[ComparisonType.ERROR_HANDLING] = {
            "validation_errors": """
# DSL Approach - Validation Errors
try:
    progress = ProgressBar(value=data.cpu_usage)
    if not 0 <= progress.value <= 1:
        progress.value = max(0, min(1, progress.value))
    canvas.add(progress)
except ValueError as e:
    canvas.add(Text(f"Error: {e}").color('red'))
""",
            "data_errors": """
# DSL Approach - Data Errors
text = Text(content=data.get('status', 'Unknown')).position(10, 10)
progress = ProgressBar(
    value=data.get('progress', 0),
    fallback_value=0
).position(10, 30)
canvas.add(text, progress)
""",
        }

        self._json_examples[ComparisonType.ERROR_HANDLING] = {
            "validation_errors": """{
  "canvas": {
    "widgets": [
      {
        "type": "progress_bar",
        "value": {"binding": "data.cpu_usage"},
        "validation": {
          "min": 0,
          "max": 1,
          "on_error": "clamp"
        },
        "error_fallback": {
          "type": "text",
          "content": "Error: Invalid value",
          "color": "red"
        }
      }
    ]
  }
}""",
            "data_errors": """{
  "canvas": {
    "widgets": [
      {
        "type": "text",
        "content": {"binding": "data.status", "fallback": "Unknown"},
        "position": {"x": 10, "y": 10}
      },
      {
        "type": "progress_bar",
        "value": {"binding": "data.progress", "fallback": 0},
        "position": {"x": 10, "y": 30}
      }
    ]
  }
}""",
        }

    def compare_approaches(
        self,
        comparison_type: ComparisonType,
        scenario: str,
        custom_dsl: Optional[str] = None,
        custom_json: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare DSL and JSON approaches for a specific scenario.

        Args:
            comparison_type: Type of comparison to perform
            scenario: Scenario name to compare
            custom_dsl: Custom DSL code (if scenario is "custom")
            custom_json: Custom JSON code (if scenario is "custom")

        Returns:
            Dictionary with comparison results
        """
        # Get code examples
        if scenario == "custom":
            if not custom_dsl or not custom_json:
                raise ValueError(
                    "Custom DSL and JSON code must be provided for custom scenarios"
                )
            dsl_code = custom_dsl
            json_code = custom_json
        else:
            if (
                comparison_type not in self._dsl_examples
                or scenario not in self._dsl_examples[comparison_type]
            ):
                raise ValueError(
                    f"Scenario '{scenario}' not found for comparison type '{comparison_type.value}'"
                )

            dsl_code = self._dsl_examples[comparison_type][scenario]
            json_code = self._json_examples[comparison_type][scenario]

        # Analyze both approaches
        dsl_analysis = self._analyze_code(dsl_code, "dsl", comparison_type)
        json_analysis = self._analyze_code(json_code, "json", comparison_type)

        # Compare approaches
        comparison = self._compare_analyses(dsl_analysis, json_analysis)

        # Determine winner
        winner = "dsl" if comparison["dsl_score"] > comparison["json_score"] else "json"

        # Create result dictionary
        result = {
            "dsl_analysis": dsl_analysis,
            "json_analysis": json_analysis,
            "comparison": {**comparison, "winner": winner},
            "scenario": scenario,
            "comparison_type": comparison_type.value,
        }

        # Store result for summary statistics
        self._comparison_results.append(result)

        return result

    def _analyze_code(
        self, code: str, code_type: str, comparison_type: ComparisonType
    ) -> Dict[str, Any]:
        """Analyze code metrics for DSL or JSON."""
        metrics = {
            "code": code,
            "code_type": code_type,
            "lines_of_code": len(code.split("\n")),
            "logical_lines": len([line for line in code.split("\n") if line.strip()]),
            "readability_score": self._calculate_readability_score(code, code_type),
            "complexity_score": self._calculate_complexity_score(code, code_type),
            "maintainability_score": self._calculate_maintainability_score(
                code, code_type
            ),
            "expressiveness_score": self._calculate_expressiveness_score(
                code, code_type, comparison_type
            ),
        }

        return metrics

    def _compare_analyses(
        self, dsl_analysis: Dict[str, Any], json_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two analyses and return a comparison result."""
        # Calculate scores
        dsl_score = (
            dsl_analysis["readability_score"] * 0.3
            + dsl_analysis["maintainability_score"] * 0.3
            + dsl_analysis["expressiveness_score"] * 0.4
        )

        json_score = (
            json_analysis["readability_score"] * 0.3
            + json_analysis["maintainability_score"] * 0.3
            + json_analysis["expressiveness_score"] * 0.4
        )

        comparison = {
            "dsl_score": dsl_score,
            "json_score": json_score,
            "readability_advantage_dsl": dsl_analysis["readability_score"]
            - json_analysis["readability_score"],
            "maintainability_advantage_dsl": dsl_analysis["maintainability_score"]
            - json_analysis["maintainability_score"],
            "expressiveness_advantage_dsl": dsl_analysis["expressiveness_score"]
            - json_analysis["expressiveness_score"],
            "lines_of_code_ratio": dsl_analysis["lines_of_code"]
            / max(json_analysis["lines_of_code"], 1),
            "performance_data": self._compare_performance(
                dsl_analysis["code"], json_analysis["code"]
            ),
            "readability_scores": {
                "dsl": dsl_analysis["readability_score"],
                "json": json_analysis["readability_score"],
            },
            "complexity_analysis": {
                "dsl": dsl_analysis["complexity_score"],
                "json": json_analysis["complexity_score"],
            },
            "success": True,
            "error_message": None,
        }

        return comparison

    def _calculate_readability_score(self, code: str, code_type: str) -> float:
        """Calculate readability score for a given code."""
        lines = [line.strip() for line in code.split("\n") if line.strip()]
        if not lines:
            return 5.0

        # Average line length (shorter is generally more readable)
        avg_line_length = sum(len(line) for line in lines) / len(lines)

        # Nesting complexity (fewer levels is more readable)
        max_indent = max(
            [len(line) - len(line.lstrip()) for line in code.split("\n")], default=0
        )

        # Base score starts at 5.0
        score = 5.0

        # Penalize long lines
        if avg_line_length > 80:
            score -= (avg_line_length - 80) / 40

        # Penalize deep nesting
        if max_indent > 8:
            score -= (max_indent - 8) / 16

        # DSL generally more readable than JSON
        if code_type == "dsl":
            score += 0.5

        return max(0.0, min(5.0, score))

    def _calculate_complexity_score(self, code: str, code_type: str) -> float:
        """Calculate complexity score for a given code."""
        if code_type == "dsl":
            try:
                tree = ast.parse(code)
                # Count control flow structures
                complexity = 1
                for node in ast.walk(tree):
                    if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                        complexity += 1
                    elif isinstance(node, ast.BoolOp):
                        complexity += len(node.values) - 1

                # Lower complexity is better, so invert the score
                return max(0.0, 5.0 - (complexity - 1) * 0.5)
            except:
                return 2.0  # Moderate score for unparseable code

        elif code_type == "json":
            try:
                data = json.loads(code)
                depth = self._calculate_json_depth(data)
                # Lower depth is better
                return max(0.0, 5.0 - depth * 0.5)
            except:
                return 2.0

        return 3.0

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

    def _calculate_maintainability_score(self, code: str, code_type: str) -> float:
        """Calculate maintainability score for a given code."""
        lines = [line.strip() for line in code.split("\n") if line.strip()]
        if not lines:
            return 5.0

        # Comment ratio (more comments = better maintainability)
        comment_lines = 0
        if code_type == "dsl":
            comment_lines = len([line for line in lines if line.startswith("#")])

        comment_ratio = comment_lines / len(lines) if lines else 0

        # Base score
        score = 3.0

        # Reward comments
        score += comment_ratio * 2.0

        # DSL generally more maintainable
        if code_type == "dsl":
            score += 1.0

        # Penalize very long files
        if len(lines) > 50:
            score -= (len(lines) - 50) / 100

        return max(0.0, min(5.0, score))

    def _calculate_expressiveness_score(
        self, code: str, code_type: str, comparison_type: ComparisonType
    ) -> float:
        """Calculate expressiveness score for a given code."""
        # DSL is generally more expressive for widget composition
        if code_type == "dsl":
            base_score = 4.0

            # Check for method chaining (more expressive)
            if ".position(" in code or ".add(" in code:
                base_score += 0.5

            # Check for data binding expressions
            if "data." in code:
                base_score += 0.3

            # Check for animation coordination
            if ".animate." in code or ".sync(" in code:
                base_score += 0.2

        else:  # JSON
            base_score = 3.0

            # JSON can be expressive with good structure
            try:
                data = json.loads(code)
                if isinstance(data, dict):
                    # Reward structured data
                    if "widgets" in data:
                        base_score += 0.5
                    if "binding" in str(data):
                        base_score += 0.3
            except:
                base_score -= 1.0

        return max(0.0, min(5.0, base_score))

    def _compare_performance(self, dsl_code: str, json_config: str) -> Dict[str, float]:
        """Compare parsing and processing performance."""
        # Simulate parsing performance
        start_time = time.perf_counter()
        try:
            ast.parse(dsl_code)
            dsl_parse_time = time.perf_counter() - start_time
        except:
            dsl_parse_time = float("inf")

        start_time = time.perf_counter()
        try:
            json.loads(json_config)
            json_parse_time = time.perf_counter() - start_time
        except:
            json_parse_time = float("inf")

        return {
            "dsl_parse_time_ms": dsl_parse_time * 1000,
            "json_parse_time_ms": json_parse_time * 1000,
            "parse_time_ratio": (
                dsl_parse_time / json_parse_time
                if json_parse_time > 0
                else float("inf")
            ),
        }

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics across all comparisons."""
        if not self._comparison_results:
            return {}

        successful_results = [
            r for r in self._comparison_results if r["comparison"]["success"]
        ]

        if not successful_results:
            return {"error": "No successful comparisons"}

        # Aggregate metrics
        total_comparisons = len(successful_results)
        dsl_wins = 0
        json_wins = 0

        for result in successful_results:
            dsl_score = result["comparison"]["readability_scores"]["dsl"]
            json_score = result["comparison"]["readability_scores"]["json"]

            if dsl_score > json_score:
                dsl_wins += 1
            else:
                json_wins += 1

        return {
            "total_comparisons": total_comparisons,
            "dsl_preference_rate": dsl_wins / total_comparisons,
            "json_preference_rate": json_wins / total_comparisons,
            "average_dsl_readability": sum(
                r["comparison"]["readability_scores"]["dsl"] for r in successful_results
            )
            / total_comparisons,
            "average_json_readability": sum(
                r["comparison"]["readability_scores"]["json"]
                for r in successful_results
            )
            / total_comparisons,
        }

    def clear_results(self) -> None:
        """Clear all comparison results."""
        self._comparison_results.clear()
