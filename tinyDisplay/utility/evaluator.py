# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Evaluator utility for tinyDisplay - provides dynamic value evaluation.
"""

import builtins
import logging
import math
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
        :rtype: `tinyDisplay.utility.evaluator.dynamicValue`
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
        
        # Process all statements in one loop
        for dv in statements:
            try:
                dv.eval()
                # Direct attribute access instead of property for better performance
                if hasattr(dv, "_changed") and dv._changed:
                    changed = True
            except Exception:
                # Silently continue on error - matches widget._evalAll behavior
                continue
                
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
        self._dataset = dataset 
        self._localDataset = localDataset if localDataset is not None else {}
        self._debug = debug

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
        # Use ChainMap instead of merging dictionaries
        d = ChainMap(self._localDataset, self._dataset)

        if self.func is not None:
            if not self.static or not hasattr(self, "prevValue"):
                try:
                    ans = self.func(d)
                except NoChangeToValue:
                    raise
                except (KeyError, TypeError, AttributeError) as ex:
                    if self._debug:
                        errMsg = (
                            f"While evaluating {self.name} with '{self.source}'"
                            if self.name is not None
                            else f"While evaluating '{self.source}'"
                        )
                        raise EvaluationError(
                            f"{errMsg} a {ex.__class__.__name__} error occured: {' '.join(ex.args)}"
                        )
                    ans = self.default
                except Exception as ex:
                    errMsg = (
                        f"While evaluating {self.name} with '{self.source}'"
                        if self.name is not None
                        else f"While evaluating '{self.source}'"
                    )
                    raise EvaluationError(
                        f"{errMsg} a {ex.__class__.__name__} error occured: {' '.join(ex.args)}"
                    )
            else:
                ans = self.prevValue
        else:
            ans = self.source

        # Streamlined change detection
        if not hasattr(self, "prevValue"):
            # First evaluation, always consider it changed
            self._changed = True
        elif ans is self.prevValue:
            # Fast path: Same object identity means no change
            self._changed = False
        elif type(ans) != type(self.prevValue):
            # Different types means change
            self._changed = True
        else:
            # Safe comparison with same types
            try:
                self._changed = ans != self.prevValue
            except:
                # For truly incomparable objects
                self._changed = True

        if self._changed and self.validator is not None:
            if not self.validator(ans):
                errMsg = (
                    f"While evaluating {self.name} with '{self.source}'"
                    if self.name is not None
                    else f"While evaluating '{self.source}'"
                )
                raise ValidationError(f"{errMsg}: {ans} is not a valid result")

        self.prevValue = ans
        return ans

    @property
    def changed(self):
        """
        Check if the evaluator statement named `key` has recently changed.

        :returns: True if the value of the statement changed during the last
            evaluation of it.
        """
        # Direct dictionary access is faster than hasattr
        return self.__dict__.get("_changed", False) 