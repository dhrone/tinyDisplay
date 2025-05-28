#!/usr/bin/env python3
"""
Migration Validation Framework

Validates migration tool accuracy and ensures converted DSL applications
maintain functional equivalence with legacy applications.
"""

import os
import sys
import ast
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

from migration_tool import SystemAnalyzer, SystemAnalysis
from migration_generator import CodeGenerator, GenerationConfig
from dsl_converter import JSONToDSLConverter


@dataclass
class ValidationResult:
    """Result of a validation test"""
    test_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    details: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    execution_time: float


@dataclass
class MigrationReport:
    """Complete migration validation report"""
    source_path: str
    target_path: str
    validation_results: List[ValidationResult]
    overall_score: float
    success_rate: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    generation_time: float
    validation_time: float
    recommendations: List[str]


class ValidationTest(ABC):
    """Base class for migration validation tests"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def validate(self, legacy_analysis: SystemAnalysis, generated_code: str, target_path: Path) -> ValidationResult:
        """Perform validation test"""
        pass


class WidgetCountValidation(ValidationTest):
    """Validates that all widgets are migrated"""
    
    def __init__(self):
        super().__init__("Widget Count", "Verify all legacy widgets are converted to DSL")
    
    def validate(self, legacy_analysis: SystemAnalysis, generated_code: str, target_path: Path) -> ValidationResult:
        start_time = time.time()
        errors = []
        warnings = []
        
        # Count widgets in legacy analysis
        legacy_widget_count = len(legacy_analysis.widgets)
        
        # Count widgets in generated DSL
        dsl_widget_count = generated_code.count("widget_")
        
        # Calculate score
        if legacy_widget_count == 0:
            score = 1.0 if dsl_widget_count == 0 else 0.0
        else:
            score = min(dsl_widget_count / legacy_widget_count, 1.0)
        
        passed = score >= 0.95  # 95% threshold
        
        if not passed:
            errors.append(f"Widget count mismatch: legacy={legacy_widget_count}, dsl={dsl_widget_count}")
        
        if score < 1.0:
            warnings.append(f"Some widgets may not have been converted ({score:.1%} conversion rate)")
        
        return ValidationResult(
            test_name=self.name,
            passed=passed,
            score=score,
            details={
                "legacy_widgets": legacy_widget_count,
                "dsl_widgets": dsl_widget_count,
                "conversion_rate": score
            },
            errors=errors,
            warnings=warnings,
            execution_time=time.time() - start_time
        )


class AnimationConversionValidation(ValidationTest):
    """Validates animation conversion accuracy"""
    
    def __init__(self):
        super().__init__("Animation Conversion", "Verify animations are properly converted to DSL")
    
    def validate(self, legacy_analysis: SystemAnalysis, generated_code: str, target_path: Path) -> ValidationResult:
        start_time = time.time()
        errors = []
        warnings = []
        
        # Count animations in legacy analysis
        legacy_animation_count = len(legacy_analysis.animations)
        
        # Count animations in generated DSL
        dsl_animation_count = generated_code.count(".animate.")
        
        # Calculate score
        if legacy_animation_count == 0:
            score = 1.0 if dsl_animation_count == 0 else 0.0
        else:
            score = min(dsl_animation_count / legacy_animation_count, 1.0)
        
        passed = score >= 0.90  # 90% threshold for animations
        
        if not passed:
            errors.append(f"Animation count mismatch: legacy={legacy_animation_count}, dsl={dsl_animation_count}")
        
        # Check for specific animation types
        animation_types = ['marquee', 'fade', 'slide', 'pulse', 'blink', 'rotate']
        for anim_type in animation_types:
            legacy_count = sum(1 for a in legacy_analysis.animations if a.animation_type == anim_type)
            dsl_count = generated_code.count(f".{anim_type}(")
            
            if legacy_count > 0 and dsl_count == 0:
                warnings.append(f"Animation type '{anim_type}' not found in DSL")
        
        return ValidationResult(
            test_name=self.name,
            passed=passed,
            score=score,
            details={
                "legacy_animations": legacy_animation_count,
                "dsl_animations": dsl_animation_count,
                "conversion_rate": score
            },
            errors=errors,
            warnings=warnings,
            execution_time=time.time() - start_time
        )


class DataBindingValidation(ValidationTest):
    """Validates data binding conversion"""
    
    def __init__(self):
        super().__init__("Data Binding", "Verify reactive data bindings are properly converted")
    
    def validate(self, legacy_analysis: SystemAnalysis, generated_code: str, target_path: Path) -> ValidationResult:
        start_time = time.time()
        errors = []
        warnings = []
        
        # Count dynamic values in legacy analysis
        legacy_binding_count = len(legacy_analysis.dynamic_values)
        
        # Count reactive bindings in generated DSL
        reactive_count = generated_code.count("reactive(")
        bind_count = generated_code.count(".bind_")
        dsl_binding_count = reactive_count + bind_count
        
        # Calculate score
        if legacy_binding_count == 0:
            score = 1.0 if dsl_binding_count == 0 else 0.0
        else:
            score = min(dsl_binding_count / legacy_binding_count, 1.0)
        
        passed = score >= 1.0  # 100% threshold for data bindings
        
        if not passed:
            errors.append(f"Data binding count mismatch: legacy={legacy_binding_count}, dsl={dsl_binding_count}")
        
        # Check for data source connections
        data_sources = set()
        for dv in legacy_analysis.dynamic_values:
            data_sources.update(dv.dependencies)
        
        for source in data_sources:
            if f"data_source.connect('{source}')" not in generated_code:
                warnings.append(f"Data source '{source}' connection not found in DSL")
        
        return ValidationResult(
            test_name=self.name,
            passed=passed,
            score=score,
            details={
                "legacy_bindings": legacy_binding_count,
                "dsl_bindings": dsl_binding_count,
                "reactive_expressions": reactive_count,
                "bind_methods": bind_count,
                "data_sources": len(data_sources)
            },
            errors=errors,
            warnings=warnings,
            execution_time=time.time() - start_time
        )


class DSLSyntaxValidation(ValidationTest):
    """Validates generated DSL syntax"""
    
    def __init__(self):
        super().__init__("DSL Syntax", "Verify generated DSL code has valid syntax")
    
    def validate(self, legacy_analysis: SystemAnalysis, generated_code: str, target_path: Path) -> ValidationResult:
        start_time = time.time()
        errors = []
        warnings = []
        
        try:
            # Try to parse the generated DSL as Python code
            ast.parse(generated_code)
            syntax_valid = True
            score = 1.0
        except SyntaxError as e:
            syntax_valid = False
            score = 0.0
            errors.append(f"Syntax error in generated DSL: {e}")
        
        # Check for common DSL patterns
        required_patterns = [
            "Canvas(",
            "def create_application():",
            "if __name__ == '__main__':"
        ]
        
        pattern_score = 0
        for pattern in required_patterns:
            if pattern in generated_code:
                pattern_score += 1
            else:
                warnings.append(f"Missing expected pattern: {pattern}")
        
        pattern_score = pattern_score / len(required_patterns)
        
        # Combine syntax and pattern scores
        final_score = (score + pattern_score) / 2
        passed = syntax_valid and final_score >= 0.8
        
        return ValidationResult(
            test_name=self.name,
            passed=passed,
            score=final_score,
            details={
                "syntax_valid": syntax_valid,
                "pattern_score": pattern_score,
                "required_patterns_found": pattern_score * len(required_patterns)
            },
            errors=errors,
            warnings=warnings,
            execution_time=time.time() - start_time
        )


class PerformanceValidation(ValidationTest):
    """Validates migration performance metrics"""
    
    def __init__(self):
        super().__init__("Performance", "Verify migration meets performance requirements")
    
    def validate(self, legacy_analysis: SystemAnalysis, generated_code: str, target_path: Path) -> ValidationResult:
        start_time = time.time()
        errors = []
        warnings = []
        
        # Check code size (should be reasonable)
        code_lines = len(generated_code.split('\n'))
        widget_count = len(legacy_analysis.widgets)
        
        # Calculate lines per widget ratio
        if widget_count > 0:
            lines_per_widget = code_lines / widget_count
        else:
            lines_per_widget = code_lines
        
        # Performance thresholds
        max_lines_per_widget = 50  # Reasonable threshold
        max_total_lines = 1000     # For typical applications
        
        size_score = 1.0
        if lines_per_widget > max_lines_per_widget:
            size_score *= 0.5
            warnings.append(f"Generated code may be verbose: {lines_per_widget:.1f} lines per widget")
        
        if code_lines > max_total_lines:
            size_score *= 0.7
            warnings.append(f"Generated code is large: {code_lines} lines")
        
        # Check for performance-critical patterns
        performance_patterns = [
            "ring_buffer",
            "data_manager",
            "reactive(",
            "computed("
        ]
        
        pattern_count = sum(1 for pattern in performance_patterns if pattern in generated_code)
        pattern_score = pattern_count / len(performance_patterns)
        
        # Combine scores
        final_score = (size_score + pattern_score) / 2
        passed = final_score >= 0.7
        
        return ValidationResult(
            test_name=self.name,
            passed=passed,
            score=final_score,
            details={
                "code_lines": code_lines,
                "lines_per_widget": lines_per_widget,
                "performance_patterns": pattern_count,
                "size_score": size_score,
                "pattern_score": pattern_score
            },
            errors=errors,
            warnings=warnings,
            execution_time=time.time() - start_time
        )


class BeforeAfterComparisonValidation(ValidationTest):
    """Validates functional equivalence between legacy and migrated applications"""
    
    def __init__(self):
        super().__init__("Before/After Comparison", "Compare legacy and migrated application functionality")
    
    def validate(self, legacy_analysis: SystemAnalysis, generated_code: str, target_path: Path) -> ValidationResult:
        start_time = time.time()
        errors = []
        warnings = []
        
        # Analyze widget functionality preservation
        widget_preservation_score = self._validate_widget_preservation(legacy_analysis, generated_code)
        
        # Analyze animation behavior preservation
        animation_preservation_score = self._validate_animation_preservation(legacy_analysis, generated_code)
        
        # Analyze data flow preservation
        data_flow_preservation_score = self._validate_data_flow_preservation(legacy_analysis, generated_code)
        
        # Calculate overall preservation score
        preservation_scores = [widget_preservation_score, animation_preservation_score, data_flow_preservation_score]
        overall_score = sum(preservation_scores) / len(preservation_scores)
        
        passed = overall_score >= 0.95  # 95% functional equivalence threshold
        
        if not passed:
            errors.append(f"Functional equivalence below threshold: {overall_score:.1%}")
        
        if widget_preservation_score < 1.0:
            warnings.append(f"Widget functionality preservation: {widget_preservation_score:.1%}")
        
        if animation_preservation_score < 1.0:
            warnings.append(f"Animation behavior preservation: {animation_preservation_score:.1%}")
        
        if data_flow_preservation_score < 1.0:
            warnings.append(f"Data flow preservation: {data_flow_preservation_score:.1%}")
        
        return ValidationResult(
            test_name=self.name,
            passed=passed,
            score=overall_score,
            details={
                "widget_preservation": widget_preservation_score,
                "animation_preservation": animation_preservation_score,
                "data_flow_preservation": data_flow_preservation_score,
                "overall_preservation": overall_score
            },
            errors=errors,
            warnings=warnings,
            execution_time=time.time() - start_time
        )
    
    def _validate_widget_preservation(self, legacy_analysis: SystemAnalysis, generated_code: str) -> float:
        """Validate that widget properties and behaviors are preserved"""
        if not legacy_analysis.widgets:
            return 1.0
        
        preserved_count = 0
        total_widgets = len(legacy_analysis.widgets)
        
        for widget in legacy_analysis.widgets:
            # Check if widget type is preserved
            widget_type_preserved = widget.widget_type.lower() in generated_code.lower()
            
            # Check if position is preserved (approximate)
            position_preserved = (
                f"position({widget.x}" in generated_code or
                f".x({widget.x}" in generated_code or
                str(widget.x) in generated_code
            )
            
            # Check if widget attributes are preserved
            attributes_preserved = True
            for attr_name, attr_value in widget.attributes.items():
                if str(attr_value) not in generated_code:
                    attributes_preserved = False
                    break
            
            if widget_type_preserved and (position_preserved or attributes_preserved):
                preserved_count += 1
        
        return preserved_count / total_widgets if total_widgets > 0 else 1.0
    
    def _validate_animation_preservation(self, legacy_analysis: SystemAnalysis, generated_code: str) -> float:
        """Validate that animation behaviors are preserved"""
        if not legacy_analysis.animations:
            return 1.0
        
        preserved_count = 0
        total_animations = len(legacy_analysis.animations)
        
        for animation in legacy_analysis.animations:
            # Check if animation type is preserved
            anim_type_preserved = (
                f".{animation.animation_type}(" in generated_code or
                animation.animation_type in generated_code
            )
            
            # Check if duration is preserved
            duration_preserved = True
            if hasattr(animation, 'duration') and animation.duration:
                duration_preserved = str(animation.duration) in generated_code
            
            if anim_type_preserved and duration_preserved:
                preserved_count += 1
        
        return preserved_count / total_animations if total_animations > 0 else 1.0
    
    def _validate_data_flow_preservation(self, legacy_analysis: SystemAnalysis, generated_code: str) -> float:
        """Validate that data flow patterns are preserved"""
        if not legacy_analysis.dynamic_values:
            return 1.0
        
        preserved_count = 0
        total_bindings = len(legacy_analysis.dynamic_values)
        
        for dynamic_value in legacy_analysis.dynamic_values:
            # Check if dependencies are preserved
            dependencies_preserved = all(
                dep in generated_code for dep in dynamic_value.dependencies
            )
            
            # Check if reactive pattern is implemented
            reactive_pattern_preserved = (
                "reactive(" in generated_code or
                ".bind_" in generated_code or
                "data_source.connect" in generated_code
            )
            
            if dependencies_preserved and reactive_pattern_preserved:
                preserved_count += 1
        
        return preserved_count / total_bindings if total_bindings > 0 else 1.0


class RegressionTestValidation(ValidationTest):
    """Validates that migration tool enhancements don't break existing functionality"""
    
    def __init__(self):
        super().__init__("Regression Testing", "Ensure migration tool enhancements maintain compatibility")
    
    def validate(self, legacy_analysis: SystemAnalysis, generated_code: str, target_path: Path) -> ValidationResult:
        start_time = time.time()
        errors = []
        warnings = []
        
        # Test core migration patterns
        core_patterns_score = self._validate_core_patterns(generated_code)
        
        # Test backward compatibility
        compatibility_score = self._validate_backward_compatibility(legacy_analysis, generated_code)
        
        # Test code quality standards
        quality_score = self._validate_code_quality(generated_code)
        
        # Calculate overall regression score
        regression_scores = [core_patterns_score, compatibility_score, quality_score]
        overall_score = sum(regression_scores) / len(regression_scores)
        
        passed = overall_score >= 0.90  # 90% regression threshold
        
        if not passed:
            errors.append(f"Regression test failed: {overall_score:.1%}")
        
        if core_patterns_score < 1.0:
            warnings.append(f"Core pattern compliance: {core_patterns_score:.1%}")
        
        if compatibility_score < 1.0:
            warnings.append(f"Backward compatibility: {compatibility_score:.1%}")
        
        if quality_score < 1.0:
            warnings.append(f"Code quality standards: {quality_score:.1%}")
        
        return ValidationResult(
            test_name=self.name,
            passed=passed,
            score=overall_score,
            details={
                "core_patterns": core_patterns_score,
                "backward_compatibility": compatibility_score,
                "code_quality": quality_score,
                "regression_score": overall_score
            },
            errors=errors,
            warnings=warnings,
            execution_time=time.time() - start_time
        )
    
    def _validate_core_patterns(self, generated_code: str) -> float:
        """Validate that core DSL patterns are present"""
        required_patterns = [
            "Canvas(",
            "def create_application():",
            "if __name__ == '__main__':",
            ".position(",
            ".add("
        ]
        
        pattern_count = sum(1 for pattern in required_patterns if pattern in generated_code)
        return pattern_count / len(required_patterns)
    
    def _validate_backward_compatibility(self, legacy_analysis: SystemAnalysis, generated_code: str) -> float:
        """Validate backward compatibility with legacy patterns"""
        compatibility_checks = []
        
        # Check widget type compatibility
        if legacy_analysis.widgets:
            widget_types = {w.widget_type for w in legacy_analysis.widgets}
            supported_types = {'text', 'progress', 'image', 'button', 'gauge', 'chart'}
            compatibility_checks.append(
                len(widget_types.intersection(supported_types)) / len(widget_types)
            )
        
        # Check animation compatibility
        if legacy_analysis.animations:
            anim_types = {a.animation_type for a in legacy_analysis.animations}
            supported_anims = {'fade', 'slide', 'marquee', 'pulse', 'blink', 'rotate'}
            compatibility_checks.append(
                len(anim_types.intersection(supported_anims)) / len(anim_types)
            )
        
        # Check data binding compatibility
        if legacy_analysis.dynamic_values:
            # All dynamic values should be convertible to reactive patterns
            compatibility_checks.append(1.0)
        
        return sum(compatibility_checks) / len(compatibility_checks) if compatibility_checks else 1.0
    
    def _validate_code_quality(self, generated_code: str) -> float:
        """Validate code quality standards"""
        quality_checks = []
        
        # Check for proper imports
        has_imports = any(line.strip().startswith('import ') or line.strip().startswith('from ') 
                         for line in generated_code.split('\n'))
        quality_checks.append(1.0 if has_imports else 0.0)
        
        # Check for proper function structure
        has_main_function = "def create_application():" in generated_code
        quality_checks.append(1.0 if has_main_function else 0.0)
        
        # Check for proper error handling patterns
        has_error_handling = "try:" in generated_code or "except:" in generated_code
        quality_checks.append(1.0 if has_error_handling else 0.5)  # Not always required
        
        # Check for documentation
        has_docstrings = '"""' in generated_code or "'''" in generated_code
        quality_checks.append(1.0 if has_docstrings else 0.5)  # Not always required
        
        return sum(quality_checks) / len(quality_checks)


