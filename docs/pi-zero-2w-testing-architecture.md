# Pi Zero 2W Testing Architecture

**Document Version:** 1.0  
**Author:** Timmy (Software Architect)  
**Epic:** Epic 3 - Tick-Based Animation & Coordination System  
**Status:** Architecture Design  

---

## Overview

This document defines the comprehensive testing architecture for validating the tick-based animation system on Raspberry Pi Zero 2W hardware, ensuring 60fps performance with multi-core optimization.

## Hardware Specifications

### Raspberry Pi Zero 2W Target Platform
- **CPU:** Broadcom BCM2710A1, quad-core 64-bit ARM Cortex-A53 @ 1GHz
- **Memory:** 512MB LPDDR2 SDRAM
- **Cores:** 4 cores (1 master + 3 workers for animation)
- **Architecture:** ARMv8-A (64-bit)
- **GPU:** VideoCore IV
- **Storage:** MicroSD card (Class 10 minimum)

### Performance Constraints
- **Memory Budget:** <55MB for animation system (leaving 457MB for applications)
- **CPU Utilization:** Target >80% worker utilization across 3 cores
- **Thermal Limits:** Sustained operation without throttling
- **Power Consumption:** Optimized for battery-powered applications

---

## Testing Architecture Components

### 1. Hardware Test Environment

**Physical Test Setup:**
```python
class PiZero2WTestEnvironment:
    """
    Physical test environment for Pi Zero 2W validation.
    Manages hardware monitoring and test execution.
    """
    
    def __init__(self):
        self.hardware_monitor = HardwareMonitor()
        self.thermal_monitor = ThermalMonitor()
        self.power_monitor = PowerMonitor()
        self.performance_profiler = PerformanceProfiler()
    
    def setup_test_environment(self) -> bool:
        """
        Setup Pi Zero 2W for animation testing.
        
        Returns:
            True if environment setup successful
        """
        # Configure CPU governor for performance testing
        self._set_cpu_governor('performance')
        
        # Set up memory monitoring
        self._configure_memory_monitoring()
        
        # Initialize thermal monitoring
        self._setup_thermal_monitoring()
        
        # Configure GPU memory split
        self._set_gpu_memory_split(64)  # 64MB for GPU
        
        return self._validate_environment()
    
    def _set_cpu_governor(self, governor: str) -> bool:
        """Set CPU frequency governor."""
        try:
            with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', 'w') as f:
                f.write(governor)
            return True
        except Exception as e:
            print(f"Failed to set CPU governor: {e}")
            return False
    
    def _configure_memory_monitoring(self) -> None:
        """Configure memory usage monitoring."""
        self.memory_baseline = self._get_memory_usage()
        self.memory_threshold = 55 * 1024 * 1024  # 55MB in bytes
    
    def _setup_thermal_monitoring(self) -> None:
        """Setup thermal throttling monitoring."""
        self.thermal_threshold = 80.0  # Celsius
        self.thermal_monitor.set_threshold(self.thermal_threshold)
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        import psutil
        return psutil.virtual_memory().used
    
    def _validate_environment(self) -> bool:
        """Validate test environment is ready."""
        # Check CPU frequency
        cpu_freq = self._get_cpu_frequency()
        if cpu_freq < 1000:  # Should be 1GHz
            return False
        
        # Check available memory
        available_memory = self._get_available_memory()
        if available_memory < 400 * 1024 * 1024:  # Need at least 400MB
            return False
        
        # Check thermal state
        cpu_temp = self._get_cpu_temperature()
        if cpu_temp > 70.0:  # Too hot to start
            return False
        
        return True

class HardwareMonitor:
    """Monitor Pi Zero 2W hardware metrics during testing."""
    
    def __init__(self):
        self.cpu_usage_history = []
        self.memory_usage_history = []
        self.temperature_history = []
        self.frequency_history = []
    
    def start_monitoring(self, interval_seconds: float = 0.1) -> None:
        """Start continuous hardware monitoring."""
        import threading
        import time
        
        def monitor_loop():
            while self.monitoring_active:
                timestamp = time.time()
                
                # CPU metrics
                cpu_usage = self._get_cpu_usage_per_core()
                cpu_freq = self._get_cpu_frequency()
                
                # Memory metrics
                memory_usage = self._get_memory_usage()
                
                # Thermal metrics
                cpu_temp = self._get_cpu_temperature()
                
                # Store metrics
                self.cpu_usage_history.append((timestamp, cpu_usage))
                self.memory_usage_history.append((timestamp, memory_usage))
                self.temperature_history.append((timestamp, cpu_temp))
                self.frequency_history.append((timestamp, cpu_freq))
                
                time.sleep(interval_seconds)
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=monitor_loop)
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> HardwareMetrics:
        """Stop monitoring and return collected metrics."""
        self.monitoring_active = False
        self.monitor_thread.join()
        
        return HardwareMetrics(
            cpu_usage_history=self.cpu_usage_history,
            memory_usage_history=self.memory_usage_history,
            temperature_history=self.temperature_history,
            frequency_history=self.frequency_history
        )
    
    def _get_cpu_usage_per_core(self) -> List[float]:
        """Get CPU usage percentage for each core."""
        import psutil
        return psutil.cpu_percent(percpu=True)
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        import psutil
        return psutil.virtual_memory().used
    
    def _get_cpu_temperature(self) -> float:
        """Get CPU temperature in Celsius."""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_millidegrees = int(f.read().strip())
                return temp_millidegrees / 1000.0
        except:
            return 0.0
    
    def _get_cpu_frequency(self) -> int:
        """Get current CPU frequency in MHz."""
        try:
            with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq', 'r') as f:
                freq_khz = int(f.read().strip())
                return freq_khz // 1000
        except:
            return 0

@dataclass
class HardwareMetrics:
    """Hardware metrics collected during testing."""
    cpu_usage_history: List[Tuple[float, List[float]]]
    memory_usage_history: List[Tuple[float, int]]
    temperature_history: List[Tuple[float, float]]
    frequency_history: List[Tuple[float, int]]
    
    def get_average_cpu_usage(self) -> List[float]:
        """Get average CPU usage per core."""
        if not self.cpu_usage_history:
            return [0.0, 0.0, 0.0, 0.0]
        
        core_totals = [0.0, 0.0, 0.0, 0.0]
        count = len(self.cpu_usage_history)
        
        for _, core_usage in self.cpu_usage_history:
            for i, usage in enumerate(core_usage):
                core_totals[i] += usage
        
        return [total / count for total in core_totals]
    
    def get_peak_memory_usage(self) -> int:
        """Get peak memory usage in bytes."""
        if not self.memory_usage_history:
            return 0
        return max(usage for _, usage in self.memory_usage_history)
    
    def get_max_temperature(self) -> float:
        """Get maximum CPU temperature."""
        if not self.temperature_history:
            return 0.0
        return max(temp for _, temp in self.temperature_history)
    
    def check_thermal_throttling(self) -> bool:
        """Check if thermal throttling occurred."""
        return self.get_max_temperature() > 80.0
```

