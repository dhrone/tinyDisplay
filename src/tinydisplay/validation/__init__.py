"""DSL Validation Framework for tinyDisplay.

This module provides comprehensive validation tools to compare DSL and JSON
approaches for widget composition, animation coordination, and developer experience.
"""

from .comparison_framework import ComparisonFramework, ComparisonResult, ComparisonType
from .metrics_collector import MetricsCollector, DeveloperExperienceMetrics, TaskType
from .complexity_analyzer import ComplexityAnalyzer, ComplexityMetrics
from .performance_tester import PerformanceTester, PerformanceMetrics
from .report_generator import ReportGenerator, ValidationReport, ReportFormat

__all__ = [
    "ComparisonFramework",
    "ComparisonResult",
    "ComparisonType",
    "MetricsCollector",
    "DeveloperExperienceMetrics",
    "TaskType",
    "ComplexityAnalyzer",
    "ComplexityMetrics",
    "PerformanceTester",
    "PerformanceMetrics",
    "ReportGenerator",
    "ValidationReport",
    "ReportFormat",
]

__version__ = "1.0.0"