class MigrationRollbackManager:
    """Manages rollback mechanisms for failed migrations"""
    
    def __init__(self):
        self.backup_registry = {}
        self.rollback_log = []
    
    def create_backup(self, source_path: str) -> str:
        """Create backup of source before migration"""
        import shutil
        import tempfile
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = tempfile.mkdtemp(prefix=f"migration_backup_{timestamp}_")
        
        try:
            shutil.copytree(source_path, backup_dir, dirs_exist_ok=True)
            self.backup_registry[source_path] = backup_dir
            self.rollback_log.append({
                'timestamp': timestamp,
                'source': source_path,
                'backup': backup_dir,
                'action': 'backup_created'
            })
            return backup_dir
        except Exception as e:
            raise RuntimeError(f"Failed to create backup: {e}")
    
    def rollback_migration(self, source_path: str, target_path: str = None) -> bool:
        """Rollback failed migration"""
        import shutil
        from datetime import datetime
        
        if source_path not in self.backup_registry:
            self.rollback_log.append({
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'source': source_path,
                'action': 'rollback_failed',
                'error': 'No backup found'
            })
            return False
        
        backup_path = self.backup_registry[source_path]
        
        try:
            # Remove failed migration target if it exists
            if target_path and Path(target_path).exists():
                shutil.rmtree(target_path)
            
            # Restore from backup if source was modified
            if Path(source_path).exists():
                shutil.rmtree(source_path)
            shutil.copytree(backup_path, source_path)
            
            self.rollback_log.append({
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'source': source_path,
                'target': target_path,
                'backup': backup_path,
                'action': 'rollback_successful'
            })
            return True
            
        except Exception as e:
            self.rollback_log.append({
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'source': source_path,
                'action': 'rollback_failed',
                'error': str(e)
            })
            return False
    
    def cleanup_backup(self, source_path: str) -> bool:
        """Clean up backup after successful migration"""
        import shutil
        from datetime import datetime
        
        if source_path not in self.backup_registry:
            return False
        
        backup_path = self.backup_registry[source_path]
        
        try:
            shutil.rmtree(backup_path)
            del self.backup_registry[source_path]
            self.rollback_log.append({
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'source': source_path,
                'backup': backup_path,
                'action': 'backup_cleaned'
            })
            return True
        except Exception as e:
            self.rollback_log.append({
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'source': source_path,
                'action': 'cleanup_failed',
                'error': str(e)
            })
            return False
    
    def get_rollback_log(self) -> List[Dict[str, Any]]:
        """Get rollback operation log"""
        return self.rollback_log.copy()


