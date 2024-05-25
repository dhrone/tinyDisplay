# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Utility functions to support tinyDisplay.

.. versionadded:: 0.0.1
"""
import builtins
import logging
import math
import os
import time
import warnings
from collections import deque
from inspect import getfullargspec, getmro
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Thread

from PIL import ImageColor
from simple_pid import PID

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


# from IPython.core.debugger import set_trace


class animate(Thread):
    """
    Animate function.

    Create a thread to call a function at a specified number of calls per second (CPS)
    placing the results in a queue for consumption

    :param function: the function (or method) that will be called
    :type function: function or method
    :param cps: Calls per second.  The rate to call the provided function
    :type cps: int
    :param queueSize: The size of the queue used to record return results from function
    :type queueSize: int
    :param args:  The arguments to pass to the function
    :type args: tuple
    :param kwargs:  The keyworded arguments to pass to the function
    :type kwargs: dict

    To begin animation, call the start method.  Example::
        a = animate(function=func, cps=10)
        a.start

    ..note:
        The animate function uses a queue to pass results back.  This allows for the
        results to be consumed asynchronous.  If the queue fills up though,
        the function will no longer be called until space opens up in the queue.
    """

    def __init__(self, function=None, cps=1, queueSize=100, *args, **kwargs):
        Thread.__init__(self)
        assert function, "You must supply a function to animate"
        self._speed = cps

        Kp = 5
        Ki = 0.2
        Kd = 0.05
        self._pid = PID(
            Kp,
            Ki,
            Kd,
            setpoint=self._speed,
            sample_time=0.1,
            output_limits=(cps * 0.1, None),
        )

        self._function = function
        self._args = args
        self._kwargs = kwargs

        self.fps = 0
        self._running = True
        self._queue = Queue(maxsize=queueSize)
        self._event = Event()
        self._forceEvent = Event()

    @property
    def empty(self):
        """
        Return whether queue is empty.

        :returns: True of empty, False if not
        """
        return self._queue.empty()

    @property
    def full(self):
        """
        Return whether queue is full.

        :returns: True if full, False if not
        """
        return self._queue.full()

    @property
    def qsize(self):
        """
        Return estimate of queue size.

        :returns: Estimate of queue size
        """
        return self._queue.qsize()

    def pause(self):
        """Temporarily pause calling the function."""
        self._event.clear()

    def restart(self):
        """
        Restart Animation.

        Restart calling the function (if paused).  Otherwise this will have no effect.
        """
        self._event.set()

    def toggle(self):
        """Toggle calling the function from on to off or off to on."""
        if self._event.is_set():
            self._event.clear()
        else:
            self._event.set()

    def stop(self):
        """Shut down the animate object including terminating its internal thread."""
        self._running = False
        self._event.set()
        self.get()
        self.join()

    def clear(self):
        """Clear the queue of all curent values."""
        self._emptyQueue()

    def force(self, *args, **kwargs):
        """
        Change the parameters that are passed to the function.

        :param args: The positional arguments to provide to the animated function (optional)
        :type args: tuple
        :param kwargs: The keyword arguments to provide to teh animated function (optional)
        :type kwargs: dict

        ..note:
            force has the side effect of clearing any existing values within the queue.
        """
        self._Force = True

        # Set new arguments for animated function
        self._args = args
        self._kwargs = kwargs

        # If needed, unblock run if the queue if full
        try:
            self._queue.get_nowait()
            self._queue.task_done()
        except Empty:
            pass

        # Wait until animate confirms force is finished
        self._forceEvent.clear()
        self._forceEvent.wait()

    def get(self, wait=0):
        """
        Get the current value from the results queue.

        :param wait: Number of seconds to wait for a response.  If zero (the default)
            return immediately even if no value is currently available
        :type wait: float
        :returns: The current result.  Type of value is determined by what the
            animated function returns.
        :rtype: object

        ..note:
            Be careful with long wait values.  The animate thread will block during
            the wait.  If you attempt to shut down the animate object (using stop),
            it will not finish closing down until the wait has completed.
        """
        try:
            retval = self._queue.get(wait)
            self._queue.task_done()
        except Empty:
            retval = None

        return retval

    def _emptyQueue(self):
        while True:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Empty:
                break

    def _invoke(self, *args, **kwargs):
        # Invoke function
        if args and kwargs:
            retval = self._function(*args, **kwargs)
        elif args:
            retval = self._function(*args)
        elif kwargs:
            retval = self._function(**kwargs)
        else:
            retval = self._function()
        return retval

    def run(self):
        """
        Animate function.

        Main loop for the animate thread
        """
        correction = 0
        loopTime = 1 / self._speed
        tpf = 1 / self._speed

        renderTimer = time.time()
        renderCounter = 0
        renderCounterLimit = 1
        self._event.set()
        self._Force = False

        while self._running:

            # Compute current FPS every 5 seconds
            renderCounter += 1
            if renderCounter > renderCounterLimit:
                self.fps = renderCounter / (time.time() - renderTimer)
                renderCounter = 0
                renderCounterLimit = 10
                renderTimer = time.time()

            if not self._event.is_set():
                # Disable pid while waiting to be activated
                self._pid.set_auto_mode(False)
                self._event.wait()
                # Activated!  Re-enable PID, begin processing
                self._pid.set_auto_mode(True, last_output=correction)

            fps = 1 / loopTime  # Time per frame
            correction = self._pid(fps)
            startLoop = time.time()
            tpf = (
                1 / (self._speed + correction)
                if self._speed + correction > 0
                else 0
            )
            time.sleep(tpf)

            # Disable PID while trying to place new render in queue
            putStart = time.time()
            if self._Force:
                self._Force = False
                self._emptyQueue()

                # Must put value in queue before clearing the force Event
                # so that the forced function receives the newly computed value
                try:
                    retval = self._invoke(*self._args, **self._kwargs)
                    self._queue.put(retval)
                except NoResult:
                    pass

                self._forceEvent.set()
            else:
                try:
                    retval = self._invoke(*self._args, **self._kwargs)
                    try:
                        self._queue.put_nowait(retval)
                    except Full:
                        self._pid.set_auto_mode(False)
                        self._queue.put(retval)
                        self._pid.set_auto_mode(True, last_output=correction)
                except NoResult:
                    pass

            # Correct startLoop to account for time blocked by full queue
            startLoop = startLoop + (time.time() - putStart)

            loopTime = time.time() - startLoop


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

    def compile(
        self,
        source=None,
        name=None,
        default=None,
        validator=None,
        dynamic=True,
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
        :returns: a new dynamicValue
        :rtype: `tinyDisplay.utility.dynamicValue`
        """
        # create dynamic value
        # compile dynamic value
        # store dynamic value in _statements list
        ds = dynamicValue(
            name or id(source), self._dataset, self._localDataset, self._debug
        )
        ds.compile(source, default, validator, dynamic)
        self._statements[name or id(source)] = ds
        return ds

    def eval(self, name):
        """
        Evaluate dynamicValue with provide name.

        :param name: The name of the dynamicValue
        :type name: str
        :returns: the resulting value
        """
        if name in self._statements:
            return self._statements[name].eval()
        if id(name) in self._statements:
            return self._statements[id(name)].eval()
        raise KeyError(f"{name} not found in evaluator")

    def evalAll(self):
        """
        Evaluate all of the statements contained within the evaluator.

        :returns: True if any of the values have changed
        :rtype: bool
        """

        changed = False
        for dv in self._statements.values():
            dv.eval()
            if dv.changed:
                changed = True
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
        self._dV._statements[name].validator = func

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

        # If data was provided during initialization, update the state of the dataset with it
        if dataset:
            for k in dataset:
                self.update(k, dataset[k])

        self._debug = globalVars.__DEBUG__
        self._localDB = {"_VAL_": None}
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

        # Add timestamp to update
        update["__timestamp__"] = time.time() - self._startedAt

        update = self.validateUpdate(dbName, update)

        if dbName not in self._dataset:
            self._checkForReserved(dbName)
            db = update
            # Initialize _prevDS with current values
            self._prevDS[dbName] = deque(maxlen=self._lookBack)
            self._prevDS[dbName].append(db)
        else:
            # Update prevDS with the current values that are about to get updated
            self._prevDS[dbName].append(
                {**self._prevDS[dbName][-1], **self._dataset[dbName]}
            )

            # Merge current db values with new values
            db = {**self._dataset[dbName], **update} if merge else update

        # Update d with any cached values
        db = {**db, **self._cacheDB[dbName]} if dbName in self._cacheDB else db

        self.__dict__[dbName] = db
        self._dataset[dbName] = db
        self._ringBuffer.append({dbName: update})

        # If any cache values were for different databases, merge update them
        if len(self._cacheDB) > 0:
            cdb = {k: v for k, v in self._cacheDB.items() if k != dbName}
            self._clearCache()
            for k, v in cdb.items():
                self.update(k, v, merge=True)

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

    # TODO: add persistence methods
    """
    def save(self, filename):
        with open(filename, 'w') as fn:
            fn.write(f'# STARTED AT: {self._startedAt}\n{json.dumps(self._dsStart)}\n')
            fn.write('\n# UPDATES\n')
            for item in self._ringBuffer:
                fn.write(json.dumps(item))
                fn.write('\n')
    """

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


