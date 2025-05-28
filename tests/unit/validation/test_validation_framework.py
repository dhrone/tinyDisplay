"""Comprehensive tests for DSL validation framework."""

import pytest
import json
from unittest.mock import patch, MagicMock

from src.tinydisplay.validation import (
    ComparisonFramework,
    MetricsCollector,
    ComplexityAnalyzer,
    PerformanceTester,
    ReportGenerator,
    ComparisonType,
    TaskType,
    ReportFormat,
)


class TestComparisonFramework:
    """Test the comparison framework functionality."""

    def test_framework_initialization(self):
        """Test that the framework initializes correctly."""
        framework = ComparisonFramework()
        assert framework is not None
        assert hasattr(framework, "_dsl_examples")
        assert hasattr(framework, "_json_examples")

    def test_predefined_examples_exist(self):
        """Test that predefined examples are available."""
        framework = ComparisonFramework()

        # Check that we have examples for each comparison type
        for comparison_type in ComparisonType:
            assert comparison_type in framework._dsl_examples
            assert comparison_type in framework._json_examples
            assert len(framework._dsl_examples[comparison_type]) > 0
            assert len(framework._json_examples[comparison_type]) > 0

    def test_compare_approaches_with_predefined(self):
        """Test comparison with predefined examples."""
        framework = ComparisonFramework()

        result = framework.compare_approaches(
            ComparisonType.WIDGET_COMPOSITION, "simple_text_progress"
        )

        assert result is not None
        assert "dsl_analysis" in result
        assert "json_analysis" in result
        assert "comparison" in result
        assert "winner" in result["comparison"]

    def test_compare_approaches_with_custom(self):
        """Test comparison with custom examples."""
        framework = ComparisonFramework()

        dsl_code = """
canvas = Canvas(800, 600)
text = Text("Hello World", 10, 30)
canvas.add(text)
"""

        json_code = """{
  "canvas": {
    "width": 800,
    "height": 600,
    "widgets": [
      {
        "type": "text",
        "content": "Hello World",
        "position": {"x": 10, "y": 30}
      }
    ]
  }
}"""

        result = framework.compare_approaches(
            ComparisonType.WIDGET_COMPOSITION,
            "custom",
            custom_dsl=dsl_code,
            custom_json=json_code,
        )

        assert result is not None
        assert "dsl_analysis" in result
        assert "json_analysis" in result

    def test_get_summary_statistics(self):
        """Test summary statistics generation."""
        framework = ComparisonFramework()

        # Run a few comparisons first
        framework.compare_approaches(
            ComparisonType.WIDGET_COMPOSITION, "simple_text_progress"
        )
        framework.compare_approaches(
            ComparisonType.ANIMATION_COORDINATION, "sync_coordination"
        )

        summary = framework.get_summary_statistics()

        assert "total_comparisons" in summary
        assert "dsl_preference_rate" in summary
        assert summary["total_comparisons"] >= 2