class MigrationValidator:
    """Main migration validation framework"""
    
    def __init__(self):
        self.tests = [
            WidgetCountValidation(),
            AnimationConversionValidation(),
            DataBindingValidation(),
            DSLSyntaxValidation(),
            PerformanceValidation(),
            BeforeAfterComparisonValidation(),
            RegressionTestValidation()
        ]
        self.json_converter = JSONToDSLConverter()
        self.rollback_manager = MigrationRollbackManager()
    
    def validate_migration(self, source_path: str, target_path: str = None, create_backup: bool = True) -> MigrationReport:
        """Validate complete migration from source to target with optional rollback support"""
        start_time = time.time()
        backup_path = None
        
        try:
            # Create backup if requested
            if create_backup:
                backup_path = self.rollback_manager.create_backup(source_path)
            
            # Analyze legacy system
            analyzer = SystemAnalyzer(source_path)
            legacy_analysis = analyzer.analyze()
            
            # Generate new system
            generation_start = time.time()
            if target_path is None:
                target_path = f"{source_path}_migrated"
            
            target_path_obj = Path(target_path)
            config = GenerationConfig()
            generator = CodeGenerator(legacy_analysis, config)
            
            # Generate DSL from legacy analysis
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                # Create directory structure first
                (temp_path / "dsl").mkdir(parents=True, exist_ok=True)
                generator._generate_application_dsl(temp_path)
                dsl_file = temp_path / "dsl" / "application.py"
                if dsl_file.exists():
                    generated_dsl = dsl_file.read_text()
                else:
                    generated_dsl = "# DSL generation failed"
            
            # Write generated code to file for inspection
            dsl_file = target_path_obj / "application.py"
            target_path_obj.mkdir(parents=True, exist_ok=True)
            dsl_file.write_text(generated_dsl)
            
            generation_time = time.time() - generation_start
            
            # Run validation tests
            validation_start = time.time()
            validation_results = []
            
            for test in self.tests:
                try:
                    result = test.validate(legacy_analysis, generated_dsl, target_path_obj)
                    validation_results.append(result)
                except Exception as e:
                    # Create error result for failed test
                    error_result = ValidationResult(
                        test_name=test.name,
                        passed=False,
                        score=0.0,
                        details={"error": str(e)},
                        errors=[f"Test execution failed: {e}"],
                        warnings=[],
                        execution_time=0.0
                    )
                    validation_results.append(error_result)
            
            validation_time = time.time() - validation_start
            
            # Calculate overall metrics
            total_tests = len(validation_results)
            passed_tests = sum(1 for r in validation_results if r.passed)
            failed_tests = total_tests - passed_tests
            success_rate = passed_tests / total_tests if total_tests > 0 else 0.0
            overall_score = sum(r.score for r in validation_results) / total_tests if total_tests > 0 else 0.0
            
            # Check if migration should be rolled back
            critical_failures = [r for r in validation_results if not r.passed and r.test_name in 
                               ["DSL Syntax", "Before/After Comparison"]]
            
            if critical_failures and create_backup:
                # Rollback on critical failures
                rollback_success = self.rollback_manager.rollback_migration(source_path, target_path)
                if rollback_success:
                    for result in validation_results:
                        if result.test_name in ["DSL Syntax", "Before/After Comparison"]:
                            result.warnings.append("Migration rolled back due to critical failure")
            elif create_backup and overall_score >= 0.95:
                # Clean up backup on successful migration
                self.rollback_manager.cleanup_backup(source_path)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(validation_results, legacy_analysis)
            
            return MigrationReport(
                source_path=source_path,
                target_path=target_path,
                validation_results=validation_results,
                overall_score=overall_score,
                success_rate=success_rate,
                total_tests=total_tests,
                passed_tests=passed_tests,
                failed_tests=failed_tests,
                generation_time=generation_time,
                validation_time=validation_time,
                recommendations=recommendations
            )
            
        except Exception as e:
            # Handle migration failure with rollback
            if create_backup and backup_path:
                rollback_success = self.rollback_manager.rollback_migration(source_path, target_path)
                error_msg = f"Migration failed: {e}. Rollback {'successful' if rollback_success else 'failed'}."
            else:
                error_msg = f"Migration failed: {e}"
            
            # Return error report
            error_result = ValidationResult(
                test_name="Migration",
                passed=False,
                score=0.0,
                details={"error": str(e)},
                errors=[error_msg],
                warnings=[],
                execution_time=time.time() - start_time
            )
            
            return MigrationReport(
                source_path=source_path,
                target_path=target_path or f"{source_path}_migrated",
                validation_results=[error_result],
                overall_score=0.0,
                success_rate=0.0,
                total_tests=1,
                passed_tests=0,
                failed_tests=1,
                generation_time=0.0,
                validation_time=0.0,
                recommendations=["Fix migration errors and retry"]
            )
    
    def _generate_recommendations(self, results: List[ValidationResult], analysis: SystemAnalysis) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Check for common issues
        widget_result = next((r for r in results if r.test_name == "Widget Count"), None)
        if widget_result and not widget_result.passed:
            recommendations.append("Review widget analysis patterns - some widgets may not be detected")
        
        animation_result = next((r for r in results if r.test_name == "Animation Conversion"), None)
        if animation_result and animation_result.score < 0.9:
            recommendations.append("Enhance animation pattern detection for better conversion coverage")
        
        binding_result = next((r for r in results if r.test_name == "Data Binding"), None)
        if binding_result and not binding_result.passed:
            recommendations.append("Improve dynamic value analysis to capture all data dependencies")
        
        syntax_result = next((r for r in results if r.test_name == "DSL Syntax"), None)
        if syntax_result and not syntax_result.passed:
            recommendations.append("Fix DSL generation templates to ensure valid Python syntax")
        
        performance_result = next((r for r in results if r.test_name == "Performance"), None)
        if performance_result and performance_result.score < 0.8:
            recommendations.append("Optimize DSL generation to reduce code verbosity")
        
        # General recommendations
        if len(analysis.widgets) > 10:
            recommendations.append("Consider breaking large applications into smaller modules")
        
        if len(analysis.dynamic_values) > 20:
            recommendations.append("Review data binding patterns for potential optimization")
        
        return recommendations
    
    def validate_json_conversion(self, json_file: str) -> ValidationResult:
        """Validate JSON-to-DSL conversion"""
        start_time = time.time()
        
        try:
            dsl_code = self.json_converter.convert_file(json_file)
            report = self.json_converter.get_conversion_report()
            
            passed = report['success']
            score = 1.0 if passed else 0.0
            
            return ValidationResult(
                test_name="JSON Conversion",
                passed=passed,
                score=score,
                details=report,
                errors=report['errors'],
                warnings=report['warnings'],
                execution_time=time.time() - start_time
            )
        
        except Exception as e:
            return ValidationResult(
                test_name="JSON Conversion",
                passed=False,
                score=0.0,
                details={"error": str(e)},
                errors=[f"JSON conversion failed: {e}"],
                warnings=[],
                execution_time=time.time() - start_time
            )
    
    def generate_report(self, report: MigrationReport, output_file: str = None) -> str:
        """Generate detailed validation report"""
        report_lines = []
        
        # Header
        report_lines.append("# Migration Validation Report")
        report_lines.append("")
        report_lines.append(f"**Source:** {report.source_path}")
        report_lines.append(f"**Target:** {report.target_path}")
        report_lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Summary
        report_lines.append("## Summary")
        report_lines.append("")
        report_lines.append(f"- **Overall Score:** {report.overall_score:.1%}")
        report_lines.append(f"- **Success Rate:** {report.success_rate:.1%}")
        report_lines.append(f"- **Tests Passed:** {report.passed_tests}/{report.total_tests}")
        report_lines.append(f"- **Generation Time:** {report.generation_time:.2f}s")
        report_lines.append(f"- **Validation Time:** {report.validation_time:.2f}s")
        report_lines.append("")
        
        # Test Results
        report_lines.append("## Test Results")
        report_lines.append("")
        
        for result in report.validation_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            report_lines.append(f"### {result.test_name} - {status}")
            report_lines.append("")
            report_lines.append(f"- **Score:** {result.score:.1%}")
            report_lines.append(f"- **Execution Time:** {result.execution_time:.3f}s")
            
            if result.details:
                report_lines.append("- **Details:**")
                for key, value in result.details.items():
                    report_lines.append(f"  - {key}: {value}")
            
            if result.errors:
                report_lines.append("- **Errors:**")
                for error in result.errors:
                    report_lines.append(f"  - {error}")
            
            if result.warnings:
                report_lines.append("- **Warnings:**")
                for warning in result.warnings:
                    report_lines.append(f"  - {warning}")
            
            report_lines.append("")
        
        # Recommendations
        if report.recommendations:
            report_lines.append("## Recommendations")
            report_lines.append("")
            for i, rec in enumerate(report.recommendations, 1):
                report_lines.append(f"{i}. {rec}")
            report_lines.append("")
        
        report_text = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
        
        return report_text

    def get_rollback_log(self) -> List[Dict[str, Any]]:
        """Get rollback operation log"""
        return self.rollback_manager.get_rollback_log()


def main():
    """Main CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate tinyDisplay migration')
    parser.add_argument('source', help='Source directory to migrate')
    parser.add_argument('--target', '-t', help='Target directory for migration')
    parser.add_argument('--report', '-r', help='Output report file')
    parser.add_argument('--json', help='Validate JSON file conversion')
    
    args = parser.parse_args()
    
    validator = MigrationValidator()
    
    if args.json:
        # Validate JSON conversion
        result = validator.validate_json_conversion(args.json)
        print(f"JSON Conversion: {'PASS' if result.passed else 'FAIL'}")
        print(f"Score: {result.score:.1%}")
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"  - {error}")
    else:
        # Validate full migration
        report = validator.validate_migration(args.source, args.target)
        
        print(f"Migration Validation Complete")
        print(f"Overall Score: {report.overall_score:.1%}")
        print(f"Success Rate: {report.success_rate:.1%}")
        print(f"Tests Passed: {report.passed_tests}/{report.total_tests}")
        
        # Generate detailed report
        report_text = validator.generate_report(report, args.report)
        
        if args.report:
            print(f"Detailed report saved to: {args.report}")
        else:
            print("\nDetailed Report:")
            print(report_text)


if __name__ == "__main__":
    main() 