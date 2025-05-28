"""Developer experience metrics collection for DSL validation.

This module provides tools to collect and analyze developer experience metrics
comparing DSL and JSON approaches across various usability factors.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class TaskType(Enum):
    """Types of development tasks for metrics collection."""

    SIMPLE_WIDGET_CREATION = "simple_widget_creation"
    COMPLEX_LAYOUT = "complex_layout"
    ANIMATION_SETUP = "animation_setup"
    DATA_BINDING = "data_binding"
    ERROR_DEBUGGING = "error_debugging"
    MODIFICATION_TASK = "modification_task"


@dataclass
class TaskMetrics:
    """Metrics for a single development task."""

    task_type: TaskType
    approach: str  # "dsl" or "json"
    completion_time_seconds: float
    lines_of_code: int
    errors_encountered: int
    successful_completion: bool
    difficulty_rating: float  # 1-5 scale
    confidence_rating: float  # 1-5 scale
    timestamp: float = field(default_factory=time.time)


@dataclass
class DeveloperExperienceMetrics:
    """Comprehensive developer experience metrics."""

    # Learning curve metrics
    time_to_productivity_hours: float
    initial_task_completion_rate: float
    learning_curve_slope: float

    # Productivity metrics
    average_task_completion_time: float
    lines_of_code_per_hour: float
    successful_task_rate: float

    # Error and debugging metrics
    average_errors_per_task: float
    error_resolution_time: float
    debugging_difficulty_rating: float

    # Subjective experience metrics
    overall_satisfaction_rating: float
    ease_of_use_rating: float
    confidence_rating: float
    preference_score: float

    # Comparative metrics
    productivity_improvement_vs_baseline: float
    error_rate_improvement_vs_baseline: float
    learning_time_improvement_vs_baseline: float


class MetricsCollector:
    """Collector for developer experience metrics across DSL and JSON approaches."""

    def __init__(self):
        """Initialize the metrics collector."""
        self.task_metrics: List[TaskMetrics] = []
        self.developer_sessions: Dict[str, List[TaskMetrics]] = {}
        self.baseline_metrics: Optional[DeveloperExperienceMetrics] = None

    def record_task_completion(
        self,
        task_type: TaskType,
        approach: str,
        completion_time_seconds: float,
        lines_of_code: int,
        errors_encountered: int,
        successful_completion: bool,
        difficulty_rating: float,
        confidence_rating: float,
        developer_id: Optional[str] = None,
    ) -> None:
        """Record completion metrics for a development task.

        Args:
            task_type: Type of development task
            approach: "dsl" or "json"
            completion_time_seconds: Time taken to complete task
            lines_of_code: Number of lines written
            errors_encountered: Number of errors during task
            successful_completion: Whether task was completed successfully
            difficulty_rating: Subjective difficulty rating (1-5)
            confidence_rating: Developer confidence rating (1-5)
            developer_id: Optional identifier for developer session tracking
        """
        metrics = TaskMetrics(
            task_type=task_type,
            approach=approach,
            completion_time_seconds=completion_time_seconds,
            lines_of_code=lines_of_code,
            errors_encountered=errors_encountered,
            successful_completion=successful_completion,
            difficulty_rating=difficulty_rating,
            confidence_rating=confidence_rating,
        )

        self.task_metrics.append(metrics)

        if developer_id:
            if developer_id not in self.developer_sessions:
                self.developer_sessions[developer_id] = []
            self.developer_sessions[developer_id].append(metrics)

    def simulate_developer_session(
        self, approach: str, developer_experience_level: str = "intermediate"
    ) -> List[TaskMetrics]:
        """Simulate a developer session with various tasks.

        Args:
            approach: "dsl" or "json"
            developer_experience_level: "beginner", "intermediate", or "expert"

        Returns:
            List of simulated task metrics
        """
        # Define base metrics based on experience level and approach
        experience_multipliers = {
            "beginner": {"time": 2.0, "errors": 2.5, "difficulty": 1.5},
            "intermediate": {"time": 1.0, "errors": 1.0, "difficulty": 1.0},
            "expert": {"time": 0.7, "errors": 0.5, "difficulty": 0.8},
        }

        # DSL generally performs better than JSON
        approach_modifiers = {
            "dsl": {"time": 0.8, "errors": 0.6, "difficulty": 0.7, "confidence": 1.3},
            "json": {"time": 1.0, "errors": 1.0, "difficulty": 1.0, "confidence": 1.0},
        }

        multiplier = experience_multipliers[developer_experience_level]
        modifier = approach_modifiers[approach]

        # Simulate various tasks
        simulated_tasks = [
            (
                TaskType.SIMPLE_WIDGET_CREATION,
                300,
                8,
                1,
            ),  # base: 5min, 8 lines, 1 error
            (TaskType.COMPLEX_LAYOUT, 1200, 25, 3),  # base: 20min, 25 lines, 3 errors
            (TaskType.ANIMATION_SETUP, 900, 15, 2),  # base: 15min, 15 lines, 2 errors
            (TaskType.DATA_BINDING, 600, 12, 2),  # base: 10min, 12 lines, 2 errors
            (TaskType.ERROR_DEBUGGING, 1800, 5, 1),  # base: 30min, 5 lines, 1 error
            (TaskType.MODIFICATION_TASK, 450, 10, 1),  # base: 7.5min, 10 lines, 1 error
        ]

        session_metrics = []

        for task_type, base_time, base_lines, base_errors in simulated_tasks:
            # Apply experience and approach modifiers
            actual_time = base_time * multiplier["time"] * modifier["time"]
            actual_errors = max(
                0, int(base_errors * multiplier["errors"] * modifier["errors"])
            )
            actual_lines = int(
                base_lines * (1.2 if approach == "json" else 1.0)
            )  # JSON tends to be more verbose

            # Calculate subjective ratings
            difficulty = min(
                5.0, max(1.0, 3.0 * multiplier["difficulty"] * modifier["difficulty"])
            )
            confidence = min(
                5.0, max(1.0, 3.5 * modifier["confidence"] / multiplier["difficulty"])
            )

            # Success rate depends on errors and experience
            success_probability = max(
                0.1, 1.0 - (actual_errors * 0.2) - (difficulty - 3.0) * 0.1
            )
            successful = success_probability > 0.7

            self.record_task_completion(
                task_type=task_type,
                approach=approach,
                completion_time_seconds=actual_time,
                lines_of_code=actual_lines,
                errors_encountered=actual_errors,
                successful_completion=successful,
                difficulty_rating=difficulty,
                confidence_rating=confidence,
                developer_id=f"sim_{approach}_{developer_experience_level}",
            )

            session_metrics.append(self.task_metrics[-1])

        return session_metrics

    def calculate_learning_curve(
        self, approach: str, developer_id: str
    ) -> Dict[str, float]:
        """Calculate learning curve metrics for a specific developer and approach.

        Args:
            approach: "dsl" or "json"
            developer_id: Developer identifier

        Returns:
            Dictionary with learning curve metrics
        """
        if developer_id not in self.developer_sessions:
            return {}

        session_tasks = [
            task
            for task in self.developer_sessions[developer_id]
            if task.approach == approach
        ]

        if len(session_tasks) < 3:
            return {"error": "Insufficient data for learning curve analysis"}

        # Sort by timestamp
        session_tasks.sort(key=lambda x: x.timestamp)

        # Calculate improvement over time
        initial_avg_time = (
            sum(task.completion_time_seconds for task in session_tasks[:2]) / 2
        )
        final_avg_time = (
            sum(task.completion_time_seconds for task in session_tasks[-2:]) / 2
        )

        initial_error_rate = (
            sum(task.errors_encountered for task in session_tasks[:2]) / 2
        )
        final_error_rate = (
            sum(task.errors_encountered for task in session_tasks[-2:]) / 2
        )

        initial_confidence = (
            sum(task.confidence_rating for task in session_tasks[:2]) / 2
        )
        final_confidence = (
            sum(task.confidence_rating for task in session_tasks[-2:]) / 2
        )

        return {
            "time_improvement_ratio": (
                initial_avg_time / final_avg_time if final_avg_time > 0 else 1.0
            ),
            "error_reduction_ratio": initial_error_rate / max(final_error_rate, 0.1),
            "confidence_improvement": final_confidence - initial_confidence,
            "learning_velocity": (final_confidence - initial_confidence)
            / len(session_tasks),
        }

    def generate_developer_experience_metrics(
        self, approach: str
    ) -> DeveloperExperienceMetrics:
        """Generate comprehensive developer experience metrics for an approach.

        Args:
            approach: "dsl" or "json"

        Returns:
            DeveloperExperienceMetrics object
        """
        approach_tasks = [
            task for task in self.task_metrics if task.approach == approach
        ]

        if not approach_tasks:
            raise ValueError(f"No task data available for approach: {approach}")

        # Calculate basic metrics
        total_tasks = len(approach_tasks)
        successful_tasks = sum(
            1 for task in approach_tasks if task.successful_completion
        )
        total_time = sum(task.completion_time_seconds for task in approach_tasks)
        total_lines = sum(task.lines_of_code for task in approach_tasks)
        total_errors = sum(task.errors_encountered for task in approach_tasks)

        # Learning curve analysis (simulate time to productivity)
        time_to_productivity = self._estimate_time_to_productivity(approach_tasks)

        # Calculate averages
        avg_completion_time = total_time / total_tasks
        avg_errors_per_task = total_errors / total_tasks
        success_rate = successful_tasks / total_tasks

        # Subjective metrics
        avg_difficulty = (
            sum(task.difficulty_rating for task in approach_tasks) / total_tasks
        )
        avg_confidence = (
            sum(task.confidence_rating for task in approach_tasks) / total_tasks
        )

        # Productivity metrics
        lines_per_hour = (total_lines / (total_time / 3600)) if total_time > 0 else 0

        # Calculate comparative metrics if baseline exists
        productivity_improvement = 0.0
        error_improvement = 0.0
        learning_improvement = 0.0

        if self.baseline_metrics:
            productivity_improvement = (
                lines_per_hour - self.baseline_metrics.lines_of_code_per_hour
            ) / self.baseline_metrics.lines_of_code_per_hour
            error_improvement = (
                self.baseline_metrics.average_errors_per_task - avg_errors_per_task
            ) / self.baseline_metrics.average_errors_per_task
            learning_improvement = (
                self.baseline_metrics.time_to_productivity_hours - time_to_productivity
            ) / self.baseline_metrics.time_to_productivity_hours

        return DeveloperExperienceMetrics(
            time_to_productivity_hours=time_to_productivity,
            initial_task_completion_rate=self._calculate_initial_completion_rate(
                approach_tasks
            ),
            learning_curve_slope=self._calculate_learning_slope(approach_tasks),
            average_task_completion_time=avg_completion_time,
            lines_of_code_per_hour=lines_per_hour,
            successful_task_rate=success_rate,
            average_errors_per_task=avg_errors_per_task,
            error_resolution_time=avg_completion_time
            * 0.3,  # Estimate 30% of time on debugging
            debugging_difficulty_rating=avg_difficulty,
            overall_satisfaction_rating=5.0 - avg_difficulty + avg_confidence - 3.0,
            ease_of_use_rating=5.0 - avg_difficulty,
            confidence_rating=avg_confidence,
            preference_score=avg_confidence * success_rate * (5.0 - avg_difficulty),
            productivity_improvement_vs_baseline=productivity_improvement,
            error_rate_improvement_vs_baseline=error_improvement,
            learning_time_improvement_vs_baseline=learning_improvement,
        )

    def _estimate_time_to_productivity(self, tasks: List[TaskMetrics]) -> float:
        """Estimate time to reach productivity based on task progression."""
        if len(tasks) < 3:
            return 2.0  # Default 2 hours

        # Sort by timestamp
        sorted_tasks = sorted(tasks, key=lambda x: x.timestamp)

        # Find when success rate stabilizes above 80%
        for i in range(2, len(sorted_tasks)):
            recent_tasks = sorted_tasks[max(0, i - 2) : i + 1]
            success_rate = sum(
                1 for task in recent_tasks if task.successful_completion
            ) / len(recent_tasks)

            if success_rate >= 0.8:
                # Estimate hours based on task index (assuming 30 min per task)
                return i * 0.5

        # If never reached 80%, estimate based on final performance
        return len(sorted_tasks) * 0.5

    def _calculate_initial_completion_rate(self, tasks: List[TaskMetrics]) -> float:
        """Calculate completion rate for first few tasks."""
        if not tasks:
            return 0.0

        sorted_tasks = sorted(tasks, key=lambda x: x.timestamp)
        initial_tasks = sorted_tasks[: min(3, len(sorted_tasks))]

        return sum(1 for task in initial_tasks if task.successful_completion) / len(
            initial_tasks
        )

    def _calculate_learning_slope(self, tasks: List[TaskMetrics]) -> float:
        """Calculate learning curve slope (improvement rate)."""
        if len(tasks) < 4:
            return 0.0

        sorted_tasks = sorted(tasks, key=lambda x: x.timestamp)

        # Compare first half vs second half performance
        mid_point = len(sorted_tasks) // 2
        first_half = sorted_tasks[:mid_point]
        second_half = sorted_tasks[mid_point:]

        first_half_score = sum(task.confidence_rating for task in first_half) / len(
            first_half
        )
        second_half_score = sum(task.confidence_rating for task in second_half) / len(
            second_half
        )

        return (
            second_half_score - first_half_score
        ) / mid_point  # Improvement per task

    def set_baseline_metrics(self, metrics: DeveloperExperienceMetrics) -> None:
        """Set baseline metrics for comparative analysis."""
        self.baseline_metrics = metrics

    def compare_approaches(self) -> Dict[str, Any]:
        """Compare DSL and JSON approaches across all collected metrics."""
        dsl_metrics = self.generate_developer_experience_metrics("dsl")
        json_metrics = self.generate_developer_experience_metrics("json")

        return {
            "dsl_metrics": dsl_metrics,
            "json_metrics": json_metrics,
            "comparison": {
                "productivity_advantage_dsl": (
                    dsl_metrics.lines_of_code_per_hour
                    - json_metrics.lines_of_code_per_hour
                )
                / json_metrics.lines_of_code_per_hour,
                "error_rate_advantage_dsl": (
                    json_metrics.average_errors_per_task
                    - dsl_metrics.average_errors_per_task
                )
                / json_metrics.average_errors_per_task,
                "learning_time_advantage_dsl": (
                    json_metrics.time_to_productivity_hours
                    - dsl_metrics.time_to_productivity_hours
                )
                / json_metrics.time_to_productivity_hours,
                "confidence_advantage_dsl": dsl_metrics.confidence_rating
                - json_metrics.confidence_rating,
                "preference_advantage_dsl": dsl_metrics.preference_score
                - json_metrics.preference_score,
                "overall_dsl_superiority_score": (
                    dsl_metrics.preference_score / json_metrics.preference_score
                    + dsl_metrics.successful_task_rate
                    / json_metrics.successful_task_rate
                    + json_metrics.average_errors_per_task
                    / max(dsl_metrics.average_errors_per_task, 0.1)
                )
                / 3,
            },
        }

    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        self.task_metrics.clear()
        self.developer_sessions.clear()
        self.baseline_metrics = None