### 2. Animation Performance Test Suite

**Comprehensive performance validation:**
```python
class AnimationPerformanceTestSuite:
    """
    Comprehensive test suite for animation performance on Pi Zero 2W.
    Tests single-core, multi-core, and stress scenarios.
    """
    
    def __init__(self):
        self.test_environment = PiZero2WTestEnvironment()
        self.hardware_monitor = HardwareMonitor()
        self.results = []
    
    def run_full_test_suite(self) -> TestSuiteResults:
        """
        Run complete animation performance test suite.
        
        Returns:
            Comprehensive test results
        """
        print("Setting up Pi Zero 2W test environment...")
        if not self.test_environment.setup_test_environment():
            raise RuntimeError("Failed to setup test environment")
        
        print("Starting hardware monitoring...")
        self.hardware_monitor.start_monitoring()
        
        try:
            # Test 1: Single Animation Performance
            print("Running single animation performance test...")
            single_result = self._test_single_animation_performance()
            self.results.append(single_result)
            
            # Test 2: Multiple Animation Performance
            print("Running multiple animation performance test...")
            multiple_result = self._test_multiple_animation_performance()
            self.results.append(multiple_result)
            
            # Test 3: Multi-Core Frame Pre-computation
            print("Running multi-core pre-computation test...")
            multicore_result = self._test_multicore_precomputation()
            self.results.append(multicore_result)
            
            # Test 4: Coordination Performance
            print("Running coordination performance test...")
            coordination_result = self._test_coordination_performance()
            self.results.append(coordination_result)
            
            # Test 5: Stress Test
            print("Running stress test...")
            stress_result = self._test_stress_scenario()
            self.results.append(stress_result)
            
            # Test 6: Memory Pressure Test
            print("Running memory pressure test...")
            memory_result = self._test_memory_pressure()
            self.results.append(memory_result)
            
        finally:
            print("Stopping hardware monitoring...")
            hardware_metrics = self.hardware_monitor.stop_monitoring()
        
        return TestSuiteResults(
            test_results=self.results,
            hardware_metrics=hardware_metrics,
            environment_info=self._get_environment_info()
        )
    
    def _test_single_animation_performance(self) -> TestResult:
        """Test single animation performance."""
        engine = TickAnimationEngine(fps=60)
        widget = TickAnimatedTextWidget("Performance Test")
        widget.set_animation_engine(engine)
        
        # Create simple fade animation
        fade_def = create_tick_fade_animation(
            start_tick=0,
            duration_ticks=60,
            start_opacity=0.0,
            end_opacity=1.0,
            easing='ease_out'
        )
        
        widget.start_animation('opacity', fade_def)
        
        # Measure performance over 300 ticks (5 seconds at 60fps)
        tick_times = []
        start_time = time.perf_counter()
        
        for tick in range(300):
            tick_start = time.perf_counter_ns()
            
            engine.advance_tick()
            widget.update_animations(tick)
            
            tick_end = time.perf_counter_ns()
            tick_times.append(tick_end - tick_start)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        return TestResult(
            test_name="single_animation_performance",
            duration_seconds=total_time,
            tick_count=300,
            average_tick_time_ns=sum(tick_times) / len(tick_times),
            max_tick_time_ns=max(tick_times),
            min_tick_time_ns=min(tick_times),
            estimated_fps=300 / total_time,
            success=True
        )
    
    def _test_multiple_animation_performance(self) -> TestResult:
        """Test performance with multiple concurrent animations."""
        engine = TickAnimationEngine(fps=60)
        
        # Create 10 widgets with different animations
        widgets = []
        for i in range(10):
            widget = TickAnimatedTextWidget(f"Widget {i}")
            widget.set_animation_engine(engine)
            
            # Different animation types
            if i % 3 == 0:
                # Fade animation
                anim_def = create_tick_fade_animation(
                    start_tick=i * 5,
                    duration_ticks=60,
                    start_opacity=0.0,
                    end_opacity=1.0
                )
                widget.start_animation('opacity', anim_def)
            elif i % 3 == 1:
                # Slide animation
                anim_def = create_tick_slide_animation(
                    start_tick=i * 5,
                    duration_ticks=45,
                    start_position=(0, 0),
                    end_position=(100, 50)
                )
                widget.start_animation('position', anim_def)
            else:
                # Scale animation
                anim_def = create_tick_scale_animation(
                    start_tick=i * 5,
                    duration_ticks=30,
                    start_scale=0.5,
                    end_scale=1.0
                )
                widget.start_animation('scale', anim_def)
            
            widgets.append(widget)
        
        # Measure performance over 600 ticks (10 seconds)
        tick_times = []
        start_time = time.perf_counter()
        
        for tick in range(600):
            tick_start = time.perf_counter_ns()
            
            engine.advance_tick()
            for widget in widgets:
                widget.update_animations(tick)
            
            tick_end = time.perf_counter_ns()
            tick_times.append(tick_end - tick_start)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        return TestResult(
            test_name="multiple_animation_performance",
            duration_seconds=total_time,
            tick_count=600,
            average_tick_time_ns=sum(tick_times) / len(tick_times),
            max_tick_time_ns=max(tick_times),
            min_tick_time_ns=min(tick_times),
            estimated_fps=600 / total_time,
            animation_count=10,
            success=True
        )
    
    def _test_multicore_precomputation(self) -> TestResult:
        """Test multi-core frame pre-computation performance."""
        engine = TickAnimationEngine(fps=60)
        
        # Create complex animation scenario
        widgets = []
        for i in range(15):  # More widgets for multi-core test
            widget = TickAnimatedTextWidget(f"MultiCore Widget {i}")
            widget.set_animation_engine(engine)
            
            # Complex animation with coordination
            fade_def = create_tick_fade_animation(
                start_tick=i * 3,
                duration_ticks=90,
                start_opacity=0.0,
                end_opacity=1.0,
                easing='ease_in_out'
            )
            widget.start_animation('opacity', fade_def)
            widgets.append(widget)
        
        # Setup worker pool
        worker_pool = TickAnimationWorkerPool(num_workers=3)
        worker_pool.start_workers()
        
        try:
            # Start pre-computation
            precompute_start = time.perf_counter()
            worker_pool.compute_future_frames(engine, lookahead_ticks=180)  # 3 seconds
            
            # Measure performance with pre-computation
            tick_times = []
            cache_hits = 0
            cache_misses = 0
            
            start_time = time.perf_counter()
            
            for tick in range(360):  # 6 seconds
                tick_start = time.perf_counter_ns()
                
                engine.advance_tick()
                
                # Try to get pre-computed frame
                frame_state = worker_pool.get_frame(tick)
                
                if frame_state:
                    cache_hits += 1
                    # Apply pre-computed states
                    for widget in widgets:
                        for prop in widget.get_animation_properties():
                            if prop in frame_state:
                                widget.apply_animation_state(prop, frame_state[prop])
                else:
                    cache_misses += 1
                    # Fallback to real-time computation
                    for widget in widgets:
                        widget.update_animations(tick)
                
                tick_end = time.perf_counter_ns()
                tick_times.append(tick_end - tick_start)
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            # Get worker utilization
            worker_utilization = worker_pool.get_worker_utilization()
            cache_stats = worker_pool.get_cache_statistics()
            
        finally:
            worker_pool.stop_workers()
        
        return TestResult(
            test_name="multicore_precomputation",
            duration_seconds=total_time,
            tick_count=360,
            average_tick_time_ns=sum(tick_times) / len(tick_times),
            max_tick_time_ns=max(tick_times),
            min_tick_time_ns=min(tick_times),
            estimated_fps=360 / total_time,
            animation_count=15,
            cache_hit_rate=cache_hits / (cache_hits + cache_misses),
            worker_utilization=worker_utilization,
            success=True
        )
    
    def _test_coordination_performance(self) -> TestResult:
        """Test coordination primitive performance."""
        engine = TickAnimationEngine(fps=60)
        coordination_engine = TickCoordinationEngine()
        
        # Create complex coordination scenario
        widgets = []
        for i in range(8):
            widget = TickAnimatedTextWidget(f"Coord Widget {i}")
            widget.set_animation_engine(engine)
            widgets.append(widget)
        
        # Create coordination plan with multiple primitives
        plan = TickCoordinationPlan("performance_test")
        
        # Sync primitive
        sync = TickAnimationSync("sync_group", sync_tick=30)
        for i in range(4):
            sync.add_animation(f"widget_{i}_fade")
        plan.add_primitive(sync)
        
        # Barrier primitive
        barrier = TickAnimationBarrier("completion_barrier", barrier_tick=90)
        for i in range(4):
            barrier.add_waiting_animation(f"widget_{i}_fade")
        for i in range(4, 8):
            barrier.add_dependent_animation(f"widget_{i}_slide")
        plan.add_primitive(barrier)
        
        # Sequence primitive
        sequence = TickAnimationSequence("final_sequence")
        for i in range(4):
            sequence.add_step(120 + i * 10, f"widget_{i}_scale")
        plan.add_primitive(sequence)
        
        coordination_engine.execute_plan("performance_test", engine)
        
        # Measure coordination performance
        tick_times = []
        coordination_events = []
        
        start_time = time.perf_counter()
        
        for tick in range(300):  # 5 seconds
            tick_start = time.perf_counter_ns()
            
            engine.advance_tick()
            
            # Evaluate coordination
            events = coordination_engine.evaluate_at_tick(tick, engine)
            coordination_events.extend(events)
            
            # Update widgets
            for widget in widgets:
                widget.update_animations(tick)
            
            tick_end = time.perf_counter_ns()
            tick_times.append(tick_end - tick_start)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        return TestResult(
            test_name="coordination_performance",
            duration_seconds=total_time,
            tick_count=300,
            average_tick_time_ns=sum(tick_times) / len(tick_times),
            max_tick_time_ns=max(tick_times),
            min_tick_time_ns=min(tick_times),
            estimated_fps=300 / total_time,
            animation_count=8,
            coordination_events=len(coordination_events),
            success=True
        )
    
    def _test_stress_scenario(self) -> TestResult:
        """Test system under maximum stress."""
        engine = TickAnimationEngine(fps=60)
        
        # Create maximum load scenario
        widgets = []
        for i in range(25):  # 25 widgets with complex animations
            widget = TickAnimatedTextWidget(f"Stress Widget {i}")
            widget.set_animation_engine(engine)
            
            # Multiple concurrent animations per widget
            fade_def = create_tick_fade_animation(
                start_tick=i * 2,
                duration_ticks=120,
                start_opacity=0.0,
                end_opacity=1.0,
                easing='elastic'
            )
            widget.start_animation('opacity', fade_def)
            
            slide_def = create_tick_slide_animation(
                start_tick=i * 2 + 10,
                duration_ticks=100,
                start_position=(0, 0),
                end_position=(200, 150),
                easing='bounce'
            )
            widget.start_animation('position', slide_def)
            
            widgets.append(widget)
        
        # Setup multi-core with maximum workers
        worker_pool = TickAnimationWorkerPool(num_workers=3)
        worker_pool.start_workers()
        
        try:
            # Stress test for 10 seconds
            tick_times = []
            failed_ticks = 0
            
            start_time = time.perf_counter()
            
            for tick in range(600):  # 10 seconds
                tick_start = time.perf_counter_ns()
                
                try:
                    engine.advance_tick()
                    
                    # Try pre-computed frames first
                    frame_state = worker_pool.get_frame(tick)
                    
                    if frame_state:
                        for widget in widgets:
                            for prop in widget.get_animation_properties():
                                if prop in frame_state:
                                    widget.apply_animation_state(prop, frame_state[prop])
                    else:
                        # Real-time computation
                        for widget in widgets:
                            widget.update_animations(tick)
                    
                    tick_end = time.perf_counter_ns()
                    tick_time = tick_end - tick_start
                    tick_times.append(tick_time)
                    
                    # Check if tick took too long (>16.67ms for 60fps)
                    if tick_time > 16_670_000:  # 16.67ms in nanoseconds
                        failed_ticks += 1
                
                except Exception as e:
                    failed_ticks += 1
                    tick_times.append(50_000_000)  # 50ms penalty for failed tick
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
        finally:
            worker_pool.stop_workers()
        
        success = failed_ticks < 30  # Allow up to 5% failed ticks
        
        return TestResult(
            test_name="stress_scenario",
            duration_seconds=total_time,
            tick_count=600,
            average_tick_time_ns=sum(tick_times) / len(tick_times),
            max_tick_time_ns=max(tick_times),
            min_tick_time_ns=min(tick_times),
            estimated_fps=600 / total_time,
            animation_count=50,  # 25 widgets * 2 animations each
            failed_ticks=failed_ticks,
            success=success
        )
    
    def _test_memory_pressure(self) -> TestResult:
        """Test performance under memory pressure."""
        engine = TickAnimationEngine(fps=60)
        
        # Create scenario that approaches memory limits
        widgets = []
        memory_start = self._get_memory_usage()
        
        # Gradually add widgets until approaching memory limit
        widget_count = 0
        while self._get_memory_usage() - memory_start < 45 * 1024 * 1024:  # 45MB
            widget = TickAnimatedTextWidget(f"Memory Widget {widget_count}")
            widget.set_animation_engine(engine)
            
            # Create memory-intensive animation
            fade_def = create_tick_fade_animation(
                start_tick=widget_count * 2,
                duration_ticks=180,
                start_opacity=0.0,
                end_opacity=1.0,
                easing='ease_in_out'
            )
            widget.start_animation('opacity', fade_def)
            
            widgets.append(widget)
            widget_count += 1
            
            if widget_count > 100:  # Safety limit
                break
        
        memory_peak = self._get_memory_usage()
        memory_used = memory_peak - memory_start
        
        # Test performance under memory pressure
        tick_times = []
        start_time = time.perf_counter()
        
        for tick in range(300):  # 5 seconds
            tick_start = time.perf_counter_ns()
            
            engine.advance_tick()
            for widget in widgets:
                widget.update_animations(tick)
            
            tick_end = time.perf_counter_ns()
            tick_times.append(tick_end - tick_start)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        success = memory_used < 55 * 1024 * 1024  # Under 55MB limit
        
        return TestResult(
            test_name="memory_pressure",
            duration_seconds=total_time,
            tick_count=300,
            average_tick_time_ns=sum(tick_times) / len(tick_times),
            max_tick_time_ns=max(tick_times),
            min_tick_time_ns=min(tick_times),
            estimated_fps=300 / total_time,
            animation_count=widget_count,
            memory_used_mb=memory_used / (1024 * 1024),
            success=success
        )
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        import psutil
        return psutil.virtual_memory().used
    
    def _get_environment_info(self) -> Dict[str, Any]:
        """Get Pi Zero 2W environment information."""
        import platform
        import psutil
        
        return {
            'platform': platform.platform(),
            'processor': platform.processor(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'python_version': platform.python_version(),
            'cpu_freq': self._get_cpu_frequency(),
            'temperature': self._get_cpu_temperature()
        }

@dataclass
class TestResult:
    """Individual test result."""
    test_name: str
    duration_seconds: float
    tick_count: int
    average_tick_time_ns: float
    max_tick_time_ns: float
    min_tick_time_ns: float
    estimated_fps: float
    success: bool
    animation_count: int = 0
    cache_hit_rate: float = 0.0
    worker_utilization: Dict[int, float] = field(default_factory=dict)
    coordination_events: int = 0
    failed_ticks: int = 0
    memory_used_mb: float = 0.0

@dataclass
class TestSuiteResults:
    """Complete test suite results."""
    test_results: List[TestResult]
    hardware_metrics: HardwareMetrics
    environment_info: Dict[str, Any]
    
    def generate_report(self) -> str:
        """Generate comprehensive test report."""
        report = []
        report.append("# Pi Zero 2W Animation Performance Test Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Environment info
        report.append("## Environment Information")
        for key, value in self.environment_info.items():
            report.append(f"- **{key}**: {value}")
        report.append("")
        
        # Test results summary
        report.append("## Test Results Summary")
        report.append("| Test | Duration | FPS | Avg Tick Time | Success |")
        report.append("|------|----------|-----|---------------|---------|")
        
        for result in self.test_results:
            fps = f"{result.estimated_fps:.1f}"
            tick_time = f"{result.average_tick_time_ns / 1000:.2f} μs"
            success = "✅" if result.success else "❌"
            report.append(f"| {result.test_name} | {result.duration_seconds:.2f}s | {fps} | {tick_time} | {success} |")
        
        report.append("")
        
        # Hardware metrics
        report.append("## Hardware Metrics")
        avg_cpu = self.hardware_metrics.get_average_cpu_usage()
        report.append(f"- **Average CPU Usage**: Core 0: {avg_cpu[0]:.1f}%, Core 1: {avg_cpu[1]:.1f}%, Core 2: {avg_cpu[2]:.1f}%, Core 3: {avg_cpu[3]:.1f}%")
        report.append(f"- **Peak Memory Usage**: {self.hardware_metrics.get_peak_memory_usage() / (1024*1024):.1f} MB")
        report.append(f"- **Max Temperature**: {self.hardware_metrics.get_max_temperature():.1f}°C")
        report.append(f"- **Thermal Throttling**: {'Yes' if self.hardware_metrics.check_thermal_throttling() else 'No'}")
        report.append("")
        
        # Detailed results
        report.append("## Detailed Test Results")
        for result in self.test_results:
            report.append(f"### {result.test_name}")
            report.append(f"- **Duration**: {result.duration_seconds:.2f} seconds")
            report.append(f"- **Tick Count**: {result.tick_count}")
            report.append(f"- **Average Tick Time**: {result.average_tick_time_ns / 1000:.2f} μs")
            report.append(f"- **Max Tick Time**: {result.max_tick_time_ns / 1000:.2f} μs")
            report.append(f"- **Min Tick Time**: {result.min_tick_time_ns / 1000:.2f} μs")
            report.append(f"- **Estimated FPS**: {result.estimated_fps:.1f}")
            report.append(f"- **Animation Count**: {result.animation_count}")
            
            if result.cache_hit_rate > 0:
                report.append(f"- **Cache Hit Rate**: {result.cache_hit_rate * 100:.1f}%")
            
            if result.worker_utilization:
                util_str = ", ".join([f"Worker {i}: {util:.1f}%" for i, util in result.worker_utilization.items()])
                report.append(f"- **Worker Utilization**: {util_str}")
            
            if result.failed_ticks > 0:
                report.append(f"- **Failed Ticks**: {result.failed_ticks}")
            
            if result.memory_used_mb > 0:
                report.append(f"- **Memory Used**: {result.memory_used_mb:.1f} MB")
            
            report.append(f"- **Success**: {'✅ Pass' if result.success else '❌ Fail'}")
            report.append("")
        
        return "\n".join(report)
    
    def save_report(self, filename: str) -> None:
        """Save test report to file."""
        with open(filename, 'w') as f:
            f.write(self.generate_report())
```

