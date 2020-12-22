# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Utility functions to support tinyDisplay.

.. versionadded:: 0.0.1
"""

import builtins
import time
from collections import deque
from queue import Empty, Queue
from threading import Event, RLock, Thread

from simple_pid import PID


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
        self._speed = 1 / cps

        Kp = 1
        Ki = 0.1
        Kd = 0.05
        self._pid = PID(
            Kp, Ki, Kd, setpoint=self._speed, sample_time=self._speed
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
        if self._event.isSet():
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
        loopTime = self._speed

        renderTimer = time.time()
        renderCounter = 0
        self._event.set()
        self._Force = False

        while self._running:

            # Compute current FPS every 5 seconds
            renderCounter += 1
            if renderTimer + 5 < time.time():
                self.fps = renderCounter / 5
                renderCounter = 0
                renderTimer = time.time()

            # Disable pid while waiting to be activated
            self._pid.set_auto_mode(False)
            self._event.wait()

            # Activated!  Re-enable PID, begin processing
            self._pid.set_auto_mode(True, last_output=correction)
            correction = self._pid(loopTime)
            startLoop = time.time()
            if self._speed + correction > 0:
                time.sleep(self._speed + correction)

            # Disable PID while trying to place new render in queue
            self._pid.set_auto_mode(False)
            putStart = time.time()
            if self._Force:
                self._Force = False
                self._emptyQueue()

                # Must put value in queue before clearing the force Event
                # so that the forced function receives the newly computed value
                retval = self._invoke(*self._args, **self._kwargs)
                self._queue.put(retval)
                self._forceEvent.set()
            else:
                retval = self._invoke(*self._args, **self._kwargs)
                self._queue.put(retval)

            # Correct the loop timer if queue was blocked and restart the PID
            startLoop = startLoop + (time.time() - putStart)
            self._pid.set_auto_mode(True, last_output=correction)

            loopTime = time.time() - startLoop


class _evaluate:
    """
    Class to compile and evaluate values for a dataset.

    :param dataset: The dataset to be used when compiling and evaluating statements
    :type dataset: `tinyDisplay.utility.dataset`
    """

    __allowedBuiltIns = {
        "__import__": builtins.__import__,
        "abs": builtins.abs,
        "bin": builtins.bin,
        "bool": builtins.bool,
        "bytes": builtins.bytes,
        "chr": builtins.chr,
        "dict": builtins.dict,
        "float": builtins.float,
        "format": builtins.format,
        "hex": builtins.hex,
        "int": builtins.int,
        "len": builtins.len,
        "list": builtins.list,
        "max": builtins.max,
        "min": builtins.min,
        "oct": builtins.oct,
        "ord": builtins.ord,
        "round": builtins.round,
        "str": builtins.str,
        "sum": builtins.sum,
        "tuple": builtins.tuple,
        "time": time,
    }
    __allowedMethods = [
        "get",
        "lower",
        "upper",
        "capitalize",
        "title",
        "find",
        "strftime",
        "gmtime",
        "localtime",
        "timezone",
    ]

    def __init__(self, child):
        self._allowedBuiltIns = dict(self.__allowedBuiltIns)
        self._changed = {}
        self._allowedBuiltIns["changed"] = self._isChanged
        self._allowedBuiltIns["select"] = self._select
        self._allowedBuiltIns["history"] = child.history
        self._allowedMethods = list(self.__allowedMethods)

        self._child = child

        # Used to support methods that will be called by eval but need to be
        #    able to distinguish which object is calling it (e.g. changed)
        #    _evalLock protects usage of _currentCodeID if this code is used
        #    in a multithreaded application.
        self._currentCodeID = None
        self._evalLock = RLock()

    def _isChanged(self, value):
        ret = (
            False
            if self._currentCodeID not in self._changed
            else True
            if self._changed.get(self._currentCodeID) != value
            else False
        )
        self._changed[self._currentCodeID] = value
        return ret

    @staticmethod
    def _select(value, *args, **kwargs):
        if len(args) % 2 != 0:
            raise TypeError(
                "TypeError: {args} is not an even number of arguments which is required for select transformations"
            )
        for i in range(0, len(args), 1):
            if value == args[i]:
                return args[i + 1]
        return ""

    def compile(self, input, dataset=None, data=None):
        """
        Compile provided input.

        :param input: The value to convert into compiled code
        :type input: str
        :param dataset: The dataset that will be used when compiled code is evaluated
        :type dataset: `tinyDisplay.utility.dataset`
        :param dataset: A dataset that will be temporarily merged into the
            internal dataset during the compile
        :type dataset: `tinyDisplay.utility.dataset`
        :param data: A dict that will be temporarily merged with the internal
            dataset during the compile
        :type data: dict
        :returns: A tuple containing the compiled code and the input that was used
            to create it.
        :rtype: (code object, str)
        :raises RuntimeError: if both a dataset and a data argument are provided
        :raises NameError: if input includes unauthorized function or references
            a database that is not within the dataset

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
        if data and dataset:
            raise RuntimeError(
                "You can provide data or a dataset but not both"
            )

        dataset = dataset if dataset else data if data else {}
        code = compile(input, "<string>", "eval")
        for name in code.co_names:
            if (
                name not in self._allowedBuiltIns
                and name not in self._allowedMethods
                and name not in self._dataset
                and name not in dataset
                and name not in self._child
            ):
                raise NameError(
                    f"While compiling '{input}' discovered {name} which is not a valid function or variable"
                )
        return (code, input)

    def eval(
        self,
        f,
        dataset=None,
        data=None,
        suppressErrors=None,
        returnOnError=None,
    ):
        """
        (Eval)uate the function and return resulting value.

        :param f: The compiled code (or function) to execute
        :type f: Either a tuple containing compiled code and the string that was compiled
            or a function
        :param dataset: A dataset to be merged with the internal dataset during the
            processing of this eval
        :type dataset: `tinyDisplay.utility.dataset`
        :param data: A dict to be merged with the internal dataset during the
            processing of this eval
        :type data: dict
        :param suppressErrors: Determines whether KeyErrors and TypeErrors in the
            evaluation should be ignored.  If true, then returnOnError is returned
            when these two errors occur.
        :type suppressErrors: bool
        :param returnOnError: The value to return when a KeyError or TypeError
            occurs and suppressErrors is True.
        :type returnOnError: object
        :returns: The results of the eval.  It can be any valid python object
            (default is an empty string e.g. '')
        :rtype: object
        :raises RuntimeError: if both a dataset and a data argument are provided
        """
        if data is not None and dataset is not None:
            raise RuntimeError(
                "You can provide data or a dataset but not both"
            )
        dataset = (
            dataset
            if dataset is not None
            else data
            if data is not None
            else None
        )

        # Pull values from object if not included as arguments
        suppressErrors = suppressErrors or self._suppressErrors
        returnOnError = returnOnError or self._returnOnError

        d = {**self._dataset, **dataset} if dataset else self._dataset

        # If we've receive a tuple it was hopefully produced by _evaluate.compile
        f, s = f if type(f) == tuple else (f, None)

        # If we've received a compilation from _evaluate.compile, evaluate it and return the answer
        if f.__class__.__name__ == "code":
            retval = self._eval(
                f,
                d,
                s,
                suppressErrors=suppressErrors,
                returnOnError=returnOnError,
            )
            return retval
        # If we've received a method or function, execute it and return the answer
        elif f.__class__.__name__ in ["method", "function"]:
            return f(d)
        else:
            # If we've received anything else, it could be from a variable that is only optionally dynamic (e.g. evaluatable)
            # In this case, the value did not need to be calculated so return it back to the calling method
            return f

    def _eval(
        self, code, variables, input, suppressErrors=False, returnOnError=""
    ):

        # If suppressErrors set
        #  return returnOnError value when KeyError or TypeError is thrown.

        # This in effect causes widgets to be blank when there is an error in
        # the evaluated statement (such as a missing key in the dataset)

        # Need to protect evaluation due to shared self._currentCodeID possibility
        self._evalLock.acquire()
        self._currentCodeID = id(code)
        try:
            return eval(
                code, {"__builtins__": self._allowedBuiltIns}, variables
            )
        except KeyError as e:
            if suppressErrors:
                return returnOnError
            raise KeyError(f"KeyError: {e} while trying to evaluate {input}")
        except TypeError as e:
            if suppressErrors:
                return returnOnError
            raise TypeError(f"Type Error: {e} while trying to evalute {input}")
        except AttributeError as e:
            raise AttributeError(
                f"Attribute Error: {e} while trying to evalute {input}"
            )
        finally:
            self._evalLock.release()