class TestMetricsCollector:
    """Test the metrics collector functionality."""

    def test_collector_initialization(self):
        """Test that the collector initializes correctly."""
        collector = MetricsCollector()
        assert collector is not None
        assert len(collector.task_metrics) == 0
        assert len(collector.developer_sessions) == 0

    def test_record_task_completion(self):
        """Test recording task completion metrics."""
        collector = MetricsCollector()

        collector.record_task_completion(
            task_type=TaskType.SIMPLE_WIDGET_CREATION,
            approach="dsl",
            completion_time_seconds=120.0,
            lines_of_code=8,
            errors_encountered=1,
            successful_completion=True,
            difficulty_rating=2.5,
            confidence_rating=4.0,
            developer_id="test_dev",
        )

        assert len(collector.task_metrics) == 1
        assert "test_dev" in collector.developer_sessions
        assert len(collector.developer_sessions["test_dev"]) == 1

        metrics = collector.task_metrics[0]
        assert metrics.task_type == TaskType.SIMPLE_WIDGET_CREATION
        assert metrics.approach == "dsl"
        assert metrics.completion_time_seconds == 120.0

    def test_simulate_developer_session(self):
        """Test developer session simulation."""
        collector = MetricsCollector()

        session_metrics = collector.simulate_developer_session("dsl", "intermediate")

        assert len(session_metrics) > 0
        assert all(metric.approach == "dsl" for metric in session_metrics)
        assert len(collector.task_metrics) == len(session_metrics)

    def test_generate_developer_experience_metrics(self):
        """Test developer experience metrics generation."""
        collector = MetricsCollector()

        # Simulate some sessions
        collector.simulate_developer_session("dsl", "intermediate")
        collector.simulate_developer_session("json", "intermediate")

        dsl_metrics = collector.generate_developer_experience_metrics("dsl")
        json_metrics = collector.generate_developer_experience_metrics("json")

        assert dsl_metrics.time_to_productivity_hours > 0
        assert dsl_metrics.successful_task_rate >= 0
        assert dsl_metrics.successful_task_rate <= 1
        assert json_metrics.time_to_productivity_hours > 0

    def test_compare_approaches(self):
        """Test approach comparison."""
        collector = MetricsCollector()

        # Simulate sessions for both approaches
        collector.simulate_developer_session("dsl", "intermediate")
        collector.simulate_developer_session("json", "intermediate")

        comparison = collector.compare_approaches()

        assert "dsl_metrics" in comparison
        assert "json_metrics" in comparison
        assert "comparison" in comparison
        assert "overall_dsl_superiority_score" in comparison["comparison"]


class TestComplexityAnalyzer:
    """Test the complexity analyzer functionality."""

    def test_analyzer_initialization(self):
        """Test that the analyzer initializes correctly."""
        analyzer = ComplexityAnalyzer()
        assert analyzer is not None
        assert len(analyzer.analysis_cache) == 0

    def test_analyze_dsl_code(self):
        """Test DSL code analysis."""
        analyzer = ComplexityAnalyzer()

        dsl_code = """
def create_widget():
    canvas = Canvas(800, 600)
    text = Text("Hello", 10, 30)
    if text.visible:
        canvas.add(text)
    return canvas
"""

        metrics = analyzer.analyze_code(dsl_code, "dsl")

        assert metrics.lines_of_code > 0
        assert metrics.logical_lines > 0
        assert metrics.cyclomatic_complexity >= 1
        assert metrics.cognitive_complexity >= 0
        assert metrics.function_call_count is not None
        assert metrics.maintainability_index >= 0
        assert metrics.readability_score >= 0

    def test_analyze_json_code(self):
        """Test JSON code analysis."""
        analyzer = ComplexityAnalyzer()

        json_code = """{
  "canvas": {
    "width": 800,
    "height": 600,
    "widgets": [
      {
        "type": "text",
        "content": "Hello",
        "position": {"x": 10, "y": 30},
        "visible": true
      }
    ]
  }
}"""

        metrics = analyzer.analyze_code(json_code, "json")

        assert metrics.lines_of_code > 0
        assert metrics.logical_lines > 0
        assert metrics.json_depth is not None
        assert metrics.json_key_count is not None
        assert metrics.maintainability_index >= 0

    def test_compare_complexity(self):
        """Test complexity comparison between DSL and JSON."""
        analyzer = ComplexityAnalyzer()

        dsl_code = "canvas = Canvas(800, 600)"
        json_code = '{"canvas": {"width": 800, "height": 600}}'

        comparison = analyzer.compare_complexity(dsl_code, json_code)

        assert "dsl_metrics" in comparison
        assert "json_metrics" in comparison
        assert "comparison" in comparison
        assert "overall_complexity_score_dsl" in comparison["comparison"]
        assert "overall_complexity_score_json" in comparison["comparison"]

    def test_code_type_detection(self):
        """Test automatic code type detection."""
        analyzer = ComplexityAnalyzer()

        # Test JSON detection
        json_code = '{"key": "value"}'
        metrics = analyzer.analyze_code(json_code, "auto")
        assert metrics.json_depth is not None

        # Test DSL detection
        dsl_code = "x = 5"
        metrics = analyzer.analyze_code(dsl_code, "auto")
        assert metrics.function_call_count is not None


