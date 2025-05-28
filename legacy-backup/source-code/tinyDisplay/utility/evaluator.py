# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Evaluator utility for tinyDisplay - provides dynamic value evaluation.
"""

import builtins
import logging
import math
import re
import time
import warnings
from collections import ChainMap
from pathlib import Path

from tinyDisplay.exceptions import (
    CompileError,
    EvaluationError,
    NoChangeToValue,
    ValidationError,
)
from tinyDisplay.utility.variable_dependencies import variable_registry

class evaluator:
    """
    Class to compile and evaluate values for a dataset.

    :param dataset: The dataset to be used when compiling and evaluating statements
    :type dataset: `tinyDisplay.utility.dataset`
    """

    def __init__(self, dataset, localDataset=None, debug=False):
        self._dataset = dataset
        self._localDataset = localDataset if localDataset is not None else {}
        self._debug = debug

        self._logger = logging.getLogger("tinyDisplay")

        # Holds the collection of statements that this evaluator manages
        self._statements = {}

    def eval_expression(self, expression):
        """
        Evaluate an expression directly without creating a dynamicValue.
        
        :param expression: The expression to evaluate
        :returns: The result of evaluating the expression
        """
        if not isinstance(expression, str):
            return expression
        
        # Create a namespace from dataset and local dataset
        namespace = ChainMap(self._localDataset, self._dataset)
        
        # Add dynamicValues to the namespace
        for name, dv in self._statements.items():
            if isinstance(name, str):
                namespace[name] = dv
        
        try:
            # Compile the expression
            code = compile(expression, "<string>", "eval")
            
            # Get builtins to use
            allowed_builtins = dynamicValue._allowedBuiltIns.copy()
            
            # Evaluate the expression
            result = eval(code, {"__builtins__": allowed_builtins}, namespace)
            return result
        except Exception as e:
            self._logger.error(f"Error evaluating expression '{expression}': {str(e)}")
            raise EvaluationError(f"Error evaluating '{expression}': {str(e)}")

    def compile(
        self,
        source=None,
        name=None,
        default=None,
        validator=None,
        dynamic=True,
        depends_on=None,
    ):
        """
        Compile and return a dynamic Value.

        :param source: The source to compile (if dynamic)
        :param name: The name to associate with the dynamieValue
        :type name: str
        :param default: A value to use if evaluation fails
        :param validator: Function used to test if evaluation produced a valid answer
        :type validator: `callable` that returns a bool
        :param dynamic: Enables dynamic evaluation
        :type dynamic: bool
        :param depends_on: Optional dynamicValue or list of dynamicValues that this value depends on
        :returns: a new dynamicValue
        :rtype: `tinyDisplay.utility.evaluator.dynamicValue`
        """
        # create dynamic value
        # compile dynamic value
        # store dynamic value in _statements list
        ds = dynamicValue(
            name or id(source), self._dataset, self._localDataset, self._debug,
            source, default, validator, None, depends_on
        )
        ds.compile(source, default, validator, dynamic)
        self._statements[name or id(source)] = ds
        
        # Register variable dependencies
        if dynamic and isinstance(source, str):
            # Extract field dependencies from the source expression
            field_deps = variable_registry.parse_dependencies_from_expression(source)
            for field_path in field_deps:
                variable_registry.register_variable_dependency(ds, field_path)
                
            # Also register dependencies on other dynamic values
            # Look for potential dynamic value names in the expression
            for dv_name, dv in self._statements.items():
                if isinstance(dv_name, str) and dv_name in source and dv is not ds:
                    variable_registry.register_variable_to_variable_dependency(ds, dv)
                    self._logger.debug(f"Registered dependency: {ds.name} depends on {dv.name}")
        
        # Register explicit dependencies on other dynamic values
        if depends_on:
            if not isinstance(depends_on, list):
                depends_on = [depends_on]
                
            for dep in depends_on:
                variable_registry.register_variable_to_variable_dependency(ds, dep)
        
        return ds

    def eval(self, name):
        """
        Evaluate dynamicValue with provide name.

        :param name: The name of the dynamicValue
        :type name: str
        :returns: the resulting value
        """
        # Using direct dictionary access for better performance
        statements = self._statements
        if name in statements:
            return statements[name].eval()
        if id(name) in statements:
            return statements[id(name)].eval()
        raise KeyError(f"{name} not found in evaluator")

    def evalAll(self):
        """
        Evaluate all of the statements contained within the evaluator.

        :returns: True if any of the values have changed
        :rtype: bool
        """
        changed = False
        # Direct dictionary access for better performance
        statements = self._statements.values()
        
        # Track which variables have been evaluated in this cycle
        evaluated = set()
        
        # Helper function to evaluate a variable and its dependencies
        def evaluate_with_dependencies(dv):
            if dv in evaluated:
                return  # Already evaluated in this cycle
                
            dv_name = getattr(dv, 'name', str(dv))
                
            # First, find all variables this one depends on and evaluate them
            dependencies = variable_registry.variable_to_fields.get(dv, set())
            
            # Check variable-to-variable dependencies
            var_dependencies = []
            for dep_var in variable_registry.variable_dependencies.keys():
                if dv in variable_registry.variable_dependencies[dep_var]:
                    # This variable depends on dep_var, so evaluate dep_var first
                    dep_name = getattr(dep_var, 'name', str(dep_var))
                    var_dependencies.append(dep_var)
                    if dep_var in self._statements.values():
                        evaluate_with_dependencies(dep_var)
            
            # Now evaluate this variable
            try:
                # Only evaluate if marked for update or static
                needs_update = hasattr(dv, "_needs_update") and dv._needs_update
                is_static = getattr(dv, "static", False)
                
                if needs_update or is_static:
                    prev_value = getattr(dv, "prevValue", "undefined")
                    dv.eval()
                    # Direct attribute access instead of property for better performance
                    if hasattr(dv, "_changed") and dv._changed:
                        nonlocal changed
                        changed = True
                        
                        # Notify any variables that depend on this one
                        if hasattr(dv, 'name'):
                            variable_registry.notify_field_change(dv.name)
                else:
                    pass
                
                # Mark as evaluated in this cycle
                evaluated.add(dv)
            except Exception:  # Continue to next variable on error
                pass
        
        # Process all statements
        for dv in statements:
            evaluate_with_dependencies(dv)
        
        return changed

    def addValidator(self, name, func):
        """Add validator to named dynamicValue.

        :param name: The name of the dynamicValue
        :type name: str
        :param func: A function to perform the validation
        :type func: callable
        :raises: KeyError if name not in evaluator

        ..note:
            func must accept a value to test and return a bool value that is
            True when the answer is valid and False when not.
        """
        self._statements[name].validator = func

    def changed(self, key):
        """
        Check if the evaluator statement named `key` has recently changed.

        :param key: The name of the statement
        :type key: str
        :returns: True if the value of the statement changed during the last
            evaluation of it.
        """
        return (
            self._statements[key].changed if key in self._statements else False
        )

    def __getitem__(self, key):
        # Try retrieving using both the key value and an id of the key value
        if id(key) not in self._statements:
            if hasattr(self._statements[key], "prevValue"):
                return self._statements[key].prevValue

        if hasattr(self._statements[id(key)], "prevValue"):
            return self._statements[id(key)]["prevValue"]

        # If no previous value recorded, return None
        return None

    def __len__(self):
        return len(self._statements)

    def _makeDict(self):
        return {
            k: v.prevValue if hasattr(v, "prevValue") else None
            for k, v in self._statements.items()
        }

    def items(self):
        """
        Implement items interface for evaluator class.

        :returns: iterable for all key value pairs in evaluator
        """
        return self._makeDict().items()

    def __iter__(self):
        d = self._makeDict()
        return d.__iter__()

    def __repr__(self):
        d = self._makeDict()
        return d.__repr__()


class dynamicValue:
    """
    Dynamic value that automatically updates when its data sources change.

    :param name: The name of the dynamicValue (optional)
    :type name: str
    :param dataset: The main dataset to use when calculating the dynamicValue
    :type dataset: `tinyDisplay.utility.dataset`
    :param localDataset: An additional dict or dataset to use when calculating
        the dynamicValue.  (optional)
    :type localDataset: dict or `tinyDisplay.utility.dataset`
    :param debug: Set debug mode
    :type debug: bool
    :param source: The source expression or value to evaluate
    :param default: The default value to use if evaluation fails
    :param validator: A validator function to check if the evaluated value is valid
    :param dependencies: Optional explicit list of data sources this depends on
    :param depends_on: Optional dynamicValue or list of dynamicValues that this value depends on

    .. attribute:: prevValue
       The previously evaluated value of this dynamic value

    ..note:
        Debug mode will cause any evaluation failures to result in exceptions
    """

    _allowedBuiltIns = {
        k: getattr(builtins, k)
        for k in [
            "abs",
            "bin",
            "bool",
            "bytes",
            "chr",
            "dict",
            "float",
            "hex",
            "int",
            "set",
            "len",
            "list",
            "max",
            "min",
            "oct",
            "ord",
            "round",
            "str",
            "sum",
            "tuple",
            "type",
        ]
    }
    for m in [i for i in dir(math) if i[0] != "_"]:
        _allowedBuiltIns[m] = getattr(math, m)

    _allowedBuiltIns["time"] = time
    # Add common time module functions directly
    _allowedBuiltIns["strftime"] = time.strftime
    _allowedBuiltIns["localtime"] = time.localtime
    _allowedBuiltIns["gmtime"] = time.gmtime
    _allowedBuiltIns["sleep"] = time.sleep
    _allowedBuiltIns["time_time"] = time.time  # Use time_time to avoid conflict with the time module itself
    
    _allowedBuiltIns["Path"] = Path

    _allowedMethods = [
        "__getitem__",
        "__contains__",
        "__len__",
        "get",
        "lower",
        "upper",
        "split",
        "capitalize",
        "title",
        "find",
        "strftime",
        "gmtime",
        "localtime",
        "timezone",
        "monotonic",
        "items",
        "keys",
        "values",
        "format",
    ]

    def __init__(
        self, name=None, dataset=None, localDataset=None, debug=False, 
        source=None, default=None, validator=None, dependencies=None, depends_on=None
    ):

        self.name = name
        self._dataset = dataset 
        self._localDataset = localDataset if localDataset is not None else {}
        self._debug = debug
        self._needs_update = True  # Flag to indicate if re-evaluation is needed
        self.source = source
        self.default = default
        self.validator = validator
        self.prevValue = None  # Store the previous value

        self._logger = logging.getLogger("tinyDisplay")

        # Used to support methods that will be called by eval but need to be
        # able to distinguish which object is calling it (e.g. changed)
        self._holdForIsChanged = {}
        self._changeID = id(self)

        # Defines allowable functions for compiled statements
        self._allowedBuiltIns = dynamicValue._allowedBuiltIns.copy()
        self._allowedBuiltIns["changed"] = self._isChanged
        
        # Import these here to avoid circular imports
        from tinyDisplay.utility.dataset import dataset as Dataset
        if isinstance(self._dataset, Dataset):
            self._allowedBuiltIns["history"] = self._dataset.history
            self._allowedBuiltIns["store"] = self.store
        
        # Add dependency tracking properties from DynamicValue
        self.dependencies = dependencies or self._infer_dependencies(source) if source else []
        self._changed = False
        
        # Register dependencies if source is provided
        if source is not None:
            self._register_field_dependencies()
        
        # Register explicit dynamic value dependencies
        if depends_on:
            self._register_dynamic_value_dependencies(depends_on)
    
    def _infer_dependencies(self, source):
        """Attempt to infer dependencies from the expression."""
        dependencies = []
        if isinstance(source, str):
            # Simple parsing to detect database references like db['key']
            matches = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\['[^']*'\]", source)
            dependencies.extend(matches)
        return dependencies
    
    def _register_field_dependencies(self):
        """Register field-level dependencies with the variable registry."""
        if isinstance(self.source, str):
            field_deps = variable_registry.parse_dependencies_from_expression(self.source)
            for field_path in field_deps:
                variable_registry.register_variable_dependency(self, field_path)
    
    def _register_dynamic_value_dependencies(self, depends_on):
        """Register dependencies on other dynamic values.
        
        Args:
            depends_on: List or single dynamicValue that this value depends on
        """
        # Convert single dependency to list
        if not isinstance(depends_on, list):
            depends_on = [depends_on]
            
        # Register each dependency
        for dep in depends_on:
            variable_registry.register_variable_to_variable_dependency(self, dep)

    def store(self, dbName=None, key=None, value=None, when=True):
        """
        Store new value to dataset.

        Updates a database with new data.  If in addition to the dbName, only a
        single value is provided it updates the entire database with the
        the provided value.  If two additional arguments are provided, it
        updates a specific key within the database

        :param dbName: the name of the database within the dataset to update
        :type dbName: str
        :param key: (optional) If updating a single key within the database,
            the value of that key
        :param value: The data to use for the update
        :param when: Store value if when is True else ignore
        :type when: bool
        :raises NoChangeToValue: To signal that store is not updating the
            current database value.
        """
        if when:
            if key is not None:
                self._dataset._cache(dbName, {key: value})
            else:
                self._dataset._cache(dbName, key)
        raise NoChangeToValue()

    def _isChanged(self, value):
        ret = (
            False
            if self._changeID not in self._holdForIsChanged
            else (
                True
                if self._holdForIsChanged.get(self._changeID) != value
                else False
            )
        )
        self._holdForIsChanged[self._changeID] = value
        return ret
        
    def mark_for_update(self):
        """Mark this variable as needing re-evaluation."""
        self._needs_update = True

    def compile(self, source=None, default=None, validator=None, dynamic=True):
        """
        Compile the value for later evaluation.

        :param source: The source to compile.
        :param default: A value to return if evaluation fails.
        :param validator: A function used to test if evaluation
            produced a valid answer.
        :type validator: `callable` that returns a bool
        :param dynamic: Enables dynamic evaluation of the source
        :type dynamic: bool
        :raises CompileError: If dynamci is True and an error occurs
            compiling the source.
        :raises RuntimeError: If source is None.
        """
        if not dynamic:
            self.source = source
            self.default = default
            self.validator = validator
            self.func = None
            self.static = True
            return

        if source is None:
            return

        # Define name (used in log output)
        name = (
            f"'{self.name}'" if self.name is not None else f"at 0x{id(source)}"
        )

        self.source = source
        self.default = default
        self.validator = validator
        self.func = None
        
        # Register field dependencies for tracking
        self._register_field_dependencies()

        if dynamic is True:
            if type(source) is str:
                warnings.simplefilter("error")
                try:
                    # Modify the source to use time_time instead of time.time for better compatibility
                    modified_source = source
                    if "time.time" in source:
                        modified_source = source.replace("time.time", "time_time")
                        
                    code = compile(modified_source, "<string>", "eval")
                    
                    # Check for undefined names
                    for n in code.co_names:
                        # Skip attribute access patterns (will be handled during eval)
                        if "." in n:
                            continue
                            
                        # Check if name is directly available
                        if (
                            n not in self._allowedBuiltIns
                            and n not in self._allowedMethods
                            and n not in self._dataset
                            and n not in self._localDataset
                        ):
                            raise CompileError(
                                f"While compiling {name} with '{source}': '{n}' is not defined"
                            )

                    # Use the modified source for evaluation
                    self.func = lambda v: eval(
                        code, {"__builtins__": self._allowedBuiltIns}, v
                    )
                except (ValueError, SyntaxError) as ex:
                    raise CompileError(
                        f"While compiling {name} with '{source}' a {ex.__class__.__name__} error occured: {ex}"
                    )
                finally:
                    warnings.simplefilter("default")
            elif callable(source):
                self.func = source
        else:
            # If not dynamic the source will be returned
            # whenever this dynamicValue is evaluated
            self.source = source

        # If input is not a function or a evaluatable string that contains
        # no variables (e.g. always returns the same value) or a syntax error
        # then no need to calculate the value more than once
        self.static = (
            True
            if not self.func
            or (
                hasattr(self.func, "co_names") and len(self.func.co_names) == 0
            )
            else False
        )

    def eval(self):
        """
        Evaluate the dynamic value.

        :returns: The result of evaluating the source
        :raises EvaluationError: If an error is encountered during evaluation
        :raises ValidationError: If validator fails.
        """
        dv_name = self.name if hasattr(self, 'name') else f"at 0x{id(self)}"
        
        # Check if re-evaluation is needed
        # if not self._needs_update and not self.static and hasattr(self, "prevValue"):
        #     return self.prevValue
            
        from tinyDisplay import globalVars
        
        try:
            # Save old value for change detection
            oldValue = getattr(self, "prevValue", None)

            # If not yet compiled, source will be returned
            try:
                if self.func is None:
                    newValue = self.source
                else:
                    # Create a namespace from the dataset and the locals
                    namespace = ChainMap(self._localDataset, self._dataset)
                    
                    # Add dynamicValues from the evaluator to the namespace
                    if hasattr(self, "_dataset") and hasattr(self._dataset, "_dV"):
                        # Add all dynamicValues from the evaluator to allow referencing them
                        statements = self._dataset._dV._statements
                        for name, dv in statements.items():
                            if isinstance(name, str) and dv is not self:  # Avoid self-references
                                namespace[name] = dv
                    
                    newValue = self.func(namespace)
            except (NameError, AttributeError, TypeError, KeyError) as ex:
                message = str(ex)
                # Deal with SyntaxError
                if hasattr(ex, "filename") and isinstance(
                    getattr(ex, "filename", None), str
                ):
                    message += f" at line {ex.lineno}"
                if self.default is not None:
                    newValue = self.default
                elif self._debug or globalVars.__DEBUG__:
                    raise EvaluationError(
                        f"Error [{ex.__class__.__name__}] evaluating {dv_name} with '{self.source}': {message}"
                    )
                else:
                    return oldValue
            except Exception as ex:
                message = str(ex)
                if hasattr(ex, "filename") and isinstance(
                    getattr(ex, "filename", None), str
                ):
                    message += f" at line {ex.lineno}"
                if self.default is not None:
                    newValue = self.default
                elif self._debug or globalVars.__DEBUG__:
                    raise EvaluationError(
                        f"Error [{ex.__class__.__name__}] evaluating {dv_name} with '{self.source}': {message}"
                    )
                else:
                    return oldValue

            # Validate if necessary
            try:
                if self.validator is not None and not self.validator(newValue):
                    if self.default is not None:
                        newValue = self.default
                    elif self._debug or globalVars.__DEBUG__:
                        raise ValidationError(
                            f"Validation failed for {dv_name}: {newValue}"
                        )
                    else:
                        return oldValue
            except AttributeError:
                # self.validator was None
                pass

            # Check if value has changed
            self._changed = newValue != oldValue

            # Store previous value (current becomes previous)
            self.prevValue = newValue

            # Mark as evaluated
            self._needs_update = False
            
            return newValue
        except Exception as ex:
            # Reset need for update flag
            self._needs_update = False
            
            # Set _changed flag
            self._changed = False
            
            # Re-raise the exception
            raise

    @property
    def changed(self):
        """
        Return True if value changed during most recent evaluation.

        :returns: True if value changed
        :rtype: bool
        :raises AttributeError: if not yet evaluated
        """
        if not hasattr(self, "_changed"):
            raise AttributeError("The changed attribute is only available after the dynamic value has been evaluated")
        return bool(self._changed)

    @property
    def needs_update(self):
        """Whether this variable needs to be re-evaluated."""
        return self._needs_update 

    @property
    def dynamic(self):
        """Returns whether this value is dynamic (inverse of static)."""
        return not getattr(self, 'static', False) 
        
    def __repr__(self):
        """String representation of this dynamic value."""
        if hasattr(self, 'source') and self.source is not None:
            return f"Dynamic({self.source})"
        return f"Dynamic({self.name})"

    def depends_on(self, *other_variables):
        """
        Explicitly register this variable as dependent on other dynamicValue instances.
        
        This method allows for explicit dependency registration after variable creation.
        When any of the dependency variables change, this variable will be marked for update.
        
        Args:
            *other_variables: One or more dynamicValue instances this value depends on
            
        Returns:
            self: The dynamicValue instance, for method chaining
            
        Example:
            ```python
            # Creating variables
            count = dynamicValue(name="count", source="db['count']")
            doubled = dynamicValue(name="doubled", source="count * 2")
            
            # Explicitly register dependency
            doubled.depends_on(count)
            ```
        """
        for var in other_variables:
            variable_registry.register_variable_to_variable_dependency(self, var)
        return self  # Enable method chaining 