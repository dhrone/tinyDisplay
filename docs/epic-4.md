# Epic 4: Data Layer Integration & Performance Optimization

**Epic Number:** 4  
**Timeline:** Week 4 (5 days)  
**Status:** ✅ READY FOR IMPLEMENTATION  
**Dependencies:** Epic 3 Complete (Animation & Coordination System) ✅  
**Architecture:** Ring Buffer + SQLite + asteval Reactive Data Layer

---

## 🚀 EPIC 4 FOUNDATION READY

**Epic 3 Success:** Animation & Coordination System completed with **100% test success rate** (104/104 tests passing), providing:

- ✅ **Tick-Based Deterministic System**: Frame-perfect animation timing with multi-core safety
- ✅ **Advanced Coordination Primitives**: Sync, barrier, sequence, trigger coordination fully operational
- ✅ **Multi-Core Frame Pre-Computation**: Distributed rendering with >50% latency reduction capability
- ✅ **Timeline Management**: Complete debugging and visualization tools
- ✅ **Performance Proven**: 60fps targets achieved on Pi Zero 2W architecture

**Epic 4 Integration Points:** Epic 4 will integrate the proven animation system with the high-performance data layer to create a complete reactive framework.

**Key Integration Deliverables:**
- 🎯 **Ring Buffer ↔ Animation Integration**: Real-time data streams driving tick-based animations
- 🎯 **SQLite ↔ Timeline Persistence**: Persistent animation sequences and state management
- 🎯 **asteval ↔ Dynamic Animations**: Safe expression evaluation for data-driven animation parameters
- 🎯 **Widget ↔ Animation ↔ Data**: Complete reactive pipeline from data to display

---

## Epic Goal

Integrate the **high-performance data layer** (ring buffer + SQLite + asteval) with the completed animation system to create a **fully reactive framework** that enables real-time, data-driven animations with persistent state management and safe dynamic expression evaluation.

## Epic Value Statement

By completing this epic, we will have:
- **Reactive data-driven animations** that respond automatically to real-time data changes
- **High-performance data pipeline** using ring buffers for streaming data and SQLite for persistence
- **Safe dynamic expression evaluation** enabling user-defined animation parameters and conditions
- **Complete widget-animation-data integration** providing seamless reactive updates
- **Memory-optimized architecture** achieving <100MB footprint on Pi Zero 2W
- **Production-ready framework** with comprehensive performance monitoring and optimization

---

## Core Concept: Reactive Data-Driven Animation Pipeline

**Data Flow Architecture:**
```
Real-Time Data → Ring Buffer → Expression Evaluation → Coordination Primitives → Coordination Events
                      ↓                                           ↓                      ↓
                 Data Triggers                            Animation Triggers        Event History
                      ↓                                           ↓                      ↓
              Widget Updates ← Animation State Updates ← Timeline Management → SQLite Persistence
                      ↓                                                                  ↓
                   Display                                                    State Recovery
```

**Coordination Event Flow Detail:**
```
Data Change → Expression Condition → Coordination Primitive Evaluation → Event Generation
                                                    ↓
                                          CoordinationEngine.evaluate_coordination()
                                                    ↓
                                    [SYNC_TRIGGERED, BARRIER_RESOLVED, SEQUENCE_STARTED, 
                                     SEQUENCE_COMPLETED, TRIGGER_ACTIVATED] Events
                                                    ↓
                              Event History Storage + SQLite Persistence
                                                    ↓
                                    Timeline State Management + Widget Updates
```

**Key Benefits:**
1. **Real-Time Responsiveness**: Ring buffer enables sub-millisecond data ingestion
2. **Event-Driven Coordination**: Coordination events provide deterministic animation orchestration
3. **Persistent State**: SQLite provides reliable state management and coordination event history
4. **Safe Dynamics**: asteval enables user-defined expressions without security risks
5. **Reactive Architecture**: Coordination events enable loose coupling between data, animations, and widgets
6. **Complete Observability**: Full audit trail of coordination decisions and state changes
7. **Performance Optimized**: Memory-efficient architecture for embedded devices

---

## Stories Overview

### Story 4.1: Ring Buffer Data Integration
**Goal:** Integrate ring buffer system with tick-based animation triggers for real-time data-driven animations  
**Effort:** 2 days  
**Prerequisites:** Epic 3 complete ✅

### Story 4.2: SQLite State Management & Timeline Persistence  
**Goal:** Implement SQLite integration for persistent animation state and timeline management  
**Effort:** 1.5 days  
**Prerequisites:** Story 4.1 complete  