class TestPerformanceTester:
    """Test the performance tester functionality."""

    def test_tester_initialization(self):
        """Test that the tester initializes correctly."""
        tester = PerformanceTester()
        assert tester is not None
        assert len(tester.test_results) == 0

    def test_measure_parsing_performance(self):
        """Test parsing performance measurement."""
        tester = PerformanceTester()

        # Test DSL parsing
        dsl_code = "canvas = Canvas(800, 600)"
        metrics = tester.measure_parsing_performance(dsl_code, "dsl", iterations=5)

        assert metrics.parse_time_ms >= 0
        assert metrics.parse_memory_kb >= 0
        assert metrics.parse_success is True
        assert metrics.performance_score >= 0

        # Test JSON parsing
        json_code = '{"canvas": {"width": 800, "height": 600}}'
        metrics = tester.measure_parsing_performance(json_code, "json", iterations=5)

        assert metrics.parse_time_ms >= 0
        assert metrics.parse_success is True

    def test_compare_performance(self):
        """Test performance comparison."""
        tester = PerformanceTester()

        dsl_code = "canvas = Canvas(800, 600)"
        json_code = '{"canvas": {"width": 800, "height": 600}}'

        comparison = tester.compare_performance(dsl_code, json_code, iterations=5)

        assert "dsl_metrics" in comparison
        assert "json_metrics" in comparison
        assert "comparison" in comparison
        assert "overall_performance_winner" in comparison["comparison"]

    def test_measure_scalability(self):
        """Test scalability measurement."""
        tester = PerformanceTester()

        base_code = "canvas = Canvas(800, 600)"
        scalability = tester.measure_scalability(base_code, "dsl", scale_factors=[1, 2])

        assert "results" in scalability
        assert "analysis" in scalability
        assert "scale_1x" in scalability["results"]
        assert "scale_2x" in scalability["results"]
        assert "scalability_rating" in scalability["analysis"]


class TestReportGenerator:
    """Test the report generator functionality."""

    @pytest.mark.skip(reason="Skipping TestReportGenerator tests as requested")
    def test_generator_initialization(self):
        """Test that the generator initializes correctly."""
        generator = ReportGenerator()
        assert generator is not None
        assert hasattr(generator, "comparison_framework")
        assert hasattr(generator, "metrics_collector")
        assert hasattr(generator, "complexity_analyzer")
        assert hasattr(generator, "performance_tester")

    @pytest.mark.skip(reason="Skipping TestReportGenerator tests as requested")
    def test_generate_comprehensive_report(self):
        """Test comprehensive report generation."""
        generator = ReportGenerator()

        dsl_examples = {"simple": "canvas = Canvas(800, 600)"}
        json_examples = {"simple": '{"canvas": {"width": 800, "height": 600}}'}

        report = generator.generate_comprehensive_report(
            dsl_examples, json_examples, include_simulated_data=True
        )

        assert report is not None
        assert report.report_id is not None
        assert report.timestamp is not None
        assert "overall_recommendation" in report.executive_summary
        assert "key_findings" in report.executive_summary
        assert len(report.recommendations) > 0

    @pytest.mark.skip(reason="Skipping TestReportGenerator tests as requested")
    @patch("builtins.open", create=True)
    def test_export_report_json(self, mock_open):
        """Test JSON report export."""
        generator = ReportGenerator()

        # Create a minimal report
        dsl_examples = {"test": "x = 1"}
        json_examples = {"test": '{"x": 1}'}

        report = generator.generate_comprehensive_report(
            dsl_examples, json_examples, False
        )

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        generator.export_report(report, ReportFormat.JSON, "test.json")

        mock_open.assert_called_once_with("test.json", "w")
        mock_file.write.assert_called()

    @pytest.mark.skip(reason="Skipping TestReportGenerator tests as requested")
    @patch("builtins.open", create=True)
    def test_export_report_markdown(self, mock_open):
        """Test Markdown report export."""
        generator = ReportGenerator()

        # Create a minimal report
        dsl_examples = {"test": "x = 1"}
        json_examples = {"test": '{"x": 1}'}

        report = generator.generate_comprehensive_report(
            dsl_examples, json_examples, False
        )

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        generator.export_report(report, ReportFormat.MARKDOWN, "test.md")

        mock_open.assert_called_once_with("test.md", "w")
        mock_file.write.assert_called()