### 3. Automated Test Execution

**Automated testing framework:**
```python
class AutomatedTestRunner:
    """
    Automated test runner for continuous integration and validation.
    Runs tests on Pi Zero 2W and reports results.
    """
    
    def __init__(self, config_file: str = "test_config.json"):
        self.config = self._load_config(config_file)
        self.test_suite = AnimationPerformanceTestSuite()
        self.notification_service = NotificationService()
    
    def run_automated_tests(self) -> bool:
        """
        Run automated test suite and handle results.
        
        Returns:
            True if all tests pass
        """
        try:
            print("Starting automated Pi Zero 2W animation tests...")
            
            # Pre-test validation
            if not self._validate_hardware():
                raise RuntimeError("Hardware validation failed")
            
            # Run test suite
            results = self.test_suite.run_full_test_suite()
            
            # Generate report
            report_filename = f"pi_zero_2w_test_report_{int(time.time())}.md"
            results.save_report(report_filename)
            
            # Analyze results
            success = self._analyze_results(results)
            
            # Send notifications
            if success:
                self.notification_service.send_success_notification(results)
            else:
                self.notification_service.send_failure_notification(results)
            
            # Upload results if configured
            if self.config.get('upload_results', False):
                self._upload_results(report_filename, results)
            
            return success
            
        except Exception as e:
            print(f"Automated test run failed: {e}")
            self.notification_service.send_error_notification(str(e))
            return False
    
    def _validate_hardware(self) -> bool:
        """Validate Pi Zero 2W hardware before testing."""
        # Check if running on Pi Zero 2W
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                if 'BCM2710' not in cpuinfo:
                    print("Warning: Not running on Pi Zero 2W")
                    return False
        except:
            return False
        
        # Check memory availability
        import psutil
        available_memory = psutil.virtual_memory().available
        if available_memory < 400 * 1024 * 1024:  # 400MB
            print(f"Insufficient memory: {available_memory / (1024*1024):.1f} MB available")
            return False
        
        # Check CPU frequency
        try:
            with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq', 'r') as f:
                freq_khz = int(f.read().strip())
                if freq_khz < 800000:  # 800MHz minimum
                    print(f"CPU frequency too low: {freq_khz / 1000} MHz")
                    return False
        except:
            pass
        
        return True
    
    def _analyze_results(self, results: TestSuiteResults) -> bool:
        """Analyze test results for pass/fail."""
        # Check individual test success
        failed_tests = [r for r in results.test_results if not r.success]
        if failed_tests:
            print(f"Failed tests: {[t.test_name for t in failed_tests]}")
            return False
        
        # Check performance targets
        for result in results.test_results:
            # FPS target: minimum 30fps, target 60fps
            if result.estimated_fps < 30:
                print(f"FPS too low in {result.test_name}: {result.estimated_fps:.1f}")
                return False
            
            # Tick time target: maximum 16.67ms for 60fps
            max_tick_time_ms = result.max_tick_time_ns / 1_000_000
            if max_tick_time_ms > 20:  # 20ms tolerance
                print(f"Tick time too high in {result.test_name}: {max_tick_time_ms:.2f}ms")
                return False
        
        # Check hardware metrics
        if results.hardware_metrics.check_thermal_throttling():
            print("Thermal throttling detected")
            return False
        
        peak_memory_mb = results.hardware_metrics.get_peak_memory_usage() / (1024 * 1024)
        if peak_memory_mb > 55:  # 55MB limit
            print(f"Memory usage too high: {peak_memory_mb:.1f} MB")
            return False
        
        return True
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load test configuration."""
        try:
            import json
            with open(config_file, 'r') as f:
                return json.load(f)
        except:
            return {
                'upload_results': False,
                'notification_webhook': None,
                'test_timeout': 600  # 10 minutes
            }
    
    def _upload_results(self, report_filename: str, results: TestSuiteResults) -> None:
        """Upload test results to configured endpoint."""
        # Implementation depends on upload service
        pass

class NotificationService:
    """Service for sending test result notifications."""
    
    def send_success_notification(self, results: TestSuiteResults) -> None:
        """Send success notification."""
        message = f"✅ Pi Zero 2W animation tests PASSED\n"
        message += f"All {len(results.test_results)} tests successful\n"
        message += f"Peak memory: {results.hardware_metrics.get_peak_memory_usage() / (1024*1024):.1f} MB\n"
        message += f"Max temperature: {results.hardware_metrics.get_max_temperature():.1f}°C"
        
        self._send_notification(message)
    
    def send_failure_notification(self, results: TestSuiteResults) -> None:
        """Send failure notification."""
        failed_tests = [r.test_name for r in results.test_results if not r.success]
        
        message = f"❌ Pi Zero 2W animation tests FAILED\n"
        message += f"Failed tests: {', '.join(failed_tests)}\n"
        message += f"Peak memory: {results.hardware_metrics.get_peak_memory_usage() / (1024*1024):.1f} MB\n"
        message += f"Max temperature: {results.hardware_metrics.get_max_temperature():.1f}°C"
        
        self._send_notification(message)
    
    def send_error_notification(self, error_message: str) -> None:
        """Send error notification."""
        message = f"🚨 Pi Zero 2W test execution ERROR\n{error_message}"
        self._send_notification(message)
    
    def _send_notification(self, message: str) -> None:
        """Send notification via configured method."""
        print(f"NOTIFICATION: {message}")
        # Add webhook, email, or other notification methods here
```