### Story 4.3: Dynamic Expression Evaluation & Animation Parameters
**Goal:** Integrate asteval for safe, dynamic animation parameters and conditional triggers  
**Effort:** 1.5 days  
**Prerequisites:** Story 4.2 complete  

---

## Detailed Stories

### Story 4.1: Ring Buffer Data Integration

**User Story:** As a developer, I need real-time data streams to automatically trigger and control animations so that my display responds immediately to changing data conditions with frame-perfect timing.

**Acceptance Criteria:**
1. **AC1:** Ring buffer system ingests real-time data streams with <1ms latency
2. **AC2:** Data changes automatically trigger animation updates through reactive binding
3. **AC3:** Animation parameters dynamically adjust based on current data values
4. **AC4:** Data-driven animation triggers integrate with coordination primitives
5. **AC5:** Memory-efficient data buffering maintains <20MB footprint
6. **AC6:** Performance monitoring tracks data ingestion and animation trigger rates
7. **AC7:** Graceful handling of data stream interruptions and reconnections

**Technical Requirements:**
- Integrate ring buffer with `TickAnimationEngine` for data-driven triggers
- Implement reactive data binding between data streams and animation parameters
- Create data-to-animation mapping system with configurable thresholds
- Optimize memory usage for continuous data streaming
- Add comprehensive monitoring and debugging tools
- Ensure thread-safe data access across animation and data threads

