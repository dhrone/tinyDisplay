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
        if type(t) is type:
            return t
        if type(t) is str:
            try:
                return {
                    "int": int,
                    "float": float,
                    "complex": complex,
                    "str": str,
                    "bool": bool,
                    "dict": dict,
                    "list": list,
                    "range": range,
                    "set": set,
                    "none": type(None),
                    type(None): type(None),
                }[t.lower()]
            except KeyError:
                raise TypeError(f"{t} is not a valid type")
        raise TypeError(f"{type(t)} is not a valid type")

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

    def _registerType(self, type, default, sample, cfg):
        default = default if default is not None else cfg.get("default")
        sample = sample if sample is not None else cfg.get("sample")

        if type is not None:
            if builtins.type(type) is str:
                vtl = []
                for vt in type.split(","):
                    vtl.append(self._getType(vt.strip()))
                cfg["type"] = vtl
            else:
                # If input is not a string, see if it is a valid type
                cfg["type"] = [self._getType(type)]
        elif "type" in cfg:
            return
        elif default is not None:
            cfg["type"] = [builtins.type(default)]
        elif sample is not None:
            cfg["type"] = [builtins.type(sample)]
        else:
            # If no value was provide or can be inferred, use str as default
            cfg["type"] = [str]

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
        # Register validation statement for variable (onUpdate, validate).

        if stmt is not None:
            stmt = [stmt] if type(stmt) is not list else stmt
            cfg[stmtType] = stmt

            for i, u in enumerate(stmt):
                dvKey = (
                    f"{dbName}.{key}.{stmtType}{i}"
                    if key is not None
                    else f"{dbName}.{stmtType}{i}"
                )
                self._dV.compile(u, name=dvKey, default=None)

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

        :param dbName:  The name of the database
        :type dbName: str
        :param key: The value of the key (optional).  If not provided, the
            validation data will be for the whole database
        :type key: str
        :param type: Sets the variable type for the data element.  If type is
            provided for a key, when new data arrives it will be type
            checked using this value.  If it fails, an attempt will be made
            to convert it to the correct value.
        :type type: A str containing a valid type from the set {'int', 'float',
            'complex', 'str', 'bool', 'dict', 'list', 'range', 'set', 'None'}
        :param onUpdate: An evaluatable statement (or list of statements) that
            can take actions on received data including storing new values in
            any database contained within the dataset
        :type onUpdate: str or [str,]
        :param default: The default value for the data element.  This is used
            during initialization and whenever the element is missing from an
            update or if there is a ValidationError from an update
        :param sample: A sample value for the data element.  Specifying sample
            values is helpful for testing.  The `setDemo` method will update
            the dataset with any configued sample values.
        :param validate: An evaluatable statement (or list of statements) that
            can test whether a new value for the data element is correct.  Each
            statement MUST return either True for valid and False for invalid.
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

    def _validateType(self, dbName, key, value, cfg):
        # Validate type of element converting if necessary and possible.

        if key in cfg:
            tl = cfg[key].get("type", [str])
            if type(value) not in tl:
                # Attempt to convert to valid type
                for t in tl:
                    try:
                        value = t(value)
                    except (ValueError, TypeError):
                        continue
            if type(value) not in tl:
                errDK = f"{dbName}[{key}]" if key is not None else f"{dbName}"
                raise ValidationError(
                    f"{errDK}: {value} failed validation: {type(value)} not in {tl}"
                )
            return value
        else:
            return value

    def _validateStatement(
        self, dbName, key, value, stmtType, cfg, failOn=None
    ):
        # Generic processing for validation methods

        if key is not None:
            if key in cfg:
                cfg = cfg[key]
            else:
                raise NoChangeToValue

        if stmtType not in cfg:
            raise NoChangeToValue

        actCFG = cfg[stmtType]

        self._localDB["_VAL_"] = value
        ans = value

        errDK = f"{dbName}[{key}]" if key is not None else f"{dbName}"

        ul = [f"{stmtType}{i}" for i in range(len(actCFG))]
        for i, ui in enumerate(ul):
            try:
                ue = actCFG[i]

                stmtKey = (
                    f"{dbName}.{key}.{ui}"
                    if key is not None
                    else f"{dbName}.{ui}"
                )

                ans = self._dV.eval(stmtKey)

                if failOn is not None:
                    if ans == failOn:
                        raise ValidationError(
                            f"{errDK}: {value} failed validation: {ue}"
                        )
                else:
                    self._localDB["_VAL_"] = ans
            except NoChangeToValue:
                pass
            except ValidationError:
                raise
            except Exception as ex:
                raise UpdateError(
                    f"{errDK}: {value} {stmtType} failed using \"{ue}\" with _VAL_ = '{self._localDB['_VAL_']}': {ex}"
                )

        return ans

    def validateUpdate(self, dbName, update):
        """
        Perform any configured validation activities.

        :param dbName: Name of the database to validate the update against
        :param update: The update that is being submitted to the database
        :raises: ValidationError
        :returns: new version of update if any validation activity required it
        """

        # If no validset record then skip validation
        if dbName not in self._validset:
            return update

        cfg = self._validset[dbName]

        # VALIDATE STEP
        # Check for full DB validation
        try:
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
                return

        # VALIDATE individual items
        for k, v in update.items():
            try:
                ans = self._validateType(dbName, k, v, cfg)
                self._validateStatement(dbName, k, v, "validate", cfg, False)
            except NoChangeToValue:
                pass
            except ValidationError as ex:
                if self._debug:
                    raise
                # If validation fails, use default value
                self._logger.debug(ex)
                ans = cfg[k].get("default", "")
            update[k] = ans

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

        # Update d with any cached values
        if dbName in self._cacheDB:
            for key, value in self._cacheDB[dbName].items():
                if key not in db or not self._values_equal(db[key], value):
                    self._logger.debug(f"Cached field '{key}' changed: {value}")
                    changed_fields.append(key)
                    field_paths.append(f"{dbName}['{key}']")
            db = {**db, **self._cacheDB[dbName]}

        self.__dict__[dbName] = db
        self._dataset[dbName] = db
        self._ringBuffer.append({dbName: update})
        
        # Update hash value for this database using Zobrist hashing
        self._update_hash_zobrist(dbName, update, old_values)

        # Notify dependent widgets about the data change (traditional way)
        dependency_registry.notify_data_change(dbName)
        
        self._logger.debug(f"Changed fields: {changed_fields}")
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

    def _update(self, dbName, update, merge=False):
        # Initial update method used when _ringBuffer is not full

        self._baseUpdate(dbName, update, merge)

        # If the ringBuffer has become full switch to _updateFull from now on
        if len(self._ringBuffer) == self._ringBuffer.maxlen:
            self.update = self._updateFull

    def update(self, dbName, update, merge=False):
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

    def _updateFull(self, dbName, update, merge=False):
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
    
    def _update_hash_zobrist(self, dbName, update, old_values=None):
        """
        Update hash values for the specified database using Zobrist hashing.
        This is an O(1) operation when only a few fields are updated.
        
        Args:
            dbName: Name of the database to update hash for
            update: Dictionary of updated values
            old_values: Dictionary of previous values (for incremental updates)
        """
        # Ensure we have a hash entry for the database name
        if dbName not in self._db_name_table:
            self._db_name_table[dbName] = self._hash_bytes(dbName.encode('utf-8'), b'db_name')
        
        # If this is the first time we're hashing this database, do a full hash
        if dbName not in self._hashes:
            # Initialize with database name hash
            db_hash = self._db_name_table[dbName]
            
            # XOR with all key-value pairs
            for key, value in self._dataset[dbName].items():
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
        
        # Also update the whole dataset hash if it exists
        if '__dataset__' in self._hashes:
            # Start with deterministic base hash
            dataset_hash = self._hash_bytes(b'dataset_base', b'hash')
            
            # XOR all database hashes
            for db in self._dataset:
                # Ensure we have a hash for this database
                if db not in self._hashes:
                    self._update_hash_zobrist(db, self._dataset[db])
                
                # XOR this database's hash into the result
                dataset_hash = bytes(a ^ b for a, b in zip(dataset_hash, self._hashes[db]))
            
            self._hashes['__dataset__'] = dataset_hash
    
    def get_hash(self, dbName=None):
        """
        Get the hash value for a database or the entire dataset.
        
        Args:
            dbName: Name of the database to get hash for. If None, get hash for entire dataset.
            
        Returns:
            Hexadecimal string representation of the hash
        """
        if dbName is not None:
            # Ensure hash is up to date
            if dbName not in self._hashes and dbName in self._dataset:
                self._update_hash_zobrist(dbName, self._dataset[dbName])
                
            # Convert bytes to hex string for user-friendly representation
            hash_bytes = self._hashes.get(dbName)
            return hash_bytes.hex() if hash_bytes else None
        else:
            # Calculate hash for entire dataset if not already done
            if '__dataset__' not in self._hashes:
                # Start with deterministic base hash
                dataset_hash = self._hash_bytes(b'dataset_base', b'hash')
                
                # XOR all database hashes
                for db in self._dataset:
                    # Ensure we have a hash for this database
                    if db not in self._hashes:
                        self._update_hash_zobrist(db, self._dataset[db])
                    
                    # XOR this database's hash into the result
                    dataset_hash = bytes(a ^ b for a, b in zip(dataset_hash, self._hashes[db]))
                
                self._hashes['__dataset__'] = dataset_hash
                
            # Convert bytes to hex string
            hash_bytes = self._hashes.get('__dataset__')
            return hash_bytes.hex() if hash_bytes else None
    
    def get_timestamp(self, dbName):
        """
        Get the timestamp of the last update for a database.
        
        Args:
            dbName: Name of the database to get timestamp for
            
        Returns:
            Timestamp (seconds since dataset creation) or None if database doesn't exist
        """
        return self._timestamps.get(dbName)