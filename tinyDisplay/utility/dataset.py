# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Dataset utility for tinyDisplay - provides data storage with validation and history.
"""

import builtins
import logging
import time
from collections import deque

from tinyDisplay import globalVars
from tinyDisplay.exceptions import (
    CompileError,
    EvaluationError,
    NoChangeToValue,
    NoResult,
    RegistrationError,
    UpdateError,
    ValidationError,
)
from tinyDisplay.utility.dynamic import dependency_registry
from tinyDisplay.utility.variable_dependencies import variable_registry


class Table:
    """
    Represents a table within a dataset, providing a more Pythonic interface.
    
    This class allows for dictionary-style access to items within a table,
    while ensuring all updates go through the dataset's update mechanism
    to maintain history, validation, and dependency tracking.
    
    :param parent_dataset: The dataset containing this table
    :type parent_dataset: dataset
    :param name: The name of the table
    :type name: str
    """
    def __init__(self, parent_dataset, name):
        self._dataset = parent_dataset
        self._name = name
        
    def __getitem__(self, key):
        """
        Get a value from the table.
        
        :param key: The key to retrieve
        :type key: str
        :returns: The value associated with the key
        :raises KeyError: If the key doesn't exist in the table
        """
        return self._dataset[self._name][key]
        
    def __setitem__(self, key, value):
        """
        Set a value in the table.
        
        This method ensures the update goes through the dataset's update mechanism
        to maintain history, validation, and dependency tracking.
        
        :param key: The key to set
        :type key: str
        :param value: The value to set
        :type value: Any
        """
        self._dataset.update(self._name, {key: value})
        
    def __contains__(self, key):
        """
        Check if a key exists in the table.
        
        :param key: The key to check
        :type key: str
        :returns: True if the key exists, False otherwise
        :rtype: bool
        """
        return key in self._dataset[self._name]
        
    def __iter__(self):
        """
        Iterate over the keys in the table.
        
        :returns: An iterator over the keys
        """
        return iter(self._dataset[self._name])
        
    def __len__(self):
        """
        Get the number of items in the table.
        
        :returns: The number of items
        :rtype: int
        """
        return len(self._dataset[self._name])
        
    def __repr__(self):
        """
        Get a string representation of the table.
        
        :returns: A string representation
        :rtype: str
        """
        return self._dataset[self._name].__repr__()
        
    def get(self, key, default=None):
        """
        Get a value from the table, returning a default if the key doesn't exist.
        
        :param key: The key to retrieve
        :type key: str
        :param default: The value to return if the key doesn't exist
        :type default: Any
        :returns: The value associated with the key, or the default value
        """
        try:
            return self[key]
        except KeyError:
            return default
            
    def update(self, data):
        """
        Update multiple values in the table.
        
        :param data: A dictionary of key-value pairs to update
        :type data: dict
        """
        self._dataset.update(self._name, data)
        
    def keys(self):
        """
        Get the keys in the table.
        
        :returns: The keys
        :rtype: dict_keys
        """
        return self._dataset[self._name].keys()
        
    def values(self):
        """
        Get the values in the table.
        
        :returns: The values
        :rtype: dict_values
        """
        return self._dataset[self._name].values()
        
    def items(self):
        """
        Get the key-value pairs in the table.
        
        :returns: The key-value pairs
        :rtype: dict_items
        """
        return self._dataset[self._name].items()


class dataset:
    """
    Class to manage data that tinyDisplay will use to render widgets and test conditions.

    :param dataset: Dataset that will be used to initialize this dataset (optional)
    :type dataset: `tinyDisplay.utility.dataset`
    :param data: Dictionary that will be used to initialize this dataset (optional)
    :type data: dict
    :param suppressErrors: Determines whether common errors are suppressed
        during any evaluations
    :type suppressErrors: bool
    :param returnOnError: The value to return when an error occurs during evaluation
        suppressErrors is True.
    :type returnOnError: object
    :param historySize: The number of historical versions of each database to
        retain
    :type historySize: int
    :param lookBack: The number of versions back that the `history` method can retrieve
    :type lookBack: int
    :raises RuntimeError: if both a dataset and a data argument are provided
    """

    def __init__(
        self,
        dataset=None,
        historySize=100,
        lookBack=10,
    ):

        self._logger = logging.getLogger("tinyDisplay")
        dataset = dataset if dataset is not None else {}
        for tk in (
            (False, i) if type(i) is not str else (True, i)
            for i in dataset.keys()
        ):
            if not tk[0]:
                raise ValueError(
                    f"All datasets within a database must use strings as names.  This dataset has a database named {tk[1]}"
                )

        # Set the number updates that the dataset will store
        self._historySize = int(historySize)
        if self._historySize < 1:
            raise ValueError(
                f'Requested history size "{self._historySize}" is too small.  It must be at least one.'
            )

        # Set the number of updates back that you can request from the history method
        self._lookBack = int(lookBack)
        if self._lookBack < 1:
            raise ValueError(
                f'Requested lookBack size "{self._lookBack}" is too small.  It must be at least one.'
            )

        # Initialize empty dataset
        self._dataset = {}

        # Initialize validation / transformation configuration
        self._validset = {}

        # Initialize cache dataset to cache values stored during onUpdate processing
        self._cacheDB = {}

        # Start the clock
        self._startedAt = time.time()

        """ Initialize starting position.  This dictionary holds a version of the
            dataset that can be safely walked forward from through all of the updates
            in the ring buffer to get to current state """
        self._dsStart = {}

        # Initialize ring buffer which will hold each update
        self._ringBuffer = deque(maxlen=self._historySize)

        # Set self.update to initial update method
        self.update = self._update

        # Initialize prev dataset
        self._prevDS = {}
        
        # Dictionary to store timestamps of database updates
        self._timestamps = {}
        
        # Dictionary to store hash values of databases and datasets
        self._hashes = {}
        
        # Initialize Zobrist hashing tables
        self._init_zobrist_tables()

        # If data was provided during initialization, update the state of the dataset with it
        if dataset:
            for k in dataset:
                self.update(k, dataset[k])

        self._debug = globalVars.__DEBUG__
        self._localDB = {"_VAL_": None}
        
        # Import here to avoid circular imports
        from tinyDisplay.utility.evaluator import evaluator
        self._dV = evaluator(
            self, localDataset=self._localDB, debug=self._debug
        )

    def __getitem__(self, key):
        if key == "prev":
            return self.prev
        return self._dataset[key]

    def __getattr__(self, name):
        """
        Allow attribute-style access to tables in the dataset.
        
        This enables more Pythonic access to tables, e.g.:
        dataset.table_name["key"] = value
        
        :param name: The name of the table to access
        :type name: str
        :returns: A Table object representing the table
        :rtype: Table
        :raises AttributeError: if the table doesn't exist in the dataset
        """
        if name in self._dataset:
            return Table(self, name)
        raise AttributeError(f"Dataset has no table named '{name}'")

    def __iter__(self):
        self._dataset["prev"] = self.prev
        return iter(self._dataset)

    def __len__(self):
        return len(self._dataset)

    def __repr__(self):
        return self._dataset.__repr__()

    def get(self, key, default=None):
        """
        Get database from dataset.

        :param key: The name of the database to retrieve from the dataset
        :type key: str
        :param default: The value to return if the database is not found
        :type default: object
        :returns: The database or the default value if the database is not found
        :rtype: dict or object
        """
        if key in self._dataset:
            return self._dataset[key]
        return default

    def _checkForReserved(self, dbName):
        if dbName in self.__class__.__dict__:
            raise NameError(
                f"{dbName} is a reserved name and cannot be used witin a dataset"
            )

    def keys(self):
        """
        Return current list of database values.

        :returns: A list of the current database names
        :rtype: list
        """
        return self._dataset.keys()

    def setDefaults(self):
        """
        Initialize dataset to its default values.

        If the default values for the datasets have been defined through calls
        to registerValidation, this method will initialize the dataset to those
        defaults
        """
        for db, data in self._validset.items():
            defaults = {
                k: v["default"]
                for k, v in data.items()
                if type(v) is dict and "default" in v
            }
            self.update(db, defaults)

    def setDemo(self):
        """
        Initialize dataset to its sample values.

        To make testing the use of a dataset easier, this method will initialize
        a sample version of the dataset as defined by previous calls to the
        registerValidation method
        """
        self.setDefaults()
        for db, data in self._validset.items():
            samples = {k: v["sample"] for k, v in data.items()}
            self.update(db, samples)

    @staticmethod
    def _getType(t):
        """
        Convert a type specification to a Python type object.
        
        Args:
            t: Type specification, which can be:
               - A Python type object (int, str, etc.)
               - A string name of a type ('int', 'str', etc.)
               - None (which returns type(None))
               
        Returns:
            A Python type object
            
        Raises:
            TypeError: If the type specification is invalid
        """
        # Handle None type
        if t is None:
            return type(None)
            
        # Already a Python type
        if isinstance(t, type):
            return t
            
        # String representation of a type
        if isinstance(t, str):
            try:
                return {
                    "int": int,
                    "float": float,
                    "complex": complex,
                    "str": str,
                    "bool": bool,
                    "dict": dict,
                    "list": list,
                    "tuple": tuple,
                    "range": range,
                    "set": set,
                    "frozenset": frozenset,
                    "bytes": bytes,
                    "bytearray": bytearray,
                    "none": type(None),
                    "nonetype": type(None),
                }[t.lower()]
            except KeyError:
                raise TypeError(f"{t} is not a recognized type name")
                
        # Invalid type specification
        raise TypeError(f"Cannot convert {type(t).__name__} to a type object")


    @staticmethod
    def _getDefaultForType(t):
        return {
            int: 0,
            float: 0.0,
            complex: complex(),
            str: "",
            bool: False,
            dict: {},
            list: [],
            range: (0),
            set: set(),
        }[t]

    def _registerType(self, type_spec, default, sample, cfg):
        """
        Register type information for validation.
        
        This method processes the type specification and stores it in the configuration.
        It handles various forms of type specifications and infers types from defaults
        or samples if no explicit type is provided.
        
        Args:
            type_spec: Type specification, which can be:
                - A Python type object (int, str, etc.)
                - A string name of a type ('int', 'str', etc.)
                - A comma-separated string of type names ('int,float,str')
                - A list of type objects or strings ([int, float, str])
            default: Default value for the field
            sample: Sample value for the field
            cfg: Configuration dictionary to update
            
        Returns:
            None
        """
        # Use existing default/sample if not provided
        default = default if default is not None else cfg.get("default")
        sample = sample if sample is not None else cfg.get("sample")

        # Process type specification if provided
        if type_spec is not None:
            # Handle string type specifications (comma-separated list of types)
            if isinstance(type_spec, str):
                type_list = []
                for type_name in type_spec.split(","):
                    type_list.append(self._getType(type_name.strip()))
                cfg["type"] = type_list
                
            # Handle list of types
            elif isinstance(type_spec, list) or isinstance(type_spec, tuple):
                type_list = []
                for t in type_spec:
                    type_list.append(self._getType(t))
                cfg["type"] = type_list
                
            # Handle single type object or name
            else:
                cfg["type"] = [self._getType(type_spec)]
                
        # If type already defined in config, keep it
        elif "type" in cfg:
            return
            
        # Infer type from default value
        elif default is not None:
            cfg["type"] = [builtins.type(default)]
            
        # Infer type from sample value
        elif sample is not None:
            cfg["type"] = [builtins.type(sample)]
            
        # Use string as default type if nothing else specified
        else:
            cfg["type"] = [str]
            
        # Log the registered types for debugging
        type_names = [t.__name__ for t in cfg["type"]]
        self._logger.debug(f"Registered types: {', '.join(type_names)}")


    def _registerDefault(self, default, sample, cfg):
        # Register default value for variable.
        type = cfg["type"][0]
        default = default if default is not None else cfg.get("default")
        sample = sample if sample is not None else cfg.get("sample")

        if default is not None:
            cfg["default"] = default
        elif "default" in cfg:
            return
        elif sample is not None:
            cfg["default"] = self._getDefaultForType(builtins.type(sample))
        elif type is not None:
            cfg["default"] = self._getDefaultForType(type)

    def _registerSample(self, sample, default, cfg):
        # Register sample value for variable.
        default = default if default is not None else cfg.get("default")

        if sample is not None:
            cfg["sample"] = sample
        elif "sample" in cfg:
            return
        elif default is not None:
            cfg["sample"] = default

    def _registerStatement(self, dbName, key, stmtType, stmt, cfg):
        """
        Register validation or update statements/callables.
        
        This method handles both string-based expressions (for DSL compatibility)
        and callable functions/lambdas (for programmatic use).
        
        Args:
            dbName: Name of the database
            key: Key within the database, or None for database-level statements
            stmtType: Type of statement ('validate' or 'onUpdate')
            stmt: The statement(s) to register, can be:
                - A string containing an evaluatable expression
                - A callable function/lambda
                - A list of strings or callables
            cfg: Configuration dictionary to update
            
        Returns:
            None
        """
        if stmt is None:
            return
            
        # Convert single statement to list for uniform handling
        stmt_list = [stmt] if not isinstance(stmt, list) else stmt
        
        # Store the original statements/callables
        cfg[stmtType] = stmt_list
        
        # For string expressions, compile them with the expression evaluator
        for i, statement in enumerate(stmt_list):
            # Generate a unique key for this statement
            stmt_key = (
                f"{dbName}.{key}.{stmtType}{i}"
                if key is not None
                else f"{dbName}.{stmtType}{i}"
            )
            
            # Only compile string expressions, callables are used directly
            if isinstance(statement, str):
                try:
                    self._dV.compile(statement, name=stmt_key, default=None)
                    self._logger.debug(f"Compiled {stmtType} expression: {statement}")
                except Exception as ex:
                    self._logger.error(f"Failed to compile {stmtType} expression '{statement}': {ex}")
                    raise
            elif callable(statement):
                self._logger.debug(f"Registered {stmtType} callable: {statement.__name__ if hasattr(statement, '__name__') else 'lambda'}")
            else:
                raise TypeError(f"Statement must be a string or callable, got {type(statement).__name__}")


    def registerValidation(
        self,
        dbName=None,
        key=None,
        type=None,
        onUpdate=None,
        default=None,
        sample=None,
        validate=None,
    ):
        """
        Add validation data for a database or data element within a database.

        This method registers validation rules, type constraints, default values, and update
        handlers for a database or a specific key within a database. It supports both string-based
        expressions (for DSL compatibility) and callable functions/lambdas (for programmatic use).

        Args:
            dbName (str): The name of the database to register validation for.
            key (str, optional): The specific key within the database to validate. If not provided,
                the validation applies to the entire database.
            type (str, type, list, optional): Type constraint for the data element. Can be:
                - A string containing a valid type name ('int', 'float', 'str', etc.)
                - A Python type object (int, float, str, etc.)
                - A list of types to allow multiple types
                If provided, incoming data will be type-checked and conversion will be attempted if needed.
            onUpdate (str, callable, list, optional): Action to perform when data is updated. Can be:
                - A string containing an evaluatable expression
                - A callable function/lambda that processes the value
                - A list of strings or callables to execute in sequence
                The expression/function has access to the value via the '_VAL_' variable.
            default (any, optional): Default value for the data element. Used during initialization
                and when the element is missing or fails validation during an update.
            sample (any, optional): Sample value for testing. The `setDemo` method will update
                the dataset with these sample values.
            validate (str, callable, list, optional): Validation rule(s) for the data element. Can be:
                - A string containing an evaluatable expression that returns True/False
                - A callable function/lambda that returns True/False
                - A list of strings or callables to execute in sequence
                Each validation must return True for valid data or False for invalid data.

        Raises:
            RegistrationError: If registration fails due to invalid parameters or configuration.

        Examples:
            # String-based validation (DSL compatible)
            ds.registerValidation(
                dbName="users", 
                key="age", 
                type="int", 
                validate="_VAL_ >= 18", 
                default=18
            )

            # Lambda-based validation (programmatic use)
            ds.registerValidation(
                dbName="users", 
                key="email", 
                type=str, 
                validate=lambda val: '@' in val, 
                default="user@example.com"
            )
        """

        if dbName not in self._validset:
            self._validset[dbName] = {}

        if key is not None and key not in self._validset[dbName]:
            self._validset[dbName][key] = {}

        cfg = (
            self._validset[dbName][key]
            if key is not None
            else self._validset[dbName]
        )

        try:
            errType = "type"
            self._registerType(type, default, sample, cfg)
            errType = "default"
            self._registerDefault(default, sample, cfg)
            if key is not None:
                self.update(
                    dbName,
                    {key: self._validset[dbName][key].get("default", None)},
                )
            errType = "sample"
            self._registerSample(sample, default, cfg)
            errType = "validate"
            self._registerStatement(dbName, key, "validate", validate, cfg)
            errType = "onUpdate"
            self._registerStatement(dbName, key, "onUpdate", onUpdate, cfg)
        except Exception as ex:
            raise RegistrationError(
                f"{dbName}[{key}] {errType} failed: {ex.__class__.__name__}: {ex}"
            )

    def registerSchema(self, dbName, schema):
        """
        Register a schema for a database, defining the structure and validation rules for all fields.
        
        A schema is a dictionary that defines the expected structure of a database, including:
        - Field names and their expected types
        - Validation rules for each field
        - Default values
        - Required fields
        - Nested schemas for complex structures
        
        Args:
            dbName: Name of the database to register the schema for
            schema: Dictionary defining the schema structure
                    Each key in the schema corresponds to a field in the database
                    Each value is a dictionary with the following optional keys:
                    - type: Type constraint(s) for the field
                    - required: Boolean indicating if the field is required
                    - validate: Expression(s) or callable(s) to validate the field
                    - default: Default value to use if validation fails
                    - onUpdate: Expression(s) or callable(s) to execute when the field is updated
                    - schema: Nested schema for complex structures (dictionaries)
                    - items: Schema for array items (for lists/arrays)
            
        Returns:
            None
            
        Examples:
            # Simple schema
            ds.registerSchema("users", {
                "name": {"type": str, "required": True},
                "age": {"type": int, "validate": "_VAL_ >= 18", "default": 18},
                "email": {"type": str, "validate": lambda val: '@' in val}
            })
            
            # Schema with nested structure
            ds.registerSchema("products", {
                "name": {"type": str, "required": True},
                "price": {"type": float, "validate": "_VAL_ > 0"},
                "attributes": {
                    "type": dict,
                    "schema": {
                        "color": {"type": str},
                        "size": {"type": str, "validate": lambda val: val in ['S', 'M', 'L', 'XL']}
                    }
                },
                "tags": {
                    "type": list,
                    "items": {"type": str}
                }
            })
        """
        # Create validset entry for database if it doesn't exist
        if dbName not in self._validset:
            self._validset[dbName] = {}
            
        # Create database entry if it doesn't exist
        if dbName not in self._dataset:
            self._dataset[dbName] = {}
            self.__dict__[dbName] = self._dataset[dbName]
            
        # Initialize _prevDS for this database if it doesn't exist
        if dbName not in self._prevDS:
            self._prevDS[dbName] = deque(maxlen=self._lookBack)
            self._prevDS[dbName].append({})
            
        # Store the schema in the validset
        self._validset[dbName]["_schema"] = schema
        
        # Collect initial values from the schema (defaults and required fields)
        initial_values = {}
        
        # First pass: collect all default values
        for field_name, field_schema in schema.items():
            if "default" in field_schema:
                initial_values[field_name] = field_schema["default"]
        
        # Second pass: collect required fields that don't have defaults
        for field_name, field_schema in schema.items():
            if field_schema.get("required", False) and field_name not in initial_values:
                # For required fields with no default, use an appropriate empty value based on type
                field_type = field_schema.get("type")
                if field_type is str or field_type == "str":
                    initial_values[field_name] = ""
                elif field_type is int or field_type == "int":
                    initial_values[field_name] = 0
                elif field_type is float or field_type == "float":
                    initial_values[field_name] = 0.0
                elif field_type is bool or field_type == "bool":
                    initial_values[field_name] = False
                elif field_type is list or field_type == "list":
                    initial_values[field_name] = []
                elif field_type is dict or field_type == "dict":
                    initial_values[field_name] = {}
                else:
                    # For unknown types, use None
                    initial_values[field_name] = None
    
        # Register validation for each field in the schema
        for field_name, field_schema in schema.items():
            # Skip default value initialization in _registerFieldSchema
            # since we'll apply defaults directly
            self._registerFieldSchema(dbName, field_name, field_schema, apply_defaults=False)
            
        # Apply initial values if any - use update to ensure proper validation and initialization
        if initial_values:
            self._logger.debug(f"Initializing {dbName} with values: {initial_values}")
            # Use the public update method to ensure proper validation and field setup
            # This ensures the values are properly set in the database
            self.update(dbName, initial_values)
            
    def _registerFieldSchema(self, dbName, field_path, field_schema, parent_path=None, apply_defaults=True):
        """
        Register validation for a field based on its schema definition.
        
        Args:
            dbName: Name of the database
            field_path: Path to the field (can be nested using dot notation)
            field_schema: Schema definition for the field
            parent_path: Parent path for nested fields
            apply_defaults: Whether to apply default values during registration
            
        Returns:
            None
        """
        # Build the full field path
        full_path = field_path if parent_path is None else f"{parent_path}.{field_path}"
        
        # Extract schema properties
        field_type = field_schema.get("type")
        required = field_schema.get("required", False)
        validate = field_schema.get("validate")
        default = field_schema.get("default") if apply_defaults else None
        on_update = field_schema.get("onUpdate")
        nested_schema = field_schema.get("schema")
        items_schema = field_schema.get("items")
        
        # Register validation for this field without applying defaults
        # (we'll handle defaults separately in registerSchema)
        if full_path not in self._validset[dbName]:
            self._validset[dbName][full_path] = {}
            
        # Register type constraint
        if field_type is not None:
            # Get the configuration for this field
            field_cfg = self._validset[dbName][full_path]
            # Register the type with the proper parameters
            self._registerType(field_type, default, None, field_cfg)
            
        # Register validation expression/callable
        if validate is not None:
            self._registerStatement(dbName, full_path, "validate", validate, self._validset[dbName][full_path])
            
        # Register update expression/callable
        if on_update is not None:
            self._registerStatement(dbName, full_path, "onUpdate", on_update, self._validset[dbName][full_path])
            
        # Register default value (but don't apply it if apply_defaults is False)
        if default is not None:
            self._validset[dbName][full_path]["default"] = default
        
        # If this field is required, add a required validation
        if required:
            # Add to the list of required fields for this database
            if "_required_fields" not in self._validset[dbName]:
                self._validset[dbName]["_required_fields"] = []
            self._validset[dbName]["_required_fields"].append(full_path)
        
        # If this field has a nested schema, register validation for each nested field
        if nested_schema and (field_type is dict or field_type == "dict"):
            for nested_field, nested_field_schema in nested_schema.items():
                self._registerFieldSchema(dbName, nested_field, nested_field_schema, full_path, apply_defaults)
                
        # If this field is an array with item schema, register the item schema
        if items_schema and (field_type is list or field_type == "list"):
            self._validset[dbName][full_path]["_items_schema"] = items_schema
            
    def _validateSchema(self, dbName, update, schema):
        """
        Validate an update against a schema.
        
        Args:
            dbName: Name of the database
            update: Dictionary of updates to validate
            schema: Schema to validate against
            
        Returns:
            Validated update dictionary with type conversions applied
            
        Raises:
            ValidationError: If validation fails and no default is available
        """
        self._logger.debug(f"Validating schema for {dbName}: {update}")
        
        # Ensure we have a valid update dictionary
        if update is None:
            self._logger.warning(f"Received None update for schema validation in {dbName}")
            return {}
            
        # Make a copy of the update to avoid modifying the original
        validated_update = update.copy()
        
        # Get the current state of the database to check for required fields
        current_db = self._dataset.get(dbName, {})
        
        # Check for required fields
        for field_name, field_schema in schema.items():
            if field_schema.get("required", False):
                # CASE 1: Required field is missing in both update and current database
                if field_name not in validated_update and field_name not in current_db:
                    # If a required field is missing and has a default, use the default
                    if "default" in field_schema:
                        validated_update[field_name] = field_schema["default"]
                        self._logger.debug(f"Using default value for required field {dbName}.{field_name}")
                    elif self._debug:
                        # In debug mode, raise an error for missing required fields
                        raise ValidationError(f"Required field '{field_name}' is missing in {dbName}")
                    else:
                        # Otherwise, log a warning
                        self._logger.warning(f"Required field '{field_name}' is missing in {dbName}")
                # CASE 2: Required field exists in current database but is missing from update
                # This prevents required fields from being removed during partial updates
                elif field_name not in validated_update and field_name in current_db:
                    # In debug mode, raise an error when required fields are omitted from updates
                    if self._debug:
                        raise ValidationError(f"Required field '{field_name}' is missing from update in debug mode")
                    # Otherwise, preserve the existing value for the required field
                    validated_update[field_name] = current_db[field_name]
                    self._logger.debug(f"Preserving required field {dbName}.{field_name} from current database")
                # CASE 3: Required field is in the update - normal validation will proceed
        
        # Validate each field in the update
        for field_name, value in list(validated_update.items()):
            # Skip fields not in the schema
            if field_name not in schema:
                continue
                
            field_schema = schema[field_name]
            
            # Validate field type
            if "type" in field_schema:
                try:
                    # Get the expected type(s)
                    field_type = field_schema["type"]
                    
                    # Handle multiple allowed types
                    if isinstance(field_type, (list, tuple)):
                        # Check if value is already of one of the allowed types
                        type_valid = False
                        for t in field_type:
                            expected_type = self._getType(t)
                            if isinstance(value, expected_type):
                                type_valid = True
                                break
                                
                        # If not valid, try to convert to one of the allowed types
                        if not type_valid:
                            for t in field_type:
                                try:
                                    expected_type = self._getType(t)
                                    validated_update[field_name] = expected_type(value)
                                    type_valid = True
                                    break
                                except (ValueError, TypeError):
                                    continue
                                    
                        # If still not valid, raise error
                        if not type_valid:
                            raise ValidationError(f"{dbName}.{field_name}: Value {value} is not of allowed types")
                    else:
                        # Single type validation
                        expected_type = self._getType(field_type)
                        if not isinstance(value, expected_type):
                            # Try to convert to the expected type
                            try:
                                validated_update[field_name] = expected_type(value)
                            except (ValueError, TypeError):
                                raise ValidationError(f"{dbName}.{field_name}: Value {value} is not of type {field_type}")
                except ValidationError as e:
                    # Type validation failed
                    if "default" in field_schema:
                        # Use default value
                        validated_update[field_name] = field_schema["default"]
                        self._logger.debug(f"Using default value for {dbName}.{field_name} after type validation failure")
                    elif self._debug:
                        # In debug mode, re-raise the error
                        raise
                    else:
                        # Remove the field from the update
                        del validated_update[field_name]
                        self._logger.warning(f"{e}")
                        continue
            
            # Update value reference after potential type conversion
            value = validated_update[field_name]
            
            # Validate field against validation rules
            if "validate" in field_schema:
                validate = field_schema["validate"]
                valid = False
                
                try:
                    # Store the value in the local database for evaluation
                    self._localDB["_VAL_"] = value
                    
                    # Handle different types of validation
                    if callable(validate):
                        # For callable validation, call it directly with the field value
                        self._logger.debug(f"Validating {dbName}.{field_name} with callable: value={value}")
                        valid = validate(value)
                    else:
                        # Evaluate the validation expression
                        self._logger.debug(f"Validating {dbName}.{field_name} with expression: {validate}, value={value}")
                        valid = self._dV.eval(f"{dbName}.{field_name}.validate0")
                    
                    # Handle validation result
                    if not valid:
                        raise ValidationError(f"{dbName}.{field_name}: Validation failed for value {value}")
                except Exception as e:
                    # Validation failed
                    if "default" in field_schema:
                        # Use default value
                        validated_update[field_name] = field_schema["default"]
                        self._logger.debug(f"Using default value for {dbName}.{field_name} after validation failure")
                    elif self._debug:
                        # In debug mode, re-raise the error
                        raise ValidationError(f"{dbName}.{field_name}: Validation error: {e}")
                    else:
                        # Remove the field from the update
                        del validated_update[field_name]
                        self._logger.warning(f"{dbName}.{field_name}: Validation failed: {e}")
                        continue
            
            # Handle nested schema for dictionaries
            if "schema" in field_schema and isinstance(value, dict):
                nested_schema = field_schema["schema"]
                try:
                    # Recursively validate the nested dictionary
                    validated_nested = self._validateSchema(f"{dbName}.{field_name}", value, nested_schema)
                    validated_update[field_name] = validated_nested
                except ValidationError as e:
                    # Nested validation failed
                    if "default" in field_schema:
                        # Use default value
                        validated_update[field_name] = field_schema["default"]
                        self._logger.debug(f"Using default value for {dbName}.{field_name} after nested validation failure")
                    elif self._debug:
                        # In debug mode, re-raise the error
                        raise
                    else:
                        # Remove the field from the update
                        del validated_update[field_name]
                        self._logger.warning(f"{dbName}.{field_name}: Nested schema validation failed: {e}")
                        continue
            
            # Handle array items validation
            if "items" in field_schema and isinstance(value, list):
                items_schema = field_schema["items"]
                validated_items = []
                
                # Validate each item in the array
                for i, item in enumerate(value):
                    try:
                        # For nested schema validation within arrays
                        if "schema" in items_schema and isinstance(item, dict):
                            # Check for required fields in nested schema
                            for nested_field, nested_schema_def in items_schema["schema"].items():
                                if nested_schema_def.get("required", False) and nested_field not in item:
                                    # Missing required field
                                    self._logger.warning(f"Required field '{nested_field}' is missing in {dbName}.{field_name}[{i}]")
                                    raise ValidationError(f"Required field '{nested_field}' is missing in {dbName}.{field_name}[{i}]")
                            
                            # Validate nested dictionary against its schema
                            validated_item = self._validateSchema(f"{dbName}.{field_name}[{i}]", item, items_schema["schema"])
                            validated_items.append(validated_item)
                            continue
                        
                        # Validate item type
                        if "type" in items_schema:
                            item_type = items_schema["type"]
                            expected_type = self._getType(item_type)
                            
                            if not isinstance(item, expected_type):
                                # Try to convert to the expected type
                                try:
                                    item = expected_type(item)
                                except (ValueError, TypeError):
                                    raise ValidationError(f"{dbName}.{field_name}[{i}]: Item is not of type {item_type}")
                        
                        # Validate item against validation rules
                        if "validate" in items_schema:
                            item_validate = items_schema["validate"]
                            item_valid = False
                            
                            # Store the value in the local database for evaluation
                            self._localDB["_VAL_"] = item
                            
                            if callable(item_validate):
                                # For callable validation, call it directly with the item value
                                item_valid = item_validate(item)
                            else:
                                # For string validation, create a temporary validation
                                temp_key = f"_temp_validate_{field_name}_{i}"
                                if temp_key not in self._validset[dbName]:
                                    self._validset[dbName][temp_key] = {}
                                self._validset[dbName][temp_key]["validate"] = [item_validate]
                                
                                try:
                                    # Evaluate the validation expression
                                    item_valid = self._dV.eval(f"{dbName}.{temp_key}.validate0")
                                finally:
                                    # Clean up the temporary validation
                                    if temp_key in self._validset[dbName]:
                                        del self._validset[dbName][temp_key]
                            
                            # Handle validation result
                            if not item_valid:
                                raise ValidationError(f"{dbName}.{field_name}[{i}]: Item validation failed")
                        
                        # Item passed all validations, add it to the result
                        validated_items.append(item)
                    except ValidationError as e:
                        # Item validation failed, log and skip this item
                        self._logger.warning(f"{e}")
                
                # Update with validated items
                validated_update[field_name] = validated_items
                
                # If the list is empty and there's a default, use the default
                if not validated_items and "default" in field_schema:
                    validated_update[field_name] = field_schema["default"]
                    self._logger.debug(f"Using default value for {dbName}.{field_name} after all items failed validation")
        
        return validated_update
    
    def _getNestedValue(self, data, path):
        """
        Get a value from a nested dictionary using a dot-separated path.
        
        Args:
            data: The dictionary to get the value from
            path: The path to the value, using dot notation for nested fields
            
        Returns:
            The value at the specified path, or None if not found
        """
        if not path:
            return None
            
        # Split the path into parts
        parts = path.split('.')
        
        # Start with the root data
        current = data
        
        # Traverse the path
        for part in parts:
            # Check if current is a dictionary and contains the part
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                # Path not found
                return None
                
        return current
    
    def _setNestedValue(self, data, path, value):
        """
        Set a value in a nested dictionary using a dot-separated path.
        
        Args:
            data: The dictionary to set the value in
            path: The path to the value, using dot notation for nested fields
            value: The value to set
            
        Returns:
            None
        """
        if not path:
            return
            
        # Split the path into parts
        parts = path.split('.')
        
        # Start with the root data
        current = data
        
        # Traverse the path, creating dictionaries as needed
        for i, part in enumerate(parts[:-1]):
            # If this part doesn't exist, create a new dictionary
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            
            # Move to the next level
            current = current[part]
            
        # Set the value at the final part
        current[parts[-1]] = value

    def _validateType(self, dbName, key, value, cfg):
        """
        Validate and convert the type of a value if necessary.
        
        This method checks if a value matches one of the allowed types for a field.
        If not, it attempts to convert the value to one of the allowed types.
        
        Args:
            dbName: Name of the database
            key: Key within the database
            value: Value to validate and potentially convert
            cfg: Configuration dictionary containing type information
            
        Returns:
            The validated or converted value
            
        Raises:
            ValidationError: If the value cannot be converted to any of the allowed types
        """
        # If key is not in config, return value as is
        if key not in cfg:
            return value
            
        # Get the list of allowed types
        allowed_types = cfg[key].get("type", [str])
        
        # If value is already of an allowed type, return it
        if type(value) in allowed_types:
            return value
            
        # Log the conversion attempt
        self._logger.debug(f"Attempting to convert {value} ({type(value).__name__}) to one of {[t.__name__ for t in allowed_types]}")
        
        # Attempt to convert to each allowed type
        for target_type in allowed_types:
            try:
                # Special handling for bool type (strings like "False" should convert to False)
                if target_type is bool and isinstance(value, str):
                    if value.lower() in ("false", "0", "no", "n", "f", ""):
                        converted_value = False
                    else:
                        converted_value = bool(value)
                else:
                    # Standard conversion
                    converted_value = target_type(value)
                    
                self._logger.debug(f"Successfully converted to {target_type.__name__}: {converted_value}")
                return converted_value
            except (ValueError, TypeError) as e:
                self._logger.debug(f"Conversion to {target_type.__name__} failed: {e}")
                continue
                
        # If we get here, conversion failed for all types
        # For float values, try a best-effort conversion to one of the allowed types
        if isinstance(value, float) and (int in allowed_types or str in allowed_types):
            self._logger.debug(f"Attempting best-effort conversion of float {value}")
            if int in allowed_types:
                # Convert to int if possible without losing too much precision
                if value.is_integer():
                    converted_value = int(value)
                    self._logger.debug(f"Converted float to int: {converted_value}")
                    return converted_value
            if str in allowed_types:
                # Convert to string as a fallback
                converted_value = str(value)
                self._logger.debug(f"Converted float to string: {converted_value}")
                return converted_value
                
        # If we get here, all conversion attempts failed
        error_context = f"{dbName}[{key}]" if key is not None else f"{dbName}"
        error_msg = f"{error_context}: {value} ({type(value).__name__}) could not be converted to any of {[t.__name__ for t in allowed_types]}"
        self._logger.warning(error_msg)
        raise ValidationError(error_msg)


    def _validateStatement(
        self, dbName, key, value, stmtType, cfg, failOn=None
    ):
        """
        Execute validation or update statements/callables on a value.
        
        This method handles both string-based expressions (for DSL compatibility)
        and callable functions/lambdas (for programmatic use).
        
        Args:
            dbName: Name of the database
            key: Key within the database, or None for database-level validation
            value: The value to validate or update
            stmtType: Type of statement ('validate' or 'onUpdate')
            cfg: Configuration dictionary containing the statements
            failOn: For validation, the value that indicates failure (typically False)
            
        Returns:
            The validated or updated value
            
        Raises:
            NoChangeToValue: If no validation/update is configured
            ValidationError: If validation fails
            UpdateError: If an update operation fails
        """
        # Get the appropriate configuration based on key
        if key is not None:
            if key in cfg:
                cfg = cfg[key]
            else:
                raise NoChangeToValue

        # Check if we have statements of the requested type
        if stmtType not in cfg:
            raise NoChangeToValue

        # Get the list of statements/callables
        statements = cfg[stmtType]
        
        # Store the value in the local database for string-based expressions
        self._localDB["_VAL_"] = value
        result = value

        # Format for error messages
        error_context = f"{dbName}[{key}]" if key is not None else f"{dbName}"

        # Process each statement/callable
        for i, statement in enumerate(statements):
            try:
                # Generate the statement key for string-based expressions
                stmt_key = (
                    f"{dbName}.{key}.{stmtType}{i}"
                    if key is not None
                    else f"{dbName}.{stmtType}{i}"
                )
                
                # Handle different types of statements
                if isinstance(statement, str):
                    # String-based expression (DSL compatibility)
                    self._logger.debug(f"Evaluating {stmtType} expression: {statement}")
                    result = self._dV.eval(stmt_key)
                elif callable(statement):
                    # Callable function/lambda (programmatic use)
                    self._logger.debug(f"Executing {stmtType} callable on value: {self._localDB['_VAL_']}")
                    # Ensure we're passing the correct value to the callable
                    result = statement(self._localDB["_VAL_"])
                else:
                    # This shouldn't happen if _registerStatement is working correctly
                    raise TypeError(f"Invalid statement type: {type(statement).__name__}")
                
                # For validation, check if the result indicates failure
                if failOn is not None:
                    # This is a validation statement
                    if result == failOn:
                        # Include the validation rule in the error message for better debugging
                        rule_description = statement if isinstance(statement, str) else "custom validation"
                        raise ValidationError(
                            f"{error_context}: {value} failed validation: {rule_description}"
                        )
                    # For validation, we keep the original value if validation passes
                    # The result of validation is just True/False, not the new value
                    result = self._localDB["_VAL_"]
                else:
                    # For updates, store the result for the next statement
                    self._localDB["_VAL_"] = result
                    
            except NoChangeToValue:
                # No validation/update configured, continue
                pass
            except ValidationError:
                # Re-raise validation errors
                raise
            except Exception as ex:
                # Wrap other exceptions in UpdateError
                stmt_desc = statement if isinstance(statement, str) else "callable"
                raise UpdateError(
                    f"{error_context}: {stmtType} failed using {stmt_desc} with _VAL_ = '{self._localDB['_VAL_']}': {ex}"
                )
        
        return result

    def validateUpdate(self, dbName, update):
        """
        Perform any configured validation activities.

        :param dbName: Name of the database to validate the update against
        :param update: The update that is being submitted to the database
        :raises: ValidationError
        :returns: new version of update if any validation activity required it
        """
        # Ensure we have a valid update dictionary
        if update is None:
            self._logger.warning(f"Received None update for {dbName}, using empty dict instead")
            return {}
            
        # Make a copy of the update to avoid modifying the original
        update = update.copy()

        # If no validset record then skip validation
        if dbName not in self._validset:
            return update

        cfg = self._validset[dbName]
        
        # SCHEMA VALIDATION STEP
        # Check if a schema is defined for this database
        if "_schema" in cfg:
            try:
                # Validate the update against the schema
                validated_update = self._validateSchema(dbName, update, cfg["_schema"])
                
                # Use the validated update
                if validated_update is not None:
                    update = validated_update
                else:
                    self._logger.warning(f"Schema validation failed for {dbName} with no default")
                    # Return empty update instead of None to avoid errors
                    return {}
            except Exception as ex:
                self._logger.error(f"Error during schema validation for {dbName}: {ex}")
                if self._debug:
                    raise
                # In non-debug mode, continue with the original update

        # DATABASE-LEVEL VALIDATION STEP
        # Check for full DB validation
        try:
            # Only perform database-level validation if there's a validate statement at the database level
            if "validate" in cfg:
                self._validateStatement(
                    dbName, None, update, "validate", cfg, False
                )
        except NoChangeToValue:
            pass
        except ValidationError as ex:
            if self._debug:
                raise
            # If validation fails, use default value
            self._logger.debug(ex)
            if "default" in cfg:
                update = cfg["default"]
            else:
                # If no default then reject entire update
                self._logger.debug(
                    f"Validation failed with no default for {dbName}"
                )
                return {}  # Return empty dict instead of None

        # FIELD-LEVEL VALIDATION STEP
        # Validate individual items
        for k, v in list(update.items()):
            try:
                # First perform type validation/conversion
                # This will convert values to the appropriate type if possible
                if k in cfg:
                    self._logger.debug(f"Validating type for {dbName}[{k}]: {v} (type: {type(v).__name__})")
                    converted_value = self._validateType(dbName, k, v, cfg)
                    
                    # Store the converted value back in the update dictionary
                    update[k] = converted_value
                    
                    # Then validate the converted value
                    self._logger.debug(f"Validating {k}: {converted_value} (converted from {v})")
                    validated_value = self._validateStatement(dbName, k, converted_value, "validate", cfg, False)
                    
                    # Store the validated value
                    update[k] = validated_value
                else:
                    # No validation configured for this key
                    self._logger.debug(f"No validation for {dbName}[{k}]")
            except NoChangeToValue:
                # No validation configured, keep original value
                self._logger.debug(f"No validation statement for {dbName}[{k}]")
                pass
            except ValidationError as ex:
                if self._debug:
                    raise
                # If validation fails, use default value
                self._logger.debug(f"Validation failed for {dbName}[{k}]: {ex}")
                if k in cfg and "default" in cfg[k]:
                    update[k] = cfg[k]["default"]
                    self._logger.debug(f"Using default value for {dbName}[{k}]: {update[k]}")
                else:
                    # If no default is specified, remove the key from the update
                    self._logger.debug(f"No default for {dbName}[{k}], removing from update")
                    del update[k]
                    
        # Check required fields (if defined in schema)
        if "_required_fields" in cfg:
            # Get the current state of the database
            current_db = self._dataset.get(dbName, {})
            # Merge the update with the current state to check if all required fields are present
            merged_db = {**current_db, **update}
            
            # Check each required field
            for required_field in cfg["_required_fields"]:
                # Check if the required field exists in the merged database
                field_exists = self._getNestedValue(merged_db, required_field) is not None
                if not field_exists:
                    if self._debug:
                        raise ValidationError(f"{dbName}: Required field '{required_field}' is missing")
                    self._logger.warning(f"{dbName}: Required field '{required_field}' is missing")
                    # If there's a default value for this field, use it
                    if required_field in cfg and "default" in cfg[required_field]:
                        # Set the default value in the update
                        self._setNestedValue(update, required_field, cfg[required_field]["default"])
                    else:
                        # No default value, reject the update
                        self._logger.debug(f"Required field '{required_field}' missing with no default")
                        return None

        # UPDATE STEP
        # Update Database
        try:
            update = self._validateStatement(
                dbName, None, update, "onUpdate", cfg
            )
        except NoChangeToValue:
            pass
        except ValidationError as ex:
            if self._debug:
                raise
            # If onUpdate fails, revert to original value in update
            self._logger.debug(ex)

        # Update individual items
        for k, v in update.items():
            try:
                update[k] = self._validateStatement(
                    dbName, k, v, "onUpdate", cfg
                )
            except NoChangeToValue:
                pass
            except ValidationError as ex:
                if self._debug:
                    raise
                # If onUpdate fails, revert to original value in update
                self._logger.debug(ex)

        # Pull in defaults for missing values
        for k, v in self._validset[dbName].items():
            if k not in update and "default" in v:
                update[k] = v["default"]

        return update

    def _cache(self, dbName, key):
        # Place stored values in cache to be processed during next update.

        if dbName not in self._cacheDB:
            self._cacheDB = {dbName: {}}

        self._cacheDB[dbName] = {**self._cacheDB[dbName], **key}

    def _clearCache(self):
        self._cacheDB = {}

    def add(self, dbName, db):
        """
        Add a new database to the dataset.

        :param dbName: Name of the database to add to the dataset
        :type dbName: str
        :param db: The dictionary to use to initialize the database
        :type db: dict
        :raises NameError: when attempting to add a database with a name that
            already exists
        """
        # Make sure we don't overwrite existing database.
        # Use update instead to modify existing database
        if dbName in self._dataset:
            raise NameError(f"{dbName} already exists in dataset")

        self.update(dbName, db)

    def _baseUpdate(self, dbName, update, merge):
        # Update database named dbName using the dictionary contained within update.

        # Copy update
        update = update.copy()
        
        # Keep track of changed fields for dependency tracking
        changed_fields = []
        field_paths = []  # Store the full field paths for notification

        # Track timestamp in dedicated member variable instead of in the update
        current_time = time.time() - self._startedAt
        if dbName not in self._timestamps:
            self._timestamps[dbName] = current_time
        else:
            self._timestamps[dbName] = current_time
            
        # Store old values for hash updates
        old_values = {}
        if dbName in self._dataset:
            for key in update:
                if key in self._dataset[dbName]:
                    old_values[key] = self._dataset[dbName][key]

        update = self.validateUpdate(dbName, update)

        self._logger.debug(f"Updating database '{dbName}' with {update}")
        print(f"DEBUG: Updating database '{dbName}' with {update}")

        if dbName not in self._dataset:
            self._checkForReserved(dbName)
            db = update
            # Initialize _prevDS with current values
            self._prevDS[dbName] = deque(maxlen=self._lookBack)
            self._prevDS[dbName].append(db)
            # All fields in a new database are considered changed
            for key in update.keys():
                changed_fields.append(key)
                field_paths.append(f"{dbName}['{key}']")
            self._logger.debug(f"New database: all fields considered changed: {changed_fields}")
        else:
            # Update prevDS with the current values that are about to get updated
            self._prevDS[dbName].append(
                {**self._prevDS[dbName][-1], **self._dataset[dbName]}
            )

            # Identify which fields are actually changing
            for key, value in update.items():
                if key not in self._dataset[dbName]:
                    self._logger.debug(f"New field '{key}': '{value}'")
                    changed_fields.append(key)
                    field_paths.append(f"{dbName}['{key}']")
                elif not self._values_equal(self._dataset[dbName][key], value):
                    self._logger.debug(f"Field '{key}' changed: '{self._dataset[dbName][key]}' -> '{value}'")
                    print(f"DEBUG: Field '{key}' changed from {self._dataset[dbName][key]} to {value}")
                    print(f"DEBUG: Types - old: {type(self._dataset[dbName][key])}, new: {type(value)}")
                    
                    changed_fields.append(key)
                    field_paths.append(f"{dbName}['{key}']")
                    
                    # Handle nested dictionaries - detect specific nested field changes
                    if isinstance(value, dict) and isinstance(self._dataset[dbName][key], dict):
                        print(f"DEBUG: Detecting nested changes in {key}")
                        self._detect_nested_changes(dbName, key, self._dataset[dbName][key], value, changed_fields, field_paths)
                else:
                    self._logger.debug(f"Field '{key}' unchanged: '{value}'")

            # Merge current db values with new values
            db = {**self._dataset[dbName], **update} if merge else update
        # Update the dataset with the new values
        self.__dict__[dbName] = db
        self._dataset[dbName] = db
        self._ringBuffer.append({dbName: update})
        
        # Update hash values efficiently using Zobrist hashing
        # This provides O(1) performance for incremental updates
        # Use all fields for hash calculation
        actual_update = update
        actual_old_values = old_values
        if actual_update:  # Only update hash if there are fields changed
            self._update_hash_zobrist(dbName, actual_update, actual_old_values)
        
        print(f"DEBUG: Changed fields: {changed_fields}")
        print(f"DEBUG: Field paths for notification: {field_paths}")
        
        # Notify field-level dependencies about specific changes
        for field_path in field_paths:
            self._logger.debug(f"Notifying field change: {field_path}")
            print(f"DEBUG: Notifying field change: {field_path}")
            variable_registry.notify_field_change(field_path)

        # If any cache values were for different databases, merge update them
        if len(self._cacheDB) > 0:
            cdb = {k: v for k, v in self._cacheDB.items() if k != dbName}
            self._clearCache()
            for k, v in cdb.items():
                self.update(k, v, merge=True)
    
    def _values_equal(self, value1, value2):
        """
        Compare two values with special handling for dictionaries.
        For dictionaries, does a deep comparison of values.
        
        Args:
            value1: First value to compare
            value2: Second value to compare
            
        Returns:
            True if values are equal, False otherwise
        """
        print(f"DEBUG: _values_equal comparing {value1} and {value2}")
        if type(value1) != type(value2):
            print(f"DEBUG: Different types: {type(value1)} != {type(value2)}")
            return False
            
        if isinstance(value1, dict) and isinstance(value2, dict):
            # If dictionaries have different keys, they're not equal
            if set(value1.keys()) != set(value2.keys()):
                print(f"DEBUG: Different keys: {set(value1.keys())} != {set(value2.keys())}")
                return False
                
            # Check each key-value pair recursively
            for key in value1:
                print(f"DEBUG: Comparing nested key '{key}': {value1[key]} vs {value2[key]}")
                if not self._values_equal(value1[key], value2[key]):
                    print(f"DEBUG: Nested values different for key '{key}'")
                    return False
            
            print(f"DEBUG: Dictionaries are equal")
            return True
        else:
            # For non-dictionary types, use normal equality
            result = value1 == value2
            print(f"DEBUG: Simple comparison result: {result}")
            return result

    def _detect_nested_changes(self, dbName, parent_key, old_dict, new_dict, changed_fields, field_paths):
        """
        Recursively detect changes in nested dictionaries and add field paths to changed_fields.
        
        Args:
            dbName: Name of the database
            parent_key: Key of the parent dictionary
            old_dict: Previous version of the dictionary
            new_dict: New version of the dictionary
            changed_fields: List to store changed field paths
            field_paths: List to store full field paths for notification
        """
        print(f"DEBUG: _detect_nested_changes for {parent_key}")
        print(f"DEBUG: old_dict = {old_dict}")
        print(f"DEBUG: new_dict = {new_dict}")
        
        # Check for keys in new_dict but not in old_dict
        for key in new_dict:
            # Build the proper field path for notifications
            field_path = f"{dbName}['{parent_key}']['{key}']"
            
            # Record the nested field
            nested_key = f"{parent_key}['{key}']"
                
            if key not in old_dict:
                self._logger.debug(f"New nested field '{nested_key}': '{new_dict[key]}'")
                print(f"DEBUG: New nested field '{nested_key}': '{new_dict[key]}'")
                changed_fields.append(nested_key)
                field_paths.append(field_path)
            elif old_dict[key] != new_dict[key]:
                self._logger.debug(f"Nested field '{nested_key}' changed: '{old_dict[key]}' -> '{new_dict[key]}'")
                print(f"DEBUG: Nested field '{nested_key}' changed: '{old_dict[key]}' -> '{new_dict[key]}'")
                changed_fields.append(nested_key)
                field_paths.append(field_path)
                
                # Recursive check for nested dictionaries
                if isinstance(new_dict[key], dict) and isinstance(old_dict[key], dict):
                    self._detect_nested_changes(dbName, f"{parent_key}['{key}']", old_dict[key], new_dict[key], changed_fields, field_paths)
                    
        # Check for keys in old_dict but not in new_dict
        for key in old_dict:
            if key not in new_dict:
                field_path = f"{dbName}['{parent_key}']['{key}']"
                nested_key = f"{parent_key}['{key}']"
                
                self._logger.debug(f"Removed nested field '{nested_key}'")
                print(f"DEBUG: Removed nested field '{nested_key}'")
                changed_fields.append(nested_key)
                field_paths.append(field_path)

    def _update(self, dbName, update, merge=True):
        # Initial update method used when _ringBuffer is not full

        self._baseUpdate(dbName, update, merge)

        # If the ringBuffer has become full switch to _updateFull from now on
        if len(self._ringBuffer) == self._ringBuffer.maxlen:
            self.update = self._updateFull

    def update(self, dbName, update, merge=True):
        """Update a database within the dataset.

        :param dbName: The name of the database to update
        :type dbName: str
        :param update: The content of the update
        :type update: dict
        :param merge: Update will be merged into database if True and will overwrite
            database if False
        :type merge: bool
        """
        pass

    def _updateFull(self, dbName, update, merge=True):
        # Adds updating of starting position when the ring buffer has become full

        # Add databases from oldest ringbuffer entry into dsStart if dsStart does not already contain them
        for db in self._ringBuffer[0]:
            if db not in self._dsStart:
                self._dsStart[db] = self._ringBuffer[0][db]

        # Merge values that already exist in dsStart
        for db in self._dsStart:
            if db in self._ringBuffer[0]:
                self._dsStart[db] = {
                    **self._dsStart[db],
                    **self._ringBuffer[0][db],
                }

        self._baseUpdate(dbName, update, merge)

    def history(self, dbName, back):
        """
        Return historical version of database.

        Returns the version of the database {back} versions from the current one
        If version does not exist, return the oldest version that does.

        :param dbName: The name of the database to retrieve
        :type dbName: str
        :param back: The number of versions back to retrieve
        :type back: int
        :returns: The version of database `dbName` that is `back` versions from
            the current version
        :rtype: dict

        ..Note:
            history(dbName, 0) is current state
            history(dbName, 1) is previous state
            history(dbName, `back`) The version of the dbName database that is `back`
                versions older than the current version

            If `back` is larger than the size of the history buffer, the oldest
            available version is used instead.

        ..example::
            # Return the value of 'temp' from the sys database two versions back.
            "history('sys', 2)['temp'] > 100"
        """
        if back == 0:
            return self._dataset[dbName]

        try:
            return self._prevDS[dbName][0 - abs(back)]
        except IndexError:
            return self._prevDS[dbName][-len(self._prevDS[dbName])]

    class _PrevData(dict):
        def __init__(self, *args, **kwargs):
            self.update(dict(*args, **kwargs))
            for k, v in self.items():
                self.__dict__[k] = v[-1]

    @property
    def prev(self):
        """
        Return previous dataset.

        Returns a dataset composed of the version of the databases that is one update behind the current versions.

        :returns: The previous dataset
        :type: `tinyDisplay.utility.dataset`

        ..example::
            # Return the previous value of 'title' from the 'db' database
            "prev.db['title']"
        """
        return self._PrevData(self._prevDS)
        
    def _init_zobrist_tables(self):
        """
        Initialize Zobrist hashing tables with random 128-bit values.
        Uses a fixed bit pattern for reproducibility.
        """
        # Use fixed values for complete determinism across instances
        base_bytes = bytes([i % 256 for i in range(16)])
        
        # Initialize table for database names
        self._db_name_table = {}
        
        # Initialize table for keys
        self._key_table = {}
        
        # Initialize table for primitive values (types and common values)
        self._type_table = {
            'int': self._hash_bytes(base_bytes, b'int'),
            'float': self._hash_bytes(base_bytes, b'float'),
            'str': self._hash_bytes(base_bytes, b'str'),
            'bool': self._hash_bytes(base_bytes, b'bool'),
            'dict': self._hash_bytes(base_bytes, b'dict'),
            'list': self._hash_bytes(base_bytes, b'list'),
            'tuple': self._hash_bytes(base_bytes, b'tuple'),
            'set': self._hash_bytes(base_bytes, b'set'),
            'None': self._hash_bytes(base_bytes, b'None'),
        }
        
        # Special values table for common values
        self._value_table = {
            # Boolean values
            True: self._hash_bytes(base_bytes, b'True'),
            False: self._hash_bytes(base_bytes, b'False'),
            # None value
            None: self._hash_bytes(base_bytes, b'None_val'),
            # Common numeric values
            0: self._hash_bytes(base_bytes, b'int_0'),
            1: self._hash_bytes(base_bytes, b'int_1'),
            -1: self._hash_bytes(base_bytes, b'int_-1'),
            # Empty collections
            "": self._hash_bytes(base_bytes, b'empty_str'),
            (): self._hash_bytes(base_bytes, b'empty_tuple'),
            frozenset(): self._hash_bytes(base_bytes, b'empty_frozenset'),
        }
        
    def _hash_bytes(self, base, salt):
        """
        Generate a deterministic 16-byte hash from a base and salt.
        
        Args:
            base: Base bytes to start with
            salt: Salt bytes to mix in
            
        Returns:
            A 16-byte hash value
        """
        import hashlib
        md5 = hashlib.md5(base + salt)
        return md5.digest()
    
    def _get_hash_for_value(self, value):
        """
        Get a zobrist hash for any value.
        
        Args:
            value: The value to hash
            
        Returns:
            A 128-bit hash as bytes
        """
        import hashlib
        import pickle
        import struct
        
        # Check if it's a common value in our table (only for hashable types)
        if isinstance(value, (bool, int, float, str, type(None), tuple, frozenset)):
            if value in self._value_table:
                return self._value_table[value]
        
        # Generate hash based on type
        value_type = type(value).__name__
        if value_type in self._type_table:
            type_hash = self._type_table[value_type]
        else:
            # Use a default hash for unknown types
            type_hash = self._type_table['None']
        
        # For strings, numbers, and other simple types, hash the value
        if isinstance(value, (str, int, float, bool, type(None))):
            # Create a hash of the actual value
            value_bytes = str(value).encode('utf-8')
            value_md5 = hashlib.md5(value_bytes).digest()
            
            # XOR the type hash with the value hash
            return bytes(a ^ b for a, b in zip(type_hash, value_md5))
        elif isinstance(value, (list, tuple)):
            # For lists and tuples, start with the type hash
            result = type_hash
            
            # XOR with hashes of all elements
            for i, item in enumerate(value):
                item_hash = self._get_hash_for_value(item)
                # XOR position with item hash to account for order
                pos_bytes = struct.pack("<Q", i % 1000)[:8] + b'\x00' * 8  # Convert position to bytes
                pos_item_hash = bytes(a ^ b for a, b in zip(pos_bytes, item_hash))
                result = bytes(a ^ b for a, b in zip(result, pos_item_hash))
            return result
        elif isinstance(value, dict):
            # For dictionaries, start with the type hash
            result = type_hash
            
            # Sort keys for deterministic hashing
            for key in sorted(value.keys()):
                # Get key hash
                if key not in self._key_table:
                    # Use deterministic method to generate key hash
                    key_bytes = str(key).encode('utf-8')
                    self._key_table[key] = self._hash_bytes(key_bytes, b'key')
                key_hash = self._key_table[key]
                
                # Get value hash
                value_hash = self._get_hash_for_value(value[key])
                
                # Combine key and value hash
                combined = bytes(a ^ b for a, b in zip(key_hash, value_hash))
                
                # XOR into result
                result = bytes(a ^ b for a, b in zip(result, combined))
            return result
        else:
            # For complex objects, use pickle and MD5
            try:
                pickled = pickle.dumps(value)
                value_md5 = hashlib.md5(pickled).digest()
                return bytes(a ^ b for a, b in zip(type_hash, value_md5))
            except:
                # Fallback for unpicklable objects
                return type_hash
    
    def _compute_hash_for_db(self, dbName):
        """
        Compute the full hash for a database from scratch using Zobrist hashing.
        
        This method calculates a deterministic hash for a database based on its content.
        The hash is calculated by XORing the hashes of all key-value pairs in the database.
        Timestamps and internal fields (starting with '_') are excluded from the hash calculation
        to ensure that only the actual data affects the hash value.
        
        This is an O(n) operation where n is the number of key-value pairs in the database.
        It's used when a hash doesn't exist or needs to be recalculated from scratch.
        
        Args:
            dbName: Name of the database to compute hash for
            
        Returns:
            The computed hash as bytes
            
        Raises:
            KeyError: If the database doesn't exist
        """
        # Check if database exists
        if dbName not in self._dataset:
            raise KeyError(f"Database '{dbName}' does not exist")
            
        # Initialize with database name hash
        if dbName not in self._db_name_table:
            self._db_name_table[dbName] = self._hash_bytes(dbName.encode('utf-8'), b'db_name')
        db_hash = self._db_name_table[dbName]
        
        # Get a sorted list of keys to ensure consistent order
        # This ensures hash consistency regardless of update order
        keys = sorted(self._dataset[dbName].keys())
        
        # For large datasets, we can optimize by processing keys in batches
        # This helps with memory usage and can be more efficient
        batch_size = 1000  # Process 1000 keys at a time
        
        # Process keys in batches
        for i in range(0, len(keys), batch_size):
            batch_keys = keys[i:i+batch_size]
            
            # XOR with all key-value pairs in this batch
            for key in batch_keys:
                # All fields are now valid for processing
                    
                try:
                    # Get or create hash for key
                    if key not in self._key_table:
                        # Use deterministic method to generate key hash
                        key_bytes = str(key).encode('utf-8')
                        self._key_table[key] = self._hash_bytes(key_bytes, b'key')
                    key_hash = self._key_table[key]
                    
                    # Get hash for value
                    value = self._dataset[dbName][key]
                    value_hash = self._get_hash_for_value(value)
                    
                    # Combine key and value hash
                    combined = bytes(a ^ b for a, b in zip(key_hash, value_hash))
                    
                    # XOR into result
                    db_hash = bytes(a ^ b for a, b in zip(db_hash, combined))
                except Exception as e:
                    self._logger.error(f"Error hashing key '{key}' in database '{dbName}': {e}")
                    # Continue with other keys rather than failing completely
                    continue
        
        return db_hash
        
    def _update_hash_zobrist(self, dbName, update, old_values=None):
        """
        Update hash values for the specified database using Zobrist hashing.
        This is an O(1) operation when only a few fields are updated.
        
        Args:
            dbName: Name of the database to update hash for
            update: Dictionary of updated values
            old_values: Dictionary of previous values (for incremental updates)
        """
        # Initialize hash storage if needed
        if not hasattr(self, '_hashes'):
            self._hashes = {}
        if not hasattr(self, '_db_name_table'):
            self._db_name_table = {}
        if not hasattr(self, '_key_table'):
            self._key_table = {}
        if not hasattr(self, '_dirty_dbs'):
            self._dirty_dbs = set()
            
        # Ensure we have a hash entry for the database name
        if dbName not in self._db_name_table:
            self._db_name_table[dbName] = self._hash_bytes(dbName.encode('utf-8'), b'db_name')
        
        # If this is the first time we're hashing this database, do a full hash
        if dbName not in self._hashes:
            # Initialize with database name hash
            db_hash = self._db_name_table[dbName]
            
            # XOR with all key-value pairs
            for key, value in self._dataset[dbName].items():
                # All fields are now valid for processing
                    
                # Get or create hash for key
                if key not in self._key_table:
                    # Use deterministic method to generate key hash
                    key_bytes = str(key).encode('utf-8')
                    self._key_table[key] = self._hash_bytes(key_bytes, b'key')
                key_hash = self._key_table[key]
                
                # Get hash for value
                value_hash = self._get_hash_for_value(value)
                
                # Combine key and value hash
                combined = bytes(a ^ b for a, b in zip(key_hash, value_hash))
                
                # XOR into result
                db_hash = bytes(a ^ b for a, b in zip(db_hash, combined))
            
            # Store the hash
            self._hashes[dbName] = db_hash
        else:
            # Incremental update: start with existing hash
            db_hash = self._hashes[dbName]
            
            # For each changed key, remove old value and add new value
            for key, new_value in update.items():
                # All fields are now valid for processing
                    
                # Get hash for key
                if key not in self._key_table:
                    self._key_table[key] = self._hash_bytes(str(key).encode('utf-8'), b'key')
                key_hash = self._key_table[key]
                
                # If we have the old value, remove its contribution
                if old_values and key in old_values:
                    old_value = old_values[key]
                    old_value_hash = self._get_hash_for_value(old_value)
                    old_combined = bytes(a ^ b for a, b in zip(key_hash, old_value_hash))
                    # XOR out the old value (XOR is its own inverse)
                    db_hash = bytes(a ^ b for a, b in zip(db_hash, old_combined))
                
                # Add new value's contribution
                new_value_hash = self._get_hash_for_value(new_value)
                new_combined = bytes(a ^ b for a, b in zip(key_hash, new_value_hash))
                db_hash = bytes(a ^ b for a, b in zip(db_hash, new_combined))
            
            # Store updated hash
            self._hashes[dbName] = db_hash
        
        # Also update the dataset hash if needed
        if '__dataset__' in self._hashes:
            self._dirty_dbs = getattr(self, '_dirty_dbs', set())
            self._dirty_dbs.add('__dataset__')
            # We'll recalculate the dataset hash when get_hash is called
    
    def get_hash(self, dbName=None, format='hex'):
        """
        Get the hash value for a database or the entire dataset using lazy evaluation.
        
        This method implements lazy evaluation for hash calculations - hashes are only
        computed when this method is called, not when data is updated. This ensures
        efficient operation for scenarios where many updates occur but hash values
        are rarely needed.
        
        For individual databases, the hash is only recalculated if the database has been
        modified since the last hash calculation. For the entire dataset, the hash is
        recalculated if any database has been modified.
        
        The hash calculation is deterministic - identical dataset states will always
        produce identical hash values, regardless of the update history.
        
        Args:
            dbName: Name of the database to get hash for. If None, get hash for the entire dataset.
            format: Format of the returned hash. Options are:
                   - 'hex': Hexadecimal string (default)
                   - 'bytes': Raw bytes
                   - 'base64': Base64 encoded string
            
        Returns:
            Hash in the requested format, or None if the database doesn't exist
            
        Raises:
            KeyError: If a specific database is requested but doesn't exist
            ValueError: If an invalid format is specified
        """
        try:
            # Initialize hash storage if needed
            if not hasattr(self, '_hashes'):
                self._hashes = {}
                self._db_name_table = {}
                self._key_table = {}
                self._dirty_dbs = set()
                # Mark all databases as dirty initially
                for db in self._dataset:
                    self._dirty_dbs.add(db)
            
            # Special case for entire dataset hash
            if dbName is None:
                dbName = '__dataset__'
                
                # Mark as dirty if any database is dirty
                if hasattr(self, '_dirty_dbs') and self._dirty_dbs:
                    self._dirty_dbs.add('__dataset__')
            elif dbName != '__dataset__' and dbName not in self._dataset:
                # Database doesn't exist
                self._logger.warning(f"Attempted to get hash for non-existent database '{dbName}'")
                return None
                
            # Check if we need to calculate the hash
            if dbName not in self._hashes or dbName in self._dirty_dbs:
                # Calculate hash
                if dbName == '__dataset__':
                    # Calculate hash for entire dataset
                    # Ensure all database hashes are up to date
                    for db in self._dataset:
                        if db in self._dirty_dbs or db not in self._hashes:
                            self._hashes[db] = self._compute_hash_for_db(db)
                    
                    # Clear dirty flags
                    if hasattr(self, '_dirty_dbs'):
                        self._dirty_dbs.clear()
                    
                    # Compute dataset hash by combining all database hashes
                    # Start with a deterministic seed hash
                    dataset_hash = self._hash_bytes(b'dataset_base', b'hash')
                    
                    # Get sorted list of database names for consistent order
                    db_names = sorted(self._dataset.keys())
                    
                    # XOR all database hashes in a consistent order
                    for db in db_names:
                        dataset_hash = bytes(a ^ b for a, b in zip(dataset_hash, self._hashes[db]))
                    
                    # Store the result
                    self._hashes['__dataset__'] = dataset_hash
                else:
                    # Calculate hash for specific database
                    self._hashes[dbName] = self._compute_hash_for_db(dbName)
                    
                    # Mark as clean
                    if hasattr(self, '_dirty_dbs'):
                        self._dirty_dbs.discard(dbName)
            
            # Return the hash in the requested format
            hash_bytes = self._hashes.get(dbName)
            if not hash_bytes:
                return None
                
            if format.lower() == 'hex':
                return hash_bytes.hex()
            elif format.lower() == 'bytes':
                return hash_bytes
            elif format.lower() == 'base64':
                import base64
                return base64.b64encode(hash_bytes).decode('ascii')
            else:
                raise ValueError(f"Invalid hash format: {format}. Valid options are 'hex', 'bytes', or 'base64'.")
            
            
        except Exception as e:
            self._logger.error(f"Error getting hash for database '{dbName}': {e}")
            # Re-raise KeyError for non-existent databases, but handle other exceptions gracefully
            if isinstance(e, KeyError):
                raise
            return None
    
    def compare_hash(self, other_dataset, dbName=None):
        """
        Compare the hash of this dataset with another dataset.
        
        This method compares the hash of this dataset (or a specific database within it)
        with the hash of another dataset. This is useful for checking if two datasets
        have identical content without having to compare all their values.
        
        Args:
            other_dataset: Another dataset instance to compare with
            dbName: Name of the database to compare. If None, compare the entire datasets.
            
        Returns:
            True if the hashes match, False otherwise
            
        Raises:
            KeyError: If a specific database is requested but doesn't exist in either dataset
        """
        if not isinstance(other_dataset, type(self)):
            raise TypeError(f"Expected dataset object, got {type(other_dataset).__name__}")
            
        # Get hashes in bytes format for efficient comparison
        this_hash = self.get_hash(dbName, format='bytes')
        other_hash = other_dataset.get_hash(dbName, format='bytes')
        
        # Compare hashes
        return this_hash == other_hash
    
    def verify_hash(self, expected_hash, dbName=None, format='hex'):
        """
        Verify that a database or the entire dataset matches an expected hash.
        
        This method is useful for integrity checking, to ensure that a dataset
        hasn't been modified or corrupted.
        
        Args:
            expected_hash: The expected hash value to compare against
            dbName: Name of the database to verify. If None, verify the entire dataset.
            format: Format of the expected_hash. Options are 'hex', 'bytes', or 'base64'.
            
        Returns:
            True if the hash matches the expected value, False otherwise
            
        Raises:
            KeyError: If a specific database is requested but doesn't exist
            ValueError: If an invalid format is specified
        """
        # Get the current hash in the same format as the expected hash
        current_hash = self.get_hash(dbName, format=format)
        
        # Compare with expected hash
        return current_hash == expected_hash
    
    def invalidate_hash(self, dbName=None):
        """
        Explicitly invalidate the hash for a database or the entire dataset.
        
        This method marks a database as 'dirty', forcing a hash recalculation
        the next time get_hash() is called. This is useful when you know the
        data has changed through external means that the dataset class isn't
        aware of.
        
        Args:
            dbName: Name of the database to invalidate. If None, invalidate all databases.
            
        Returns:
            None
        """
        # Initialize dirty database tracking if needed
        if not hasattr(self, '_dirty_dbs'):
            self._dirty_dbs = set()
            
        if dbName is None:
            # Invalidate all databases
            for db in self._dataset:
                self._dirty_dbs.add(db)
            # Also invalidate the dataset-level hash
            self._dirty_dbs.add('__dataset__')
        else:
            # Invalidate specific database
            self._dirty_dbs.add(dbName)
            # Also invalidate the dataset-level hash
            self._dirty_dbs.add('__dataset__')
    
    def get_timestamp(self, dbName):
        """
        Get the timestamp of the last update for a database.
        
        Args:
            dbName: Name of the database to get timestamp for
            
        Returns:
            Timestamp (seconds since dataset creation) or None if database doesn't exist
        """
        return self._timestamps.get(dbName)