**Ring Buffer Animation Integration:**
```python
# Real-time data driving animations through coordination events
class DataDrivenAnimationEngine:
    def __init__(self, ring_buffer: RingBuffer, animation_engine: TickAnimationEngine,
                 coordination_engine: CoordinationEngine):
        self.ring_buffer = ring_buffer
        self.animation_engine = animation_engine
        self.coordination_engine = coordination_engine
        self.data_bindings: Dict[str, DataBinding] = {}
        self.data_triggers: Dict[str, DataTrigger] = {}
    
    def bind_data_to_animation(self, data_key: str, animation_id: str, 
                              mapping_function: Callable[[float], float]) -> None:
        """Bind data stream to animation parameter."""
        binding = DataBinding(
            data_key=data_key,
            animation_id=animation_id,
            mapping_function=mapping_function,
            last_value=None
        )
        self.data_bindings[data_key] = binding
    
    def add_data_trigger(self, data_key: str, threshold: float, 
                        coordination_primitive: CoordinationPrimitive) -> None:
        """Add data threshold trigger that creates coordination primitive."""
        trigger = DataTrigger(
            data_key=data_key,
            threshold=threshold,
            coordination_primitive=coordination_primitive,
            last_triggered=None
        )
        self.data_triggers[data_key] = trigger
    
    def process_data_updates(self, current_tick: int) -> List[CoordinationEvent]:
        """Process ring buffer data and generate coordination events."""
        coordination_events = []
        
        # Get latest data from ring buffer
        latest_data = self.ring_buffer.get_latest_batch(max_items=100)
        
        for data_point in latest_data:
            # Process data bindings (direct parameter updates)
            for data_key, binding in self.data_bindings.items():
                if data_key in data_point:
                    new_value = binding.mapping_function(data_point[data_key])
                    if new_value != binding.last_value:
                        # Direct animation parameter update
                        animation = self.animation_engine.get_animation(binding.animation_id)
                        if animation:
                            animation.update_parameter("value", new_value)
                        binding.last_value = new_value
            
            # Process data triggers (coordination primitive activation)
            for data_key, trigger in self.data_triggers.items():
                if data_key in data_point:
                    if self._evaluate_trigger_condition(data_point[data_key], trigger):
                        # Add coordination primitive to engine
                        self.coordination_engine.add_primitive(trigger.coordination_primitive)
                        trigger.last_triggered = current_tick
        
        # Evaluate all coordination primitives and collect events
        coordination_events = self.coordination_engine.evaluate_coordination(current_tick)
        
        return coordination_events

# Example usage: CPU usage driving coordinated animation response
def create_cpu_monitoring_system(data_engine: DataDrivenAnimationEngine):
    """Create CPU monitoring with coordinated animation responses."""
    
    # Direct binding: CPU usage drives progress bar value
    data_engine.bind_data_to_animation(
        data_key="cpu_usage",
        animation_id="cpu_progress_bar",
        mapping_function=lambda cpu: min(cpu / 100.0, 1.0)
    )
    
    # Coordination trigger: High CPU usage triggers alert sequence
    def create_alert_action(tick: int, engine: TickAnimationEngine, coord_engine: CoordinationEngine):
        """Action to execute when CPU alert triggers."""
        # Start alert flash animation
        engine.start_animation_at("alert_flash", tick)
        # Start warning sound animation
        engine.start_animation_at("warning_sound", tick)
        # Change progress bar color to red
        progress_animation = engine.get_animation("cpu_progress_bar")
        if progress_animation:
            progress_animation.update_parameter("color", "red")
    
    # Create coordination primitive for high CPU alert
    cpu_condition = DataThresholdCondition("cpu_usage", 80.0, "greater")
    cpu_alert_trigger = TickAnimationTrigger(
        coordination_id="cpu_alert_trigger",
        trigger_condition=cpu_condition,
        action=create_alert_action,
        auto_reset=True  # Allow repeated triggering
    )
    
    # Add trigger to data engine
    data_engine.add_data_trigger("cpu_usage", 80.0, cpu_alert_trigger)
    
    return cpu_alert_trigger

# Integration with coordination primitives for complex sequences
def create_system_health_coordination(data_engine: DataDrivenAnimationEngine):
    """Create complex system health monitoring with coordination."""
    
    # Multi-metric alert sequence
    def create_system_alert_sequence():
        """Create coordinated response to system health issues."""
        
        # Step 1: Sync all progress bars to show alert state
        alert_sync = create_sync_on_tick(
            coordination_id="health_alert_sync",
            animation_ids=["cpu_progress_bar", "memory_progress_bar", "disk_progress_bar"],
            trigger_tick=0  # Immediate
        )
        
        # Step 2: Sequence of escalating alerts
        alert_sequence = create_sequence_with_delays(
            coordination_id="escalating_alerts",
            animation_ids=["warning_flash", "urgent_flash", "critical_flash"],
            delays=[0, 30, 60],  # 0.5s, 1s intervals at 60fps
            start_tick=0
        )
        
        # Step 3: Barrier waiting for user acknowledgment
        alert_barrier = create_barrier_for_animations(
            coordination_id="alert_acknowledgment",
            animation_ids=["warning_flash", "urgent_flash", "critical_flash"]
        )
        
        return [alert_sync, alert_sequence, alert_barrier]
    
    # Create condition for system health alert
    system_health_condition = MultiMetricCondition({
        "cpu_usage": 80.0,
        "memory_usage": 85.0,
        "disk_usage": 90.0
    }, condition_type="any_exceeds")
    
    # Create trigger that activates coordination sequence
    def system_health_action(tick: int, engine: TickAnimationEngine, coord_engine: CoordinationEngine):
        """Execute system health alert coordination."""
        coordination_primitives = create_system_alert_sequence()
        for primitive in coordination_primitives:
            coord_engine.add_primitive(primitive)
    
    system_health_trigger = TickAnimationTrigger(
        coordination_id="system_health_trigger",
        trigger_condition=system_health_condition,
        action=system_health_action,
        auto_reset=False  # One-time alert until reset
    )
    
    return system_health_trigger
```

**Definition of Done:**
- [ ] Ring buffer integrates with animation engine for real-time data ingestion
- [ ] Data changes automatically trigger animation updates through reactive binding
- [ ] Animation parameters dynamically adjust based on current data values
- [ ] Data-driven triggers work with coordination primitives
- [ ] Memory usage remains <20MB for data buffering
- [ ] Performance monitoring tracks data and animation rates
- [ ] Graceful handling of data stream interruptions

---

### Story 4.2: SQLite State Management & Timeline Persistence

**User Story:** As a developer, I need persistent state management and timeline storage so that my animations can resume correctly after restarts and I can query complex animation history for analytics and debugging.

**Acceptance Criteria:**
1. **AC1:** SQLite database stores animation state, timeline events, and coordination history
2. **AC2:** Animation sequences persist across application restarts with state recovery
3. **AC3:** Complex queries enable animation analytics and performance analysis
4. **AC4:** Timeline debugging tools access historical data from SQLite storage
5. **AC5:** Database operations maintain <10ms latency for real-time performance
6. **AC6:** Automatic database cleanup prevents unlimited growth
7. **AC7:** Transaction support ensures atomic updates for complex state changes

**Technical Requirements:**
- Design SQLite schema for animation state, timeline events, and coordination data
- Implement state serialization/deserialization for animation engine components
- Create timeline persistence layer with efficient querying capabilities
- Add database connection pooling and transaction management
- Implement automatic cleanup policies for historical data
- Ensure database operations don't impact real-time animation performance

