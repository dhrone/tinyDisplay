#!/usr/bin/env python3
"""Fallback setup.py for compatibility with older build systems.

This file provides compatibility for systems that don't support pyproject.toml.
The primary configuration is in pyproject.toml.
"""

from setuptools import setup

if __name__ == "__main__":
    setup() 