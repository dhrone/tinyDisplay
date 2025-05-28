# -*- coding: utf-8 -*-
# Copyright (c) 2020 Ron Ritchey and contributors
# See License.rst for details

"""
Miscellaneous utility functions for tinyDisplay.
"""

from inspect import getfullargspec, getmro, isclass

def getArgDecendents(key_or_class):
    """
    Return arguments for a class including args from parent classes, or a filtering function.

    :param key_or_class: The class to search or a key to use for filtering
    :type key_or_class: class or str
    :returns: List of arguments or a filtering function
    :rtype: list or function
    """
    # If called with a class, return its arguments
    if isclass(key_or_class):
        args = []
        for i in getmro(key_or_class):
            for arg in getfullargspec(i)[0][1:]:
                if arg not in args:
                    args.append(arg)
        return args
    
    # If called with a string, return a filtering function (legacy mode)
    def inner(k):
        return k.startswith('d') and k != 'dev'
    return inner

def getNotDynamicDecendents(key_or_class):
    """
    Return a list of NOTDYNAMIC arguments for all descendent classes, or a filtering function.

    :param key_or_class: The class to search or a key to use for filtering 
    :type key_or_class: class or str
    :returns: List of arguments or a filtering function
    :rtype: list or function
    """
    # If called with a class, return its NOTDYNAMIC arguments
    if isclass(key_or_class):
        args = []
        for i in getmro(key_or_class):
            if hasattr(i, "NOTDYNAMIC"):
                for arg in i.NOTDYNAMIC:
                    args.append(arg)
        return args
    
    # If called with a string, return a filtering function (legacy mode)
    def inner(k):
        return not k.startswith('d') or k == 'dev'
    return inner 