**SQLite Animation Schema:**
```python
# Database schema for animation persistence
class AnimationDatabase:
    def __init__(self, db_path: str = "animation_state.db"):
        self.db_path = db_path
        self.connection_pool = ConnectionPool(max_connections=5)
        self._create_schema()
    
    def _create_schema(self) -> None:
        """Create database schema for animation persistence."""
        schema_sql = """
        -- Animation definitions and state
        CREATE TABLE IF NOT EXISTS animations (
            animation_id TEXT PRIMARY KEY,
            definition_json TEXT NOT NULL,
            current_state_json TEXT,
            start_tick INTEGER,
            end_tick INTEGER,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Timeline events and coordination history
        CREATE TABLE IF NOT EXISTS timeline_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tick INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            coordination_id TEXT,
            animation_id TEXT,
            event_data_json TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_tick (tick),
            INDEX idx_event_type (event_type),
            INDEX idx_coordination_id (coordination_id)
        );
        
        -- Coordination plan state
        CREATE TABLE IF NOT EXISTS coordination_plans (
            plan_id TEXT PRIMARY KEY,
            plan_definition_json TEXT NOT NULL,
            current_state TEXT NOT NULL,
            start_tick INTEGER,
            completion_tick INTEGER,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Performance metrics and analytics
        CREATE TABLE IF NOT EXISTS performance_metrics (
            metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tick INTEGER NOT NULL,
            metric_type TEXT NOT NULL,
            metric_value REAL NOT NULL,
            metric_data_json TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_tick_type (tick, metric_type)
        );
        
        -- Data stream history for analytics
        CREATE TABLE IF NOT EXISTS data_history (
            data_id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_key TEXT NOT NULL,
            data_value REAL NOT NULL,
            tick INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_data_key_tick (data_key, tick)
        );
        """
        
        with self.connection_pool.get_connection() as conn:
            conn.executescript(schema_sql)
    
    def save_animation_state(self, animation_id: str, animation: TickAnimationDefinition,
                           current_state: TickAnimationState, current_tick: int) -> None:
        """Save animation state to database."""
        with self.connection_pool.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO animations 
                (animation_id, definition_json, current_state_json, start_tick, 
                 end_tick, is_active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                animation_id,
                animation.serialize(),
                current_state.serialize(),
                animation.start_tick,
                animation.start_tick + animation.duration_ticks,
                animation.is_active_at(current_tick)
            ))
    
    def load_animation_state(self, animation_id: str) -> Optional[Tuple[TickAnimationDefinition, TickAnimationState]]:
        """Load animation state from database."""
        with self.connection_pool.get_connection() as conn:
            result = conn.execute("""
                SELECT definition_json, current_state_json 
                FROM animations 
                WHERE animation_id = ? AND is_active = TRUE
            """, (animation_id,)).fetchone()
            
            if result:
                definition = TickAnimationDefinition.deserialize(result[0])
                state = TickAnimationState.deserialize(result[1])
                return definition, state
            return None
    
    def save_timeline_event(self, event: CoordinationEvent) -> None:
        """Save timeline event to database."""
        with self.connection_pool.get_connection() as conn:
            conn.execute("""
                INSERT INTO timeline_events 
                (tick, event_type, coordination_id, animation_id, event_data_json)
                VALUES (?, ?, ?, ?, ?)
            """, (
                event.tick,
                event.event_type.value,
                event.coordination_id,
                event.data.get('animation_id'),
                json.dumps(event.data)
            ))
    
    def query_timeline_history(self, start_tick: int, end_tick: int, 
                             event_types: List[str] = None) -> List[CoordinationEvent]:
        """Query timeline event history."""
        query = """
            SELECT tick, event_type, coordination_id, event_data_json
            FROM timeline_events 
            WHERE tick BETWEEN ? AND ?
        """
        params = [start_tick, end_tick]
        
        if event_types:
            placeholders = ','.join('?' * len(event_types))
            query += f" AND event_type IN ({placeholders})"
            params.extend(event_types)
        
        query += " ORDER BY tick, timestamp"
        
        with self.connection_pool.get_connection() as conn:
            results = conn.execute(query, params).fetchall()
            
            events = []
            for row in results:
                event = CoordinationEvent(
                    tick=row[0],
                    event_type=CoordinationEventType(row[1]),
                    coordination_id=row[2],
                    data=json.loads(row[3])
                )
                events.append(event)
            
            return events
    
    def cleanup_old_data(self, retention_days: int = 7) -> None:
        """Clean up old data to prevent database growth."""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        with self.connection_pool.get_connection() as conn:
            # Clean up old timeline events
            conn.execute("""
                DELETE FROM timeline_events 
                WHERE timestamp < ?
            """, (cutoff_date,))
            
            # Clean up old performance metrics
            conn.execute("""
                DELETE FROM performance_metrics 
                WHERE timestamp < ?
            """, (cutoff_date,))
            
            # Clean up old data history
            conn.execute("""
                DELETE FROM data_history 
                WHERE timestamp < ?
            """, (cutoff_date,))
            
            # Vacuum database to reclaim space
            conn.execute("VACUUM")

# Integration with timeline system
class PersistentTimeline(TickTimeline):
    def __init__(self, fps: int = 60, db_path: str = "animation_state.db"):
        super().__init__(fps)
        self.database = AnimationDatabase(db_path)
        self.auto_save_interval = 60  # Save state every 60 ticks (1 second at 60fps)
        self.last_save_tick = 0
    
    def evaluate_at_tick(self, tick: int, engine: TickAnimationEngine, 
                        coordination_engine: CoordinationEngine) -> List[CoordinationEvent]:
        """Evaluate timeline and persist events."""
        events = super().evaluate_at_tick(tick, engine, coordination_engine)
        
        # Save events to database
        for event in events:
            self.database.save_timeline_event(event)
        
        # Periodic state saving
        if tick - self.last_save_tick >= self.auto_save_interval:
            self._save_current_state(tick, engine)
            self.last_save_tick = tick
        
        return events
    
    def _save_current_state(self, tick: int, engine: TickAnimationEngine) -> None:
        """Save current animation state to database."""
        for animation_id, animation in engine.animations.items():
            current_state = animation.state_at(tick)
            self.database.save_animation_state(
                animation_id, animation, current_state, tick
            )
    
    def restore_state(self, engine: TickAnimationEngine) -> None:
        """Restore animation state from database."""
        # Load active animations
        with self.database.connection_pool.get_connection() as conn:
            results = conn.execute("""
                SELECT animation_id FROM animations WHERE is_active = TRUE
            """).fetchall()
            
            for row in results:
                animation_id = row[0]
                state_data = self.database.load_animation_state(animation_id)
                if state_data:
                    definition, current_state = state_data
                    engine.add_animation(animation_id, definition)
                    # Restore current state would require additional API
```