### 4. Continuous Integration Integration

**CI/CD pipeline integration:**
```bash
#!/bin/bash
# pi_zero_2w_test_runner.sh
# Automated test runner script for Pi Zero 2W

set -e

echo "Pi Zero 2W Animation Performance Test Runner"
echo "============================================"

# Check if running on Pi Zero 2W
if ! grep -q "BCM2710" /proc/cpuinfo; then
    echo "ERROR: Not running on Pi Zero 2W hardware"
    exit 1
fi

# Setup test environment
echo "Setting up test environment..."
sudo cpufreq-set -g performance  # Set performance governor
sudo sysctl vm.swappiness=10     # Reduce swap usage

# Install test dependencies
echo "Installing test dependencies..."
pip install -r test_requirements.txt

# Run hardware validation
echo "Validating hardware..."
python3 -c "
import psutil
import sys

# Check memory
mem = psutil.virtual_memory()
if mem.available < 400 * 1024 * 1024:
    print(f'Insufficient memory: {mem.available / (1024*1024):.1f} MB')
    sys.exit(1)

# Check CPU
if psutil.cpu_count() != 4:
    print(f'Expected 4 CPU cores, found {psutil.cpu_count()}')
    sys.exit(1)

print('Hardware validation passed')
"

# Run animation tests
echo "Running animation performance tests..."
python3 -m tests.pi_zero_2w.automated_test_runner

# Check test results
if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
    exit 0
else
    echo "❌ Tests failed!"
    exit 1
fi
```

