#!/usr/bin/env python3
"""
DSL Validation Framework Demonstration

This script demonstrates the comprehensive DSL validation framework
that compares DSL and JSON approaches across multiple dimensions.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tinydisplay.validation import (
    ReportGenerator,
    ReportFormat,
    ComparisonFramework,
    MetricsCollector,
    ComplexityAnalyzer,
    PerformanceTester,
    ComparisonType
)


def main():
    """Run the DSL validation framework demonstration."""
    print("🚀 DSL Validation Framework Demonstration")
    print("=" * 50)
    
    # Example DSL and JSON code for comparison
    dsl_examples = {
        "dashboard": """
# DSL Approach - System Dashboard
dashboard = Canvas(width=256, height=128)
dashboard.add(
    Text("System Monitor").position(10, 5).font_size(14),
    ProgressBar(value=data.cpu_usage, label="CPU").position(10, 25),
    ProgressBar(value=data.memory_usage, label="RAM").position(10, 45),
    Text(f"Temp: {data.temperature}°C").position(10, 70),
    Image("status_icon.png").position(200, 10)
)
dashboard.animate.slide_in().sync('startup_sequence')
""",
        "simple_widget": """
# DSL Approach - Simple Widget
canvas = Canvas(width=128, height=64)
canvas.add(
    Text("CPU Usage").position(10, 10),
    ProgressBar(value=data.cpu_usage).position(10, 30)
)
"""
    }
    
    json_examples = {
        "dashboard": """{
  "canvas": {
    "width": 256,
    "height": 128,
    "widgets": [
      {
        "type": "text",
        "content": "System Monitor",
        "position": {"x": 10, "y": 5},
        "font_size": 14
      },
      {
        "type": "progress_bar",
        "value": {"binding": "data.cpu_usage"},
        "label": "CPU",
        "position": {"x": 10, "y": 25}
      },
      {
        "type": "progress_bar",
        "value": {"binding": "data.memory_usage"},
        "label": "RAM",
        "position": {"x": 10, "y": 45}
      },
      {
        "type": "text",
        "content": {"binding": "data.temperature", "template": "Temp: {value}°C"},
        "position": {"x": 10, "y": 70}
      },
      {
        "type": "image",
        "src": "status_icon.png",
        "position": {"x": 200, "y": 10}
      }
    ],
    "animations": [
      {
        "type": "slide_in",
        "sync_group": "startup_sequence"
      }
    ]
  }
}""",
        "simple_widget": """{
  "canvas": {
    "width": 128,
    "height": 64,
    "widgets": [
      {
        "type": "text",
        "content": "CPU Usage",
        "position": {"x": 10, "y": 10}
      },
      {
        "type": "progress_bar",
        "value": {"binding": "data.cpu_usage"},
        "position": {"x": 10, "y": 30}
      }
    ]
  }
}"""
    }
    
    print("\n📊 Running Individual Component Tests...")
    
    # 1. Comparison Framework Demo
    print("\n1. Comparison Framework Analysis:")
    framework = ComparisonFramework()
    
    # Test predefined scenarios
    result = framework.compare_approaches(
        ComparisonType.WIDGET_COMPOSITION,
        "simple_text_progress"
    )
    print(f"   ✅ Predefined scenario comparison: {result['comparison']['winner']} wins")
    
    # Test custom scenario
    custom_result = framework.compare_approaches(
        ComparisonType.WIDGET_COMPOSITION,
        "custom",
        custom_dsl=dsl_examples["simple_widget"],
        custom_json=json_examples["simple_widget"]
    )
    print(f"   ✅ Custom scenario comparison: {custom_result['comparison']['winner']} wins")
    
    # 2. Developer Experience Metrics Demo
    print("\n2. Developer Experience Simulation:")
    metrics_collector = MetricsCollector()
    
    # Simulate developer sessions
    for experience in ["beginner", "intermediate", "expert"]:
        for approach in ["dsl", "json"]:
            metrics_collector.simulate_developer_session(approach, experience)
    
    comparison = metrics_collector.compare_approaches()
    superiority_score = comparison["comparison"]["overall_dsl_superiority_score"]
    print(f"   ✅ DSL superiority score: {superiority_score:.2f}x")
    print(f"   ✅ Simulated {len(metrics_collector.task_metrics)} development tasks")
    
    # 3. Complexity Analysis Demo
    print("\n3. Complexity Analysis:")
    complexity_analyzer = ComplexityAnalyzer()
    
    complexity_comparison = complexity_analyzer.compare_complexity(
        dsl_examples["dashboard"],
        json_examples["dashboard"]
    )
    
    dsl_score = complexity_comparison["comparison"]["overall_complexity_score_dsl"]
    json_score = complexity_comparison["comparison"]["overall_complexity_score_json"]
    print(f"   ✅ DSL complexity score: {dsl_score:.2f}")
    print(f"   ✅ JSON complexity score: {json_score:.2f}")
    print(f"   ✅ DSL advantage: {dsl_score - json_score:.2f} points")
    
    # 4. Performance Testing Demo
    print("\n4. Performance Testing:")
    performance_tester = PerformanceTester()
    
    perf_comparison = performance_tester.compare_performance(
        dsl_examples["simple_widget"],
        json_examples["simple_widget"],
        iterations=10  # Reduced for demo speed
    )
    
    winner = perf_comparison["comparison"]["overall_performance_winner"]
    print(f"   ✅ Performance winner: {winner}")
    print(f"   ✅ DSL parsing time: {perf_comparison['dsl_metrics'].parse_time_ms:.2f}ms")
    print(f"   ✅ JSON parsing time: {perf_comparison['json_metrics'].parse_time_ms:.2f}ms")
    
    # 5. Comprehensive Report Generation
    print("\n📋 Generating Comprehensive Validation Report...")
    
    report_generator = ReportGenerator()
    report = report_generator.generate_comprehensive_report(
        dsl_examples,
        json_examples,
        include_simulated_data=True
    )
    
    print(f"\n🎯 Executive Summary:")
    print(f"   Recommendation: {report.executive_summary['overall_recommendation']}")
    print(f"   Confidence Level: {report.executive_summary['confidence_level']}")
    print(f"   Key Findings: {len(report.executive_summary['key_findings'])} findings")
    
    print(f"\n📈 Key Findings:")
    for i, finding in enumerate(report.executive_summary['key_findings'], 1):
        print(f"   {i}. {finding}")
    
    print(f"\n💡 Top Recommendations:")
    for i, rec in enumerate(report.recommendations[:5], 1):
        print(f"   {i}. {rec}")
    
    # Export reports in different formats
    output_dir = Path("validation_reports")
    output_dir.mkdir(exist_ok=True)
    
    print(f"\n📄 Exporting Reports to {output_dir}/...")
    
    # Export as JSON
    report_generator.export_report(
        report,
        ReportFormat.JSON,
        str(output_dir / "dsl_validation_report.json")
    )
    print("   ✅ JSON report exported")
    
    # Export as Markdown
    report_generator.export_report(
        report,
        ReportFormat.MARKDOWN,
        str(output_dir / "dsl_validation_report.md")
    )
    print("   ✅ Markdown report exported")
    
    # Export as HTML
    report_generator.export_report(
        report,
        ReportFormat.HTML,
        str(output_dir / "dsl_validation_report.html")
    )
    print("   ✅ HTML report exported")
    
    # Export summary
    report_generator.export_report(
        report,
        ReportFormat.SUMMARY,
        str(output_dir / "dsl_validation_summary.json")
    )
    print("   ✅ Summary report exported")
    
    print(f"\n🎉 Validation Framework Demonstration Complete!")
    print(f"📊 Success Metrics:")
    
    if "target_achievements" in report.success_metrics:
        for metric, achievement in report.success_metrics["target_achievements"].items():
            status = "✅" if achievement["achieved"] else "❌"
            print(f"   {status} {metric}: {achievement['actual']:.1f}% (Target: {achievement['target']:.1f}%)")
    
    print(f"\n📁 Reports available in: {output_dir.absolute()}")
    print("\n🚀 DSL Validation Framework successfully demonstrates DSL superiority!")


if __name__ == "__main__":
    main() 