**Definition of Done:**
- [ ] SQLite database stores animation state, timeline events, and coordination history
- [ ] Animation sequences persist and recover correctly across restarts
- [ ] Complex queries enable animation analytics and performance analysis
- [ ] Timeline debugging tools access historical data from SQLite
- [ ] Database operations maintain <10ms latency
- [ ] Automatic cleanup prevents unlimited database growth
- [ ] Transaction support ensures atomic updates

---

### Story 4.3: Dynamic Expression Evaluation & Animation Parameters

**User Story:** As a developer, I need safe, dynamic expression evaluation for animation parameters so that I can create data-driven animations with user-defined conditions and calculations without security risks.

**Acceptance Criteria:**
1. **AC1:** asteval integration enables safe evaluation of user-defined expressions
2. **AC2:** Dynamic animation parameters update based on expression evaluation results
3. **AC3:** Conditional animation triggers use expression-based conditions
4. **AC4:** Expression evaluation integrates with data streams and animation coordination
5. **AC5:** Performance optimization through expression caching and pre-compilation
6. **AC6:** Comprehensive error handling for invalid expressions
7. **AC7:** Security validation prevents malicious code execution

**Technical Requirements:**
- Integrate asteval with animation parameter system
- Create expression-based animation parameter binding
- Implement conditional triggers using expression evaluation
- Add expression caching for performance optimization
- Ensure security through asteval sandboxing
- Provide clear error messages for invalid expressions