class dataset(_evaluate):
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
        data=None,
        suppressErrors=False,
        returnOnError="",
        historySize=100,
        lookBack=10,
    ):

        if data is not None and dataset is not None:
            raise RuntimeError(
                "You must provide data or a dataset but not both"
            )

        dataset = data or dataset or {}
        for tk in (
            (False, i) if type(i) is not str else (True, i)
            for i in dataset.keys()
        ):
            if not tk[0]:
                raise ValueError(
                    f"All datasets within a database must use strings as names.  This dataset has a database named {tk[1]}"
                )

        self._suppressErrors = suppressErrors
        self._returnOnError = returnOnError

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

        # Initialize evaluate parent to evaluate statements for this dataset
        super().__init__(self)

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

    def _baseUpdate(self, dbName, update):
        # Update database named dbName using the dictionary contained within update.

        # Copy update
        update = dict(update)

        # Add timestamp to update
        update["__timestamp__"] = time.time() - self._startedAt

        if dbName not in self._dataset:
            self._checkForReserved(dbName)
            d = update
            # Initialize _prevDS with current values
            self._prevDS[dbName] = deque(maxlen=self._lookBack)
            self._prevDS[dbName].append(d)
        else:
            # Update prevDS with the current values that are about to get updated
            self._prevDS[dbName].append(
                {**self._prevDS[dbName][-1], **self._dataset[dbName]}
            )

            # Merge current db values with new values
            d = {**self._dataset[dbName], **update}

        self.__dict__[dbName] = d
        self._dataset[dbName] = d
        self._ringBuffer.append({dbName: update})

    def _update(self, dbName, update):
        # Initial update method used when _ringBuffer is not full

        self._baseUpdate(dbName, update)

        # If the ringBuffer has become full switch to _updateFull from now on
        if len(self._ringBuffer) == self._ringBuffer.maxlen:
            self.update = self._updateFull

    def _updateFull(self, dbName, update):
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

        self._baseUpdate(dbName, update)

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


def image2Text(img):
    """
    Convert PIL.Image to a character representation.

    :param img: The image to convert
    :type img: `PIL.Image`
    :returns: A printable string that renders the provided image as text
    :rtype: str
    """
    retval = "-" * (img.size[0] + 2)
    for j in range(img.size[1]):
        s = ""
        for i in list(img.crop((0, j, img.size[0], j + 1)).tobytes()):
            s += f"{i:>08b}".replace("0", " ").replace("1", "*")
        retval += f"\n|{s[0:img.size[0]]}|"
    retval += "\n" + ("-" * (img.size[0] + 2))
    return retval