Dataset = dataset  # Rename class due to parameter convlict in dynamicValue


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

    ..note:
        Debug mode will cause any evaluation failures to result in
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
    _allowedBuiltIns["Path"] = Path

    _allowedMethods = [
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
        "items",
        "monotonic",
    ]

    def __init__(
        self, name=None, dataset=None, localDataset=None, debug=False
    ):

        self.name = name
        self._dataset = dataset if dataset is not None else Dataset({})
        self._localDataset = localDataset if localDataset is not None else {}
        self._debug = debug

        self._logger = logging.getLogger("tinyDisplay")

        # Used to support methods that will be called by eval but need to be
        # able to distinguish which object is calling it (e.g. changed)
        self._holdForIsChanged = {}
        self._changeID = id(self)

        # Defines allowable functions for compiled statements
        self._allowedBuiltIns["changed"] = self._isChanged
        self._allowedBuiltIns["history"] = self._dataset.history
        self._allowedBuiltIns["store"] = self.store

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

    def compile(self, source=None, default=None, validator=None, dynamic=True):
        """
        Compile provided input.

        :param source: The value to convert into compiled code
        :type source: str or `callable`
        :param default: A value to use if an evaluation of this code fails
            (optional)
        :param validator: A function to call to validate the answer when
            the code gets evaluated (optional)
        :param dynamic: Enables dynamic evaluation
        :type dynamic: bool
        :raises CompileError: if input includes unauthorized functions
            or references data that is not within the dataset

        ..note:
            Compilation is limited to the set of authorized functions and the
            variables contained within the available datasets.  You will raise
            a NameError if you use any other terms.  So, make sure that your
            dataset has a database for any variable you need to reference.

            example::
                Assuming a dataset with a database named 'db' containing
                    {'value': False}

                "db['value'] == True" will compile fine and eval fine
                "db['xyz'] == True" will compile fine but not eval successfully
                "bad['value'] == True" will not compile
                "bad == True" will not compile
                "db['value'] == bad" will not compile
        """

        self.source = source
        self.default = default
        self.validator = validator
        self.dynamic = dynamic

        name = self.name if self.name is not None else id(source)

        # If code is string then compile the string, otherwise return code unchanged
        # as it can also be either be a static value or a function
        self.func = None
        if dynamic is True:
            if type(source) is str:
                warnings.simplefilter("error")
                try:
                    code = compile(source, "<string>", "eval")
                    for n in code.co_names:
                        if (
                            n not in self._allowedBuiltIns
                            and n not in self._allowedMethods
                            and n not in self._dataset
                            and n not in self._localDataset
                        ):
                            raise CompileError(
                                f"While compiling {name} with '{source}': '{n}' is not defined"
                            )

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
        (Eval)uate the function and return resulting value.

        :returns: The results of the eval.  It can be any valid python object.
        :rtype: object
        :raises NoChangeToValue: If needed to signal that this evaluation is
            not intended to produce a new value (used by store function)
        :raises ValidationError: If the evaluated value failes its validation test
        """

        d = {**self._dataset, **self._localDataset}

        if self.func is not None:
            errMsg = (
                f"While evaluating {self.name} with '{self.source}'"
                if self.name is not None
                else f"While evaluating '{self.source}'"
            )

            if not self.static or not hasattr(self, "prevValue"):
                try:
                    ans = self.func(d)
                except NoChangeToValue:
                    raise
                except (KeyError, TypeError, AttributeError) as ex:
                    if self._debug:
                        raise EvaluationError(
                            f"{errMsg} a {ex.__class__.__name__} error occured: {' '.join(ex.args)}"
                        )
                    ans = self.default
                except Exception as ex:
                    raise EvaluationError(
                        f"{errMsg} a {ex.__class__.__name__} error occured: {' '.join(ex.args)}"
                    )
            else:
                ans = self.prevValue
        else:
            ans = self.source

        try:
            self._changed = (
                False
                if hasattr(self, "prevValue") and self.prevValue == ans
                else True
            )
        # If objects are not comparible
        except:
            self._changed = True

        if self.validator is not None:
            if not self.validator(ans):
                raise ValidationError(
                    f"While evaluating {self.name} with '{self.source}': {ans} is not a valid result"
                )

        self.prevValue = ans
        return ans

    @property
    def changed(self):
        """
        Check if the evaluator statement named `key` has recently changed.

        :returns: True if the value of the statement changed during the last
            evaluation of it.
        """
        return self._changed if hasattr(self, "_changed") else False


def image2Text(img, background="black"):
    """
    Convert PIL.Image to a character representation.

    :param img: The image to convert
    :type img: `PIL.Image`
    :param background: The background color for the image
    :type background: str, int or tuple
    :returns: A printable string that renders the provided image as text
    :rtype: str
    """
    if type(background) is str:
        background = ImageColor.getcolor(background, img.mode)

    # If present, strip alpha channel
    if type(background) is not int and len(background) in [2, 4]:
        background = background[0:-1]

    retval = "-" * (img.size[0] + 2)
    for j in range(img.size[1]):
        s = ""
        for i in range(img.size[0]):
            pixel = img.getpixel((i, j))
            if type(pixel) is not int and len(pixel) in [2, 4]:
                v = " " if pixel[0:-1] == background else "*"
            else:
                v = " " if pixel == background else "*"
            s += v
        retval += f"\n|{s[0:img.size[0]]}|"
    retval += "\n" + ("-" * (img.size[0] + 2))
    return retval


def compareImage(i1, i2, debug=False):
    """
    Compare if two images are the same or different.

    :param i1: First image to compare
    :type i1: `PIL.Image`
    :param i2: Second image to compare
    :type i2: `PIL.Image`
    :returns: True if they are identical
    :param debug: If true prints the location of the first failed match to stdout
    :type debug: bool
    """

    if i1.size != i2.size:
        if debug:
            print(f"Images are different sizes: {i1.size}, {i2.size}")
        return False
    if i1.mode != i2.mode:
        if debug:
            print(f"Images are different modes: {i1.mode}, {i2.mode}")
        return False
    for j in range(i1.size[1]):
        for i in range(i1.size[0]):
            if i1.getpixel((i, j)) != i2.getpixel((i, j)):
                if i1.mode in ["L", "RGBA"]:
                    if (
                        i1.getpixel((i, j))[-1] == 0
                        and i2.getpixel((i, j))[-1] == 0
                    ):
                        continue
                if debug:
                    print(
                        f"Match failed at ({i}, {j}) i1 = {i1.getpixel((i, j))}, i2 = {i2.getpixel((i, j))}"
                    )
                return False
    return True


def okPath(dirs, path):
    """
    Determine if the path is safe.

    :param dirs: A list of safe paths
    :type dirs: list
    :param path: The path to be tested
    :type path: str
    :returns: True if safe
    :rtype: bool
    """
    for d in dirs:
        if os.path.commonpath((os.path.realpath(path), d)) == d:
            return True
    return False


def getArgDecendents(c):
    """
    Retrieve arguments for a class including args from parent classes.

    :param c: The class to search
    :type c: `class`
    :returns: A list of arguments
    """
    args = []
    for i in getmro(c):
        for arg in getfullargspec(i)[0][1:]:
            if arg not in args:
                args.append(arg)
    return args


def getNotDynamicDecendents(c):
    """
    Retrieve all of the NOTDYNAMIC arguments for all descendent classes.

    :param c: The class to search
    :type c: `class`
    :returns: A list of arguments
    """
    args = []
    for i in getmro(c):
        if "NOTDYNAMIC" in dir(i):
            for arg in i.NOTDYNAMIC:
                args.append(arg)
    return args