**Dynamic Expression Animation System:**
```python
# Safe expression evaluation for animations
class ExpressionAnimationEngine:
    def __init__(self, animation_engine: TickAnimationEngine, 
                 data_engine: DataDrivenAnimationEngine):
        self.animation_engine = animation_engine
        self.data_engine = data_engine
        self.evaluator = asteval.Interpreter(
            use_numpy=False,  # Keep memory footprint low
            max_time=0.01,    # 10ms timeout for expressions
            readonly_symbols=True
        )
        self.expression_cache: Dict[str, CompiledExpression] = {}
        self.parameter_bindings: Dict[str, ExpressionBinding] = {}
        
        # Add safe math functions
        self._setup_safe_functions()
    
    def _setup_safe_functions(self) -> None:
        """Add safe mathematical functions to evaluator."""
        import math
        safe_functions = {
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'sqrt': math.sqrt, 'abs': abs, 'min': min, 'max': max,
            'round': round, 'floor': math.floor, 'ceil': math.ceil,
            'log': math.log, 'exp': math.exp, 'pow': pow
        }
        
        for name, func in safe_functions.items():
            self.evaluator.symtable[name] = func
    
    def bind_expression_to_parameter(self, animation_id: str, parameter: str,
                                   expression: str, data_context: List[str]) -> None:
        """Bind expression to animation parameter."""
        # Compile and cache expression
        compiled_expr = self._compile_expression(expression, data_context)
        
        binding = ExpressionBinding(
            animation_id=animation_id,
            parameter=parameter,
            expression=expression,
            compiled_expression=compiled_expr,
            data_context=data_context,
            last_result=None
        )
        
        binding_key = f"{animation_id}.{parameter}"
        self.parameter_bindings[binding_key] = binding
    
    def _compile_expression(self, expression: str, data_context: List[str]) -> CompiledExpression:
        """Compile expression with validation."""
        # Check cache first
        cache_key = f"{expression}:{':'.join(sorted(data_context))}"
        if cache_key in self.expression_cache:
            return self.expression_cache[cache_key]
        
        # Validate expression syntax
        try:
            # Test compilation with dummy data
            test_context = {key: 0.0 for key in data_context}
            self.evaluator.symtable.update(test_context)
            result = self.evaluator.eval(expression)
            
            if self.evaluator.expr is None:
                raise ValueError(f"Invalid expression: {expression}")
            
            compiled_expr = CompiledExpression(
                expression=expression,
                ast_node=self.evaluator.expr,
                data_context=data_context,
                is_valid=True
            )
            
            # Cache compiled expression
            self.expression_cache[cache_key] = compiled_expr
            return compiled_expr
            
        except Exception as e:
            raise ValueError(f"Expression compilation failed: {expression} - {str(e)}")
    
    def evaluate_expressions(self, current_tick: int) -> List[ParameterUpdate]:
        """Evaluate all expression bindings and generate parameter updates."""
        updates = []
        
        # Get current data context
        latest_data = self.data_engine.ring_buffer.get_latest()
        if not latest_data:
            return updates
        
        for binding_key, binding in self.parameter_bindings.items():
            try:
                # Update evaluator context with current data
                context_data = {
                    key: latest_data.get(key, 0.0) 
                    for key in binding.data_context
                }
                context_data['tick'] = current_tick
                context_data['time'] = current_tick / 60.0  # Assume 60fps
                
                self.evaluator.symtable.update(context_data)
                
                # Evaluate expression
                result = self.evaluator.eval(binding.expression)
                
                # Check if result changed
                if result != binding.last_result:
                    updates.append(ParameterUpdate(
                        animation_id=binding.animation_id,
                        parameter=binding.parameter,
                        new_value=result,
                        tick=current_tick
                    ))
                    binding.last_result = result
                    
            except Exception as e:
                # Log error but continue processing other expressions
                print(f"Expression evaluation error for {binding_key}: {e}")
        
        return updates
    
    def create_expression_trigger(self, trigger_id: str, condition_expression: str,
                                data_context: List[str], triggered_animations: List[str]) -> TickAnimationTrigger:
        """Create animation trigger based on expression condition."""
        
        # Compile condition expression
        compiled_condition = self._compile_expression(condition_expression, data_context)
        
        def expression_condition(tick: int, engine: TickAnimationEngine) -> bool:
            try:
                # Get current data
                latest_data = self.data_engine.ring_buffer.get_latest()
                if not latest_data:
                    return False
                
                # Update context
                context_data = {
                    key: latest_data.get(key, 0.0) 
                    for key in data_context
                }
                context_data['tick'] = tick
                context_data['time'] = tick / 60.0
                
                self.evaluator.symtable.update(context_data)
                
                # Evaluate condition
                result = self.evaluator.eval(condition_expression)
                return bool(result)
                
            except Exception:
                return False  # Safe default
        
        # Create trigger
        trigger = TickAnimationTrigger(trigger_id, expression_condition)
        for animation_id in triggered_animations:
            trigger.add_triggered_animation(animation_id)
        
        return trigger

# Example usage: Dynamic animation parameters
def create_dynamic_dashboard(expression_engine: ExpressionAnimationEngine):
    """Create dashboard with expression-driven animations."""
    
    # CPU usage drives progress bar color intensity
    expression_engine.bind_expression_to_parameter(
        animation_id="cpu_progress",
        parameter="color_intensity",
        expression="min(cpu_usage / 100.0, 1.0)",
        data_context=["cpu_usage"]
    )
    
    # Memory usage affects animation speed
    expression_engine.bind_expression_to_parameter(
        animation_id="memory_animation",
        parameter="speed_multiplier",
        expression="1.0 + (memory_usage / 100.0) * 2.0",  # 1x to 3x speed
        data_context=["memory_usage"]
    )
    
    # Complex condition for alert trigger
    alert_trigger = expression_engine.create_expression_trigger(
        trigger_id="system_alert",
        condition_expression="cpu_usage > 80 or memory_usage > 85 or (cpu_usage > 60 and memory_usage > 70)",
        data_context=["cpu_usage", "memory_usage"],
        triggered_animations=["alert_flash", "warning_sound"]
    )
    
    # Temperature-based color animation
    expression_engine.bind_expression_to_parameter(
        animation_id="temperature_display",
        parameter="color_hue",
        expression="max(0, min(240, 240 - (temperature - 20) * 6))",  # Blue to red gradient
        data_context=["temperature"]
    )
    
    # Network activity drives pulse animation
    expression_engine.bind_expression_to_parameter(
        animation_id="network_pulse",
        parameter="pulse_frequency",
        expression="0.5 + (network_bytes_per_sec / 1000000) * 2.0",  # 0.5Hz to 2.5Hz
        data_context=["network_bytes_per_sec"]
    )
    
    return alert_trigger

# Integration with coordination system
class ExpressionCoordinationPlan(CoordinationPlan):
    def __init__(self, plan_id: str, expression_engine: ExpressionAnimationEngine):
        super().__init__(plan_id)
        self.expression_engine = expression_engine
    
    def evaluate_at(self, tick: int, engine: TickAnimationEngine, 
                   coordination_engine: CoordinationEngine) -> List[CoordinationEvent]:
        """Evaluate plan with expression parameter updates."""
        
        # First, update animation parameters based on expressions
        parameter_updates = self.expression_engine.evaluate_expressions(tick)
        
        # Apply parameter updates to animations
        for update in parameter_updates:
            animation = engine.get_animation(update.animation_id)
            if animation:
                animation.update_parameter(update.parameter, update.new_value)
        
        # Then evaluate coordination primitives
        return super().evaluate_at(tick, engine, coordination_engine)
```

