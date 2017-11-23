"""
Tests for coroutines, for Python versions that support them.
"""

import sys
if sys.version_info[:2] >= (3, 5):
    from .corotests import CoroutineTests, ContextTests


__all__ = ["CoroutineTests", "ContextTests"]