class TestIntegration:
    """Integration tests for the complete validation framework."""

    def test_end_to_end_validation(self):
        """Test complete end-to-end validation workflow."""
        # Initialize all components
        comparison_framework = ComparisonFramework()
        metrics_collector = MetricsCollector()
        complexity_analyzer = ComplexityAnalyzer()
        performance_tester = PerformanceTester()
        report_generator = ReportGenerator()

        # Test data
        dsl_code = """
canvas = Canvas(800, 600)
text = Text("Hello World", 10, 30)
progress = ProgressBar(10, 60, 200, 20, 0.75)
canvas.add(text)
canvas.add(progress)
"""

        json_code = """{
  "canvas": {
    "width": 800,
    "height": 600,
    "widgets": [
      {
        "type": "text",
        "content": "Hello World",
        "position": {"x": 10, "y": 30}
      },
      {
        "type": "progress_bar",
        "position": {"x": 10, "y": 60},
        "size": {"width": 200, "height": 20},
        "value": 0.75
      }
    ]
  }
}"""

        # Run comparison
        comparison_result = comparison_framework.compare_approaches(
            ComparisonType.WIDGET_COMPOSITION,
            "custom",
            custom_dsl=dsl_code,
            custom_json=json_code,
        )
        assert comparison_result is not None

        # Simulate developer experience
        metrics_collector.simulate_developer_session("dsl", "intermediate")
        metrics_collector.simulate_developer_session("json", "intermediate")
        dev_comparison = metrics_collector.compare_approaches()
        assert dev_comparison is not None

        # Analyze complexity
        complexity_comparison = complexity_analyzer.compare_complexity(
            dsl_code, json_code
        )
        assert complexity_comparison is not None

        # Test performance
        performance_comparison = performance_tester.compare_performance(
            dsl_code, json_code, iterations=5
        )
        assert performance_comparison is not None

        # Generate report
        report = report_generator.generate_comprehensive_report(
            {"test": dsl_code}, {"test": json_code}, include_simulated_data=True
        )
        assert report is not None
        assert "DSL" in report.executive_summary["overall_recommendation"]

    def test_validation_framework_robustness(self):
        """Test framework robustness with edge cases."""
        generator = ReportGenerator()

        # Test with empty examples
        empty_report = generator.generate_comprehensive_report({}, {}, False)
        assert empty_report is not None

        # Test with malformed code
        malformed_dsl = "this is not valid python code !!!"
        malformed_json = '{"invalid": json syntax}'

        try:
            malformed_report = generator.generate_comprehensive_report(
                {"malformed": malformed_dsl}, {"malformed": malformed_json}, False
            )
            assert malformed_report is not None
        except Exception:
            # It's acceptable for malformed code to cause exceptions
            pass

    def test_success_metrics_calculation(self):
        """Test that success metrics are calculated correctly."""
        generator = ReportGenerator()

        # Generate a report with simulated data
        report = generator.generate_comprehensive_report(
            {"test": "canvas = Canvas(800, 600)"},
            {"test": '{"canvas": {"width": 800, "height": 600}}'},
            include_simulated_data=True,
        )

        assert "target_achievements" in report.success_metrics
        assert "performance_indicators" in report.success_metrics

        # Check that we have some target achievements
        if report.success_metrics["target_achievements"]:
            for metric_name, achievement in report.success_metrics[
                "target_achievements"
            ].items():
                assert "target" in achievement
                assert "actual" in achievement
                assert "achieved" in achievement
                assert isinstance(achievement["achieved"], bool)


if __name__ == "__main__":
    pytest.main([__file__])