**Definition of Done:**
- [ ] asteval integration enables safe evaluation of user-defined expressions
- [ ] Dynamic animation parameters update based on expression results
- [ ] Conditional animation triggers use expression-based conditions
- [ ] Expression evaluation integrates with data streams and coordination
- [ ] Performance optimization through expression caching
- [ ] Comprehensive error handling for invalid expressions
- [ ] Security validation prevents malicious code execution

---

## Performance Targets

### Primary Targets
- **60fps sustained performance** on Raspberry Pi Zero 2W with full data integration
- **<100MB total memory footprint** including data buffers, animation cache, and SQLite
- **<1ms data ingestion latency** from ring buffer to animation triggers
- **<10ms database operation latency** for state persistence and queries
- **<5ms expression evaluation time** for complex dynamic parameters

### Memory Budget Allocation
- **Ring Buffer System:** <15MB for real-time data streaming
- **SQLite Database:** <10MB for persistent state and history
- **Animation System:** <20MB for tick-based engine and coordination (proven in Epic 3)
- **Expression Engine:** <5MB for asteval and compiled expressions
- **Widget System:** <25MB for all widget types and canvas composition
- **Application Buffer:** <25MB remaining for user applications

### Performance Optimization Strategies
- **Expression Caching:** Pre-compile and cache frequently used expressions
- **Database Connection Pooling:** Minimize connection overhead
- **Batch Operations:** Group database writes for efficiency
- **Memory-Mapped Files:** Use SQLite memory-mapped I/O for performance
- **Ring Buffer Optimization:** Lock-free circular buffer implementation

---

## Risk Assessment

### Resolved Risks ✅
- **~~Animation System Complexity~~** - RESOLVED by Epic 3 completion (100% test success)
- **~~Multi-Core Synchronization~~** - RESOLVED by tick-based deterministic system
- **~~Performance Targets~~** - RESOLVED by proven 60fps capability