---

## Test Execution Strategy

### 1. Development Testing
- **Local Development**: Run subset of tests during development
- **Pre-commit**: Quick performance validation
- **Feature Testing**: Full test suite for new features

### 2. Continuous Integration
- **Automated Runs**: Daily automated test execution
- **Performance Regression**: Detect performance degradation
- **Hardware Monitoring**: Track thermal and memory trends

### 3. Release Validation
- **Full Test Suite**: Complete performance validation
- **Stress Testing**: Extended duration tests
- **Memory Profiling**: Detailed memory usage analysis

### 4. Performance Benchmarking
- **Baseline Establishment**: Initial performance baselines
- **Regression Detection**: Automated performance comparison
- **Optimization Validation**: Verify performance improvements

---

## Success Criteria

### Performance Targets
- **60fps sustained**: All tests maintain 60fps average
- **Memory usage <55MB**: Stay within Pi Zero 2W constraints
- **Worker utilization >80%**: Efficient multi-core usage
- **Thermal stability**: No throttling during normal operation

### Quality Targets
- **Zero failed ticks**: All animation ticks complete successfully
- **Deterministic results**: Consistent performance across runs
- **Cache efficiency >70%**: Multi-core pre-computation effective
- **Coordination accuracy**: All coordination events trigger correctly

This testing architecture ensures the tick-based animation system delivers professional-grade performance on Pi Zero 2W hardware with comprehensive validation and monitoring. 