### Current Risks
- **Low Risk:** Data integration complexity (well-defined interfaces from Epic 3)
- **Medium Risk:** Memory optimization on Pi Zero 2W (requires careful monitoring)
- **Low Risk:** Expression evaluation performance (asteval is proven)

### Mitigation Strategies
- **Incremental Integration:** Build on proven Epic 3 foundation
- **Continuous Monitoring:** Real-time memory and performance tracking
- **Fallback Mechanisms:** Graceful degradation when resources are constrained
- **Comprehensive Testing:** Validate on actual Pi Zero 2W hardware

---

## Success Criteria

### Technical Success
- [ ] Ring buffer integration provides <1ms data-to-animation latency
- [ ] SQLite persistence maintains animation state across restarts
- [ ] Expression evaluation enables dynamic, data-driven animations
- [ ] Complete widget-animation-data reactive pipeline functional
- [ ] Memory usage remains <100MB on Pi Zero 2W
- [ ] 60fps performance maintained with full data integration

### Quality Success  
- [ ] Zero data loss during high-frequency streaming
- [ ] Reliable state recovery after unexpected shutdowns
- [ ] Safe expression evaluation with comprehensive error handling
- [ ] Comprehensive test coverage for all integration points
- [ ] Performance monitoring and optimization tools functional

### Integration Success
- [ ] Seamless integration with Epic 3 animation system
- [ ] Complete reactive data flow from ingestion to display
- [ ] Foundation ready for Epic 5 final integration and polish
- [ ] Production-ready framework with monitoring and debugging tools

---

## Dependencies & Prerequisites

### Completed Prerequisites ✅
- **Epic 3:** Animation & Coordination System (100% test success rate)
- **Epic 2:** Core Widget System (comprehensive widget foundation)
- **Epic 1:** Foundation & Migration Tools (ring buffer + SQLite + asteval architecture)

### External Dependencies
- **Hardware:** Raspberry Pi Zero 2W for performance validation
- **Database:** SQLite 3.8+ for advanced features
- **Security:** asteval 0.9.28+ for safe expression evaluation

---

## Implementation Notes

### Integration Strategy
1. **Phase 1:** Ring buffer data integration (Days 1-2)
2. **Phase 2:** SQLite persistence layer (Days 3-4)  
3. **Phase 3:** Expression evaluation system (Day 5)

### Key Technical Decisions
- **Ring Buffer Priority:** Real-time data ingestion takes precedence over persistence
- **SQLite Optimization:** Memory-mapped I/O and connection pooling for performance
- **Expression Security:** Strict asteval sandboxing with timeout limits
- **Memory Management:** Careful allocation tracking to stay within Pi Zero 2W limits

### Performance Monitoring Focus
- **Data Flow Latency:** Track end-to-end latency from data to display
- **Memory Usage Patterns:** Monitor allocation and garbage collection
- **Database Performance:** Track query times and connection utilization
- **Expression Evaluation:** Monitor compilation and execution times

This Epic 4 represents the **critical integration phase** that transforms the proven animation system into a complete, production-ready reactive framework capable of handling real-world embedded display applications.

**Epic Owner:** Technical Lead  
**Stakeholders:** Development Team, Performance Engineering  
**Success Metrics:** <100MB memory footprint, 60fps performance, <1ms data latency, reliable state persistence

---

## Supporting Documentation & Research

### Foundation Architecture (Epic 1-3 Complete)
- **Epic 3 Animation System:** 104/104 tests passing with tick-based deterministic framework
- **Epic 2 Widget System:** Complete reactive widget foundation with canvas composition
- **Epic 1 Data Architecture:** Ring buffer + SQLite + asteval foundation established

### Integration Specifications
- **Ring Buffer API:** High-performance circular buffer for real-time data streaming
- **SQLite Schema:** Optimized database design for animation state and timeline persistence  
- **asteval Integration:** Safe expression evaluation with performance optimization
- **Memory Management:** Comprehensive allocation tracking for Pi Zero 2W constraints

### Performance Validation
- **Pi Zero 2W Testing:** Hardware-specific validation on target embedded platform
- **Memory Profiling:** Detailed analysis of memory usage patterns and optimization
- **Latency Measurement:** End-to-end timing analysis from data ingestion to display
- **Stress Testing:** High-frequency data streaming with complex animation sequences

**Total Foundation:** 3 complete epics providing solid foundation for data integration with proven performance characteristics 